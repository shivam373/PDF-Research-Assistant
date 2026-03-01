"""
embedder.py
Builds a FAISS vector store from document chunks and persists it to disk.
On subsequent runs, loads the existing index to avoid re-embedding.
"""

import os
from pathlib import Path

from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document


STORE_PATH = str(Path(__file__).parent.parent / "data" / "vector_store")


def _make_documents(chunks: list[dict]) -> list[Document]:
    return [
        Document(
            page_content=c["text"],
            metadata={
                "pdf_name": c["pdf_name"],
                "pdf_path": c["pdf_path"],
                "page": c["page"],
            },
        )
        for c in chunks
    ]


def build_index(chunks: list[dict], save_path: str = STORE_PATH) -> FAISS:
    """Embed *chunks* and persist a FAISS index at *save_path*."""
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    docs = _make_documents(chunks)

    print(f"[embedder] Embedding {len(docs)} chunks …")
    store = FAISS.from_documents(docs, embeddings)

    Path(save_path).mkdir(parents=True, exist_ok=True)
    store.save_local(save_path)
    print(f"[embedder] Index saved to {save_path}")
    return store


def load_index(save_path: str = STORE_PATH) -> FAISS | None:
    """Load a persisted FAISS index, or return None if it doesn't exist."""
    index_file = Path(save_path) / "index.faiss"
    if not index_file.exists():
        return None
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    print(f"[embedder] Loading existing index from {save_path}")
    return FAISS.load_local(save_path, embeddings, allow_dangerous_deserialization=True)
