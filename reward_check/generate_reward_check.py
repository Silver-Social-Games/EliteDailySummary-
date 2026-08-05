"""Command-line entry point for reward verification."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from elite_lib import get_client  # noqa: E402
from reward_check.decision import (  # noqa: E402
    display_rows,
    reconcile_free_spins_from_rewards,
    slack_summary,
    verify_free_spins,
    verify_purchase_credit,
    verify_tournament_prize,
)
from reward_check.queries import (  # noqa: E402
    lookup_fact_rewards,
    lookup_fs_wallet,
    lookup_orders,
    lookup_tournament_rewards,
    resolve_players,
)


def parse_date(value: str) -> date:
    return date.fromisoformat(value)


def main() -> None:
    today = date.today()
    parser = argparse.ArgumentParser(description="Verify a player reward")
    parser.add_argument("--search", required=True, help="Exact AID or email")
    parser.add_argument(
        "--type",
        required=True,
        choices=("free_spins", "purchase_sc", "tournament_prize"),
    )
    parser.add_argument("--from", dest="date_from", type=parse_date, default=today - timedelta(days=6))
    parser.add_argument("--to", dest="date_to", type=parse_date, default=today)
    parser.add_argument("--offer-code", default="")
    parser.add_argument("--campaign-code", default="")
    parser.add_argument("--expected-fs", type=int)
    parser.add_argument("--expected-sc", type=float)
    parser.add_argument("--expected-gc", type=float)
    parser.add_argument("--zendesk-tid", default="")
    args = parser.parse_args()

    client = get_client()
    players = resolve_players(client, args.search)
    if not players:
        parser.error("No account matched that exact AID or email.")
    if len(players) > 1:
        aids = ", ".join(str(row["aid"]) for row in players)
        parser.error(f"Email matched multiple AIDs ({aids}); use an exact AID.")
    player = players[0]
    aid = int(player["aid"])

    if args.type == "free_spins":
        orders = (
            lookup_orders(client, aid, args.date_from, args.date_to, args.offer_code)
            if args.offer_code
            else []
        )
        wallet = lookup_fs_wallet(
            client,
            aid,
            args.date_from,
            args.date_to,
            args.offer_code,
        )
        result = verify_free_spins(
            orders,
            wallet,
            expected_fs=args.expected_fs,
            offer_code=args.offer_code,
            campaign_code=args.campaign_code,
        )
        if result.status in {"missing", "inconclusive"}:
            rewards = lookup_fact_rewards(
                client,
                aid,
                args.date_from,
                args.date_to,
                args.offer_code,
            )
            result = reconcile_free_spins_from_rewards(
                result,
                rewards,
                expected_fs=args.expected_fs,
                offer_code=args.offer_code,
                campaign_code=args.campaign_code,
            )
        reward_label = "Free Spins"
    elif args.type == "purchase_sc":
        orders = lookup_orders(
            client,
            aid,
            args.date_from,
            args.date_to,
            args.offer_code,
        )
        result = verify_purchase_credit(
            orders,
            expected_sc=args.expected_sc,
            expected_gc=args.expected_gc,
        )
        reward_label = "Purchase SC / GC"
    else:
        rewards = lookup_tournament_rewards(
            client,
            aid,
            args.date_from,
            args.date_to,
        )
        result = verify_tournament_prize(
            rewards,
            expected_sc=args.expected_sc,
            expected_gc=args.expected_gc,
        )
        reward_label = "Tournament Prize"

    print(
        slack_summary(
            player,
            reward_label,
            result,
            zendesk_tid=args.zendesk_tid,
        )
    )
    print("\nEvidence:")
    print(json.dumps(display_rows(result.evidence), indent=2, default=str))


if __name__ == "__main__":
    main()
