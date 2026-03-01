"""
pdf_viewer.py
An embedded PDF viewer built with PyMuPDF (fitz) + QScrollArea.
Renders pages as images; supports scroll, zoom, and jump-to-page.
"""

import fitz
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QLabel,
    QPushButton, QSpinBox, QSlider, QSizePolicy, QFrame
)
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtCore import Qt


class PDFViewer(QWidget):
    """Renders a PDF file page-by-page inside a scrollable area."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._doc = None
        self._zoom = 1.5          # default zoom factor
        self._current_page = 0
        self._setup_ui()

    # ------------------------------------------------------------------ UI --

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Toolbar
        toolbar = QFrame()
        toolbar.setObjectName("pdfToolbar")
        toolbar.setStyleSheet(
            "#pdfToolbar { background:#2b2b2b; border-bottom:1px solid #444; }"
        )
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(8, 4, 8, 4)

        self.lbl_filename = QLabel("No file open")
        self.lbl_filename.setStyleSheet("color:#ccc; font-weight:bold;")
        tb_layout.addWidget(self.lbl_filename)

        tb_layout.addStretch()

        tb_layout.addWidget(QLabel("<span style='color:#aaa'>Page:</span>"))
        self.spin_page = QSpinBox()
        self.spin_page.setMinimum(1)
        self.spin_page.setMaximum(1)
        self.spin_page.valueChanged.connect(self._on_page_spin_changed)
        self.spin_page.setFixedWidth(60)
        tb_layout.addWidget(self.spin_page)

        self.lbl_total = QLabel("/ 1")
        self.lbl_total.setStyleSheet("color:#aaa;")
        tb_layout.addWidget(self.lbl_total)

        tb_layout.addSpacing(12)

        btn_zoom_out = QPushButton("−")
        btn_zoom_out.setFixedSize(28, 28)
        btn_zoom_out.clicked.connect(self._zoom_out)
        tb_layout.addWidget(btn_zoom_out)

        self.lbl_zoom = QLabel("150%")
        self.lbl_zoom.setStyleSheet("color:#aaa; min-width:40px; text-align:center;")
        tb_layout.addWidget(self.lbl_zoom)

        btn_zoom_in = QPushButton("+")
        btn_zoom_in.setFixedSize(28, 28)
        btn_zoom_in.clicked.connect(self._zoom_in)
        tb_layout.addWidget(btn_zoom_in)

        layout.addWidget(toolbar)

        # Scrollable page area
        self.scroll = QScrollArea()
        self.scroll.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background:#525659; border:none;")

        self.page_container = QWidget()
        self.page_layout = QVBoxLayout(self.page_container)
        self.page_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.page_layout.setSpacing(12)
        self.scroll.setWidget(self.page_container)
        layout.addWidget(self.scroll)

    # --------------------------------------------------------------- public --

    def load(self, pdf_path: str, jump_to_page: int = 1):
        """Open *pdf_path* and optionally jump to *jump_to_page* (1-based)."""
        if self._doc:
            self._doc.close()
        self._doc = fitz.open(pdf_path)
        total = len(self._doc)

        import os
        self.lbl_filename.setText(os.path.basename(pdf_path))
        self.lbl_total.setText(f"/ {total}")
        self.spin_page.blockSignals(True)
        self.spin_page.setMaximum(total)
        self.spin_page.setValue(min(jump_to_page, total))
        self.spin_page.blockSignals(False)

        self._render_all()
        self._scroll_to_page(jump_to_page - 1)

    def jump_to_page(self, page: int):
        """Jump to a 1-based page number without reloading."""
        if self._doc:
            self.spin_page.setValue(page)
            self._scroll_to_page(page - 1)

    # -------------------------------------------------------------- private --

    def _render_all(self):
        """Render every page and populate the scroll area."""
        # Clear existing labels
        while self.page_layout.count():
            item = self.page_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._page_labels = []

        if not self._doc:
            return

        mat = fitz.Matrix(self._zoom, self._zoom)
        for i, page in enumerate(self._doc):
            pix = page.get_pixmap(matrix=mat, alpha=False)
            img = QImage(
                pix.samples, pix.width, pix.height,
                pix.stride, QImage.Format.Format_RGB888
            )
            lbl = QLabel()
            lbl.setPixmap(QPixmap.fromImage(img))
            lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            lbl.setStyleSheet(
                "border:2px solid #333; margin:4px; background:white;"
            )
            self.page_layout.addWidget(lbl)
            self._page_labels.append(lbl)

    def _scroll_to_page(self, index: int):
        """Scroll so that page *index* (0-based) is visible."""
        if not hasattr(self, "_page_labels") or index >= len(self._page_labels):
            return
        lbl = self._page_labels[index]
        self.scroll.ensureWidgetVisible(lbl)

    def _on_page_spin_changed(self, value: int):
        self._scroll_to_page(value - 1)

    def _zoom_in(self):
        self._zoom = min(self._zoom + 0.25, 4.0)
        self.lbl_zoom.setText(f"{int(self._zoom * 100)}%")
        self._render_all()

    def _zoom_out(self):
        self._zoom = max(self._zoom - 0.25, 0.5)
        self.lbl_zoom.setText(f"{int(self._zoom * 100)}%")
        self._render_all()
