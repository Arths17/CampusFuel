"""
HealthOS — Session Memory & Daily Check-in

Logs daily check-ins to  logs/{username}/YYYY-MM-DD.json
Provides 7-day history context injected into every Ollama seed message.
The AI can then reference real trends: "last Tuesday your energy was 3/10..."
"""

import os
import re
import json
from typing import Optional
from datetime import datetime, timedelta

_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGS_DIR    = os.path.join(_MODULE_DIR, "..", "logs")


# ──────────────────────────────────────────────
# STORAGE
# ──────────────────────────────────────────────

def _user_log_dir(username: str) -> str:
    safe = re.sub(r"[^\w\-]", "_", (username or "default").lower())
    path = os.path.join(LOGS_DIR, safe)
    os.makedirs(path, exist_ok=True)
    return path


def save_checkin(username: str, data: dict) -> None:
    """Merge `data` into today's log file (creates file if needed)."""
    log_dir  = _user_log_dir(username)
    today    = data.get("date") or datetime.now().strftime("%Y-%m-%d")
    path     = os.path.join(log_dir, f"{today}.json")
    existing: dict = {}
    if os.path.exists(path):
        try:
            with open(path) as fh:
                existing = json.load(fh)
        except Exception:
            pass
    existing.update(data)
    with open(path, "w") as fh:
        json.dump(existing, fh, indent=2)


def load_recent_logs(username: str, days: int = 7) -> list:
    """Load the last `days` days of logs. Returns list newest-first."""
    log_dir = _user_log_dir(username)
    logs    = []
    for i in range(days):
        date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        path = os.path.join(log_dir, f"{date}.json")
        if os.path.exists(path):
            try:
                with open(path) as fh:
                    entry         = json.load(fh)
                    entry["date"] = date
                    logs.append(entry)
            except Exception:
                pass
    return logs


# ──────────────────────────────────────────────
# CONTEXT FORMATTER
# ──────────────────────────────────────────────

def format_memory_context(logs: list) -> str:
    """
    Format recent logs into a compact context block for AI injection.
    Returns empty string if no logs exist yet.
    """
    if not logs:
        return ""

    lines = [
        "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "  YOUR RECENT HISTORY (last 7 days):",
    ]

    for log in reversed(logs):       # oldest → newest
        date    = log.get("date", "?")
        mood    = log.get("mood", "?")
        energy  = log.get("energy", "?")
        sleep_h = log.get("sleep_hours", "?")
        notes   = (log.get("notes") or "").strip()
        protos  = ", ".join((log.get("protocols") or [])[:2])

        line = f"    {date}:  mood={mood}  energy={energy}/10  sleep={sleep_h}h"
        if protos:
            line += f"  protocols=[{protos}]"
        lines.append(line)
        if notes:
            lines.append(f"              note: {notes[:90]}")

    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    return "\n".join(lines)


# ──────────────────────────────────────────────
# DAILY CHECK-IN
# ──────────────────────────────────────────────

_MOOD_MAP = {
    "lo": "low", "bad": "low", "sad": "low", "down": "low",
    "terrible": "low", "awful": "low", "rough": "low",
    "ok": "neutral", "okay": "neutral", "fine": "neutral",
    "meh": "neutral", "alright": "neutral", "so-so": "neutral",
    "good": "good", "great": "good", "amazing": "good", "awesome": "good",
    "happy": "good", "well": "good",
}


def run_checkin(profile: dict) -> dict:
    """
    3-question fast daily check-in.
    Returns a dict with mood, energy, sleep_hours, notes, date, timestamp.
    """
    print("\n⚡  Quick Check-in (3 questions)\n")

    # 1 — Mood
    raw_mood = input("  💭  Mood right now?  (low / neutral / good)\n  ▶  ").strip().lower()
    mood     = _MOOD_MAP.get(raw_mood, raw_mood if raw_mood in ("low", "neutral", "good") else "neutral")

    # 2 — Energy
    raw_e = input("\n  ⚡  Energy level?  (1–10)\n  ▶  ").strip()
    try:
        energy = max(1, min(10, int(round(float(raw_e)))))
    except ValueError:
        energy = 5

    # 3 — Sleep hours as a plain number
    raw_s = input("\n  😴  How many hours did you sleep last night?\n  ▶  ").strip()
    try:
        sleep_h: Optional[float] = round(float(raw_s), 1)
    except ValueError:
        sleep_h = None

    notes = input("\n  📝  Anything to note?  (press Enter to skip)\n  ▶  ").strip()

    return {
        "mood":        mood,
        "energy":      energy,
        "sleep_hours": sleep_h,
        "notes":       notes or "",
        "date":        datetime.now().strftime("%Y-%m-%d"),
        "timestamp":   datetime.now().isoformat(),
    }
