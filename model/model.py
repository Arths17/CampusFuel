"""
HealthOS v3.0 — Personal Health Intelligence System for College Students
Upgrades: Input Validation · Confidence Scoring · Risk Classification · Priority Engine · Gemini AI
Run:  .venv/bin/python model/model.py
"""

import os
import re
import json
import textwrap
import sys
import google.generativeai as genai
from datetime import datetime
# Add model/ directory to path so we can import nutrition_db / user_state
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nutrition_db
import user_state
import rag
import session_memory

# ──────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────
# Gemini model
MODEL_NAME   = os.environ.get("HEALTH_MODEL", "gemini-2.0-flash-lite")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyAZvLurB1gnxuu92p2CDdFcNH4EoQ2pNc0")
PROFILE_FILE = "user_profile.json"

# Global flag accumulator (populated during onboarding)
DATA_FLAGS: list = []

# ──────────────────────────────────────────────
# SYSTEM PROMPT
# ──────────────────────────────────────────────
SYSTEM_PROMPT = """
You are HealthOS — a medical-grade AI health optimization system for college students.

You are NOT a diet planner. You are a personal health intelligence engine.
You build lifestyle architecture — stability, performance, and resilience.

========================
INTELLIGENCE LAYERS
========================
Layer 1 – Nutritional Intelligence:
  Macro balancing, micro-nutrients, energy metabolism, hydration, gut health.

Layer 2 – Psychological Intelligence:
  Emotional eating, stress patterns, motivation modeling, burnout prevention,
  dopamine regulation.

Layer 3 – Behavioral Intelligence:
  Habit stacking, friction reduction, decision fatigue reduction, automation,
  routine building.

Layer 4 – Academic Optimization:
  Brain energy management, focus nutrition, memory nutrition, exam-period
  adaptation, sleep-nutrition coupling.

========================
CRITICAL INTELLIGENCE UPGRADES
========================
CONFIDENCE SYSTEM:
- If DATA_CONFIDENCE is LOW: ask clarifying questions before giving strong
  recommendations. Phrase as "likely" or "based on limited data".
- If DATA_CONFIDENCE is HIGH: give direct, confident recommendations.

RISK RESPONSE PROTOCOL:
- CRITICAL risk (sleep/energy): this is your #1 priority. Address immediately.
  Do not move to nutrition until critical states are acknowledged.
- HIGH risk: address in first 48 hours of the plan.
- MODERATE risk: address in week 1.
- STABLE/LOW risk: maintain and optimize.

PRIORITY ENGINE:
- Always address TOP PRIORITIES in order. Never give equal weight to all items.
- If Sleep = CRITICAL, the entire plan revolves around sleep restoration first.

VALIDATION AWARENESS:
- You will receive DATA FLAGS indicating ambiguous or concerning inputs.
- Treat flagged data with caution. Ask follow-up questions to clarify flagged items.
- Never blindly process flagged data as if it were confirmed accurate.

========================
AI BEHAVIOR RULES
========================
1. NEVER give generic meal plans.
2. Every recommendation must be: schedule-aware, budget-aware, energy-aware,
   mental-health-aware, and time-aware.
3. Adapt dynamically based on: user feedback, mood, stress, sleep, workload.
4. Prioritize: sustainable habits > perfection | adherence > optimization.
5. For CRITICAL states, always acknowledge severity before giving advice.
6. Challenge and clarify ambiguous data rather than blindly processing it.

========================
ADAPTIVE LOGIC
========================
High stress    → magnesium, complex carbs, warm foods, easy digestion
Low energy     → iron, protein, hydration, B-complex foods
Poor sleep     → tryptophan foods, light dinners, no late sugar spikes
CRITICAL sleep → immediate sleep hygiene protocol + melatonin foods + NO caffeine after 2pm
Burnout        → reduce complexity, comfort foods + nutrient density
Depression cues→ dopamine-supportive nutrition + routine stabilization
Anxiety        → blood sugar stabilization + caffeine elimination

========================
OUTPUT FORMAT
========================
ALWAYS begin EVERY full plan response with this header block:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  DATA CONFIDENCE: [SCORE] ([LEVEL])
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  RISK CLASSIFICATION:
    Sleep:       [LEVEL]
    Energy:      [LEVEL]
    Mood:        [LEVEL]
    Stress:      [LEVEL]
    Nutrition:   [LEVEL]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  TOP PRIORITIES (ORDERED):
    1. [Priority]
    2. [Priority]
    3. [Priority]
    4. [Priority]
    5. [Priority]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Then continue with all 12 sections — always addressing TOP PRIORITIES first:

1)  Daily Nutrition Plan
2)  Meal Timing Strategy
3)  Energy Optimization Strategy
4)  Mental Health Support Strategy
5)  Budget Strategy
6)  Schedule Fit Strategy
7)  Quick Meals (≤10 min)
8)  Emergency Meals (no kitchen / no time)
9)  Study Snacks
10) Stress-State Protocol
11) Sleep-State Protocol
12) Burnout Prevention Plan
"""

# ──────────────────────────────────────────────
# PROFILE QUESTIONS
# ──────────────────────────────────────────────
PROFILE_QUESTIONS = [
    ("name",           "👋  What's your name?"),
    ("age",            "🎂  How old are you? (e.g. 20)"),
    ("gender",         "⚧   Gender (male / female / non-binary / prefer not to say)?"),
    ("height",         "📏  Height? (one specific value, e.g. 5'10\" or 178cm)"),
    ("weight",         "⚖️   Weight? (e.g. 160 lbs or 73 kg)"),
    ("goal",           "🎯  Body goal? (fat loss / muscle gain / maintenance / general health)"),
    ("diet_type",      "🥗  Diet type? (omnivore / vegetarian / vegan / halal / kosher / other)"),
    ("allergies",      "⚠️   Food allergies or intolerances? (or 'none')"),
    ("budget",         "💰  Budget level? (low / medium / flexible)"),
    ("cooking_access", "🍳  Cooking access? (dorm microwave / shared kitchen / full kitchen / none)"),
    ("cultural_prefs", "🌍  Cultural food preferences? (or 'none')"),
    ("class_schedule", "📅  Class schedule? (e.g. MWF 8am–2pm, TTh 10am–4pm)"),
    ("sleep_schedule", "😴  When do you sleep and wake up? (e.g. 2am–8am or 11pm–7am)"),
    ("workout_times",  "🏋️   When do you work out? (or 'none')"),
    ("stress_level",   "😰  Stress level? (number 1–10, where 1=chill, 10=overwhelmed)"),
    ("energy_level",   "⚡  Energy level? (number 1–10, where 1=exhausted, 10=great)"),
    ("sleep_quality",  "🌙  Sleep quality? (poor / okay / good)"),
    ("mood",           "💭  Mood today? (low / neutral / good)"),
    ("extra",          "📝  Anything else? (conditions, habits, concerns — or 'none')"),
]

# ──────────────────────────────────────────────
# VALIDATION ENGINE
# ──────────────────────────────────────────────
MOOD_ALIASES = {
    "lo": "low", "bad": "low", "sad": "low", "depressed": "low", "down": "low",
    "unhappy": "low", "rough": "low", "terrible": "low",
    "ok": "neutral", "okay": "neutral", "fine": "neutral", "meh": "neutral",
    "alright": "neutral", "average": "neutral", "so-so": "neutral",
    "great": "good", "amazing": "good", "awesome": "good", "happy": "good",
    "well": "good", "excellent": "good", "positive": "good",
}

SLEEP_QUALITY_ALIASES = {
    "terrible": "poor", "bad": "poor", "awful": "poor", "rough": "poor",
    "not good": "poor", "horrible": "poor",
    "ok": "okay", "fine": "okay", "alright": "okay", "decent": "okay",
    "not bad": "okay", "average": "okay",
    "great": "good", "amazing": "good", "well": "good", "excellent": "good",
    "fantastic": "good",
}

GOAL_ALIASES = {
    "lose weight": "fat loss", "lose fat": "fat loss", "cut": "fat loss",
    "cutting": "fat loss", "slim down": "fat loss", "weight loss": "fat loss",
    "bulk": "muscle gain", "gain muscle": "muscle gain", "build muscle": "muscle gain",
    "bulking": "muscle gain", "gain weight": "muscle gain",
    "maintain": "maintenance", "stay same": "maintenance", "maintain weight": "maintenance",
    "health": "general health", "healthy": "general health", "wellness": "general health",
    "stay healthy": "general health",
}

DIET_ALIASES = {
    # vegetarian typos & shorthands
    "vegetarian": "vegetarian", "vegitarian": "vegetarian", "vegetrain": "vegetarian",
    "vegitarian": "vegetarian", "vegatarian": "vegetarian", "vegiterian": "vegetarian",
    "veg": "vegetarian", "veggie": "vegetarian", "vegetarean": "vegetarian",
    # vegan
    "vegan": "vegan", "plant based": "vegan", "plant-based": "vegan", "plantbased": "vegan",
    # omnivore
    "omnivore": "omnivore", "omni": "omnivore", "everything": "omnivore",
    "non veg": "omnivore", "non-veg": "omnivore", "meat eater": "omnivore",
    # halal / kosher
    "halal": "halal", "kosher": "kosher",
    # other
    "pescatarian": "pescatarian", "pescetarian": "pescatarian", "pescitarian": "pescatarian",
    "keto": "keto", "paleo": "paleo", "gluten free": "gluten-free", "gluten-free": "gluten-free",
}


def parse_scale(raw: str) -> tuple:
    """Parse a 1–10 integer. Returns (int_value_or_None, is_in_range)."""
    cleaned = raw.strip().lstrip("`'\"")
    try:
        n = int(round(float(cleaned)))
        return (max(1, min(10, n)), 1 <= n <= 10)
    except ValueError:
        return (None, False)


def parse_height(raw: str) -> tuple:
    """Detect ambiguous height inputs. Returns (raw, is_clear)."""
    if re.search(r"\bmaybe\b|\bor\b|\bperhaps\b|\baround\b", raw, re.IGNORECASE):
        return (raw, False)
    if re.search(r"\d.*,.*\d.*,", raw):          # e.g. "6,3 maybe 5,4"
        return (raw, False)
    return (raw, True)


def parse_sleep_schedule(raw: str) -> tuple:
    """
    Parse sleep schedule string, return (raw, sleep_hours_or_None, parseable).
    Handles: '2am-8am', '11pm-7am', '2:30am-9am',
             '2am and 8am', '2am to 8am', 'sleep 2am wake 8am',
             single-time inputs like '2am-4am' (treated as bed→wake).
    """
    # Normalise separators so everything becomes "TIME1 - TIME2"
    cleaned = raw.lower()
    cleaned = cleaned.replace("–", "-").replace("—", "-")
    cleaned = re.sub(r"\bto\b",   "-", cleaned)
    cleaned = re.sub(r"\band\b",  "-", cleaned)
    cleaned = re.sub(r"\bwake\s*(up)?\b", "-", cleaned)
    cleaned = re.sub(r"\buntil\b", "-", cleaned)
    cleaned = re.sub(r"-+", "-", cleaned)   # collapse double dashes

    time_pat = r"(\d{1,2}(?::\d{2})?)\s*(am|pm)"
    times = re.findall(time_pat, cleaned)

    if len(times) < 2:
        return (raw, None, False)

    def to_float_hours(time_str: str, ampm: str) -> float:
        parts = time_str.split(":")
        h = int(parts[0])
        mins = int(parts[1]) if len(parts) > 1 else 0
        if ampm == "pm" and h != 12:
            h += 12
        if ampm == "am" and h == 12:
            h = 0
        return h + mins / 60.0

    bed  = to_float_hours(times[0][0], times[0][1])
    wake = to_float_hours(times[1][0], times[1][1])

    # If both times are identical or result is 0, mark unparseable
    hours = (24 - bed + wake) if bed > wake else (wake - bed)
    if hours == 0 or hours > 23:
        return (raw, None, False)
    return (raw, round(hours, 1), True)


def validate_field(key: str, raw: str) -> tuple:
    """
    Validate and normalise a single profile answer.
    Returns (cleaned_value, [flag_strings]).
    Does NOT re-prompt — that's handled by ask_field().
    """
    flags = []

    if key == "height":
        cleaned, ok = parse_height(raw)
        if not ok:
            flags.append(f"HEIGHT_AMBIGUOUS: '{raw}' — multiple or unclear values given")
        return cleaned, flags

    if key == "stress_level":
        n, in_range = parse_scale(raw)
        if n is None:
            flags.append(f"STRESS_NON_NUMERIC: '{raw}'")
            return raw, flags
        if not in_range:
            flags.append(f"STRESS_OUT_OF_RANGE: '{raw}' → clamped to {n}/10")
        if n >= 9:
            flags.append(f"STRESS_CRITICAL: {n}/10 — critical stress state detected")
        return str(n), flags

    if key == "energy_level":
        n, in_range = parse_scale(raw)
        if n is None:
            flags.append(f"ENERGY_NON_NUMERIC: '{raw}'")
            return raw, flags
        if not in_range:
            flags.append(f"ENERGY_OUT_OF_RANGE: '{raw}' → clamped to {n}/10")
        if n <= 2:
            flags.append(f"ENERGY_CRISIS: {n}/10 — critical energy depletion detected")
        return str(n), flags

    if key == "mood":
        normalized = MOOD_ALIASES.get(raw.lower(), raw.lower())
        if normalized not in ("low", "neutral", "good"):
            flags.append(f"MOOD_UNRECOGNIZED: '{raw}' — defaulting to 'neutral'")
            normalized = "neutral"
        elif normalized != raw.lower():
            print(f"  ℹ️   '{raw}' → interpreted as '{normalized}'")
        return normalized, flags

    if key == "sleep_quality":
        normalized = SLEEP_QUALITY_ALIASES.get(raw.lower(), raw.lower())
        if normalized not in ("poor", "okay", "good"):
            flags.append(f"SLEEP_QUALITY_UNRECOGNIZED: '{raw}' — defaulting to 'poor'")
            normalized = "poor"
        elif normalized != raw.lower():
            print(f"  ℹ️   '{raw}' → interpreted as '{normalized}'")
        return normalized, flags

    if key == "goal":
        normalized = GOAL_ALIASES.get(raw.lower(), raw.lower())
        if normalized != raw.lower():
            print(f"  ℹ️   '{raw}' → interpreted as '{normalized}'")
        return normalized, flags

    if key == "diet_type":
        normalized = DIET_ALIASES.get(raw.lower(), raw.lower())
        if normalized != raw.lower():
            print(f"  ℹ️   '{raw}' → interpreted as '{normalized}'")
        return normalized, flags

    return raw, flags


def ask_field(key: str, question: str) -> tuple:
    """
    Prompt the user for a field with inline validation.
    Re-prompts on hard errors (ambiguous height, non-numeric scales).
    Returns (validated_value, [flags]).
    """
    while True:
        raw = input(f"  {question}\n  ▶  ").strip()
        if not raw:
            print("  (Please enter a response)\n")
            continue

        cleaned, flags = validate_field(key, raw)

        # Hard re-prompt: ambiguous height
        if key == "height" and flags:
            print("  ❓  Please enter one specific height (e.g. 5'10\" or 178cm).\n")
            continue

        # Hard re-prompt: non-numeric scale
        if key in ("stress_level", "energy_level") and any("NON_NUMERIC" in f for f in flags):
            print("  ❓  Please enter a number between 1 and 10.\n")
            continue

        # Show soft flags inline
        for f in flags:
            if "CRITICAL" in f or "CRISIS" in f:
                print(f"  🔴  {f}")
            elif "OUT_OF_RANGE" in f or "AMBIGUOUS" in f:
                print(f"  🟠  {f}")

        return cleaned, flags


# ──────────────────────────────────────────────
# ANALYSIS ENGINE — Confidence · Risk · Priority
# ──────────────────────────────────────────────
RISK_ORDER = {"CRITICAL": 0, "HIGH": 1, "MODERATE": 2, "STABLE": 3, "LOW": 4}
RISK_ICONS = {"CRITICAL": "🔴", "HIGH": "🟠", "MODERATE": "🟡", "STABLE": "🟢", "LOW": "🟢"}
PRIORITY_LABELS = {
    "sleep":     "Sleep normalization",
    "energy":    "Energy restoration",
    "stress":    "Stress management",
    "mood":      "Mood stabilization",
    "nutrition": "Nutrition optimization",
}


def analyze_profile(profile: dict) -> dict:
    """
    Compute:
      data_flags       — list of all validation warnings
      data_confidence  — 0.0–1.0 float
      confidence_level — LOW / MEDIUM / HIGH
      risk             — dict of category → risk level string
      priorities       — ordered list of focus area labels
    """
    analysis: dict = {
        "data_flags": list(DATA_FLAGS),
        "data_confidence": 1.0,
        "confidence_level": "HIGH",
        "risk": {},
        "priorities": [],
    }

    # ── Confidence score ──────────────────────
    deductions = len(DATA_FLAGS) * 0.08
    for field in ("height", "weight", "age", "stress_level", "energy_level", "sleep_schedule"):
        if not profile.get(field):
            deductions += 0.05
    score = round(max(0.0, min(1.0, 1.0 - deductions)), 2)
    analysis["data_confidence"] = score
    analysis["confidence_level"] = "HIGH" if score >= 0.75 else ("MEDIUM" if score >= 0.50 else "LOW")

    # ── Risk: Sleep ───────────────────────────
    sleep_schedule = profile.get("sleep_schedule", "")
    _, sleep_hours, parseable = parse_sleep_schedule(sleep_schedule)
    sleep_quality  = profile.get("sleep_quality", "okay")

    if parseable and sleep_hours is not None:
        if sleep_hours < 4:
            analysis["risk"]["sleep"] = "CRITICAL"
            if sleep_quality == "good":
                note = f"SLEEP_QUALITY_OVERRIDE: declared 'good' but only {sleep_hours}h detected — overriding to CRITICAL"
                if note not in analysis["data_flags"]:
                    analysis["data_flags"].append(note)
                profile["sleep_quality"] = "poor"
        elif sleep_hours < 6:
            analysis["risk"]["sleep"] = "HIGH"
        elif sleep_hours < 7:
            analysis["risk"]["sleep"] = "MODERATE"
        else:
            analysis["risk"]["sleep"] = "STABLE" if sleep_quality != "poor" else "MODERATE"
    else:
        analysis["risk"]["sleep"] = "MODERATE" if sleep_quality == "poor" else "STABLE"

    # ── Risk: Energy ──────────────────────────
    try:
        energy = int(profile.get("energy_level", "5"))
    except (ValueError, TypeError):
        energy = 5
    analysis["risk"]["energy"] = (
        "CRITICAL" if energy <= 2 else
        "HIGH"     if energy <= 4 else
        "MODERATE" if energy <= 6 else
        "STABLE"
    )

    # ── Risk: Stress ──────────────────────────
    try:
        stress = int(profile.get("stress_level", "5"))
    except (ValueError, TypeError):
        stress = 5
    analysis["risk"]["stress"] = (
        "CRITICAL" if stress >= 9 else
        "HIGH"     if stress >= 7 else
        "MODERATE" if stress >= 5 else
        "LOW"
    )

    # ── Risk: Mood ────────────────────────────
    mood = profile.get("mood", "neutral").lower()
    analysis["risk"]["mood"] = (
        "HIGH"     if mood == "low" else
        "MODERATE" if mood == "neutral" else
        "STABLE"
    )

    # ── Risk: Nutrition ───────────────────────
    cooking = profile.get("cooking_access", "").lower()
    budget  = profile.get("budget", "medium").lower()
    if cooking == "none" and budget == "low":
        analysis["risk"]["nutrition"] = "HIGH"
    elif cooking in ("none", "dorm microwave") or budget == "low":
        analysis["risk"]["nutrition"] = "MODERATE"
    else:
        analysis["risk"]["nutrition"] = "STABLE"

    # ── Priority order ────────────────────────
    sorted_cats = sorted(analysis["risk"].items(), key=lambda x: RISK_ORDER.get(x[1], 5))
    analysis["priorities"] = [PRIORITY_LABELS.get(k, k.title()) for k, _ in sorted_cats]

    return analysis


def format_analysis_block(analysis: dict) -> str:
    """Render the analysis as a structured text block for terminal + AI context."""
    lines = [
        "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"  DATA CONFIDENCE: {analysis['data_confidence']:.0%}  ({analysis['confidence_level']})",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "  RISK CLASSIFICATION:",
    ]
    for cat, level in analysis["risk"].items():
        icon = RISK_ICONS.get(level, "⚪")
        lines.append(f"    {cat.capitalize():<12} {icon} {level}")
    lines += [
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "  TOP PRIORITIES (ORDERED):",
    ]
    for i, p in enumerate(analysis["priorities"], 1):
        lines.append(f"    {i}. {p}")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    if analysis["data_flags"]:
        lines.append("  ⚠️  DATA FLAGS:")
        for f in analysis["data_flags"]:
            lines.append(f"    • {f}")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    return "\n".join(lines)


# ──────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────
def print_banner():
    print("\n" + "═" * 60)
    print("  HealthOS v3.0 — Personal Health Intelligence System")
    print(f"  Powered by Gemini [{MODEL_NAME}]")
    print("═" * 60 + "\n")


def wrap(text: str, width: int = 80) -> str:
    """Wrap long AI response lines for clean terminal output."""
    lines = text.split("\n")
    wrapped = []
    for line in lines:
        if len(line) > width:
            wrapped.extend(textwrap.wrap(line, width))
        else:
            wrapped.append(line)
    return "\n".join(wrapped)


def load_profile() -> dict:
    if os.path.exists(PROFILE_FILE):
        try:
            with open(PROFILE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_profile(profile: dict):
    with open(PROFILE_FILE, "w") as f:
        json.dump(profile, f, indent=2)


def collect_profile() -> dict:
    """Onboarding questionnaire with full validation."""
    DATA_FLAGS.clear()
    print("\n🔍  Let me learn about you. I'll validate your answers as we go.\n")
    profile = {}
    for key, question in PROFILE_QUESTIONS:
        cleaned, flags = ask_field(key, question)
        profile[key] = cleaned
        for f in flags:
            if f not in DATA_FLAGS:
                DATA_FLAGS.append(f)
        print()
    save_profile(profile)
    print("✅  Profile saved!\n")
    return profile


def profile_to_context(
    profile:        dict,
    analysis:       dict,
    priority_block: str = "",
    nutrition_ctx:  str = "",
    memory_ctx:     str = "",
    trend_ctx:      str = "",
) -> str:
    """Build the full AI seed message: profile + risk + memory + trends + priorities + RAG foods."""
    labels = {k: q.split("?")[0].lstrip("📏⚖️🎯🥗⚠️💰🍳🌍📅😴🏋️😰⚡🌙💭📝👋🎂⚧ ").strip()
              for k, q in PROFILE_QUESTIONS}
    lines = ["Here is my complete profile:\n"]
    for key, val in profile.items():
        label = labels.get(key, key.replace("_", " ").title())
        lines.append(f"  • {label}: {val}")
    lines.append(format_analysis_block(analysis))

    if memory_ctx:
        lines.append(memory_ctx)
    if trend_ctx:
        lines.append(trend_ctx)
    if priority_block:
        lines.append(priority_block)
    if nutrition_ctx:
        lines.append(nutrition_ctx)

    lines.append(
        "\nUsing ALL blocks above (profile, risk analysis, recent history, "
        "7-DAY TREND ANALYSIS, PROTOCOL PRIORITY SCORES, ACTIVE CONSTRAINTS, "
        "and the nutrition database),\n"
        "generate my full personalized health & lifestyle plan across all 12 sections.\n"
        "Reference specific trends from the TREND ANALYSIS block by name — "
        "e.g. 'Your data shows energy declines on Mondays...'\n"
        "Follow PROTOCOL PRIORITY SCORES order — address 🔴 HIGH protocols first.\n"
        "Respect every ACTIVE CONSTRAINT (time, budget, kitchen, diet, allergies).\n"
        "Reference specific real foods from the nutrition database by name and macros.\n"
        "For CRITICAL risks, acknowledge severity and provide immediate actionable steps.\n"
        "If DATA_CONFIDENCE is LOW, ask clarifying questions before strong recommendations."
    )
    return "\n".join(lines)


# ──────────────────────────────────────────────
# RESEARCH CONTEXT LOADER
# Loads sleep_insights.json + student_health.json and formats them
# as evidence-based text blocks injected into the AI system prompt.
# ──────────────────────────────────────────────
def load_research_context() -> str:
    """Return a formatted string of evidence-based stats from the Kaggle insight files."""
    model_dir = os.path.dirname(os.path.abspath(__file__))
    lines: list[str] = []

    # ── Sleep Health & Lifestyle (374 adults) ────────────────────
    sleep_file = os.path.join(model_dir, "sleep_insights.json")
    if os.path.exists(sleep_file):
        try:
            with open(sleep_file) as f:
                d = json.load(f)
            lines.append(
                "\n══ EVIDENCE-BASED SLEEP RESEARCH  "
                "(source: 374-adult sleep-health study) ══"
            )
            sqh = d.get("sleep_quality_by_hours", {})
            if sqh:
                lines.append("Sleep quality (1–10 scale) by nightly hours:")
                for bucket, q in sqh.items():
                    lines.append(f"  {bucket}: quality {q}/10")
            ssh = d.get("stress_by_sleep_hours", {})
            if ssh:
                lines.append("Stress level (1–10) by nightly hours:")
                for bucket, s in ssh.items():
                    lines.append(f"  {bucket}: stress {s}/10")
            pct = d.get("pct_high_stress_with_low_sleep")
            if pct is not None:
                lines.append(
                    f"• {pct}% of people sleeping <6 h report high stress (≥7/10)"
                )
            opt = d.get("optimal_sleep_range_for_stress")
            if opt:
                lines.append(f"• Optimal nightly sleep window for lowest stress: {opt}")
            sqa = d.get("sleep_quality_by_activity", {})
            if sqa:
                lines.append("Sleep quality by daily physical activity:")
                for bucket, q in sqa.items():
                    lines.append(f"  {bucket}: quality {q}/10")
        except Exception:
            pass

    # ── Student Mental Health (101 university students) ──────────
    mh_file = os.path.join(model_dir, "student_health.json")
    if os.path.exists(mh_file):
        try:
            with open(mh_file) as f:
                d = json.load(f)
            lines.append(
                "\n══ STUDENT MENTAL HEALTH RESEARCH  "
                "(source: 101-student university study) ══"
            )
            dep = d.get("depression_prevalence_pct")
            if dep is not None:
                lines.append(f"• Depression prevalence: {dep}% of students")
            anx = d.get("anxiety_prevalence_pct")
            if anx is not None:
                lines.append(f"• Anxiety prevalence: {anx}% of students")
            pan = d.get("panic_attack_prevalence_pct")
            if pan is not None:
                lines.append(f"• Panic attack prevalence: {pan}% of students")
            both = d.get("depression_and_anxiety_pct")
            if both is not None:
                lines.append(f"• Co-occurring depression + anxiety: {both}% of students")
            tx = d.get("sought_treatment_pct")
            if tx is not None:
                lines.append(f"• Only {tx}% sought professional treatment")
            dep_cgpa = d.get("depression_by_cgpa", {})
            if dep_cgpa:
                lines.append("Depression rate by CGPA band:")
                for cgpa, pct in dep_cgpa.items():
                    lines.append(f"  CGPA {cgpa}: {pct}%")
        except Exception:
            pass

    return "\n".join(lines)


# ──────────────────────────────────────────────
# FULL CONTEXT BUILDER  (used by web /api/chat)
# Runs the COMPLETE pipeline:
#   analyze_profile → user_state vector → protocol prioritization
#   → constraint solver → session memory → RAG foods → research stats
# Returns (system_prompt_str, seed_message_str) ready to inject into Ollama.
# ──────────────────────────────────────────────
def build_full_context(profile: dict, username: str) -> tuple[str, str]:
    """
    Run the full HealthOS intelligence pipeline and return
    (system_full, seed_message) for the Ollama chat call.

    Pipeline:
      Stage 0 · Validation + Ontology  — parse_profile → ParsedProfile
      Stage 0b· Constraint Graph       — ConstraintGraph.from_parsed_profile
      Stage 1 · Nutrition DB + RAG     — load + build index
      Stage 2 · Core Analysis          — analyze_profile
      Stage 3 · User State Vector      — analyze_user_state
      Stage 4 · Protocol Prioritization— prioritize_protocols + constraint_result
      Stage 5 · Session Memory         — last 7 days check-ins
      Stage 6 · RAG Food Retrieval     — semantic query filtered by constraint graph
      Stage 7 · Research Context       — sleep + student MH evidence stats
      Stage 8 · Assemble               — system_full + seed_message
    """
    _MODEL_DIR = os.path.dirname(os.path.abspath(__file__))

    # ── Stage 0: Validation + Ontology Mapping ─────────────────
    from validation import parse_profile as _parse_profile
    from constraint_graph import ConstraintGraph

    pp = _parse_profile(profile)
    cg = ConstraintGraph.from_parsed_profile(pp)

    # ── Stage 1: Load nutrition DB + RAG ───────────────────────
    nutrition_index_path = os.path.join(_MODEL_DIR, "nutrition_index.json")
    nutrition_db.load(nutrition_index_path)
    rag.build(nutrition_index_path)

    # ── Stage 2: Core analysis ──────────────────────────────────
    analysis = analyze_profile(profile)

    # ── Stage 3: User state vector ──────────────────────────────
    state           = user_state.analyze_user_state(profile)
    protocols       = user_state.map_state_to_protocols(state)
    constraints     = user_state.build_constraints_from_profile(profile)
    learned_weights = user_state.load_feedback_weights(username)

    # ── Stage 4: Protocol prioritization + constraint solver ────
    prioritized       = user_state.prioritize_protocols(protocols, state, learned_weights)
    constraint_result = user_state.solve_constraints(prioritized, constraints, state)
    nutrient_targets  = user_state.protocols_to_nutrients(
        {p: s for p, s in prioritized[:10]}
    )
    priority_block = user_state.format_priority_block(
        prioritized, nutrient_targets, constraint_result
    )

    # ── Stage 5: Session memory + Trend Analysis ──────────────
    from trend_engine import analyze_trends, format_trend_block
    recent_logs = session_memory.load_recent_logs(username)
    memory_ctx  = session_memory.format_memory_context(recent_logs)
    trend_ctx   = format_trend_block(analyze_trends(recent_logs))

    # ── Stage 6: RAG — constrained semantic food retrieval ──────
    # Use constraint graph's typed protocol list as the retrieval signal
    active_protocols = cg.active_protocols
    seed_query       = (
        f"{pp.goal.value} {pp.stress_state.value} {pp.energy_state.value} "
        f"{pp.sleep_quality.value} health plan"
    )
    nutrition_ctx = rag.query(
        seed_query, active_protocols[:5], n=15, constraint_graph=cg
    )
    if not nutrition_ctx:
        nutrition_ctx = nutrition_db.build_nutrition_context(profile, constraint_graph=cg)

    # ── Stage 7: Research context ───────────────────────────────
    research_ctx = load_research_context()

    # ── Stage 8: Assemble ───────────────────────────────────────
    # Constraint block goes FIRST so it is the first instruction the LLM reads.
    constraint_block = cg.to_prompt_block()
    system_full      = constraint_block + SYSTEM_PROMPT + research_ctx
    seed_message     = profile_to_context(
        profile, analysis, priority_block, nutrition_ctx, memory_ctx, trend_ctx
    )

    return system_full, seed_message

def chatbot_response(profile: dict, username: str, stream: bool = True, max_retries: int = 3) -> str:
    """
    Generate a chatbot response using the full context builder.
    
    Args:
        profile: User profile dictionary
        username: Username for context
        stream: Whether to stream the response (default: True)
        max_retries: Number of retry attempts on failure (default: 3)
    
    Returns:
        Generated response string
        
    Raises:
        ValueError: If profile or username is invalid
        ConnectionError: If unable to connect to Ollama
        RuntimeError: If response generation fails after all retries
    """
    # Input validation
    if not profile or not isinstance(profile, dict):
        raise ValueError("Invalid profile: must be a non-empty dictionary")
    if not username or not isinstance(username, str):
        raise ValueError("Invalid username: must be a non-empty string")
    
    # Verify Gemini API key is configured
    if not GEMINI_API_KEY:
        raise ConnectionError("GEMINI_API_KEY environment variable is not set.")
    genai.configure(api_key=GEMINI_API_KEY)
    
    # Build context with error handling
    try:
        system_full, seed_message = build_full_context(profile, username)
    except Exception as e:
        raise RuntimeError(f"Failed to build context: {str(e)}")
    
    if not system_full or not seed_message:
        raise ValueError("Context builder returned empty system prompt or message")
    
    # Retry logic with exponential backoff
    import time
    last_error = None
    
    for attempt in range(max_retries):
        try:
            gemini_model = genai.GenerativeModel(
                MODEL_NAME,
                system_instruction=system_full,
            )
            chat_session = gemini_model.start_chat(history=[
                {"role": "user", "parts": [seed_message]},
                {"role": "model", "parts": ["Understood. I have your full profile loaded."]},
            ])
            
            if stream:
                response_stream = chat_session.send_message(seed_message, stream=True)
                reply_parts = []
                for chunk in response_stream:
                    if chunk.text:
                        reply_parts.append(chunk.text)
                reply = "".join(reply_parts)
            else:
                response = chat_session.send_message(seed_message, stream=False)
                reply = response.text
            
            if not reply:
                raise RuntimeError("Received empty response from model")
            return reply
                
        except KeyboardInterrupt:
            raise
            
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"\n⚠️  Attempt {attempt + 1} failed: {str(e)}")
                print(f"   Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                error_msg = (
                    f"Failed to generate response after {max_retries} attempts.\n"
                    f"Last error: {str(last_error)}\n"
                    f"Model: {MODEL_NAME}"
                )
                raise RuntimeError(error_msg) from last_error
    
    raise RuntimeError("Unexpected error in retry loop")

# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────
def main():
    print_banner()

    # Verify Gemini API key before doing any work
    if not GEMINI_API_KEY:
        print("⚠️  GEMINI_API_KEY is not set. Export it before running.")
        return
    genai.configure(api_key=GEMINI_API_KEY)

    # Load nutrition index (built by train.py)
    nutrition_index_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nutrition_index.json")
    if nutrition_db.load(nutrition_index_path):
        total = nutrition_db.meta().get('total_foods', '?')
        print(f"  🥗  Nutrition DB loaded — {total:,} foods indexed")
        # Build / reuse semantic search index (one-time ~60s, then persists to chroma_db/)
        if rag.build(nutrition_index_path):
            print("  🔍  Semantic search: ready")
        else:
            print("  🔍  Semantic search: tag fallback  (pip install chromadb to enable)")
    else:
        print("  ⚠️   Nutrition DB not found. Run 'python train.py' to build it.")
        print("       The AI will still work, just without real food data.\n")

    # Load or collect profile
    profile = load_profile()
    if profile:
        name = profile.get("name", "there")
        print(f"  Welcome back, {name}! 👋  Loaded your saved profile.")
        choice = input("  Use existing profile? (y / n)\n  ▶  ").strip().lower()
        if choice == "n":
            profile = collect_profile()
        else:
            DATA_FLAGS.clear()
    else:
        print("  First time here! Let's build your profile.\n")
        profile = collect_profile()

    user_name = profile.get("name", "default")

    # ── Stage 0: Build constraint graph (single source of truth) ──────────
    from validation import parse_profile as _parse_profile
    from constraint_graph import ConstraintGraph as _CG

    _pp = _parse_profile(profile)
    _cg = _CG.from_parsed_profile(_pp)
    _constraint_block = _cg.to_prompt_block()

    # ── Optional daily check-in (returning users, first visit of the day) ─────
    _prev_logs = session_memory.load_recent_logs(user_name)
    _today     = datetime.now().strftime("%Y-%m-%d")
    if _prev_logs and not any(l.get("date") == _today for l in _prev_logs):
        _do_ci = input("  📊  Quick daily check-in? (30 sec)  (y / n)\n  ▶  ").strip().lower()
        if _do_ci == "y":
            _ci = session_memory.run_checkin(profile)
            session_memory.save_checkin(user_name, _ci)
            if _ci.get("mood"):   profile["mood"]         = _ci["mood"]
            if _ci.get("energy"): profile["energy_level"] = str(_ci["energy"])
            save_profile(profile)
            print("  ✅  Check-in saved!\n")

    # Run analysis engine
    analysis = analyze_profile(profile)

    # ── User State Vector ───────────────────────────────────────
    state           = user_state.analyze_user_state(profile)
    protocols       = user_state.map_state_to_protocols(state)
    constraints     = user_state.build_constraints_from_profile(profile)
    learned_weights = user_state.load_feedback_weights(user_name)

    # ── Protocol Prioritization Engine ─────────────────────────
    prioritized       = user_state.prioritize_protocols(protocols, state, learned_weights)
    constraint_result = user_state.solve_constraints(prioritized, constraints, state)
    nutrient_targets  = user_state.protocols_to_nutrients(
        {p: s for p, s in prioritized[:10]}
    )
    priority_block = user_state.format_priority_block(
        prioritized, nutrient_targets, constraint_result
    )

    # Print analysis to terminal
    print("\n" + "─" * 60)
    print(format_analysis_block(analysis))
    print("─" * 60)
    print(priority_block)
    print("─" * 60)

    if state["computed_flags"]:
        print("  🚨  STATE FLAGS:")
        for flag in state["computed_flags"]:
            print(f"     • {flag}")
        print("─" * 60)

    # ── Memory context + Trend Analysis (last 7 days) ─────────────────
    from trend_engine import analyze_trends, format_trend_block
    recent_logs   = session_memory.load_recent_logs(user_name)
    memory_ctx    = session_memory.format_memory_context(recent_logs)
    trend_ctx     = format_trend_block(analyze_trends(recent_logs))
    if trend_ctx:
        print(trend_ctx)

    # ── RAG: top-15 semantically relevant foods for this user's goals ────
    seed_query    = "personalized health plan " + " ".join(state.get("goals", []))
    nutrition_ctx = rag.query(
        seed_query, [p for p, _ in prioritized[:5]], n=15, constraint_graph=_cg
    )
    if not nutrition_ctx:
        nutrition_ctx = nutrition_db.build_nutrition_context(profile, constraint_graph=_cg)

    # ── Research context (sleep + student MH stats) ─────────────
    research_ctx = load_research_context()
    if research_ctx:
        print("  📊  Research context loaded (sleep + mental health data)")

    # Seed message: profile + analysis + memory + priority block + RAG nutrition
    seed_message = profile_to_context(profile, analysis, priority_block, nutrition_ctx, memory_ctx, trend_ctx)

    # Build Gemini model and chat session
    _gemini_model = genai.GenerativeModel(
        MODEL_NAME,
        system_instruction=_constraint_block + SYSTEM_PROMPT + research_ctx,
    )
    _chat_session = _gemini_model.start_chat(history=[])

    print("\n⏳  Generating your personalized plan…\n")
    try:
        response_stream = _chat_session.send_message(seed_message, stream=True)
        reply_parts = []
        for chunk in response_stream:
            if chunk.text:
                print(chunk.text, end="", flush=True)
                reply_parts.append(chunk.text)
        reply = "".join(reply_parts)
        print()   # newline after stream ends
    except Exception as e:
        print(f"\n⚠️  Gemini error: {e}")
        return
    print("\n" + "─" * 60)

    # Save today's session automatically
    session_memory.save_checkin(user_name, {
        "mood":         profile.get("mood", "neutral"),
        "energy":       profile.get("energy_level", "5"),
        "sleep_hours":  state.get("sleep_hours"),
        "protocols":    [p for p, _ in prioritized[:3]],
        "date":         datetime.now().strftime("%Y-%m-%d"),
    })

    print("\n💬  Ask follow-up questions, report state changes, or request meal swaps.")
    print("    Type 'quit' or 'exit' to end.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\n👋  Stay consistent. See you next session!")
            break

        if not user_input:
            continue
        if user_input.lower() in {"quit", "exit", "q", "bye"}:
            print("\n👋  Take care! Profile is saved for next time.")
            break

        # Inline state update (e.g. "stress: 9" or "energy: 3")
        for keyword in ["stress", "energy", "mood", "sleep"]:
            if keyword in user_input.lower() and ":" in user_input.lower():
                try:
                    val = user_input.lower().split(keyword + ":")[1].strip().split()[0]
                    pkey = f"{keyword}_level" if keyword in ("stress", "energy") else f"{keyword}_quality"
                    profile[pkey] = val
                    save_profile(profile)
                    analysis  = analyze_profile(profile)
                    state     = user_state.analyze_user_state(profile)
                    protocols = user_state.map_state_to_protocols(state)
                except Exception:
                    pass

        # ── Feedback Learning Loop ──────────────────────────────
        feedback = user_state.parse_feedback_from_text(user_input)
        if feedback:
            learned_weights = user_state.update_weights_from_feedback(
                user_name, feedback, learning_rate=0.05
            )
            # Re-rank protocols with updated weights
            prioritized = user_state.prioritize_protocols(protocols, state, learned_weights)
            top_3 = ", ".join(p.replace("_protocol", "") for p, _ in prioritized[:3])
            print(f"  📊  Feedback recorded {feedback} — top protocols: [{top_3}]\n")

        # ── Meal Swap Detection ────────────────────────────────────
        from meal_swap import detect_swap_request, find_swaps, format_swap_block as _fmt_swap
        _rejected = detect_swap_request(user_input)
        _swap_block = ""
        if _rejected and nutrition_db.is_loaded():
            _active_protos = [p for p, _ in prioritized[:5]]
            _swaps = find_swaps(_rejected, constraint_graph=_cg,
                                active_protocols=_active_protos, n=5)
            _swap_block = _fmt_swap(_rejected, _swaps, constraint_graph=_cg)
            if _swaps:
                print(f"  🔄  Swap engine: {len(_swaps)} substitutes found for '{_rejected}'")

        # RAG: fetch foods relevant to this specific follow-up query
        _rag_ctx = rag.query(user_input, [p for p, _ in prioritized[:5]], n=8,
                             constraint_graph=_cg)
        _send    = (
            f"{_swap_block}\n\n[Relevant nutrition data for this query:{_rag_ctx}]\n\n{user_input}"
            if _rag_ctx or _swap_block else user_input
        )
        if _swap_block and not _rag_ctx:
            _send = f"{_swap_block}\n\n{user_input}"

        print("\n⏳  Thinking…\n")
        try:
            response_stream = _chat_session.send_message(_send, stream=True)
            reply_parts = []
            for chunk in response_stream:
                if chunk.text:
                    print(chunk.text, end="", flush=True)
                    reply_parts.append(chunk.text)
            print()   # newline after stream ends
        except Exception as e:
            print(f"\n⚠️  Gemini error: {e}")
        print("\n" + "─" * 60 + "\n")


if __name__ == "__main__":
    main()
