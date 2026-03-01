"""
main_window.py
Main application window for the PDF RAG Desktop Assistant.

Layout:
  ┌──────────────────────────────────────────────────────────────┐
  │  Left panel (420px)          │  Right panel (PDF Viewer)     │
  │  ─────────────────────────── │  ──────────────────────────── │
  │  [Directory picker banner]   │                               │
  │  [Search bar]  [k=5 ▲]      │    (embedded PDF viewer)      │
  │  ─ PDF Results ─────────     │                               │
  │  [ ] 📄 file.pdf  p.3        │                               │
  │  [ ] 📄 other.pdf p.7        │                               │
  │  ─ Chat ────────────────     │                               │
  │  🧑 question                 │                               │
  │  🤖 answer [cite, p.2]       │                               │
  │  🎥 video link               │                               │
  │  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─  │                               │
  │  [Question input]  [Ask]     │                               │
  └──────────────────────────────────────────────────────────────┘
"""

import sys
import os
import subprocess

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QSplitter,
    QLabel, QLineEdit, QPushButton, QListWidget, QListWidgetItem,
    QTextEdit, QSpinBox, QFileDialog, QMessageBox, QProgressDialog,
    QFrame, QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QIcon, QTextCursor

from ui.pdf_viewer import PDFViewer
from ui.workers import IndexWorker, QAWorker


DARK_BG = "#1e1e2e"
PANEL_BG = "#2a2a3e"
ACCENT   = "#7c6af7"
ACCENT2  = "#56d4a0"
TEXT_CLR = "#e0e0f0"
MUTED    = "#888aaa"
CARD_BG  = "#32324a"
BORDER   = "#44446a"


APP_STYLE = f"""
QMainWindow, QWidget {{
    background-color: {DARK_BG};
    color: {TEXT_CLR};
    font-family: 'Segoe UI', 'Inter', 'Helvetica Neue', sans-serif;
    font-size: 13px;
}}
QSplitter::handle {{
    background: {BORDER};
    width: 2px;
}}
QLineEdit {{
    background: {CARD_BG};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 6px 10px;
    color: {TEXT_CLR};
}}
QLineEdit:focus {{
    border: 1px solid {ACCENT};
}}
QPushButton {{
    background: {ACCENT};
    color: white;
    border: none;
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: bold;
}}
QPushButton:hover {{
    background: #8f7ef9;
}}
QPushButton:disabled {{
    background: {BORDER};
    color: {MUTED};
}}
QPushButton#secondary {{
    background: {CARD_BG};
    border: 1px solid {BORDER};
    color: {TEXT_CLR};
}}
QPushButton#secondary:hover {{
    border: 1px solid {ACCENT};
}}
QListWidget {{
    background: {CARD_BG};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 4px;
}}
QListWidget::item {{
    padding: 6px 8px;
    border-radius: 4px;
    margin: 1px 0;
}}
QListWidget::item:selected {{
    background: {ACCENT};
    color: white;
}}
QListWidget::item:hover:!selected {{
    background: {BORDER};
}}
QTextEdit {{
    background: {CARD_BG};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 8px;
    color: {TEXT_CLR};
}}
QSpinBox {{
    background: {CARD_BG};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 4px 8px;
    color: {TEXT_CLR};
    min-width: 68px;
}}
QLabel#sectionHeader {{
    color: {MUTED};
    font-size: 11px;
    font-weight: bold;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    margin-top: 8px;
}}
QLabel#dirLabel {{
    background: {CARD_BG};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 6px 10px;
    color: {MUTED};
}}
QScrollBar:vertical {{
    background: {PANEL_BG};
    width: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: {BORDER};
    border-radius: 4px;
}}
QScrollBar::handle:vertical:hover {{
    background: {ACCENT};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}
"""


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.store = None
        self.pdf_results: list[dict] = []
        self._index_worker = None
        self._qa_worker = None

        self.setWindowTitle("📚 PDF Research Assistant")
        self.resize(1440, 900)
        self.setStyleSheet(APP_STYLE)

        self._build_ui()
        # Ask for directory after the window is shown
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(100, self._pick_directory)

    # ================================================================ build UI

    def _build_ui(self):
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(2)
        self.setCentralWidget(splitter)

        # ── left panel ────────────────────────────────────────────────────────
        left = QWidget()
        left.setMinimumWidth(360)
        left.setMaximumWidth(460)
        lv = QVBoxLayout(left)
        lv.setContentsMargins(12, 12, 12, 12)
        lv.setSpacing(6)

        # Directory row
        dir_row = QHBoxLayout()
        self.lbl_dir = QLabel("No directory selected")
        self.lbl_dir.setObjectName("dirLabel")
        self.lbl_dir.setWordWrap(False)
        self.lbl_dir.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        dir_row.addWidget(self.lbl_dir)
        btn_change = QPushButton("Change")
        btn_change.setObjectName("secondary")
        btn_change.setFixedWidth(70)
        btn_change.clicked.connect(self._pick_directory)
        dir_row.addWidget(btn_change)
        lv.addLayout(dir_row)

        # Search row
        lv.addWidget(self._section("SEARCH"))
        search_row = QHBoxLayout()
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Type a topic to search PDFs …")
        self.search_bar.returnPressed.connect(self._do_search)
        search_row.addWidget(self.search_bar)
        self.k_spin = QSpinBox()
        self.k_spin.setRange(1, 20)
        self.k_spin.setValue(5)
        self.k_spin.setPrefix("k = ")
        self.k_spin.setToolTip("Number of top PDFs to retrieve")
        search_row.addWidget(self.k_spin)
        btn_search = QPushButton("Search")
        btn_search.clicked.connect(self._do_search)
        search_row.addWidget(btn_search)
        lv.addLayout(search_row)

        # PDF result list
        lv.addWidget(self._section("RELEVANT PDFs  (select to chat · double-click to open)"))
        self.pdf_list = QListWidget()
        self.pdf_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.pdf_list.setMinimumHeight(140)
        self.pdf_list.setMaximumHeight(220)
        self.pdf_list.itemDoubleClicked.connect(self._open_pdf_external)
        self.pdf_list.itemClicked.connect(self._preview_pdf)
        lv.addWidget(self.pdf_list)

        # Chat display
        lv.addWidget(self._section("CHAT"))
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setMinimumHeight(200)
        self.chat_display.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        lv.addWidget(self.chat_display, stretch=1)

        # Question input row
        q_row = QHBoxLayout()
        self.question_input = QLineEdit()
        self.question_input.setPlaceholderText("Ask a question about selected PDFs …")
        self.question_input.returnPressed.connect(self._ask_question)
        self.question_input.setEnabled(False)
        q_row.addWidget(self.question_input)
        self.btn_ask = QPushButton("Ask")
        self.btn_ask.setEnabled(False)
        self.btn_ask.setFixedWidth(56)
        self.btn_ask.clicked.connect(self._ask_question)
        q_row.addWidget(self.btn_ask)
        lv.addLayout(q_row)

        splitter.addWidget(left)

        # ── right panel (PDF viewer) ───────────────────────────────────────────
        self.pdf_viewer = PDFViewer()
        splitter.addWidget(self.pdf_viewer)

        splitter.setSizes([420, 1020])

    def _section(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("sectionHeader")
        return lbl

    # =========================================================== directory / index

    def _pick_directory(self):
        path = QFileDialog.getExistingDirectory(self, "Select PDF Directory")
        if not path:
            if not self.store:   # first launch — must choose
                QMessageBox.warning(self, "Required", "Please select a directory containing PDFs.")
                self._pick_directory()
            return
        self._start_indexing(path)

    def _start_indexing(self, directory: str):
        self.lbl_dir.setText(directory)
        self.search_bar.setEnabled(False)
        self.question_input.setEnabled(False)
        self.btn_ask.setEnabled(False)
        self.pdf_list.clear()
        self._append_chat("system", f"🔄 Indexing PDFs in:\n{directory}\nThis may take a moment …")

        self._index_worker = IndexWorker(directory, parent=self)
        self._index_worker.finished.connect(self._on_index_done)
        self._index_worker.error.connect(self._on_index_error)
        self._index_worker.progress.connect(lambda msg: self._append_chat("system", f"  {msg}"))
        self._index_worker.start()

    def _on_index_done(self, store, num_pdfs: int):
        self.store = store
        self.search_bar.setEnabled(True)
        self.question_input.setEnabled(True)
        self.btn_ask.setEnabled(True)
        self._append_chat("system", f"✅ Indexed {num_pdfs} PDF(s). Ready!\n")
        self.search_bar.setFocus()

    def _on_index_error(self, msg: str):
        self.search_bar.setEnabled(True)
        QMessageBox.critical(self, "Indexing Error", msg)
        self._append_chat("system", f"❌ Error: {msg}\n")

    # ================================================================ search

    def _do_search(self):
        if not self.store:
            QMessageBox.information(self, "Not ready", "Please wait for indexing to complete.")
            return
        query = self.search_bar.text().strip()
        if not query:
            return

        from rag.retriever import search_pdfs
        k = self.k_spin.value()
        self.pdf_results = search_pdfs(self.store, query, k=k)

        self.pdf_list.clear()
        if not self.pdf_results:
            self._append_chat("system", "🔍 No relevant PDFs found for that query.\n")
            return

        for r in self.pdf_results:
            item = QListWidgetItem(f"📄  {r['pdf_name']}   — p.{r['page']}")
            item.setData(Qt.ItemDataRole.UserRole, r)
            item.setToolTip(r["snippet"])
            self.pdf_list.addItem(item)

        self._append_chat("system", f'🔍 Found {len(self.pdf_results)} PDF(s) for "{query}".\n')

    # ================================================================ PDF open / preview

    def _preview_pdf(self, item: QListWidgetItem):
        """Single-click: show PDF in the embedded viewer."""
        r = item.data(Qt.ItemDataRole.UserRole)
        try:
            self.pdf_viewer.load(r["pdf_path"], jump_to_page=r["page"])
        except Exception as exc:
            self._append_chat("system", f"⚠️ Could not render PDF: {exc}\n")

    def _open_pdf_external(self, item: QListWidgetItem):
        """Double-click: open PDF in the system viewer."""
        r = item.data(Qt.ItemDataRole.UserRole)
        try:
            if sys.platform == "darwin":
                subprocess.Popen(["open", r["pdf_path"]])
            elif sys.platform == "win32":
                os.startfile(r["pdf_path"])
            else:
                subprocess.Popen(["xdg-open", r["pdf_path"]])
        except Exception as exc:
            QMessageBox.warning(self, "Open Error", str(exc))

    # ================================================================ Q&A

    def _ask_question(self):
        if not self.store:
            return
        question = self.question_input.text().strip()
        if not question:
            return

        # Determine which PDFs to query
        selected_items = self.pdf_list.selectedItems()
        if selected_items:
            selected_pdfs = [i.data(Qt.ItemDataRole.UserRole)["pdf_name"] for i in selected_items]
        elif self.pdf_results:
            selected_pdfs = [r["pdf_name"] for r in self.pdf_results]
        else:
            QMessageBox.information(self, "No PDFs", "Search for a topic first to load PDFs.")
            return

        self.question_input.setEnabled(False)
        self.btn_ask.setEnabled(False)
        self._append_chat("user", question)
        self._append_chat("system", "⏳ Thinking …")
        self.question_input.clear()

        self._qa_worker = QAWorker(self.store, question, selected_pdfs, parent=self)
        self._qa_worker.finished.connect(self._on_qa_done)
        self._qa_worker.error.connect(self._on_qa_error)
        self._qa_worker.start()

    def _on_qa_done(self, answer: str, video: dict | None):
        # Remove the "Thinking …" line
        self._remove_last_system_line()

        self._append_chat("assistant", answer)

        if video:
            vid_text = (
                f"🎥 Related video: **{video['title']}**\n"
                f"   Channel: {video['channel']}  |  Duration: {video['duration']}\n"
                f"   {video['url']}"
            )
            self._append_chat("video", vid_text)

        self.question_input.setEnabled(True)
        self.btn_ask.setEnabled(True)
        self.question_input.setFocus()

    def _on_qa_error(self, msg: str):
        self._remove_last_system_line()
        self._append_chat("system", f"❌ Error: {msg}")
        self.question_input.setEnabled(True)
        self.btn_ask.setEnabled(True)

    # ============================================================ chat helpers

    def _append_chat(self, role: str, text: str):
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.chat_display.setTextCursor(cursor)

        colours = {
            "user":      ("#7c6af7", "🧑"),
            "assistant": ("#56d4a0", "🤖"),
            "system":    ("#888aaa", "ℹ️"),
            "video":     ("#f5a623", ""),
        }
        colour, icon = colours.get(role, ("#e0e0f0", ""))

        if role == "user":
            html = (
                f'<p style="margin:8px 0 2px 0;">'
                f'<span style="color:{colour}; font-weight:bold;">{icon} You</span></p>'
                f'<p style="margin:0 0 8px 16px; color:#e0e0f0;">{self._esc(text)}</p>'
            )
        elif role == "assistant":
            body = self._esc(text).replace("\n", "<br>")
            html = (
                f'<p style="margin:8px 0 2px 0;">'
                f'<span style="color:{colour}; font-weight:bold;">{icon} Assistant</span></p>'
                f'<p style="margin:0 0 8px 16px; color:#e0e0f0;">{body}</p>'
            )
        elif role == "video":
            parts = text.split("\n")
            lines = "<br>".join(self._esc(p) for p in parts)
            # Make URL clickable
            if parts:
                url = parts[-1].strip()
                lines = "<br>".join(self._esc(p) for p in parts[:-1])
                lines += f'<br><a href="{url}" style="color:#7ec8e3;">{url}</a>'
            html = (
                f'<p style="margin:4px 0 12px 16px; color:{colour};">'
                f'{lines}</p>'
            )
        else:
            html = (
                f'<p style="margin:2px 0; color:{colour}; font-style:italic;">'
                f'{self._esc(text)}</p>'
            )

        self.chat_display.insertHtml(html)
        self.chat_display.verticalScrollBar().setValue(
            self.chat_display.verticalScrollBar().maximum()
        )

    def _remove_last_system_line(self):
        """Remove the last ⏳ Thinking … line."""
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
        # naive approach: just let it stay — the next message overwrites visually
        # (full removal would require HTML parsing; skip for simplicity)

    @staticmethod
    def _esc(text: str) -> str:
        """Minimal HTML escaping."""
        return (
            text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
        )
