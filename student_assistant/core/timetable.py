"""
timetable.py
Class schedule manage  — add, show, today's classes
"""

import json
import re
from datetime import datetime
from pathlib import Path

TIMETABLE_FILE = Path(__file__).parent.parent / "data" / "timetable.json"

DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
DAY_SHORT = {"mon": "monday", "tue": "tuesday", "wed": "wednesday",
             "thu": "thursday", "fri": "friday", "sat": "saturday", "sun": "sunday"}


def _load() -> dict:
    TIMETABLE_FILE.parent.mkdir(exist_ok=True)
    if TIMETABLE_FILE.exists():
        try:
            return json.loads(TIMETABLE_FILE.read_text())
        except Exception:
            return {d: [] for d in DAYS}
    return {d: [] for d in DAYS}


def _save(tt: dict):
    TIMETABLE_FILE.write_text(json.dumps(tt, indent=2))


def _parse_day(text: str) -> str | None:
    text = text.lower().strip()
    if text in DAYS:
        return text
    if text in DAY_SHORT:
        return DAY_SHORT[text]
    for day in DAYS:
        if day in text:
            return day
    return None


def _parse_time_slot(text: str) -> str:
    """Extract time string from text"""
    m = re.search(r'(\d{1,2}(?::\d{2})?\s*(?:am|pm)?(?:\s*[-–to]+\s*\d{1,2}(?::\d{2})?\s*(?:am|pm)?)?)', text, re.IGNORECASE)
    return m.group(0).strip() if m else "TBD"


def add_class(subject: str, day: str, time_slot: str, teacher: str = "") -> dict:
    """Timetable mein class add karo"""
    parsed_day = _parse_day(day)
    if not parsed_day:
        return {"success": False, "error": f"Invalid day: '{day}'"}

    tt = _load()
    entry = {
        "id": int(datetime.now().timestamp() * 1000),
        "subject": subject.title(),
        "time": time_slot,
        "teacher": teacher,
    }
    tt[parsed_day].append(entry)
    # Sort by time
    tt[parsed_day].sort(key=lambda x: x["time"])
    _save(tt)

    return {
        "success": True,
        "subject": subject.title(),
        "day": parsed_day.capitalize(),
        "time": time_slot,
    }


def get_today_classes() -> list:
    today = DAYS[datetime.now().weekday()]
    tt = _load()
    return tt.get(today, [])


def get_day_classes(day: str) -> list:
    parsed = _parse_day(day)
    if not parsed:
        return []
    tt = _load()
    return tt.get(parsed, [])


def get_full_timetable() -> dict:
    return _load()


def delete_class(class_id: int) -> bool:
    tt = _load()
    changed = False
    for day in DAYS:
        original = len(tt[day])
        tt[day] = [c for c in tt[day] if c["id"] != class_id]
        if len(tt[day]) < original:
            changed = True
    if changed:
        _save(tt)
    return changed


def parse_add_class_from_text(text: str) -> dict:
    """
    Natural language se class info extract karo:
    "Add Physics class on Monday at 10am"
    """
    subjects = ["math", "maths", "physics", "chemistry", "biology", "english",
                "hindi", "history", "geography", "science", "computer",
                "programming", "python", "machine learning", "data science", "ai"]

    subject = "Unknown"
    for s in subjects:
        if s in text.lower():
            subject = s.title()
            break

    day = "monday"
    for d in DAYS:
        if d in text.lower():
            day = d
            break
    for short, full in DAY_SHORT.items():
        if short in text.lower():
            day = full
            break

    time_slot = _parse_time_slot(text)

    return {"subject": subject, "day": day, "time": time_slot}


def format_classes(classes: list, day_label: str = "") -> str:
    if not classes:
        label = f"{day_label} " if day_label else ""
        return f"{label}Koi class nahi hai."
    lines = [f"📅 {day_label} Classes:" if day_label else "📅 Classes:"]
    for c in classes:
        teacher = f" | {c['teacher']}" if c.get("teacher") else ""
        lines.append(f"  • {c['time']} — {c['subject']}{teacher}")
    return "\n".join(lines)


# ── Test ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Add sample classes
    add_class("Physics", "monday", "9:00 AM - 10:00 AM", "Mr. Sharma")
    add_class("Math", "monday", "10:00 AM - 11:00 AM", "Ms. Gupta")
    add_class("Chemistry", "tuesday", "11:00 AM - 12:00 PM")

    today = get_today_classes()
    print(format_classes(today, "Today's"))

    full = get_full_timetable()
    for day, classes in full.items():
        if classes:
            print(f"\n{day.capitalize()}:")
            for c in classes:
                print(f"  {c['time']} — {c['subject']}")