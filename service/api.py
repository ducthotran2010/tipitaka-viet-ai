from uuid import uuid4
import logging
from pydantic import BaseModel

from fastapi import Request, HTTPException
from fastapi import Depends, Security, HTTPException
from fastapi.security.api_key import APIKeyHeader
from fastapi import FastAPI, HTTPException, Request
from fastapi import Depends
from langchain.text_splitter import RecursiveCharacterTextSplitter
from uuid import uuid4
from langchain_mongodb import MongoDBAtlasVectorSearch

from .health_check import HealthChecker
from .auth import APIKeyManager

logger = logging.getLogger(__name__)

app = FastAPI()
api_key_header = APIKeyHeader(name="X-API-Key")


class ChatRequest(BaseModel):
    question: str


def list_routes(app: FastAPI):
    """
    Log all routes of the FastAPI application.
    """
    for route in app.routes:
        logger.info(
            f"Path: {route.path}, Name: {route.name}, Methods: {route.methods}")


async def only_authenticated(api_key: str = Security(api_key_header), request: Request = None):
    api_key_manager: APIKeyManager = request.app.state.api_key_manager
    if not api_key_manager.validate_api_key(api_key):
        raise HTTPException(
            status_code=403,
            detail="Invalid or expired API key"
        )
    return api_key


async def only_admin(api_key: str = Security(api_key_header), request: Request = None):
    api_key_manager: APIKeyManager = request.app.state.api_key_manager
    if not api_key_manager.validate_admin_key(api_key):
        raise HTTPException(
            status_code=403,
            detail="Invalid or expired API key"
        )
    return api_key


class TextSource(BaseModel):
    source_name: str
    content: str


@app.put("/sources/upload", dependencies=[Depends(only_authenticated)])
def upload_sources(request: Request, request_data: list[TextSource], secondary: bool = False):
    try:
        process_sources(
            vector_store=request.app.state.secondary_vector_store if secondary else request.app.state.vector_store,
            sources=request_data,
            slice=secondary
        )
        return {"message": "Source processed successfully"}
    except Exception as e:
        logger.error(f"Error processing sources: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sources/list")
def get_sources(request: Request, secondary: bool = False):
    try:
        print()
        sources = get_sources(
            request.app.state.secondary_vector_store if secondary else request.app.state.vector_store)
        return sources
    except Exception as e:
        logger.error(f"Error checking sources: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sources/exists")
def check_source_exist(request: Request, source_name: list[str], secondary: bool = False):
    try:
        return exists(
            request.app.state.secondary_vector_store if secondary else request.app.state.vector_store,
            source_name
        )
    except Exception as e:
        logger.error(f"Error checking sources: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api-keys/generate", dependencies=[Depends(only_admin)])
def generate_api_key(request: Request, user: str, description: str = ""):
    api_key_manager: APIKeyManager = request.app.state.api_key_manager
    api_key = api_key_manager.generate_api_key(user, description)
    return {"api_key": api_key}


@app.post("/api-keys/revoke", dependencies=[Depends(only_admin)])
def revoke_api_key(request: Request, api_key: str):
    api_key_manager: APIKeyManager = request.app.state.api_key_manager
    if api_key_manager.revoke_api_key(api_key):
        return {"message": "API key revoked successfully"}
    raise HTTPException(status_code=404, detail="API key not found")


@app.get("/api-keys/list", dependencies=[Depends(only_admin)])
def list_api_keys(request: Request):
    api_key_manager: APIKeyManager = request.app.state.api_key_manager
    return api_key_manager.list_api_keys()


@app.get("/health")
async def health_check(request: Request):
    health_checker: HealthChecker = request.app.state.health_checker
    try:
        health_checker.check()
        return {"status": "healthy"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


app.list_routes = lambda: list_routes(app)
app.set_api_key_manager = lambda api_key_manager: setattr(
    app.state, "api_key_manager", api_key_manager)
app.set_health_checker = lambda health_checker: setattr(
    app.state, "health_checker", health_checker)
app.set_vector_store = lambda vector_store: setattr(
    app.state, "vector_store", vector_store)
app.set_secondary_vector_store = lambda secondary_vector_store: setattr(
    app.state, "secondary_vector_store", secondary_vector_store)


def process_sources(vector_store: MongoDBAtlasVectorSearch, sources: list[TextSource], slice: int = 0):
    """
    Process sources: add documents to the vector store.
    """

    texts = []
    uuids = []
    metadatas = []
    if slice > 0:
        # Split texts into chunks and add to the vector store
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=100)

        for src in sources:
            chunks = text_splitter.split_text(src.content)
            texts.extend(chunks)
            uuids.extend([str(uuid4()) for _ in range(len(chunks))])
            metadatas.extend([{"source": src.source_name, "chunk_num": i}
                             for i in range(len(chunks))])
            del chunks
    else:
        uuids.extend([str(uuid4()) for _ in range(len(sources))])
        texts.extend([src.content for src in sources])
        metadatas.extend([{"source": src.source_name} for src in sources])

    vector_store.add_texts(
        texts=texts, metadatas=metadatas, ids=uuids, batch_size=100_000)


def get_sources(vector_store: MongoDBAtlasVectorSearch) -> list[str]:
    """
    Retrieve source names from the database.
    """
    collection = vector_store.collection
    sources = collection.find({})
    return [source['source'] for source in sources]


def exists(vector_store: MongoDBAtlasVectorSearch, source_name: list[str]) -> list[bool]:
    """
    Check if source exists in the database.
    """
    collection = vector_store.collection
    return [collection.find_one({"source": source}) is not None for source in source_name]
