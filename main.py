"""
main.py
Entry point for the PDF RAG Desktop Assistant.

Usage:
    python main.py

Requires:
    - OPENAI_API_KEY set in .env (copy .env.example → .env and fill in your key)
    - All packages installed:  pip install -r requirements.txt
"""

import sys
import os
from pathlib import Path

# ── Load .env before importing anything that uses the API key ──────────────────
from dotenv import load_dotenv
load_dotenv()

if not os.getenv("OPENAI_API_KEY"):
    print(
        "\n[ERROR] OPENAI_API_KEY not found.\n"
        "  1. Copy .env.example to .env\n"
        "  2. Add your OpenAI API key\n"
        "  3. Run again.\n"
    )
    sys.exit(1)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from ui.main_window import MainWindow


def main():
    # Enable HiDPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("PDF Research Assistant")
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
