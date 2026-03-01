"""
indexer.py
Loads PDFs from a directory, extracts text page-by-page,
and returns chunked documents with metadata.
"""

import fitz  # PyMuPDF
from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter


def find_pdfs(directory: str) -> list[Path]:
    """Return all PDF paths in a directory (non-recursive)."""
    return list(Path(directory).glob("*.pdf"))


def load_and_chunk_pdfs(directory: str, chunk_size: int = 500, chunk_overlap: int = 60) -> list[dict]:
    """
    Load every PDF in *directory*, split into overlapping text chunks.

    Returns a list of dicts:
        {
            "text":     str,
            "pdf_name": str,   # filename only, e.g. "report.pdf"
            "pdf_path": str,   # absolute path
            "page":     int    # 1-based page number
        }
    """
    pdf_files = find_pdfs(directory)
    if not pdf_files:
        return []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", " ", ""],
    )

    chunks = []
    for pdf_path in pdf_files:
        try:
            doc = fitz.open(str(pdf_path))
        except Exception as exc:
            print(f"[indexer] Could not open {pdf_path.name}: {exc}")
            continue

        for page_num, page in enumerate(doc, start=1):
            text = page.get_text("text")
            if not text.strip():
                continue
            for chunk in splitter.split_text(text):
                chunks.append(
                    {
                        "text": chunk,
                        "pdf_name": pdf_path.name,
                        "pdf_path": str(pdf_path.resolve()),
                        "page": page_num,
                    }
                )
        doc.close()

    print(f"[indexer] Loaded {len(pdf_files)} PDFs → {len(chunks)} chunks")
    return chunks
