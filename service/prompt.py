import copy
import logging
from uuid import uuid4
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from typing import Dict, Any, Optional, Tuple, Callable
import fastapi_poe as fp
from langchain_mongodb import MongoDBAtlasVectorSearch
from transformers import PreTrainedTokenizer, PreTrainedTokenizerFast
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_core.documents import Document

from .template_loader import TemplateLoader


logger = logging.getLogger(__name__)

# Load templates
template_loader = TemplateLoader()

INTRODUCTION_MESSAGES = template_loader.get_introduction_messages()
SYSTEM_PROMPT = template_loader.get_system_prompt()
SOURCE_TEMPLATE = template_loader.get_source_template()
QUOTE_TEMPLATE = template_loader.get_quote_template()
MESSAGE_TOO_SHORT = template_loader.get_message('too_short')
CONTEXT_LENGTH_EXCEEDED = template_loader.get_message('context_length_exceeded')
HEALTH_CHECK_FAILED = template_loader.get_message('health_check_failed')

def build_system_prompt(search_results: list[Dict[str, Any]], with_debug_log: bool = False) -> str:
    # Group documents by source and format them with source tags
    docs_by_source = {}
    for rs in search_results:
        source = rs['source']
        if source not in docs_by_source:
            docs_by_source[source] = []
        docs_by_source[source].append({
            "content": rs['content'],
            "chunk_num": rs['chunk_num'],
        })

    # Build context with source tags
    context_parts = []

    for source, contents in docs_by_source.items():
        contents.sort(key=lambda x: x['chunk_num'])
        quotes = []
        for content in contents:
            quotes.append(QUOTE_TEMPLATE.format(quote=content['content']))
        context_parts.append(SOURCE_TEMPLATE.format(
            name=source,
            quotes="\n".join(quotes)
        ))

        if with_debug_log:
            print(f"{context_parts[len(context_parts)-1]}\n\n")

    context = "\n".join(context_parts)
    return SYSTEM_PROMPT.format(context=context)


def build_keyword_response(user_messages: list[str]) -> str:
    return template_loader.get_search_keyword_template().format(keyword_text='\n'.join(['> ' + text.replace('\n', ' ') for text in user_messages]))


def refine_search_results(search_results: list[Dict[str, Any]]):
    for rs in search_results:
        rs['source'] = rs['source'].replace('\n', ' → ').title()


def build_search_response(search_results: list[Dict[str, Any]], without_quote: bool = True) -> str:
    if without_quote:
        return template_loader.get_response_template().format(search_result='\n'.join(
            ["| {0} | {1} |".format(index+1, rs['source'])
             for index, rs in enumerate(search_results)]
        ))

    return template_loader.get_response_template_with_quote().format(search_result='\n'.join(
        ["| {0} | {1} | ...{2} |".format(index+1, rs['source'], rs['content'][-200:].replace('\n', ' '))
         for index, rs in enumerate(search_results)]
    ))


def build_bot_summary(question: str, num_results: int, total_results: int, with_half_content: bool) -> str:
    summary = ""
    if with_half_content and num_results == 0:
        summary = f"tổng hợp từ các đoạn đầu của kết quả thứ {num_results+1}"
    elif with_half_content and num_results != 0:
        summary = f"tổng hợp từ {num_results} kết quả đầu và các đoạn đầu của kết quả thứ {num_results+1}"
    else:
        summary = f"tổng hợp từ {num_results} kết quả trả về"

    if total_results > num_results or with_half_content:
        summary += f" do nội dung quá dài"

    return template_loader.get_bot_summary_template().format(
        question=question,
        summary=summary
    )


def build_chat_input(messages: list[Dict[str, Any]]) -> str:
    """
    Convert a list of messages into a single string representation.
    This is a simple concatenation; adjust formatting if your model requires a specific ChatML format.
    """
    chat_str = ""
    for msg in messages:
        chat_str += f"[{msg['role'].upper()}]: {msg['content']}\n"
    return chat_str.strip()


def build_messages(
    tokenizer: PreTrainedTokenizer | PreTrainedTokenizerFast,
    query: fp.ProtocolMessage,
    user_messages: list[str],
    search_results: list[Dict[str, Any]],
    override_max_tokens: int = 0
) -> Optional[Tuple[list[Dict[str, Any]], int, bool]]:
    last_bot_response = None
    for message in reversed(query):
        if message.role == "bot":
            last_bot_response = message.content
            break

    messages = [
        {"role": "system", "content": ""},
        {"role": "user", "content": user_messages[-1]}
    ]

    if last_bot_response is not None:
        messages.insert(
            1, {"role": "assistant", "content": last_bot_response})

    max_tokens = tokenizer.model_max_length
    logger.debug(f"Max tokens: {max_tokens}")
    if override_max_tokens > 0:
        max_tokens = override_max_tokens
        logger.debug(f"Overriding max tokens: {max_tokens}")

    # cpsr = search_results.copy()
    # while cpsr:
    #     system_message_content = build_system_prompt(cpsr)
    #     for msg in messages:
    #         if msg['role'] == "system":
    #             msg['content'] = system_message_content
    #             break
    #     conversation_str = build_chat_input(messages)
    #     token_ids = tokenizer.encode(conversation_str)
    #     logger.debug(
    #         f"[0..{len(cpsr) - 1}]({len(cpsr)}), Tokens: {len(token_ids)}")
    #     cpsr.pop()

    def get_token_length(total_sr: int, str_len: int) -> int:
        """
        Calculate the token length for a given conversation with truncated search results.

        Args:
            total_sr (int): Number of search results to include from the start
            str_len (int): Length to truncate the last search result content to

        Returns:
            int: Number of tokens in the resulting conversation string
        """
        cprs = copy.deepcopy(search_results)[:total_sr]
        cp_messages = copy.deepcopy(messages)

        cprs[total_sr-1]['content'] = cprs[total_sr-1]['content'][:str_len]
        cp_messages[0]['content'] = build_system_prompt(cprs)
        conversation_str = build_chat_input(cp_messages)
        n = len(tokenizer.encode(conversation_str))
        del cp_messages, conversation_str, cprs
        return n

    valid_len = 0
    ll, hl = 1, len(search_results)
    while ll <= hl:
        ml = (ll + hl) // 2
        output = get_token_length(ml, len(search_results[ml-1]['content']))
        if output <= max_tokens:
            logger.debug(f"Valid: [0..{ml-1}]({ml}): {output} <= {max_tokens}")
            valid_len = ml  # Valid from 0..mid-1
            ll = ml + 1
        else:
            logger.debug(
                f"Invalid: [0..{ml-1}]({ml}): {output} > {max_tokens}")
            hl = ml - 1

    if valid_len == len(search_results):
        messages[0]['content'] = build_system_prompt(
            search_results[:valid_len], True)
        return [messages, valid_len, False]

    ok_str = 0
    ll, hl = 1000, len(search_results[valid_len]['content'])
    logger.debug(f"Valid length: {valid_len}, hl: {hl}")
    while ll <= hl:
        ml = (ll + hl) // 2
        output = get_token_length(valid_len+1, ml)
        if output <= max_tokens:
            logger.debug(
                f"Valid: [0..{valid_len-1}]+[{valid_len}][0..{ml-1}]: {output} <= {max_tokens}")
            ok_str = ml
            ll = ml + 1
        else:
            logger.debug(
                f"Invalid: [0..{valid_len-1}]+[{valid_len}][0..{ml-1}]: {output} > {max_tokens}")
            hl = ml - 1

    if ok_str == 0:
        messages[0]['content'] = build_system_prompt(
            search_results[:valid_len], True)
        return [messages, valid_len, False]

    valid_len += 1
    cpsr = search_results.copy()
    cpsr[valid_len-1]['content'] = cpsr[valid_len-1]['content'][:ok_str]
    messages[0]['content'] = build_system_prompt(cpsr[:valid_len], True)
    return [messages, valid_len - 1, True]


def similarity_search(vector_store: MongoDBAtlasVectorSearch, user_messages: list[str], limit: int = 10, filter: Optional[Callable[[Document], bool]] = None) -> list[Dict[str, Any]]:
    keyword = '\n'.join([text.replace('\n', ' ')
                         for text in user_messages])

    output = vector_store.similarity_search_with_score(
        query=keyword, k=limit, pre_filter=filter
    )

    return [{
        'source': doc.metadata.get('source', 'Unknown'),
        'content': doc.page_content,
        'score': score * 100,
        'chunk_num': doc.metadata.get('chunk_num', 0),
    } for doc, score in output]


def similarity_search_with_overrall_reranking(vector_store: MongoDBAtlasVectorSearch, rerank_vs: MongoDBAtlasVectorSearch, user_messages: list[str], limit: int = 15, rerank_limit: int = 30) -> list[Dict[str, Any]]:
    search_results = similarity_search(
        vector_store, user_messages, limit=limit)

    rerank_rs = similarity_search(rerank_vs, user_messages, limit=rerank_limit, filter={
        'source': {'$in': [rs['source'] for rs in search_results]}
    })

    source_counts = {}
    for result in rerank_rs:
        source = result['source']
        source_counts[source] = source_counts.get(source, 0) + 1
        # print(f"Source: {source} (appeared {source_counts[source]} times)")
        # print("Content: {}".format(
        #     result['content'].replace('\n', ' ')))
        # print(f"Score: {result['score']:.2f}%\n")

    for result in search_results:
        result['freq'] = source_counts.get(result['source'], 0)

    search_results.sort(key=lambda x: x['freq'], reverse=True)
    del rerank_rs, source_counts  # Free memory
    return search_results


def similarity_search_with_detailed_reranking(vector_store: MongoDBAtlasVectorSearch, rerank_vs: MongoDBAtlasVectorSearch, user_messages: list[str], limit: int = 15, rerank_limit: int = 45) -> list[Dict[str, Any]]:
    temp_results = similarity_search(
        rerank_vs, user_messages, limit=rerank_limit)

    score_map = {}
    for sr in temp_results:
        src = sr['source']
        if src not in score_map:
            score_map[src] = sr['score']

    sources = vector_store.collection.find(
        {"source": {"$in": [rs['source'] for rs in temp_results]}})

    transformed_sources = [
        {
            'id': doc['_id'],
            'source': doc['source'],
            'content': doc['text'],
            'score': score_map.get(doc['source'], 0),
        }
        for doc in sources
    ]

    transformed_sources.sort(key=lambda x: x['score'], reverse=True)

    return transformed_sources[:limit]


def rerank_with_memory_similarity_search(search_results: list[Dict[str, Any]], embeddings: OpenAIEmbeddings, user_messages: list[str]) -> list[Dict[str, Any]]:
    mem_vs = InMemoryVectorStore(embeddings)
    total_chunks = 0
    for result in search_results:
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100
        )

        chunks = text_splitter.split_text(result['content'])
        uuids = [str(uuid4()) for _ in range(len(chunks))]
        mem_vs.add_texts(chunks, [
            {"source": result["source"]}
            for _ in range(len(chunks))],
            ids=uuids
        )
        total_chunks += len(chunks)
        del chunks, uuids  # Free memory

    mem_rs = similarity_search(
        mem_vs, user_messages, limit=min(total_chunks // 10, 20))

    source_counts = {}
    for result in mem_rs:
        source = result['source']
        source_counts[source] = source_counts.get(source, 0) + 1
        # print(f"Source: {source} (appeared {source_counts[source]} times)")
        # print("Content: {}".format(
        #     result['content'].replace('\n', ' ')))
        # print(f"Score: {result['score']:.2f}%\n")

    for result in search_results:
        result['freq'] = source_counts.get(result['source'], 0)

    search_results.sort(key=lambda x: x['freq'], reverse=True)
    del mem_rs, source_counts, mem_vs  # Free memory
    return search_results
