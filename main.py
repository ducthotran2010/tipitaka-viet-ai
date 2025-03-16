import logging
import os

import fastapi_poe as fp
from dotenv import load_dotenv
from rich.logging import RichHandler
from rich.console import Console
from langchain_openai import OpenAIEmbeddings

from db import mongoatlas, postgres
from service.api import app
from service.auth import APIKeyManager
from service.bot import TipitakaAI
from service.health_check import HealthChecker

if __name__ == "__main__":
    ###########################################
    ############## LOAD ENV & SETUP LOGGER ####
    load_dotenv()
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        handlers=[RichHandler(console=Console(width=200))]
    )
    logger = logging.getLogger(__name__)

    ###########################################
    ################### LOAD CONFIGURATION ####
    embedding_model = "text-embedding-3-large"
    bot_name = os.environ.get("BOT_NAME", "TipitakaViet")
    admin_key = os.environ.get("ADMIN_KEY")
    poe_access_key = os.environ.get("POE_ACCESS_KEY")
    logger.info(
        f"Config loaded: BOT_NAME={bot_name}, ADMIN_KEY={admin_key}, EMBEDDING_MODEL={embedding_model}, POE_ACCESS_KEY={poe_access_key}"
    )

    mongodb_conn_sr = os.environ.get("MONGODB_CONNECTION_STRING")
    mongodb_search_index_created = os.environ.get(
        "MONGODB_SEARCH_INDEX_CREATED", "FALSE"
    ).upper() == "TRUE"
    logger.info(
        f"MONGODB_CONNECTION_STRING={mongodb_conn_sr}, MONGODB_SEARCH_INDEX_CREATED={mongodb_search_index_created}"
    )

    postgres_conn_sr = os.environ.get("POSTGRES_CONNECTION_STRING")
    logger.info(f"POSTGRES_CONNECTION_STRING={postgres_conn_sr}")

    ###########################################
    ################## INITIALIZE SERVICES ####
    embeddings = OpenAIEmbeddings(model=embedding_model)
    mongodb_helper = mongoatlas.MongoDBHelper(
        connection_str=mongodb_conn_sr,
        db_name="tipitaka-viet-db",
        vector_store_name="facts__text-embedding-3-large",
        secondary_vector_store_name="secondary-facts__text-embedding-3-large",
        vector_store_index=embedding_model,
    )
    vector_store = mongodb_helper.create_vector_store(
        embeddings, mongodb_search_index_created, dimensions=3072
    )
    secondary_vector_store = mongodb_helper.create_secondary_vector_store(
        embeddings, mongodb_search_index_created, dimensions=3072
    )

    # Initialize PostgreSQL engine and session factory
    pg_engine, SessionLocal = postgres.init_db(postgres_conn_sr)
    api_key_manager = APIKeyManager(admin_key, SessionLocal)

    # Initialize HealthChecker with PostgreSQL engine and MongoDB client
    # Assumes MongoDBHelper exposes a MongoClient as "client"
    mongodb_client = mongodb_helper.client
    health_checker = HealthChecker(
        pg_engine=pg_engine, mongodb_client=mongodb_client)

    # Set services in app state
    app.set_vector_store(vector_store)
    app.set_secondary_vector_store(secondary_vector_store)
    app.set_api_key_manager(api_key_manager)
    app.set_health_checker(health_checker)
    app.list_routes()

    bot = TipitakaAI()
    bot.init(
        bot_name=bot_name,
        session_factory=SessionLocal,
        health_checker=health_checker,
        vector_store=vector_store,
        secondary_vector_store=secondary_vector_store,
    )
    fp.run(bot, app=app, access_key=poe_access_key)
