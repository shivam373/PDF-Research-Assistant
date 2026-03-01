"""
qa_chain.py
Answers questions using GPT-4o, grounded exclusively in retrieved PDF chunks.
Responses include [filename, p.N] citations for every claim.
"""

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.vectorstores import FAISS

from rag.retriever import search_within_pdfs


SYSTEM_PROMPT = """You are a precise research assistant. Answer the user's question
using ONLY the PDF context provided below. Do not use any outside knowledge.

Rules:
1. Every factual claim MUST be followed by a citation in the format [filename, p.N].
2. If multiple chunks support a claim, cite all of them.
3. If the answer cannot be found in the context, say:
   "I couldn't find information about this in the selected PDFs."
4. Be concise but thorough. Use bullet points for multi-part answers.
5. At the very end, list the unique source PDFs you cited under "📚 Sources Used:".

Context:
{context}
"""

QA_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        ("human", "{question}"),
    ]
)


def answer_question(
    store: FAISS,
    question: str,
    selected_pdfs: list[str],
    k: int = 8,
    model: str = "gpt-4o",
) -> str:
    """
    Generate a cited answer to *question* using only *selected_pdfs*.

    Returns the answer as a plain string (markdown-friendly).
    """
    chunks = search_within_pdfs(store, question, selected_pdfs, k=k)

    if not chunks:
        return "⚠️ No relevant content found in the selected PDFs for this question."

    # Build context block with clear source labels
    context_parts = []
    for c in chunks:
        header = f"[{c['pdf_name']}, p.{c['page']}]"
        context_parts.append(f"{header}\n{c['text']}")
    context = "\n\n---\n\n".join(context_parts)

    llm = ChatOpenAI(model=model, temperature=0)
    chain = QA_PROMPT | llm
    response = chain.invoke({"context": context, "question": question})
    return response.content
