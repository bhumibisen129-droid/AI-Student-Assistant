"""
pdf_handler.py
PDF upload karo → NLP se summarize karo → voice mein sunao
Uses: PyMuPDF (fitz) for extraction, Claude API for summarization
"""

import fitz          # PyMuPDF
import os
import re
from pathlib import Path


def extract_text_from_pdf(pdf_path: str) -> str:
    """PDF ke saare pages se text nikalo"""
    try:
        doc = fitz.open(pdf_path)
        full_text = []
        for page_num, page in enumerate(doc, 1):
            text = page.get_text("text")
            if text.strip():
                full_text.append(f"--- Page {page_num} ---\n{text}")
        doc.close()
        return "\n\n".join(full_text)
    except Exception as e:
        return f"Error reading PDF: {e}"


def chunk_text(text: str, max_chars: int = 6000) -> list[str]:
    """
    Bade documents ko chunks mein toddo
    taaki Claude API ka context limit na toote
    """
    paragraphs = text.split('\n\n')
    chunks = []
    current = ""
    for para in paragraphs:
        if len(current) + len(para) < max_chars:
            current += para + "\n\n"
        else:
            if current:
                chunks.append(current.strip())
            current = para + "\n\n"
    if current:
        chunks.append(current.strip())
    return chunks if chunks else [text[:max_chars]]


def clean_text(text: str) -> str:
    """Unnecessary whitespace aur symbols hataao"""
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)
    return text.strip()


async def summarize_with_claude(text: str, topic: str = "") -> str:
    """
    Claude API se summary lo (async).
    Ye function main.py se call hoga jahaan httpx available hai.
    """
    import httpx

    topic_hint = f"The document is about: {topic}." if topic else ""
    prompt = f"""You are a helpful AI assistant for students.

{topic_hint}

Summarize the following study material clearly and concisely for a student:
- Start with a 2-line overview
- List the 5 most important key points as bullet points  
- End with "Key terms to remember:" and list important terms

Keep the language simple and easy to understand.

Document content:
{text[:5000]}"""

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={"Content-Type": "application/json"},
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 1000,
                    "messages": [{"role": "user", "content": prompt}]
                }
            )
            data = response.json()
            return data["content"][0]["text"]
    except Exception as e:
        return f"Summary error: {e}"


def summarize_sync(text: str, topic: str = "") -> str:
    import os
    import requests
    from dotenv import load_dotenv
    load_dotenv()

    api_key = os.getenv("GROQ_API_KEY", "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")
    if not api_key:
        return "GROQ_API_KEY missing hai."

    topic_hint = f"The document is about: {topic}." if topic else ""
    prompt = f"""{topic_hint}
Summarize this study material for a student:
- 2 line overview
- 5 key bullet points
- Key terms to remember

Content: {text[:5000]}"""

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama3-8b-8192",
                "messages": [
                    {"role": "system", "content": "You are a helpful study assistant for students."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 800
            },
            timeout=30,
        )
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Could not summarize: {e}"


def process_pdf(pdf_path: str, topic: str = "") -> dict:
    """
    Full pipeline:
    PDF path → extract → clean → summarize → return dict
    """
    if not os.path.exists(pdf_path):
        return {"success": False, "error": "File not found", "summary": "", "raw_text": ""}

    print(f"[PDF] Reading: {pdf_path}")
    raw_text = extract_text_from_pdf(pdf_path)

    if not raw_text.strip() or raw_text.startswith("Error"):
        return {"success": False, "error": "Could not read PDF", "summary": "", "raw_text": ""}

    cleaned = clean_text(raw_text)
    word_count = len(cleaned.split())
    print(f"[PDF] Extracted {word_count} words")

    print("[PDF] Summarizing...")
    summary = summarize_sync(cleaned, topic)

    return {
        "success": True,
        "file_name": Path(pdf_path).name,
        "word_count": word_count,
        "page_count": raw_text.count("--- Page"),
        "summary": summary,
        "raw_text": cleaned[:2000],   # first 2000 chars for Q&A context
    }


# ── Test ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "test.pdf"
    result = process_pdf(path)
    if result["success"]:
        print(f"\n📄 File: {result['file_name']}")
        print(f"📊 Words: {result['word_count']} | Pages: {result['page_count']}")
        print(f"\n📝 Summary:\n{result['summary']}")
    else:
        print(f"❌ Error: {result['error']}")