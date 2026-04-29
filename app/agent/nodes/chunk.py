from __future__ import annotations

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from ..state import InsertState
from ..utils import compute_mdhash_id


async def chunk_document(state: InsertState) -> dict:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1200,
        chunk_overlap=100,
        length_function=len,
        separators=["\n\n", "\n", ".", " ", ""],
    )

    docs = splitter.create_documents([state["raw_text"]])

    chunk_dict = {}
    langchain_docs = []
    for i, doc in enumerate(docs):
        chunk_key = compute_mdhash_id(doc.page_content, prefix="chunk-")
        doc.id = chunk_key
        doc.metadata["chunk_order_index"] = i
        doc.metadata["full_doc_id"] = state["doc_id"]
        langchain_docs.append(doc)
        chunk_dict[chunk_key] = {
            "content": doc.page_content,
            "tokens": len(doc.page_content),
            "chunk_order_index": i,
            "full_doc_id": state["doc_id"],
        }

    return {"chunks": langchain_docs, "chunk_dict": chunk_dict}
