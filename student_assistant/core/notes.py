"""
notes.py

"""

import json
import re
import os
from datetime import datetime
from pathlib import Path
import requests

NOTES_DIR  = Path(__file__).parent.parent / "data" / "notes"
INDEX_FILE = NOTES_DIR / "index.json"


def _load_index() -> list:
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    if INDEX_FILE.exists():
        try:
            return json.loads(INDEX_FILE.read_text())
        except Exception:
            return []
    return []


def _save_index(index: list):
    INDEX_FILE.write_text(json.dumps(index, indent=2))


def save_note(content: str, title: str = "", subject: str = "") -> dict:
    """Note save karo (voice ya typed)"""
    timestamp = datetime.now()
    note_id   = int(timestamp.timestamp() * 1000)

    
    if not title:
        words = content.split()[:5]
        title = " ".join(words).title() + "..."

    
    if not subject:
        subjects = ["physics", "math", "chemistry", "biology", "history",
                    "geography", "english", "computer", "python", "ai", "ml"]
        for s in subjects:
            if s in content.lower():
                subject = s.title()
                break
        subject = subject or "General"

    note = {
        "id": note_id,
        "title": title,
        "subject": subject,
        "content": content,
        "created": timestamp.isoformat(),
        "word_count": len(content.split()),
    }

    # Save to individual file
    note_file = NOTES_DIR / f"note_{note_id}.json"
    note_file.write_text(json.dumps(note, indent=2))

    # Update index
    index = _load_index()
    index.insert(0, {  # newest first
        "id": note_id,
        "title": title,
        "subject": subject,
        "created": timestamp.isoformat(),
        "file": str(note_file),
    })
    _save_index(index)

    return {"success": True, "id": note_id, "title": title, "subject": subject}


def get_note(note_id: int) -> dict | None:
    note_file = NOTES_DIR / f"note_{note_id}.json"
    if note_file.exists():
        return json.loads(note_file.read_text())
    return None


def get_all_notes(subject: str = "", limit: int = 20) -> list:
    index = _load_index()
    if subject:
        index = [n for n in index if n.get("subject", "").lower() == subject.lower()]
    return index[:limit]


def search_notes(query: str) -> list:

    results = []
    index = _load_index()
    query_lower = query.lower()
    for entry in index:
        note_file = NOTES_DIR / f"note_{entry['id']}.json"
        if note_file.exists():
            note = json.loads(note_file.read_text())
            if (query_lower in note["title"].lower() or
                query_lower in note["content"].lower() or
                query_lower in note.get("subject", "").lower()):
                results.append(note)
    return results


def delete_note(note_id: int) -> bool:
    note_file = NOTES_DIR / f"note_{note_id}.json"
    if note_file.exists():
        note_file.unlink()
    index = _load_index()
    index = [n for n in index if n["id"] != note_id]
    _save_index(index)
    return True


def enhance_note_with_ai(content: str) -> str:
    import os
    import requests
    from dotenv import load_dotenv
    load_dotenv()

    api_key = os.getenv("GROQ_API_KEY", "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")
    if not api_key:
        return content

    prompt = f"""Convert this raw note into a clean structured study note:
Raw note: "{content}"

Format:
Topic: [main topic]
Key Points:
- point 1
- point 2
Summary: [1-2 lines]

Plain text only."""

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
                    {"role": "system", "content": "You are a helpful study assistant."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 400
            },
            timeout=20,
        )
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except Exception:
        return content


def format_notes_list(notes: list) -> str:
    if not notes:
        return "Koi notes nahi mile."
    lines = ["📝 Your Notes:"]
    for i, n in enumerate(notes, 1):
        dt = datetime.fromisoformat(n["created"]).strftime("%d %b, %I:%M %p")
        lines.append(f"  {i}. [{n['subject']}] {n['title']} — {dt}")
    return "\n".join(lines)


# ── Test ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    result = save_note(
        content="Photosynthesis is the process where plants use sunlight water and carbon dioxide to make glucose and oxygen",
        subject="Biology"
    )
    print(f"Saved: {result}")

    all_notes = get_all_notes()
    print(format_notes_list(all_notes))