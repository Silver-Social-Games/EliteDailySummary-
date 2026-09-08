"""Inbound V5 NGR Free Bonus — flat Elite profile (no PVIP/VIP tiers).

Ports the Calculator V5 - NGR Inbound block from ELITE Bonus Calculator.xlsx.
Python is the spec; web/src/bonusCalc.ts mirrors this module for runtime.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import config

# Bonus status (% bonus / purchase) → label, NGR deduction multiplier (Excel N8:P17).
BONUS_STATUS_TABLE: tuple[tuple[float, str, float], ...] = (
    (0.0, "No/Low Bonus user", 1.0),
    (0.05, "No/Low Bonus user", 0.9),
    (0.10, "No/Low Bonus user", 0.8),
    (0.15, "Regular Bonus user", 0.7),
    (0.17, "Regular Bonus user", 0.6),
    (0.19, "Regular Bonus user", 0.5),
    (0.22, "Regular Bonus user", 0.4),
    (0.25, "Bonus beggar", 0.3),
    (0.30, "Bonus beggar", 0.2),
    (0.45, "Abuser", 0.1),
)

# Active + positive NGR: NGR-factor → Free Bonus $ (Excel S6:U24, col U).
ACTIVE_POS_NGR_TABLE: tuple[tuple[float, float], ...] = (
    (1, 5),
    (10, 10),
    (20, 20),
    (30, 30),
    (40, 40),
    (50, 50),
    (60, 60),
    (70, 70),
    (80, 80),
    (100, 100),
    (130, 130),
    (150, 150),
    (200, 200),
    (250, 250),
    (300, 300),
    (350, 350),
    (400, 400),
    (450, 450),
    (500, 500),
)


@dataclass(frozen=True)
class BonusCalcInput:
    active: bool
    ggr: float
    bonus: float
    purchase_count: int
    purchase_amount: float
    bonus_pct_window: float
    bonus_pct_lifetime: float
    locked: bool = False
    lock_label: str = ""


@dataclass(frozen=True)
class BonusCalcResult:
    free_bonus: float | None
    offer_label: str
    bonus_status: str
    bonus_status_mult: float
    recommended: float
    cap_note: str
    blocked: bool
    blocked_reason: str = ""
    lookup_amount: float = 0.0
    capped_by_max: bool = False
    avg_purchase_capped: bool = False
    ratio_used: float = 0.0
    segment_label: str = ""
    path: str = "none"


def _vlookup_approx(key: float, table: Sequence[tuple], value_index: int = 1) -> float:
    """Excel VLOOKUP(..., TRUE): largest first-column value <= key."""
    if not table:
        return 0.0
    chosen = table[0][value_index]
    for row in table:
        if key + 1e-9 >= row[0]:
            chosen = row[value_index]
        else:
            break
    return float(chosen)


def bonus_status_for_ratio(ratio: float) -> tuple[str, float]:
    ratio = max(0.0, ratio)
    label, mult = BONUS_STATUS_TABLE[0][1], BONUS_STATUS_TABLE[0][2]
    for threshold, tier_label, tier_mult in BONUS_STATUS_TABLE:
        if ratio + 1e-9 >= threshold:
            label, mult = tier_label, tier_mult
        else:
            break
    return label, mult


def apply_gwg(base_sc: float | None, gwg_pct: float) -> tuple[float, float]:
    """Return (gwg_sc, total_sc). gwg_pct 0 means None."""
    if base_sc is None or base_sc <= 0 or gwg_pct <= 0:
        return 0.0, base_sc or 0.0
    gwg_sc = round(base_sc * gwg_pct, 2)
    return gwg_sc, round(base_sc + gwg_sc, 2)


def compute_free_bonus(inp: BonusCalcInput) -> BonusCalcResult:
    if inp.locked:
        return BonusCalcResult(
            free_bonus=None,
            offer_label="No Free Bonus Allowed",
            bonus_status="",
            bonus_status_mult=0.0,
            recommended=0.0,
            cap_note="Locked or self-excluded: no outreach bonus.",
            blocked=True,
            blocked_reason=inp.lock_label or "Locked",
            path="blocked",
        )

    ngr = inp.ggr - inp.bonus
    avg_purchase = inp.purchase_amount / inp.purchase_count if inp.purchase_count else 0.0
    bonus_ratio = max(inp.bonus_pct_window, inp.bonus_pct_lifetime)
    status_label, status_mult = bonus_status_for_ratio(bonus_ratio)
    segment_pct = (
        config.BONUS_CALC_ACTIVE_PCT if inp.active else config.BONUS_CALC_INACTIVE_PCT
    )
    segment_label = f"{'Active' if inp.active else 'Inactive'} · {segment_pct * 100:.0f}% of NGR"

    if inp.active and ngr > 0:
        recommended = segment_pct * ngr * status_mult if ngr > 0 else 0.0
        ratio = recommended / avg_purchase if avg_purchase > 0 else 0.0
        ratio_used = ratio
        avg_purchase_capped = False
        if ratio > 4:
            recommended = avg_purchase * 3
            avg_purchase_capped = True
        elif ratio > 2:
            recommended = avg_purchase * 2
            avg_purchase_capped = True
        lookup_amt = _vlookup_approx(recommended, ACTIVE_POS_NGR_TABLE)
        capped_by_max = lookup_amt > config.BONUS_CALC_MAX_BONUS
        free_bonus = min(lookup_amt, config.BONUS_CALC_MAX_BONUS)
        cap_note = (
            f"Flat Elite {segment_pct * 100:.0f}% of NGR × {status_mult:.1f} status factor, "
            f"capped at {config.BONUS_CALC_MAX_BONUS:,.0f} SC."
        )
        return BonusCalcResult(
            free_bonus=round(free_bonus, 2),
            offer_label=f"{free_bonus:,.0f} SC",
            bonus_status=status_label,
            bonus_status_mult=status_mult,
            recommended=round(recommended, 2),
            cap_note=cap_note,
            blocked=False,
            lookup_amount=lookup_amt,
            capped_by_max=capped_by_max,
            avg_purchase_capped=avg_purchase_capped,
            ratio_used=round(ratio_used, 2),
            segment_label=segment_label,
            path="positive_ngr",
        )

    if inp.active and ngr <= 0:
        return BonusCalcResult(
            free_bonus=None,
            offer_label="Not eligible",
            bonus_status=status_label,
            bonus_status_mult=status_mult,
            recommended=0.0,
            cap_note="Active player with non-positive 14-day NGR: not eligible for Free Bonus.",
            blocked=False,
            segment_label=segment_label,
            path="not_eligible",
        )

    if ngr > 0:
        recommended = segment_pct * ngr * status_mult
        lookup_amt = _vlookup_approx(recommended, ACTIVE_POS_NGR_TABLE)
        capped_by_max = lookup_amt > config.BONUS_CALC_MAX_BONUS
        free_bonus = min(lookup_amt, config.BONUS_CALC_MAX_BONUS)
        return BonusCalcResult(
            free_bonus=round(free_bonus, 2),
            offer_label=f"{free_bonus:,.0f} SC",
            bonus_status=status_label,
            bonus_status_mult=status_mult,
            recommended=round(recommended, 2),
            cap_note="Inactive player: reactivation bonus from lifetime window.",
            blocked=False,
            lookup_amount=lookup_amt,
            capped_by_max=capped_by_max,
            segment_label=segment_label,
            path="inactive",
        )

    return BonusCalcResult(
        free_bonus=None,
        offer_label="No Free Bonus Allowed",
        bonus_status=status_label,
        bonus_status_mult=status_mult,
        recommended=0.0,
        cap_note="Non-positive NGR: no free bonus.",
        blocked=False,
        segment_label=segment_label,
        path="none",
    )
