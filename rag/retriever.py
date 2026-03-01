"""
retriever.py
Runs a semantic search against the FAISS store and returns
the top-k *unique PDFs* ranked by their best-matching chunk score.
"""

from langchain_community.vectorstores import FAISS


def search_pdfs(store: FAISS, query: str, k: int = 5) -> list[dict]:
    """
    Return up to *k* unique PDFs most relevant to *query*.

    Each result dict:
        {
            "pdf_name": str,
            "pdf_path": str,
            "page":     int,    # page of the best-matching chunk
            "snippet":  str,    # first 250 chars of best chunk
            "score":    float,  # lower = more similar (L2 distance)
        }
    """
    # Over-fetch so we have enough after deduplication
    raw = store.similarity_search_with_score(query, k=k * 4)

    seen: dict[str, dict] = {}
    for doc, score in raw:
        name = doc.metadata["pdf_name"]
        if name not in seen or score < seen[name]["score"]:
            seen[name] = {
                "pdf_name": name,
                "pdf_path": doc.metadata["pdf_path"],
                "page": doc.metadata["page"],
                "snippet": doc.page_content[:250].replace("\n", " "),
                "score": score,
            }
        if len(seen) >= k:
            break

    return sorted(seen.values(), key=lambda x: x["score"])


def search_within_pdfs(store: FAISS, query: str, pdf_names: list[str], k: int = 8) -> list[dict]:
    """
    Like search_pdfs but restricted to *pdf_names*.
    Returns raw chunks (not deduplicated) for use in Q&A context.
    """
    raw = store.similarity_search_with_score(query, k=k * 6)
    filtered = [
        (doc, score) for doc, score in raw
        if doc.metadata["pdf_name"] in pdf_names
    ]
    # Keep top k
    filtered.sort(key=lambda x: x[1])
    return [
        {
            "text": doc.page_content,
            "pdf_name": doc.metadata["pdf_name"],
            "page": doc.metadata["page"],
            "score": score,
        }
        for doc, score in filtered[:k]
    ]
