"""
main_window.py — PDF RAG Desktop Assistant

Layout uses ONE splitter with TWO panes only:

  Normal mode:  [LEFT: search-section + chat-section] | [RIGHT: PDF Viewer]
  Focus mode:   [LEFT: chat-section only (search hidden)] | [RIGHT: PDF Viewer]

The toggle button lives in the chat-section header → always visible.
The search-section (dir, search bar, pdf list, badge) is a sub-widget
inside the left pane that gets shown/hidden. Nothing is ever reparented.
"""

import sys, os, re, subprocess

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QSplitter,
    QLabel, QLineEdit, QPushButton, QListWidget, QListWidgetItem,
    QTextBrowser, QSpinBox, QFileDialog, QMessageBox,
    QSizePolicy, QApplication, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QTextCursor

from ui.pdf_viewer import PDFViewer
from ui.workers import IndexWorker, QAWorker

# ── Palette ───────────────────────────────────────────────────────────────────
DARK_BG  = "#1e1e2e"
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
QSplitter::handle {{ background: {BORDER}; width: 2px; }}
QLineEdit {{
    background: {CARD_BG}; border: 1px solid {BORDER};
    border-radius: 6px; padding: 5px 10px; color: {TEXT_CLR};
}}
QLineEdit:focus {{ border: 1px solid {ACCENT}; }}
QPushButton {{
    background: {ACCENT}; color: white; border: none;
    border-radius: 6px; padding: 5px 12px; font-weight: bold;
}}
QPushButton:hover {{ background: #8f7ef9; }}
QPushButton:disabled {{ background: {BORDER}; color: {MUTED}; }}
QPushButton#secondary {{
    background: {CARD_BG}; border: 1px solid {BORDER}; color: {TEXT_CLR};
}}
QPushButton#secondary:hover {{ border: 1px solid {ACCENT}; }}
QPushButton#toggleBtn {{
    background: transparent; border: 1px solid {ACCENT}; color: {ACCENT};
    border-radius: 6px; padding: 3px 10px; font-size: 11px; font-weight: bold;
}}
QPushButton#toggleBtn:hover {{ background: {ACCENT}; color: white; }}
QListWidget {{
    background: {CARD_BG}; border: 1px solid {BORDER};
    border-radius: 6px; padding: 3px;
}}
QListWidget::item {{ padding: 5px 8px; border-radius: 4px; margin: 1px 0; }}
QListWidget::item:selected {{ background: {ACCENT}; color: white; }}
QListWidget::item:hover:!selected {{ background: {BORDER}; }}
QTextBrowser {{
    background: {CARD_BG}; border: 1px solid {BORDER};
    border-radius: 6px; padding: 6px; color: {TEXT_CLR};
}}
QSpinBox {{
    background: {CARD_BG}; border: 1px solid {BORDER};
    border-radius: 6px; padding: 3px 6px; color: {TEXT_CLR}; min-width: 60px;
}}
QLabel#sectionHeader {{
    color: {MUTED}; font-size: 10px; font-weight: bold;
    letter-spacing: 0.08em; margin-top: 4px;
}}
QLabel#dirLabel {{
    background: {CARD_BG}; border: 1px solid {BORDER};
    border-radius: 6px; padding: 3px 8px; color: {MUTED}; font-size: 11px;
}}
QLabel#bookBadge {{
    background: #3a2e6e; border: 1px solid {ACCENT}; border-radius: 10px;
    padding: 2px 10px; color: #c4b8ff; font-size: 11px; font-weight: bold;
}}
QScrollBar:vertical {{ background: {PANEL_BG}; width: 6px; border-radius: 3px; }}
QScrollBar::handle:vertical {{ background: {BORDER}; border-radius: 3px; }}
QScrollBar::handle:vertical:hover {{ background: {ACCENT}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
"""


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.store         = None
        self.pdf_results   = []
        self._index_worker = None
        self._qa_worker    = None
        self._focus_mode   = False

        self.setWindowTitle("📚 PDF Research Assistant")
        self.resize(1440, 900)
        self.setStyleSheet(APP_STYLE)
        self._build_ui()

        from PyQt6.QtCore import QTimer
        QTimer.singleShot(100, self._pick_directory)

    # ═══════════════════════════════════════════════════════════════ build UI ══

    def _build_ui(self):
        """
        Splitter: left_panel | pdf_viewer

        left_panel (QVBoxLayout):
          ┌─ self.search_section  (QWidget — hidden in focus mode)
          │    dir row
          │    search row
          │    pdf list
          │    book badge
          └─ self.chat_section  (QWidget — always visible)
               chat header (badge + toggle btn)
               chat display
               question input row
        """
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(2)
        self.setCentralWidget(self.splitter)

        # ── Left panel ────────────────────────────────────────────────────────
        self.left_panel = QWidget()
        self.left_panel.setMinimumWidth(300)
        self.left_panel.setMaximumWidth(480)
        lv = QVBoxLayout(self.left_panel)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.setSpacing(0)

        # search_section — shown in normal mode, hidden in focus mode
        self.search_section = QWidget()
        ssv = QVBoxLayout(self.search_section)
        ssv.setContentsMargins(6, 6, 6, 4)
        ssv.setSpacing(4)
        self._build_search_section(ssv)
        lv.addWidget(self.search_section)

        # thin divider line
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"color: {BORDER};")
        lv.addWidget(line)

        # chat_section — always visible
        self.chat_section = QWidget()
        csv = QVBoxLayout(self.chat_section)
        csv.setContentsMargins(6, 4, 6, 6)
        csv.setSpacing(4)
        self._build_chat_section(csv)
        lv.addWidget(self.chat_section, stretch=1)

        self.splitter.addWidget(self.left_panel)

        # ── PDF Viewer ────────────────────────────────────────────────────────
        self.pdf_viewer = PDFViewer()
        self.splitter.addWidget(self.pdf_viewer)

        self.splitter.setSizes([420, 1020])

    # ── Search section widgets ─────────────────────────────────────────────────

    def _build_search_section(self, sv: QVBoxLayout):
        # Directory row
        dir_row = QHBoxLayout()
        self.lbl_dir = QLabel("No directory selected")
        self.lbl_dir.setObjectName("dirLabel")
        self.lbl_dir.setWordWrap(False)
        self.lbl_dir.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        dir_row.addWidget(self.lbl_dir)
        btn_change = QPushButton("📂")
        btn_change.setObjectName("secondary")
        btn_change.setFixedSize(28, 26)
        btn_change.setToolTip("Change PDF directory")
        btn_change.clicked.connect(self._pick_directory)
        dir_row.addWidget(btn_change)
        sv.addLayout(dir_row)

        # Search bar + k
        sv.addWidget(self._section("SEARCH"))
        search_row = QHBoxLayout()
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search topic across PDFs …")
        self.search_bar.returnPressed.connect(self._do_search)
        search_row.addWidget(self.search_bar)
        self.k_spin = QSpinBox()
        self.k_spin.setRange(1, 20)
        self.k_spin.setValue(5)
        self.k_spin.setPrefix("k=")
        self.k_spin.setToolTip("Number of top PDFs to retrieve")
        search_row.addWidget(self.k_spin)
        btn_search = QPushButton("Search")
        btn_search.clicked.connect(self._do_search)
        search_row.addWidget(btn_search)
        sv.addLayout(search_row)

        # PDF list
        sv.addWidget(self._section("RELEVANT PDFs  ·  click=preview  ·  dbl-click=open"))
        self.pdf_list = QListWidget()
        self.pdf_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.pdf_list.setMinimumHeight(90)
        self.pdf_list.setMaximumHeight(200)
        self.pdf_list.itemClicked.connect(self._on_pdf_clicked)
        self.pdf_list.itemDoubleClicked.connect(self._open_pdf_external)
        sv.addWidget(self.pdf_list)

        # Book badge
        badge_row = QHBoxLayout()
        badge_row.setContentsMargins(0, 2, 0, 0)
        self.lbl_book_badge = QLabel("")
        self.lbl_book_badge.setObjectName("bookBadge")
        self.lbl_book_badge.setVisible(False)
        badge_row.addWidget(self.lbl_book_badge)
        badge_row.addStretch()
        sv.addLayout(badge_row)

    # ── Chat section widgets ───────────────────────────────────────────────────

    def _build_chat_section(self, cv: QVBoxLayout):
        # Header: book badge + toggle button (always visible)
        header = QHBoxLayout()
        self.lbl_book_badge_chat = QLabel("No PDF selected")
        self.lbl_book_badge_chat.setObjectName("bookBadge")
        self.lbl_book_badge_chat.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        header.addWidget(self.lbl_book_badge_chat)

        self.btn_toggle = QPushButton("⛶  Focus")
        self.btn_toggle.setObjectName("toggleBtn")
        self.btn_toggle.setToolTip("Focus mode: hide search, expand PDF+Chat")
        self.btn_toggle.clicked.connect(self._toggle_focus_mode)
        header.addWidget(self.btn_toggle)
        cv.addLayout(header)

        # Chat display
        cv.addWidget(self._section("CHAT"))
        self.chat_display = QTextBrowser()
        self.chat_display.setReadOnly(True)
        self.chat_display.setOpenLinks(True)
        self.chat_display.setOpenExternalLinks(True)
        self.chat_display.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        cv.addWidget(self.chat_display, stretch=1)

        # Question input
        q_row = QHBoxLayout()
        self.question_input = QLineEdit()
        self.question_input.setPlaceholderText("Ask a question about selected PDFs …")
        self.question_input.returnPressed.connect(self._ask_question)
        self.question_input.setEnabled(False)
        q_row.addWidget(self.question_input)
        self.btn_ask = QPushButton("Ask")
        self.btn_ask.setEnabled(False)
        self.btn_ask.setFixedWidth(48)
        self.btn_ask.clicked.connect(self._ask_question)
        q_row.addWidget(self.btn_ask)
        cv.addLayout(q_row)

    def _section(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("sectionHeader")
        return lbl

    # ═══════════════════════════════════════════════════════ focus toggle ══════

    def _toggle_focus_mode(self):
        """
        Normal → Focus: hide search_section → left panel shows chat only,
                        PDF viewer expands.
        Focus  → Normal: show search_section again.
        chat_section and its toggle button are NEVER hidden.
        """
        self._focus_mode = not self._focus_mode
        total = self.splitter.width()

        if self._focus_mode:
            self.search_section.hide()
            self.btn_toggle.setText("⊞  Search")
            self.btn_toggle.setToolTip("Back to Search mode: Search+Chat | PDF")
            # left panel shrinks to just the chat, PDF expands
            self.splitter.setSizes([380, total - 380])
        else:
            self.search_section.show()
            self.btn_toggle.setText("⛶  Focus")
            self.btn_toggle.setToolTip("Focus mode: hide search, expand PDF+Chat")
            self.splitter.setSizes([420, total - 420])

    # ════════════════════════════════════════════════════ directory / index ══

    def _pick_directory(self):
        path = QFileDialog.getExistingDirectory(self, "Select PDF Directory")
        if not path:
            if not self.store:
                self.lbl_dir.setText("⚠️  Click 📂 to select a PDF directory")
                self.lbl_dir.setStyleSheet(
                    "background:#3a2020; border:1px solid #884444;"
                    "border-radius:6px; padding:3px 8px;"
                    "color:#ffaaaa; font-size:11px;"
                )
            return
        self.lbl_dir.setStyleSheet("")
        self._start_indexing(path)

    def _start_indexing(self, directory: str):
        max_len = 38
        display = directory if len(directory) <= max_len else "…" + directory[-(max_len-1):]
        self.lbl_dir.setText(display)
        self.lbl_dir.setToolTip(directory)
        self.search_bar.setEnabled(False)
        self.question_input.setEnabled(False)
        self.btn_ask.setEnabled(False)
        self.pdf_list.clear()
        self._append_chat("system", "🔄 Indexing PDFs …")

        self._index_worker = IndexWorker(directory, parent=self)
        self._index_worker.finished.connect(self._on_index_done)
        self._index_worker.error.connect(self._on_index_error)
        self._index_worker.progress.connect(lambda m: self._append_chat("system", f"  {m}"))
        self._index_worker.start()

    def _on_index_done(self, store, num_pdfs: int):
        self.store = store
        self.search_bar.setEnabled(True)
        self.question_input.setEnabled(True)
        self.btn_ask.setEnabled(True)
        self._append_chat("system", f"✅ {num_pdfs} PDF(s) indexed — ready!\n")
        self.search_bar.setFocus()

    def _on_index_error(self, msg: str):
        self.search_bar.setEnabled(True)
        QMessageBox.critical(self, "Indexing Error", msg)
        self._append_chat("system", f"❌ {msg}\n")

    # ════════════════════════════════════════════════════════════════ search ══

    def _do_search(self):
        if not self.store:
            return
        query = self.search_bar.text().strip()
        if not query:
            return

        from rag.retriever import search_pdfs
        self.pdf_results = search_pdfs(self.store, query, k=self.k_spin.value())
        self.pdf_list.clear()
        self._set_book_badge("")

        if not self.pdf_results:
            self._append_chat("system", "🔍 No relevant PDFs found.\n")
            return

        for r in self.pdf_results:
            item = QListWidgetItem(f"📄  {r['pdf_name']}  ·  p.{r['page']}")
            item.setData(Qt.ItemDataRole.UserRole, r)
            item.setToolTip(r["snippet"])
            self.pdf_list.addItem(item)

        self._append_chat("system", f'🔍 {len(self.pdf_results)} PDF(s) for "{query}".\n')

    # ══════════════════════════════════════════════════════════ PDF actions ══

    def _on_pdf_clicked(self, item: QListWidgetItem):
        r = item.data(Qt.ItemDataRole.UserRole)
        self._set_book_badge(r["pdf_name"])
        try:
            self.pdf_viewer.load(r["pdf_path"], jump_to_page=r["page"])
        except Exception as exc:
            self._append_chat("system", f"⚠️ Could not render PDF: {exc}\n")

    def _open_pdf_external(self, item: QListWidgetItem):
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

    def _set_book_badge(self, name: str):
        if name:
            display = name[:-4] if name.lower().endswith(".pdf") else name
            label   = f"📖  {display}"
            self.lbl_book_badge.setText(label)
            self.lbl_book_badge.setVisible(True)
            self.lbl_book_badge_chat.setText(label)
        else:
            self.lbl_book_badge.setVisible(False)
            self.lbl_book_badge_chat.setText("No PDF selected")

    # ════════════════════════════════════════════════════════════════ Q&A ══

    def _ask_question(self):
        if not self.store:
            return
        question = self.question_input.text().strip()
        if not question:
            return

        selected = self.pdf_list.selectedItems()
        if selected:
            selected_pdfs = [i.data(Qt.ItemDataRole.UserRole)["pdf_name"] for i in selected]
        elif self.pdf_results:
            selected_pdfs = [r["pdf_name"] for r in self.pdf_results]
        else:
            QMessageBox.information(self, "No PDFs", "Search for a topic first.")
            return

        self.question_input.setEnabled(False)
        self.btn_ask.setEnabled(False)
        self._append_chat("user", question)
        self._append_chat("thinking", "⏳  Thinking …")
        self.question_input.clear()

        self._qa_worker = QAWorker(self.store, question, selected_pdfs, parent=self)
        self._qa_worker.finished.connect(self._on_qa_done)
        self._qa_worker.error.connect(self._on_qa_error)
        self._qa_worker.start()

    def _on_qa_done(self, answer: str, video):
        self._remove_thinking_line()
        self._append_chat("assistant", answer)
        if video:
            self._append_raw_html(
                f'<p style="margin:4px 0 12px 14px;color:#f5a623;">'
                f'🎥&nbsp;<b>{self._esc(video["title"])}</b><br>'
                f'<span style="color:{MUTED};">{self._esc(video["channel"])} · {video["duration"]}</span><br>'
                f'<a href="{video["url"]}" style="color:#7ec8e3;">{video["url"]}</a>'
                f'</p>'
            )
        self.question_input.setEnabled(True)
        self.btn_ask.setEnabled(True)
        self.question_input.setFocus()

    def _on_qa_error(self, msg: str):
        self._remove_thinking_line()
        self._append_chat("system", f"❌ {msg}")
        self.question_input.setEnabled(True)
        self.btn_ask.setEnabled(True)

    # ══════════════════════════════════════════════════════════ chat helpers ══

    def _markdown_to_html(self, text: str) -> str:
        text = self._esc(text)
        text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
        text = re.sub(
            r"`(.+?)`",
            r'<code style="background:#1a1a2e;padding:1px 5px;border-radius:3px;'
            r'font-family:monospace;color:#a8d8a8;">\1</code>',
            text,
        )
        text = re.sub(
            r"\[([^\]]+?,\s*p\.\d+)\]",
            r'<span style="background:#2e3a5e;border:1px solid #4a5a8e;'
            r'border-radius:8px;padding:0 6px;font-size:11px;color:#9ab4f0;">[\1]</span>',
            text,
        )
        return text.replace("\n", "<br>")

    def _append_chat(self, role: str, text: str):
        if role == "user":
            body = self._esc(text).replace("\n", "<br>")
            html = (
                f'<p style="margin:10px 0 1px 0;">'
                f'<span style="color:{ACCENT};font-weight:bold;">🧑&nbsp; You</span></p>'
                f'<p style="margin:0 0 4px 14px;color:{TEXT_CLR};">{body}</p>'
            )
        elif role == "assistant":
            body = self._markdown_to_html(text)
            html = (
                f'<p style="margin:10px 0 1px 0;">'
                f'<span style="color:{ACCENT2};font-weight:bold;">🤖&nbsp; Assistant</span></p>'
                f'<p style="margin:0 0 8px 14px;color:{TEXT_CLR};line-height:1.55;">{body}</p>'
            )
        elif role in ("system", "thinking"):
            html = (
                f'<p style="margin:1px 0;color:{MUTED};font-style:italic;">'
                f'{self._esc(text)}</p>'
            )
        else:
            html = f'<p style="margin:2px 0;color:{TEXT_CLR};">{self._esc(text)}</p>'
        self._append_raw_html(html)

    def _append_raw_html(self, html: str):
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.chat_display.setTextCursor(cursor)
        self.chat_display.insertHtml(html)
        self.chat_display.verticalScrollBar().setValue(
            self.chat_display.verticalScrollBar().maximum()
        )

    def _remove_thinking_line(self):
        doc    = self.chat_display.document()
        cursor = QTextCursor(doc)
        cursor.movePosition(QTextCursor.MoveOperation.End)
        for _ in range(30):
            cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
            cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
            if "Thinking" in cursor.selectedText() or "⏳" in cursor.selectedText():
                cursor.removeSelectedText()
                cursor.deleteChar()
                return
            if not cursor.movePosition(QTextCursor.MoveOperation.PreviousBlock):
                return

    @staticmethod
    def _esc(text: str) -> str:
        return (
            text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
        )
