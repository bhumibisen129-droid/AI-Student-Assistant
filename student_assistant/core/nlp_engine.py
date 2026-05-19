"""
nlp_engine.py
Student ke commands ko samjho — kya karna chahte hain?
Pure rule-based (fast, offline, no API needed for intent)
"""

import re
from dataclasses import dataclass, field
from typing import Optional


# ── Intent definitions ───────────────────────────────────────────────────────
INTENT_PATTERNS = {
    "summarize_pdf": [
        r"\b(summarize|summary|summarise|explain|describe)\b.*(pdf|document|file|notes|chapter)",
        r"(pdf|document|file).*(summarize|summary|explain)",
        r"\bsum up\b",
    ],
    "set_reminder": [
        r"\b(remind|reminder|alert|notify|don't let me forget)\b",
        r"remind me (to|about|at)",
        r"set (a |an )?(reminder|alarm|alert)",
    ],
    "show_reminders": [
        r"\b(show|list|what are|tell me).*(reminder|alarm|schedule)",
        r"(my |all )?(reminders|alerts)",
    ],
    "add_timetable": [
        r"\b(add|set|schedule|put|create)\b.*(class|lecture|timetable|subject|period)",
        r"(class|lecture).*(at|on|every)",
    ],
    "show_timetable": [
        r"\b(show|what is|tell me|display)\b.*(timetable|schedule|class|today)",
        r"(today'?s?|tomorrow'?s?).*(class|lecture|schedule)",
        r"when (is|are) (my |the )?(class|lecture)",
    ],
    "take_notes": [
        r"\b(take|make|create|write|save|note)\b.*(note|notes)",
        r"(note (this|that|down)|remember this)",
        r"write (this|that) down",
    ],
    "show_notes": [
        r"\b(show|read|open|get|find)\b.*(note|notes)",
        r"(my |all |recent )notes",
    ],
    "ask_question": [
        r"^(what|who|when|where|why|how|which|whose|whom)\b",
        r"\b(explain|define|tell me about|what is|what are|how does|how do)\b",
        r"\?$",
    ],
    "delete_reminder": [
        r"\b(delete|remove|cancel|clear)\b.*(reminder|alarm|alert)",
    ],
    "greet": [
        r"^\s*(hi|hello|hey|good morning|good evening|good afternoon|namaste|hii)\s*[!.,]*\s*$",
        r"^\s*(how are you|what's up|sup)\s*[?!.,]*\s*$",
    ],
    "stop": [
        r"^\s*(stop|exit|quit|bye|goodbye|close|shut down|band karo)\s*[!.,]*\s*$",
    ],
    "help": [
        r"\b(help|what can you do|features|commands|options)\b",
    ],
}

# ── Entity extractors ────────────────────────────────────────────────────────
ENTITY_PATTERNS = {
    "time":    r"\b(\d{1,2}[:.]\d{2}\s*(?:am|pm)?|\d{1,2}\s*(?:am|pm)|tomorrow|today|tonight|morning|evening|night)\b",
    "subject": r"\b(math|maths|physics|chemistry|biology|english|hindi|history|geography|science|computer|programming|python|ml|ai|data science)\b",
    "day":     r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday|mon|tue|wed|thu|fri|sat|sun)\b",
    "number":  r"\b(\d+)\b",
}

WAKE_WORDS = ["hey assistant", "ok assistant", "assistant", "jarvis", "hello assistant"]


@dataclass
class NLPResult:
    text: str
    intent: str
    confidence: str          # high / medium / low
    entities: dict = field(default_factory=dict)
    remainder: str = ""      # text after removing command words


def classify_intent(text: str) -> tuple[str, str]:
    lower = text.lower().strip()
    scores = {}
    for intent, patterns in INTENT_PATTERNS.items():
        hits = sum(1 for p in patterns if re.search(p, lower, re.IGNORECASE))
        if hits:
            scores[intent] = hits
    if not scores:
        # Default: agar sentence mein question mark hai ya wh-word hai → question
        if "?" in text or re.match(r"^(what|who|when|where|why|how)", lower):
            return "ask_question", "medium"
        return "ask_question", "low"
    top = max(scores, key=scores.get)
    conf = "high" if scores[top] >= 2 else "medium"
    return top, conf


def extract_entities(text: str) -> dict:
    entities = {}
    lower = text.lower()
    for name, pattern in ENTITY_PATTERNS.items():
        m = re.search(pattern, lower, re.IGNORECASE)
        if m:
            entities[name] = m.group(0).strip()
    return entities


def get_remainder(text: str, intent: str) -> str:
    """Command words hata ke actual content nikalo"""
    removals = {
        "summarize_pdf": r"\b(summarize|summary|summarise|explain|the|pdf|document|file|please)\b",
        "set_reminder":  r"\b(remind|reminder|me|to|set|a|an|please)\b",
        "take_notes":    r"\b(take|make|create|write|save|a|note|notes|note down|please)\b",
        "ask_question":  r"\b(tell me about|explain|define|what is|what are|please)\b",
    }
    pattern = removals.get(intent)
    if pattern:
        cleaned = re.sub(pattern, "", text, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r'\s+', ' ', cleaned)
        return cleaned
    return text


def analyse(text: str) -> NLPResult:
    intent, confidence = classify_intent(text)
    entities = extract_entities(text)
    remainder = get_remainder(text, intent)
    return NLPResult(
        text=text,
        intent=intent,
        confidence=confidence,
        entities=entities,
        remainder=remainder,
    )


def detect_wake_word(text: str) -> bool:
    lower = text.lower()
    return any(w in lower for w in WAKE_WORDS)


def strip_wake_word(text: str) -> str:
    lower = text.lower()
    for w in WAKE_WORDS:
        lower = lower.replace(w, "").strip()
    # Restore original casing roughly
    return text[len(text) - len(lower):].strip() if lower else text


# ── Test ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    tests = [
        "Summarize this PDF for me",
        "Remind me to submit assignment at 5pm",
        "What is Newton's second law?",
        "Add Physics class on Monday at 10am",
        "Show my timetable for today",
        "Take notes: Photosynthesis is the process by which plants make food",
        "Show my reminders",
        "Hello!",
    ]
    for t in tests:
        r = analyse(t)
        print(f"Input:    {t}")
        print(f"Intent:   {r.intent} ({r.confidence})")
        print(f"Entities: {r.entities}")
        print(f"Content:  {r.remainder}")
        print()