# 📚 PDF Research Assistant

A desktop application that lets you **semantically search** a folder of PDFs and **chat with them** using GPT-4o — with page-level citations and related YouTube video suggestions.

---

## Features

| Feature | Details |
|---|---|
| PDF directory picker | Validates that PDFs exist before indexing |
| Semantic search | FAISS + OpenAI embeddings, returns top-k unique PDFs |
| Embedded PDF viewer | Zoom, scroll, jump to cited page — all inside the app |
| External PDF open | Double-click any result to open in your system viewer |
| Multi-PDF Q&A | Select one or more PDFs, ask anything |
| Cited answers | Every claim includes `[filename, p.N]` |
| Video suggestions | Relevant YouTube link fetched automatically |

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Set your OpenAI API key

```bash
.env
# Edit .env and paste your key
```

### 3. Run

```bash
python main.py
```

---

## 🗂 Project Structure

```
pdf-rag-desktop/
├── main.py                  # Entry point
├── requirements.txt
├── .env            # add your key here 
│
├── ui/
│   ├── main_window.py       # Full application UI
│   ├── pdf_viewer.py        # Embedded PDF viewer (fitz-rendered)
│   └── workers.py           # Background QThread workers
│
├── rag/
│   ├── indexer.py           # PDF loading + chunking (PyMuPDF)
│   ├── embedder.py          # FAISS vector store (OpenAI embeddings)
│   ├── retriever.py         # Semantic search
│   └── qa_chain.py          # GPT-4o Q&A with citations
│
├── utils/
│   └── video_search.py      # YouTube video lookup
│
└── data/
    └── vector_store/        # Persisted FAISS index (auto-created)
```

---

## How to Use

### Step 1 — Pick a PDF directory
On launch, a folder picker appears. Choose any folder that contains `.pdf` files.
The app will **index and embed** all PDFs automatically (one-time per folder).

### Step 2 — Search for a topic
Type a topic (e.g. *"transformer attention mechanism"*) and press **Search** or Enter.
Set `k = N` to control how many PDFs are retrieved.

**Single-click** a result to preview it in the embedded viewer.
**Double-click** a result to open it in your system PDF reader.

### Step 3 — Ask questions
Select one or more PDFs in the list (or leave all selected by default), type a question, and press **Ask**.

The answer will include:
- Cited page references like `[paper.pdf, p.12]`
- A 🎥 YouTube video link related to the topic

---

## ⚙️ Configuration

| Setting | Where | Default |
|---|---|---|
| `k` (top PDFs) | Spin box in UI | 5 |
| Chunk size | `rag/indexer.py` → `chunk_size` | 500 tokens |
| Chunk overlap | `rag/indexer.py` → `chunk_overlap` | 60 tokens |
| GPT model | `rag/qa_chain.py` → `model` | `gpt-4o` |
| Embedding model | `rag/embedder.py` | `text-embedding-3-small` |
| Index save path | `rag/embedder.py` → `STORE_PATH` | `data/vector_store` |

---

## Re-indexing

The FAISS index is **persisted** to `data/vector_store/`. If you add new PDFs to your folder, delete `data/vector_store/` and restart to re-index.

Future enhancement: automatic change detection.

---

## Tips

- **Select specific PDFs** before asking to get more focused answers.
- Use descriptive topic searches (e.g. *"neural network training"* not just *"neural"*).
- The embedded viewer auto-jumps to the most relevant page from your search.
- Answers only use content from your PDFs — no hallucination from outside sources.

---

## 🔧 Swap to a Local Model (no API key)

Replace `ChatOpenAI` in `rag/qa_chain.py` and `OpenAIEmbeddings` in `rag/embedder.py` with Ollama equivalents:

```python
# pip install langchain-ollama
from langchain_ollama import ChatOllama, OllamaEmbeddings

llm = ChatOllama(model="llama3.1")
embeddings = OllamaEmbeddings(model="nomic-embed-text")
```

Then run `ollama pull llama3.1` and `ollama pull nomic-embed-text`.

## Desktop Application 
```
https://drive.google.com/drive/folders/1F1iNknbhLT59SvA6yD5fM-U19j_-1qJR?usp=drive_link
```
You can Directly Copy the link and download the application. Just paste your openAI api in `.env `.

