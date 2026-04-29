from __future__ import annotations

from typing import Annotated, TypedDict

from langchain_core.documents import Document
from langgraph.graph import add_messages


class InsertState(TypedDict):
    raw_text: str
    doc_id: str
    exists: bool
    chunks: list[Document]
    chunk_dict: dict
    entities: dict[str, dict]
    relationships: list[dict]
    error: str | None


class QueryState(TypedDict):
    question: str
    param: dict
    hl_keywords: list[str]
    ll_keywords: list[str]
    local_entities: list[dict]
    local_relations: list[dict]
    global_entities: list[dict]
    global_relations: list[dict]
    vector_chunks: list[dict]
    context: str
    raw_data: dict
    answer: str
