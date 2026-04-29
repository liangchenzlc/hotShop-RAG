from __future__ import annotations

from ..state import InsertState
from ..utils import compute_mdhash_id, sanitize_text


def check_duplicates(state: InsertState) -> dict:
    doc_id = compute_mdhash_id(state["raw_text"], prefix="doc-")
    return {"doc_id": doc_id, "exists": False}


async def save_document(state: InsertState) -> dict:
    ctx = _get_context()
    clean = sanitize_text(state["raw_text"])
    await ctx["full_docs"].upsert({state["doc_id"]: {"content": clean}})
    await ctx["doc_status"].upsert({state["doc_id"]: {"status": "pending"}})
    return {}


def _get_context():
    import app.agent.graph as g
    return g._STORAGE_CTX
