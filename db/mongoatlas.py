from pymongo import MongoClient
from typing import Optional
from langchain_mongodb import MongoDBAtlasVectorSearch
from langchain.embeddings.base import Embeddings
import asyncio
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class MongoDBHelper:
    def __init__(
            self,
            connection_str: str,
            db_name: str,
            vector_store_name: str,
            secondary_vector_store_name: str,
            vector_store_index: str,
    ):
        self.client = MongoClient(connection_str)
        self.db = self.client[db_name]
        self.vector_collection = self.db[vector_store_name]
        self.secondary_vector_collection = self.db[secondary_vector_store_name]
        self.vector_store_index = vector_store_index

    def create_vector_store(self, embedding: Embeddings, should_skip_creating_index: bool, dimensions: int) -> MongoDBAtlasVectorSearch:
        return create_vector_store_helper(
            self.vector_collection, self.vector_store_index, embedding, should_skip_creating_index, dimensions)

    def create_secondary_vector_store(self, embedding: Embeddings, should_skip_creating_index: bool, dimensions: int) -> MongoDBAtlasVectorSearch:
        return create_vector_store_helper(
            self.secondary_vector_collection, self.vector_store_index, embedding, should_skip_creating_index, dimensions, filters=["source"])


def create_vector_store_helper(
    vector_collection: MongoDBAtlasVectorSearch,
    index_name: str,
    embedding: Embeddings,
    should_skip_creating_index: bool,
    dimensions: int,
    filters: Optional[list[str]] = None,
) -> MongoDBAtlasVectorSearch:
    vector_store = MongoDBAtlasVectorSearch(
        embedding=embedding,
        collection=vector_collection,
        index_name=index_name,
        relevance_score_fn="cosine"
    )
    if not should_skip_creating_index:
        asyncio.run(create_index_with_timeout_helper(
            vector_store, dimensions, filters))
    return vector_store


async def create_index_with_timeout_helper(
        vector_store: MongoDBAtlasVectorSearch,
        dimensions: int,
        filters: Optional[list[str]] = None,
        timeout: Optional[int] = 20
):
    retries = 5
    for attempt in range(retries):
        try:
            await asyncio.wait_for(
                vector_store.create_vector_search_index(
                    dimensions=dimensions,
                    filters=filters,
                    wait_until_complete=True
                ),
                timeout=timeout
            )
            break
        except asyncio.TimeoutError:
            if attempt == retries - 1:
                logger.error(
                    f"Vector search index creation timed out after {timeout} seconds and {retries} attempts")
            continue
        except Exception as e:
            if "already defined" in str(e):
                break
            if attempt == retries - 1:
                logger.error(
                    f"Failed to create vector search index after {retries} attempts: {str(e)}")
            continue
