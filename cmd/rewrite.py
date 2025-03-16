# Import dependencies from our stack
from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv
import os
import sys
from langchain_together import ChatTogether  # Using TogetherAI integration
from langchain_community.embeddings import HuggingFaceBgeEmbeddings
from rich import print
from pydantic import BaseModel, Field
from langchain.output_parsers import PydanticToolsParser
from together import Together
from langchain_openai import OpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate, FewShotChatMessagePromptTemplate

# autopep8: off # Add parent directory to path to allow absolute imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

from db import mongoatlas
from service.health_check import HealthChecker
from db import postgres
from service.bot import build_system_prompt, build_messages, similarity_search
from transformers import AutoTokenizer, PreTrainedTokenizer, PreTrainedTokenizerFast
# autopep8: on


# Load environment variables from a .env file
load_dotenv()

# Initialize the TogetherAI model
together_api_key = os.getenv("TOGETHER_API_KEY")
if not together_api_key:
    raise ValueError("Please set the TOGETHER_API_KEY environment variable.")

# Instantiate the Together model (adjust model name as needed)
model = ChatTogether(model="Qwen/Qwen2.5-7B-Instruct-Turbo",
                     api_key=together_api_key)

# Define the system prompt for query rewriting
system_rewrite = """You are a helpful assistant that generates multiple search queries based on a single input query.

Perform query expansion. If there are multiple common ways of phrasing a user question
or common synonyms for key words in the question, make sure to return multiple versions
of the query with the different phrasings.

If there are acronyms or words you are not familiar with, do not try to rephrase them.

Return 3 different versions of the question."""
system_decompose = """You are a helpful assistant that generates search queries based on a single input query.

Perform query decomposition. Given a user question, break it down into distinct sub questions that
you need to answer in order to answer the original question.

If there are acronyms or words you are not familiar with, do not try to rephrase them."""
system_step_back = """You are an expert at taking a specific question and extracting a more generic question that gets at
the underlying principles needed to answer the specific question.

Given a specific user question, write a more generic question that needs to be answered in order to answer the specific question.

If you don't recognize a word or acronym to not try to rewrite it.

Write concise questions."""
system_hyde = """You are an expert at using a question to generate a document useful for answering the question.

Given a question, generate a paragraph of text that answers the question.
"""


class ParaphrasedQuery(BaseModel):
    paraphrased_query: str = Field(
        description="A unique paraphrasing of the original question.",
    )


# Create a ChatPromptTemplate using LangChain's prompt system
rewrite_prompt = ChatPromptTemplate.from_messages([
    ("system", system_rewrite),
    ("human", "{question}")
])


# Example user query
question = "Tìm tích truyện vị thánh A la hán bị mù tìm đường về thăm đức Phật, kể tên vị ấy và cho biết tích truyện đó liên quan đến bài kinh nào"

llm_with_tools = model.bind_tools([ParaphrasedQuery])
query_analyzer = rewrite_prompt | llm_with_tools | PydanticToolsParser(tools=[
                                                                       ParaphrasedQuery])
queries = query_analyzer.invoke({"question": question})
print("[bold green]Paraphrased Queries:[/bold green]", queries)

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

search_results = []
# Print search results
print("\n======= SEARCH RESULTS =======")
for query in queries:
    search_results.extend(
        similarity_search(vector_store, [query.paraphrased_query], limit=5)
    )
for result in search_results:
    print(f"Source: {result['source']}")
    print("Content: ...{}...".format(
        result['content'][400:600].replace('\n', ' ')))
    print(f"Score: {result['score']:.2f}%\n")
