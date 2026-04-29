from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph

from .state import InsertState, QueryState


_STORAGE_CTX: dict[str, Any] = {}

_INSERT_GRAPH = None
_QUERY_GRAPH = None


def configure_graphs(storage_ctx: dict[str, Any]) -> None:
    global _STORAGE_CTX, _INSERT_GRAPH, _QUERY_GRAPH
    _STORAGE_CTX.update(storage_ctx)

    _INSERT_GRAPH = _build_insert_graph()
    _QUERY_GRAPH = _build_query_graph()


def get_insert_graph() -> StateGraph:
    return _INSERT_GRAPH


def get_query_graph() -> StateGraph:
    return _QUERY_GRAPH


def _build_insert_graph():
    from .nodes.enqueue import check_duplicates, save_document
    from .nodes.chunk import chunk_document
    from .nodes.embed import embed_chunks
    from .nodes.extract import (
        extract_entities_node,
        store_chunks,
        store_entities,
        store_relationships,
        mark_completed,
    )

    builder = StateGraph(InsertState)

    builder.add_node("check_duplicates", check_duplicates)
    builder.add_node("save_document", save_document)
    builder.add_node("chunk_document", chunk_document)
    builder.add_node("embed_chunks", embed_chunks)
    builder.add_node("extract_entities", extract_entities_node)
    builder.add_node("store_chunks", store_chunks)
    builder.add_node("store_entities", store_entities)
    builder.add_node("store_relationships", store_relationships)
    builder.add_node("mark_completed", mark_completed)

    builder.set_entry_point("check_duplicates")
    builder.add_edge("check_duplicates", "save_document")
    builder.add_edge("save_document", "chunk_document")
    builder.add_edge("chunk_document", "embed_chunks")
    builder.add_edge("chunk_document", "extract_entities")
    builder.add_edge("embed_chunks", "store_chunks")
    builder.add_edge("extract_entities", "store_entities")
    builder.add_edge("extract_entities", "store_relationships")
    builder.add_edge("store_chunks", "mark_completed")
    builder.add_edge("store_entities", END)
    builder.add_edge("store_relationships", END)
    builder.add_edge("mark_completed", END)

    return builder.compile()


def _build_query_graph():
    from .nodes.keywords import extract_keywords_node, route_by_mode
    from .nodes.search import local_search_node, global_search_node, naive_search_node
    from .nodes.merge import merge_results
    from .nodes.context import build_context_node
    from .nodes.generate import generate_answer

    builder = StateGraph(QueryState)

    builder.add_node("extract_keywords", extract_keywords_node)
    builder.add_node("local_search", local_search_node)
    builder.add_node("global_search", global_search_node)
    builder.add_node("naive_search", naive_search_node)
    builder.add_node("merge_results", merge_results)
    builder.add_node("build_context", build_context_node)
    builder.add_node("generate_answer", generate_answer)

    builder.set_entry_point("extract_keywords")
    builder.add_conditional_edges("extract_keywords", route_by_mode)
    builder.add_edge("local_search", "merge_results")
    builder.add_edge("global_search", "merge_results")
    builder.add_edge("naive_search", "merge_results")
    builder.add_edge("merge_results", "build_context")

    def route_after_context(state):
        if state["param"].get("retrieve_only", False):
            return END
        return "generate_answer"

    builder.add_conditional_edges("build_context", route_after_context)
    builder.add_edge("generate_answer", END)

    return builder.compile()
