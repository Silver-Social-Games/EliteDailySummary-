"""Vegas 2026 Top 50 — C-level slide lines + speaker notes (single source of truth)."""

from __future__ import annotations

# Correct split — use when a layout is chosen (speaker notes in second tuple element)
EVENT_GOALS_MAIN: list[tuple[str, str]] = [
    (
        "Learn What Drives Spend",
        "Games, offers, habits — why they buy and what would increase frequency.",
    ),
    (
        "What Do You Need To Stay And Increase Play On Jackpota",
        'Ask verbatim in structured conversations; log answers for offers and follow-up.',
    ),
    (
        "+10% Spend · Six Months Post-Play",
        "North-star vs pre-event baseline — measure spend at six months post-Vegas.",
    ),
]

EVENT_GOALS_SECONDARY: list[tuple[str, str]] = [
    (
        "Build Relationships And Trust",
        "Know them before Vegas; no cold intros; trust before hard questions.",
    ),
    (
        "Deliver A Premium Experience",
        "Logistics, timing, hospitality — Elite feels tangible.",
    ),
    (
        "Collect Info For Follow-Up",
        "Same-day notes — preferences, pain points — for CRM and outreach.",
    ),
]

# Blank placeholders for layout option slides on template
GOALS_MAIN_PLACEHOLDERS = ("Main goal 1", "Main goal 2", "Main goal 3")
GOALS_SECONDARY_PLACEHOLDERS = ("Secondary goal 1", "Secondary goal 2", "Secondary goal 3")

EVENT_GOALS_DELIVERY = EVENT_GOALS_SECONDARY  # legacy alias
EVENT_GOALS: list[tuple[str, str]] = EVENT_GOALS_MAIN + EVENT_GOALS_SECONDARY

FOCUS_POINTS: list[tuple[str, str]] = [
    (
        "Know Your Players — Roster & Ownership",
        "Use management roster + Detail tab: reg date, seniority group, NP 30d/lt/60d, hold %. "
        "Agent owns their 25; no cold intros on Day 1.",
    ),
    (
        "Location And Logistics — Hotel, Pickup, Gala",
        "Hotel, airport pickup, Gala Day 2 · 13:00–16:00, optional Sphere. "
        "Team answers where/when without escalation.",
    ),
    (
        "Content To Present — Elite, Thomas, Tammy",
        "Align on three presentation tracks: Elite program story and membership value; "
        "Thomas session content; Tammy session content. Same talking points across agents — "
        "clear on included vs optional.",
    ),
    (
        "Get Intel From Them — Games, Offers, Trip",
        "Structured questions on games, offers, trip expectations; notes logged same day for CRM.",
    ),
    (
        "Watch Risk Signals — Accounts & Payments",
        "Locked accounts, payment failures, sharp NP drops; check account status before "
        "issues hit on-site.",
    ),
    (
        "Close The Loop — Thank-You & Follow-Up",
        "Thank-you, summarize learnings, follow-ups within 48h; success = intel used in outreach.",
    ),
]

EVENT_GOALS_SUBTITLE = "Main Goals · Secondary Goals"
FOCUS_POINTS_SUBTITLE = "What we stay on — before and during"
