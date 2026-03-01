"""
workers.py
QThread workers for long-running tasks so the UI never freezes.
"""

from PyQt6.QtCore import QThread, pyqtSignal


class IndexWorker(QThread):
    """Indexes a PDF directory in the background."""

    finished = pyqtSignal(object, int)   # (FAISS store, num_pdfs)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self, directory: str, parent=None):
        super().__init__(parent)
        self.directory = directory

    def run(self):
        try:
            from rag.indexer import load_and_chunk_pdfs, find_pdfs
            from rag.embedder import build_index

            pdf_count = len(find_pdfs(self.directory))
            if pdf_count == 0:
                self.error.emit("No PDF files found in the selected directory.")
                return

            self.progress.emit(f"Reading {pdf_count} PDFs …")
            chunks = load_and_chunk_pdfs(self.directory)

            self.progress.emit(f"Embedding {len(chunks)} text chunks …")
            store = build_index(chunks)

            self.finished.emit(store, pdf_count)
        except Exception as exc:
            self.error.emit(str(exc))


class QAWorker(QThread):
    """Runs Q&A in the background."""

    finished = pyqtSignal(str, object)   # (answer, video_dict | None)
    error = pyqtSignal(str)

    def __init__(self, store, question: str, selected_pdfs: list[str], parent=None):
        super().__init__(parent)
        self.store = store
        self.question = question
        self.selected_pdfs = selected_pdfs

    def run(self):
        try:
            from rag.qa_chain import answer_question
            from utils.video_search import find_related_video

            answer = answer_question(self.store, self.question, self.selected_pdfs)
            video = find_related_video(self.question)
            self.finished.emit(answer, video)
        except Exception as exc:
            self.error.emit(str(exc))
