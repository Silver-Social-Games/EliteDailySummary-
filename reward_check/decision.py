"""Pure decision rules for reward verification."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Iterable


@dataclass
class VerificationResult:
    status: str
    headline: str
    detail: str
    action: str
    evidence: list[dict]


def _number(value: object) -> float:
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def _text(value: object) -> str:
    return "" if value is None else str(value)


def mask_email(email: str) -> str:
    """Mask an email while leaving it recognizable to the searching agent."""
    value = email.strip()
    if "@" not in value:
        return value
    local, domain = value.split("@", 1)
    if len(local) <= 2:
        masked_local = local[:1] + "*"
    else:
        masked_local = local[:2] + "*" * min(6, len(local) - 2)
    return f"{masked_local}@{domain}"


def campaign_matches_offer(campaign_code: str, offer_code: str) -> bool:
    """Match an offer code inside the dated/suffixed FS campaign code."""
    if not campaign_code or not offer_code:
        return False
    campaign = campaign_code.casefold()
    offer = offer_code.casefold()
    if offer in campaign:
        return True
    base = re.sub(r"_\d+$", "", offer)
    return bool(base and base in campaign)


def _valid_orders(orders: Iterable[dict]) -> list[dict]:
    return [
        row
        for row in orders
        if _text(row.get("status")).casefold() == "succeeded"
        and not bool(row.get("refunded"))
    ]


def _matching_wallet_rows(
    wallet_rows: Iterable[dict],
    *,
    offer_code: str,
    campaign_code: str,
    expected_fs: int | None,
) -> list[dict]:
    rows = list(wallet_rows)
    if campaign_code:
        exact = [
            row
            for row in rows
            if _text(row.get("campaign_code")).casefold() == campaign_code.casefold()
        ]
        if exact:
            return exact
    if offer_code:
        linked = [
            row
            for row in rows
            if campaign_matches_offer(_text(row.get("campaign_code")), offer_code)
        ]
        if linked:
            return linked
    if expected_fs is not None:
        return [
            row
            for row in rows
            if int(_number(row.get("total_spins"))) == expected_fs
        ]
    return rows


def verify_free_spins(
    orders: list[dict],
    wallet_rows: list[dict],
    *,
    expected_fs: int | None,
    offer_code: str = "",
    campaign_code: str = "",
) -> VerificationResult:
    """Classify a free-spin grant using the wallet as source of truth."""
    valid_orders = _valid_orders(orders)
    matches = _matching_wallet_rows(
        wallet_rows,
        offer_code=offer_code,
        campaign_code=campaign_code,
        expected_fs=expected_fs,
    )

    if matches:
        matches.sort(
            key=lambda row: (
                int(_number(row.get("total_spins"))) == (expected_fs or -1),
                _text(row.get("credited") or row.get("created_at")),
            ),
            reverse=True,
        )
        row = matches[0]
        total = int(_number(row.get("total_spins")))
        left = int(_number(row.get("left_spins")))
        used = row.get("used")
        status = _text(row.get("status")).casefold()

        if expected_fs is not None and total < expected_fs:
            return VerificationResult(
                status="partial",
                headline=f"Partial: {total} of {expected_fs} FS found",
                detail="A matching free-spin wallet exists, but the credited count is lower than promised.",
                action="Escalate the count mismatch before adding more spins.",
                evidence=matches,
            )

        if used is not None or (status == "finished" and left == 0):
            return VerificationResult(
                status="received_used",
                headline=f"Received and used: {total} FS",
                detail=f"The wallet grant is finished with {left} spins remaining.",
                action="No replacement credit is needed.",
                evidence=matches,
            )

        expired_at = row.get("expired")
        expired = status == "expired"
        if isinstance(expired_at, datetime):
            comparable = expired_at
            if comparable.tzinfo is None:
                comparable = comparable.replace(tzinfo=timezone.utc)
            expired = expired or comparable < datetime.now(timezone.utc)
        if expired:
            return VerificationResult(
                status="received_expired",
                headline=f"Received but expired: {total} FS",
                detail=f"The wallet still shows {left} spins, but the grant has expired.",
                action="Review the expiry policy before considering a replacement.",
                evidence=matches,
            )

        return VerificationResult(
            status="received_unused",
            headline=f"Received and unused: {total} FS",
            detail=f"The wallet shows {left} spins remaining.",
            action="Ask the player to reopen the assigned game; do not issue a duplicate grant.",
            evidence=matches,
        )

    if offer_code and not valid_orders:
        return VerificationResult(
            status="inconclusive",
            headline="No qualifying purchase found",
            detail="No succeeded, non-refunded order matched the offer and date window.",
            action="Confirm the offer code, purchase date, charge code, or transaction UUID.",
            evidence=orders,
        )

    if valid_orders:
        promised = f"{expected_fs} FS" if expected_fs is not None else "the promised FS"
        return VerificationResult(
            status="missing",
            headline=f"Missing: {promised}",
            detail="The purchase succeeded, but no matching free-spin wallet grant was found.",
            action="Re-trigger the campaign or manually credit the verified missing spins.",
            evidence=valid_orders,
        )

    return VerificationResult(
        status="missing",
        headline="No matching free-spin grant found",
        detail="No wallet grant matched the supplied campaign, count, and date window.",
        action="Confirm the campaign details before issuing a manual credit.",
        evidence=wallet_rows,
    )


def reconcile_free_spins_from_rewards(
    current: VerificationResult,
    reward_rows: list[dict],
    *,
    expected_fs: int | None,
    offer_code: str = "",
    campaign_code: str = "",
) -> VerificationResult:
    """Use played reward facts only when the wallet lookup did not prove receipt."""
    if current.status.startswith("received"):
        return current

    matches: list[dict] = []
    for row in reward_rows:
        code = _text(row.get("campaign_code"))
        count = int(
            _number(row.get("reward_count"))
            or _number(row.get("total_spins"))
        )
        campaign_ok = not campaign_code or code.casefold() == campaign_code.casefold()
        offer_ok = not offer_code or campaign_matches_offer(code, offer_code)
        count_ok = expected_fs is None or count == expected_fs
        if campaign_ok and offer_ok and count_ok:
            matches.append(row)

    if not matches:
        return current

    total = int(
        _number(matches[0].get("reward_count"))
        or _number(matches[0].get("total_spins"))
    )
    return VerificationResult(
        status="received_used",
        headline=f"Received and played: {total} FS",
        detail="The wallet row was unavailable, but played free-spin reward facts match the campaign.",
        action="No replacement credit is needed.",
        evidence=matches,
    )


def verify_purchase_credit(
    orders: list[dict],
    *,
    expected_sc: float | None,
    expected_gc: float | None,
) -> VerificationResult:
    """Classify SC/GC credited on a purchase order."""
    valid_orders = _valid_orders(orders)
    if not valid_orders:
        return VerificationResult(
            status="inconclusive",
            headline="No qualifying purchase found",
            detail="No succeeded, non-refunded purchase matched the search.",
            action="Confirm the offer code, purchase date, charge code, or transaction UUID.",
            evidence=orders,
        )

    row = valid_orders[0]
    actual_sc = _number(row.get("sc_amount"))
    actual_gc = _number(row.get("gc_amount"))
    mismatches: list[str] = []
    if expected_sc is not None and abs(actual_sc - expected_sc) > 0.01:
        mismatches.append(f"SC expected {expected_sc:g}, found {actual_sc:g}")
    if expected_gc is not None and abs(actual_gc - expected_gc) > 0.01:
        mismatches.append(f"GC expected {expected_gc:g}, found {actual_gc:g}")

    if mismatches:
        return VerificationResult(
            status="amount_mismatch",
            headline="Purchase succeeded, amount mismatch",
            detail="; ".join(mismatches),
            action="Review the offer configuration before applying any correction.",
            evidence=valid_orders,
        )

    return VerificationResult(
        status="received",
        headline=f"Received: {actual_sc:g} SC and {actual_gc:g} GC",
        detail=f"Order {row.get('order_id')} succeeded and was not refunded.",
        action="No replacement credit is needed.",
        evidence=valid_orders,
    )


def verify_tournament_prize(
    rewards: list[dict],
    *,
    expected_sc: float | None,
    expected_gc: float | None,
) -> VerificationResult:
    """Classify Platform Tournament payouts."""
    accepted = [row for row in rewards if bool(row.get("accepted"))]
    if not accepted:
        return VerificationResult(
            status="not_paid",
            headline="No tournament payout found",
            detail="No accepted Platform Tournament reward exists in the selected date window.",
            action="Confirm the tournament date and expected prize in the admin system.",
            evidence=rewards,
        )

    row = accepted[0]
    actual_sc = _number(row.get("sc_amount"))
    actual_gc = _number(row.get("gc_amount"))
    mismatches: list[str] = []
    if expected_sc is not None and abs(actual_sc - expected_sc) > 0.01:
        mismatches.append(f"SC expected {expected_sc:g}, found {actual_sc:g}")
    if expected_gc is not None and abs(actual_gc - expected_gc) > 0.01:
        mismatches.append(f"GC expected {expected_gc:g}, found {actual_gc:g}")

    if mismatches:
        return VerificationResult(
            status="amount_mismatch",
            headline="Tournament payout found, amount mismatch",
            detail="; ".join(mismatches),
            action="Confirm the player's prize tier before issuing a correction.",
            evidence=accepted,
        )

    return VerificationResult(
        status="received",
        headline=f"Tournament payout received: {actual_sc:g} SC and {actual_gc:g} GC",
        detail=f"Bonus reward {row.get('bonus_reward_id')} was accepted.",
        action="No replacement credit is needed.",
        evidence=accepted,
    )


def account_warning(player: dict) -> str:
    """Return a safety warning for restricted accounts."""
    if player.get("locked"):
        reason = _text(player.get("lock_reason")) or "No lock reason recorded"
        return f"Account is locked: {reason}. Do not recommend player outreach."
    return ""


def slack_summary(
    player: dict,
    reward_label: str,
    result: VerificationResult,
    *,
    zendesk_tid: str = "",
) -> str:
    """Build a short copy/paste Slack summary."""
    tid = f"\nZendesk TID: {zendesk_tid}" if zendesk_tid.strip() else ""
    warning = account_warning(player)
    warning_line = f"\nAccount warning: {warning}" if warning else ""
    return (
        f"AID {player.get('aid')} — {reward_label}\n\n"
        f"Result: {result.headline}\n"
        f"Evidence: {result.detail}\n"
        f"Action: {result.action}"
        f"{tid}{warning_line}"
    )


def iso_value(value: object) -> object:
    """Convert BigQuery date/time values for Streamlit tables."""
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def display_rows(rows: Iterable[dict]) -> list[dict]:
    return [{key: iso_value(value) for key, value in row.items()} for row in rows]
