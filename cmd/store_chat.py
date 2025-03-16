import os
import logging
from dotenv import load_dotenv
from rich.logging import RichHandler
from rich.console import Console
import sys

# Add parent directory to path to allow absolute imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

from db import postgres
from db.postgres_models.conversation import Conversation

# Setup logging
load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(console=Console(width=200))]
)
logger = logging.getLogger(__name__)


def store_conversation(conversation_id: str, system_prompt: str, bot_response: str, request_data: dict, sender_id: str):
    """
    Store a conversation in the PostgreSQL database.
    """
    # Get PostgreSQL connection string from environment
    postgres_conn_sr = os.environ.get("POSTGRES_CONNECTION_STRING")
    if not postgres_conn_sr:
        raise ValueError(
            "POSTGRES_CONNECTION_STRING environment variable is not set")

    # Initialize PostgreSQL connection
    _, SessionLocal = postgres.init_db(postgres_conn_sr)
    session = SessionLocal()

    try:
        # Store conversation
        Conversation.upsert(
            session,
            conversation_id=conversation_id,
            system_prompt=system_prompt,
            last_bot_response=bot_response,
            request=request_data,
            sender_id=sender_id
        )
        logger.info(f"Successfully stored conversation {conversation_id}")
    except Exception as e:
        logger.error(f"Error storing conversation {conversation_id}: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    # Example usage
    sample_conversation = "Kí tự Unicode"

    try:
        store_conversation(
            conversation_id="conversation_id",
            system_prompt="system_prompt",
            bot_response="bot_response",
            request_data=sample_conversation,
            sender_id="sender_id"
        )
    except Exception as e:
        logger.error(f"Failed to store conversation: {e}")
