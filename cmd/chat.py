import os
import sys
import logging
from dotenv import load_dotenv
from rich.logging import RichHandler
from rich.console import Console
from together import Together
from langchain_openai import OpenAIEmbeddings

# autopep8: off # Add parent directory to path to allow absolute imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

from db import mongoatlas
from service.health_check import HealthChecker
from db import postgres
from service.prompt import build_messages, similarity_search_with_detailed_reranking,build_search_response, refine_search_results, build_bot_summary, similarity_search
from transformers import AutoTokenizer
# autopep8: on


MODEL_MAPPING = {
    "Qwen/Qwen2.5-72B-Instruct-Turbo": "Qwen/Qwen2.5-72B-Instruct",
    "meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo": "meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo",
    "deepseek-ai/DeepSeek-R1-Distill-Llama-70B": "deepseek-ai/DeepSeek-R1-Distill-Llama-70B",
    "deepseek-ai/deepseek-llm-67b-chat": "deepseek-ai/deepseek-llm-67b-chat",
    "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo": "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
    "meta-llama/Llama-3.2-3B-Instruct-Turbo": "meta-llama/Llama-3.2-3B-Instruct-Turbo",
    "Qwen/Qwen2.5-7B-Instruct-Turbo": "Qwen/Qwen2.5-7B-Instruct",
    "mistralai/Mixtral-8x7B-Instruct-v0.1": "mistralai/Mixtral-8x7B-Instruct-v0.1",
    "microsoft/WizardLM-2-8x22B": "microsoft/WizardLM-2-8x22B",
    "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo": "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
    "mistralai/Mixtral-8x22B-Instruct-v0.1": "mistralai/Mixtral-8x22B-Instruct-v0.1",
    "Qwen/Qwen2-72B-Instruct": "Qwen/Qwen2-72B-Instruct",
    "scb10x/scb10x-llama3-typhoon-v1-5x-4f316": "scb10x/scb10x-llama3-typhoon-v1-5x-4f316",
    "meta-llama/Meta-Llama-3-70B-Instruct-Lite": "meta-llama/Meta-Llama-3-70B-Instruct-Lite",
    "meta-llama/Llama-3-8b-chat-hf": "meta-llama/Llama-3-8b-chat-hf",
    "meta-llama/Llama-2-13b-chat-hf": "meta-llama/Llama-2-13b-chat-hf",
}


# Setup logging
load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(console=Console(width=200))]
)
logger = logging.getLogger(__name__)


def simulate_chat():
    # Initialize services
    embedding_model = "text-embedding-3-large"
    mongodb_conn_sr = os.environ.get("MONGODB_CONNECTION_STRING")
    postgres_conn_sr = os.environ.get("POSTGRES_CONNECTION_STRING")
    together = Together()

    # Initialize MongoDB
    embeddings = OpenAIEmbeddings(model=embedding_model)
    mongodb_helper = mongoatlas.MongoDBHelper(
        connection_str=mongodb_conn_sr,
        db_name="tipitaka-viet-db",
        vector_store_name="facts__text-embedding-3-large",
        secondary_vector_store_name="secondary-facts__text-embedding-3-large",
        vector_store_index=embedding_model,
    )
    vector_store = mongodb_helper.create_vector_store(
        embeddings, dimensions=3072, should_skip_creating_index=True
    )
    rerank_vs = mongodb_helper.create_secondary_vector_store(
        embeddings, dimensions=3072, should_skip_creating_index=True
    )

    # Initialize PostgreSQL
    pg_engine, _ = postgres.init_db(postgres_conn_sr)
    health_checker = HealthChecker(
        pg_engine=pg_engine,
        mongodb_client=mongodb_helper.client
    )

    # Check health
    try:
        health_checker.check_with_cache()
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return

    # Sample user message
    # user_message = "Tìm tích truyện vị thánh A la hán bị mù tìm đường về thăm đức Phật, kể tên vị ấy và cho biết tích truyện đó liên quan đến bài kinh nào\n\n"
    # user_message = "Có tích truyện trong kinh pháp cú nào kể về 500 người phụ nữ thọ bát quan trai giới không?"
    # user_message = "Hoàng hậu Mallikā và công chúa Mallikā có ai đắc quả thánh không?"
    # user_message = "Có câu chuyện nào liên quan đến trai nghèo có vợ đẹp không?"
    user_message = "Hi there"
    user_messages = [user_message]
    print("\n======= QUESTION =======")
    print(user_message)

    # Print search results
    print("\n======= SEARCH RESULTS =======")
    search_results = similarity_search( rerank_vs, user_messages, 15)
    for result in search_results:
        print(result)
    print("\n======= SEARCH RESULTS =======")
    refine_search_results(search_results)
    print(build_search_response(search_results, without_quote=False))
    print("\n======= SEARCH RESULTS =======")
    # print(build_system_prompt(search_results))

    # Select model and build messages
    model = "Qwen/Qwen2.5-72B-Instruct-Turbo"
    tokenizer = None
    try:
        tokenizer = AutoTokenizer.from_pretrained(
            MODEL_MAPPING[model], trust_remote_code=True)
    except Exception as e:
        logger.error(f"Failed to load tokenizer: {e}")

    messages, num_results, with_half_content = build_messages(
        tokenizer=tokenizer,
        query=[],
        user_messages=user_messages,
        search_results=search_results,
        override_max_tokens=32769 * 95 // 100
    )
    print("\n======= BOT SUMMARY=======")
    print(build_bot_summary(question=user_messages[-1].strip(), num_results=num_results, with_half_content=with_half_content, total_results=len(search_results)))
    print("\n======= BOT SUMMARY=======")

    print("\n\n")
    return
# Print search results
    print("\n======= SEARCH RESULTS =======")
    search_results = similarity_search_with_detailed_reranking(
        vector_store, rerank_vs, user_messages)
    refine_search_results(search_results)
    print(build_search_response(search_results))
    # print(build_system_prompt(search_results))

    # Select model and build messages
    model = "Qwen/Qwen2.5-72B-Instruct-Turbo"
    tokenizer = None
    try:
        tokenizer = AutoTokenizer.from_pretrained(
            MODEL_MAPPING[model], trust_remote_code=True)
    except Exception as e:
        logger.error(f"Failed to load tokenizer: {e}")

    messages, num_results, with_half_content = build_messages(
        tokenizer=tokenizer,
        query=[],
        user_messages=user_messages,
        search_results=search_results,
        override_max_tokens=32769 * 95 // 100
    )

    
    print(build_bot_summary(question=user_messages[-1].strip(), num_results=num_results, with_half_content=with_half_content, total_results=len(search_results)))
    return
    print(messages)
    print("\n\n")

    # Get response using Together AI
    bot_response = ""
    stream = together.chat.completions.create(
        model=model,
        temperature=0.4,
        messages=messages,
        stream=True
    )

    print("\n======= ASSISTANT =======")
    for chunk in stream:
        if chunk.choices:
            print(chunk.choices[0].delta.content or "", end="", flush=True)
            bot_response += chunk.choices[0].delta.content or ""


if __name__ == "__main__":
    simulate_chat()
