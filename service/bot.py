import logging
import random
from typing import Callable
from sqlalchemy.orm import Session
import fastapi_poe as fp
from together import Together
from langchain_mongodb import MongoDBAtlasVectorSearch
from db.postgres_models.conversation import Conversation
from db.postgres_models.reaction_feedback import Feedback
from transformers import AutoTokenizer

from .health_check import HealthChecker
from .prompt import build_messages, build_search_response, build_keyword_response, refine_search_results, SYSTEM_PROMPT, INTRODUCTION_MESSAGES, build_bot_summary, similarity_search, MESSAGE_TOO_SHORT, CONTEXT_LENGTH_EXCEEDED, HEALTH_CHECK_FAILED

logger = logging.getLogger(__name__)

OVERRIDE_MAX_TOKENS = 32769 * 95 // 100 - 2048


class TipitakaAI(fp.PoeBot):
    def init(
            self,
            bot_name: str,
            health_checker: HealthChecker,
            vector_store: MongoDBAtlasVectorSearch,
            secondary_vector_store: MongoDBAtlasVectorSearch,
            session_factory: Callable[[], Session]
    ) -> None:
        self.bot_name = bot_name
        self.together = Together()
        self.health_checker = health_checker
        self.vector_store = vector_store
        self.secondary_vector_store = secondary_vector_store
        self.session_factory = session_factory
        self.should_insert_attachment_messages = False

        self.tokenizer = AutoTokenizer.from_pretrained(
            "Qwen/Qwen2.5-72B-Instruct", trust_remote_code=True)

    async def get_settings(self, _: fp.SettingsRequest) -> fp.SettingsResponse:
        return fp.SettingsResponse(
            allow_attachments=False,
            introduction_message=random.choice(INTRODUCTION_MESSAGES)
        )

    async def on_feedback(self, feedback_request: fp.ReportFeedbackRequest) -> None:
        session: Session = self.session_factory()
        try:
            Feedback.upsert(
                session,
                message_id=feedback_request.message_id,
                user_id=feedback_request.user_id,
                conversation_id=feedback_request.conversation_id,
                feedback_type=feedback_request.feedback_type,
                request=feedback_request.model_dump()
            )
        except Exception as e:
            logger.error(f"Error updating feedback: {e}")
        finally:
            session.close()

    async def get_response(self, request: fp.QueryRequest):
        ######################################
        #### HEALTH CHECK ####################
        try:
            self.health_checker.check_with_cache()
        except Exception as e:
            yield fp.ErrorResponse(text=HEALTH_CHECK_FAILED)
            return

        ######################################
        #### PRINT SEARCH KEYWORDS ###########
        user_messages = []
        for query in request.query:
            if query.role == "user":
                user_messages.append(query.content.strip())
        user_messages = user_messages[-5:]  # Only keep the last 5 messages

        if len(user_messages[-1].strip().split()) < 10:
            yield fp.PartialResponse(text=MESSAGE_TOO_SHORT, is_replace_response=True)
            return # Early return if the last message is too short

        # Filter out messages with less than 10 words
        user_messages = [msg for msg in user_messages if len(
            msg.strip().split()) >= 10]
        keyword_response = build_keyword_response(user_messages)
        last_bot_response = keyword_response
        yield fp.PartialResponse(text=keyword_response)

        ######################################
        #### PRINT SEARCH RESULTS ############
        search_results = similarity_search(
            vector_store=self.secondary_vector_store,
            user_messages=user_messages,
            limit=20
        )
        refine_search_results(search_results)
        search_response = build_search_response(
            search_results, without_quote=False)
        last_bot_response += search_response
        yield fp.PartialResponse(text=search_response)

        ######################################
        #### BOT RESPONSE ####################
        messages, num_results, with_half_content = build_messages(
            self.tokenizer, request.query, user_messages, search_results, override_max_tokens=OVERRIDE_MAX_TOKENS)

        try:
            if messages is None:
                raise Exception("Context too long")

            bot_summary_msg = build_bot_summary(
                question=user_messages[-1].strip(),
                num_results=num_results,
                with_half_content=with_half_content,
                total_results=len(search_results)
            )
            last_bot_response += bot_summary_msg
            yield fp.PartialResponse(text=bot_summary_msg)

            stream = self.together.chat.completions.create(
                model="Qwen/Qwen2.5-72B-Instruct-Turbo",
                temperature=0.5,
                messages=messages,
                stream=True
            )

            for chunk in stream:
                if chunk.choices:
                    yield fp.PartialResponse(text=chunk.choices[0].delta.content or "")
                    last_bot_response += chunk.choices[0].delta.content or ""

        except Exception as e:
            last_bot_response += "\n" + CONTEXT_LENGTH_EXCEEDED
            yield fp.ErrorResponse(text=CONTEXT_LENGTH_EXCEEDED, allow_retry=False)
            logger.error(f"Error getting response: {e}")

        finally:
            conversation_id: str = request.conversation_id
            try:
                session: Session = self.session_factory()
                request.api_key = "<poe_api_key>"
                request.access_key = "<poe_access_key>"
                Conversation.upsert(
                    session,
                    conversation_id=conversation_id,
                    system_prompt=SYSTEM_PROMPT,
                    last_bot_response=last_bot_response,
                    request=request.model_dump(),
                    sender_id=request.user_id
                )
            except Exception as e:
                logger.error(
                    f"Error updating conversation {conversation_id}: {e}")
            finally:
                session.close()
