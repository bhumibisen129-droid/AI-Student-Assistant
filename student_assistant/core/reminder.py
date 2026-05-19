"""
reminder.py
Reminders set karo, store karo, aur sahi time pe alert doo
Uses: threading + JSON storage
"""

import json
import threading
import time
import re
from datetime import datetime, timedelta
from pathlib import Path

REMINDERS_FILE = Path(__file__).parent.parent / "data" / "reminders.json"


def _load() -> list:
    REMINDERS_FILE.parent.mkdir(exist_ok=True)
    if REMINDERS_FILE.exists():
        try:
            return json.loads(REMINDERS_FILE.read_text())
        except Exception:
            return []
    return []


def _save(reminders: list):
    REMINDERS_FILE.write_text(json.dumps(reminders, indent=2))


def _parse_time(text: str) -> datetime | None:
    """
    Natural language time parse karo:
    "5pm", "5:30pm", "17:00", "in 10 minutes", "tomorrow 9am"
    """
    now = datetime.now()
    text = text.lower().strip()

    # "in X minutes/hours"
    m = re.search(r'in (\d+) (minute|minutes|hour|hours)', text)
    if m:
        val = int(m.group(1))
        unit = m.group(2)
        delta = timedelta(minutes=val) if 'minute' in unit else timedelta(hours=val)
        return now + delta

    # "tomorrow at HH:MM am/pm"
    base_date = now.date()
    if 'tomorrow' in text:
        base_date = (now + timedelta(days=1)).date()

    # HH:MM am/pm  or  H am/pm
    m = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)', text)
    if m:
        hour   = int(m.group(1))
        minute = int(m.group(2)) if m.group(2) else 0
        period = m.group(3)
        if period == 'pm' and hour != 12:
            hour += 12
        elif period == 'am' and hour == 12:
            hour = 0
        try:
            dt = datetime(base_date.year, base_date.month, base_date.day, hour, minute)
            if dt < now:
                dt += timedelta(days=1)   # next day agar past mein hai
            return dt
        except ValueError:
            return None

    # 24-hour: 17:30
    m = re.search(r'(\d{1,2}):(\d{2})(?!\s*[ap]m)', text)
    if m:
        hour, minute = int(m.group(1)), int(m.group(2))
        try:
            dt = datetime(base_date.year, base_date.month, base_date.day, hour, minute)
            if dt < now:
                dt += timedelta(days=1)
            return dt
        except ValueError:
            return None

    return None


def add_reminder(message: str, time_str: str, callback=None) -> dict:
    """
    Reminder add karo aur background thread start karo
    callback(message) jab time aaye
    """
    dt = _parse_time(time_str)
    if dt is None:
        return {"success": False, "error": f"Could not parse time: '{time_str}'"}

    reminder = {
        "id": int(time.time() * 1000),
        "message": message,
        "time": dt.isoformat(),
        "created": datetime.now().isoformat(),
        "triggered": False,
    }

    reminders = _load()
    reminders.append(reminder)
    _save(reminders)

    # Start watcher thread
    _start_watcher(reminder, callback)

    return {
        "success": True,
        "message": message,
        "time": dt.strftime("%I:%M %p, %d %b %Y"),
        "id": reminder["id"],
    }


def _start_watcher(reminder: dict, callback):
    """Background thread jo reminder ke time pe fire karta hai"""
    def _watch():
        target = datetime.fromisoformat(reminder["time"])
        while True:
            now = datetime.now()
            diff = (target - now).total_seconds()
            if diff <= 0:
                # Mark triggered
                reminders = _load()
                for r in reminders:
                    if r["id"] == reminder["id"]:
                        r["triggered"] = True
                _save(reminders)
                if callback:
                    callback(reminder["message"])
                break
            elif diff > 60:
                time.sleep(30)
            else:
                time.sleep(1)

    t = threading.Thread(target=_watch, daemon=True)
    t.start()


def get_reminders(include_triggered: bool = False) -> list:
    """Saare reminders return karo"""
    reminders = _load()
    if not include_triggered:
        reminders = [r for r in reminders if not r["triggered"]]
    # Sort by time
    reminders.sort(key=lambda r: r["time"])
    return reminders


def delete_reminder(reminder_id: int) -> bool:
    reminders = _load()
    original_len = len(reminders)
    reminders = [r for r in reminders if r["id"] != reminder_id]
    _save(reminders)
    return len(reminders) < original_len


def format_reminders_text(reminders: list) -> str:
    """Human-readable format mein reminders"""
    if not reminders:
        return "Koi reminder nahi hai abhi."
    lines = []
    for i, r in enumerate(reminders, 1):
        dt = datetime.fromisoformat(r["time"])
        time_str = dt.strftime("%I:%M %p, %d %b")
        lines.append(f"{i}. {r['message']} — at {time_str}")
    return "\n".join(lines)


def restore_reminders_on_startup(callback):
    """App restart hone pe pending reminders restore karo"""
    reminders = get_reminders()
    now = datetime.now()
    restored = 0
    for r in reminders:
        target = datetime.fromisoformat(r["time"])
        if target > now:
            _start_watcher(r, callback)
            restored += 1
    print(f"[Reminders] Restored {restored} pending reminders")


# ── Test ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    def on_trigger(msg):
        print(f"\n🔔 REMINDER: {msg}\n")

    result = add_reminder("Study Physics chapter 3", "in 1 minutes", callback=on_trigger)
    print(f"Added: {result}")

    all_r = get_reminders()
    print(f"\nAll reminders:\n{format_reminders_text(all_r)}")

    print("\nWaiting for reminder...")
    time.sleep(75)