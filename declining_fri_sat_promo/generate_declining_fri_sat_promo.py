"""
Friday–Saturday declining players promo — target-bucket bonuses.

3rd purchase: 10% of Target offer, rounded UP to nearest $5
5th purchase: 15% of Target offer, rounded UP to nearest $5
"""

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
EXPORTS = ROOT / "exports"

DECLINING_CSV = Path(r"c:\Users\Owner\Downloads\Declining Players (15).csv")
TARGET_XLSX = Path(
    r"c:\Users\Owner\Downloads\elite_vip_trimmed_avg_target_list_TO_ALon_16.7.xlsx"
)
DOWNLOADS_COPY = Path(
    r"c:\Users\Owner\Downloads\declining_players_fri_sat_promo_buckets.xlsx"
)

# Fixed bucket table: offer -> (bonus_3rd, bonus_5th)
BUCKET_BONUSES = {
    34.99: (5, 10),
    69.99: (10, 15),
    119.99: (15, 20),
    199.99: (20, 30),
    299.99: (30, 45),
}


def round_up_5(x: float | None) -> int | None:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return None
    return int(math.ceil(float(x) / 5.0) * 5)


def bonus_3rd(offer: float | None) -> int | None:
    if offer is None or (isinstance(offer, float) and math.isnan(offer)):
        return None
    return round_up_5(0.10 * float(offer))


def bonus_5th(offer: float | None) -> int | None:
    if offer is None or (isinstance(offer, float) and math.isnan(offer)):
        return None
    return round_up_5(0.15 * float(offer))


def player_line(offer: float | None, b3: int | None, b5: int | None) -> str:
    if (
        offer is None
        or b3 is None
        or b5 is None
        or (isinstance(offer, float) and math.isnan(offer))
    ):
        return "No matched target offer — exclude or handle manually"
    return (
        f"Purchase at ${float(offer):.2f} — get ${int(b3)} on 3rd and "
        f"${int(b5)} on 5th (max ${int(b3) + int(b5)})"
    )


def load_declining() -> pd.DataFrame:
    decl = pd.read_csv(DECLINING_CSV, encoding="utf-16", sep="\t")
    decl.columns = [c.strip() for c in decl.columns]
    if "Churn Risk Ind" in decl.columns:
        decl["Churn Risk Ind"] = (
            decl["Churn Risk Ind"]
            .astype(str)
            .str.replace(r"[^\x00-\x7F]+", "", regex=True)
            .str.strip()
        )
    decl = decl[pd.to_numeric(decl["account_id"], errors="coerce").notna()].copy()
    decl["account_id"] = decl["account_id"].astype(int)
    return decl


def build() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, list[str]]:
    decl = load_declining()
    tgt = pd.read_excel(TARGET_XLSX, sheet_name="Sheet1")
    tgt["Account ID"] = tgt["Account ID"].astype(int)

    m = decl.merge(
        tgt[
            [
                "Account ID",
                "Segment (Bucket)",
                "Player trimmed avg purchase",
                "Bucket max trimmed avg",
                "Target offer (final)",
            ]
        ],
        left_on="account_id",
        right_on="Account ID",
        how="left",
    )
    m["Target offer (final)"] = pd.to_numeric(m["Target offer (final)"], errors="coerce")
    m["b3"] = m["Target offer (final)"].map(bonus_3rd)
    m["b5"] = m["Target offer (final)"].map(bonus_5th)
    m["matched"] = m["Target offer (final)"].notna().map({True: "yes", False: "no"})
    m["player_message"] = [
        player_line(o, b3, b5)
        for o, b3, b5 in zip(m["Target offer (final)"], m["b3"], m["b5"])
    ]

    players = pd.DataFrame(
        {
            "AID": m["account_id"],
            "Agent": m["agent_name (group)"],
            "First name": m["first_name"],
            "Last name": m["last_name"],
            "Email": m["email"],
            "Matched to target list": m["matched"],
            "Segment (Bucket)": m["Segment (Bucket)"],
            "Player trimmed avg purchase": m["Player trimmed avg purchase"],
            "Target offer (purchase at)": m["Target offer (final)"],
            "Bonus on 3rd purchase (10%)": m["b3"],
            "Bonus on 5th purchase (15%)": m["b5"],
            "Max total bonus (3rd+5th)": [
                (b3 + b5) if pd.notna(b3) and pd.notna(b5) else None
                for b3, b5 in zip(m["b3"], m["b5"])
            ],
            "Player message": m["player_message"],
            "Days From Last Purchase": m.get("Days From Last Purchase"),
            "Is Locked": m.get("Is Locked"),
            "Churn Risk Ind": m.get("Churn Risk Ind"),
        }
    ).sort_values(
        ["Matched to target list", "Target offer (purchase at)", "AID"],
        ascending=[False, True, True],
    )

    matched = players[players["Matched to target list"] == "yes"].copy()
    summary_rows = []
    for offer, g in matched.groupby("Target offer (purchase at)"):
        b3 = int(g["Bonus on 3rd purchase (10%)"].iloc[0])
        b5 = int(g["Bonus on 5th purchase (15%)"].iloc[0])
        n = len(g)
        rev3 = n * float(offer) * 3
        rew3 = n * b3
        rev5 = n * float(offer) * 5
        rew5 = n * (b3 + b5)
        summary_rows.append(
            {
                "Purchase at": float(offer),
                "Players": n,
                "Bonus on 3rd (10%)": b3,
                "Bonus on 5th (15%)": b5,
                "Max total bonus": b3 + b5,
                "Purchase if 3x": round(rev3, 2),
                "Rewards if 3x (1 hit)": rew3,
                "Reward % if 3x": round(100 * rew3 / rev3, 2),
                "Purchase if 5x": round(rev5, 2),
                "Rewards if 5x (2 hits)": rew5,
                "Reward % if 5x": round(100 * rew5 / rev5, 2),
            }
        )
    summary = pd.DataFrame(summary_rows).sort_values("Purchase at")
    tot = {
        "Purchase at": "TOTAL matched",
        "Players": int(summary["Players"].sum()),
        "Bonus on 3rd (10%)": "",
        "Bonus on 5th (15%)": "",
        "Max total bonus": "",
        "Purchase if 3x": round(summary["Purchase if 3x"].sum(), 2),
        "Rewards if 3x (1 hit)": int(summary["Rewards if 3x (1 hit)"].sum()),
        "Reward % if 3x": round(
            100
            * summary["Rewards if 3x (1 hit)"].sum()
            / summary["Purchase if 3x"].sum(),
            2,
        ),
        "Purchase if 5x": round(summary["Purchase if 5x"].sum(), 2),
        "Rewards if 5x (2 hits)": int(summary["Rewards if 5x (2 hits)"].sum()),
        "Reward % if 5x": round(
            100
            * summary["Rewards if 5x (2 hits)"].sum()
            / summary["Purchase if 5x"].sum(),
            2,
        ),
    }
    summary = pd.concat([summary, pd.DataFrame([tot])], ignore_index=True)

    unit_rows = []
    for offer, (b3, b5) in BUCKET_BONUSES.items():
        rev3 = round(offer * 3, 2)
        rev5 = round(offer * 5, 2)
        unit_rows.append(
            {
                "Purchase at": offer,
                "Bonus 3rd (10%)": b3,
                "Bonus 5th (15%)": b5,
                "Max total": b3 + b5,
                "Rev 3x": rev3,
                "Reward 3x": b3,
                "Reward % 3x": round(100 * b3 / rev3, 2),
                "Rev 5x": rev5,
                "Reward 5x": b3 + b5,
                "Reward % 5x": round(100 * (b3 + b5) / rev5, 2),
            }
        )
    unit = pd.DataFrame(unit_rows)

    rules = pd.DataFrame(
        [
            {"Item": "Promo window", "Value": "Friday-Saturday"},
            {
                "Item": "Bonus events",
                "Value": "3rd purchase and 5th purchase only",
            },
            {
                "Item": "3rd purchase bonus",
                "Value": "10% of Target offer, rounded UP to nearest $5",
            },
            {
                "Item": "5th purchase bonus",
                "Value": "15% of Target offer, rounded UP to nearest $5",
            },
            {"Item": "Purchases 1, 2, 4", "Value": "No bonus"},
            {
                "Item": "Language",
                "Value": "Use purchase (not buy) in player reach-outs",
            },
            {"Item": "Declining list source", "Value": str(DECLINING_CSV)},
            {"Item": "Target buckets source", "Value": str(TARGET_XLSX)},
            {"Item": "Players in declining list", "Value": str(len(players))},
            {
                "Item": "Matched to target offer",
                "Value": str((players["Matched to target list"] == "yes").sum()),
            },
            {
                "Item": "Unmatched / exclude or manual",
                "Value": str((players["Matched to target list"] == "no").sum()),
            },
            {
                "Item": "Max scenario (5x all matched)",
                "Value": (
                    f"Purchase ${tot['Purchase if 5x']:,.2f} | "
                    f"Rewards ${tot['Rewards if 5x (2 hits)']:,} | "
                    f"{tot['Reward % if 5x']}%"
                ),
            },
        ]
    )

    matched_n = int((players["Matched to target list"] == "yes").sum())
    unmatched_n = int((players["Matched to target list"] == "no").sum())
    email_lines = [
        "Subject: Fri-Sat declining players promo — 10% on 3rd, 15% on 5th",
        "",
        "Hi team,",
        "",
        f"This Friday-Saturday promo is for the declining players list ({matched_n} matched players).",
        "",
        "Rules:",
        "- Player purchases at their assigned target offer",
        "- Bonus on the 3rd and 5th purchase only",
        "- 3rd purchase = 10% rounded up to nearest $5",
        "- 5th purchase = 15% rounded up to nearest $5",
        "",
        "Purchase at | Players | 3rd bonus | 5th bonus | Max total",
    ]
    for _, r in summary[summary["Purchase at"] != "TOTAL matched"].iterrows():
        email_lines.append(
            f"${r['Purchase at']:.2f} | {int(r['Players'])} | "
            f"${int(r['Bonus on 3rd (10%)'])} | ${int(r['Bonus on 5th (15%)'])} | "
            f"${int(r['Max total bonus'])}"
        )
    email_lines += [
        "",
        "Max scenario if all matched players complete 5 purchases:",
        (
            f"Total purchase ~${tot['Purchase if 5x'] / 1000:.1f}k · "
            f"Total rewards ~${tot['Rewards if 5x (2 hits)'] / 1000:.1f}k · "
            f"~{tot['Reward % if 5x']}% of purchase"
        ),
        "",
        "Player lines:",
    ]
    for offer, (b3, b5) in BUCKET_BONUSES.items():
        email_lines.append(
            f"- Purchase at ${offer:.2f} — get ${b3} on 3rd and "
            f"${b5} on 5th (max ${b3 + b5})"
        )
    email_lines += [
        "",
        (
            f"Note: {unmatched_n} players from the declining list have no "
            "matched target offer and are excluded for now."
        ),
    ]

    return players, summary, unit, rules, email_lines


def main() -> None:
    EXPORTS.mkdir(parents=True, exist_ok=True)
    players, summary, unit, rules, email_lines = build()
    unmatched = players[players["Matched to target list"] == "no"][
        ["AID", "Agent", "First name", "Last name", "Email", "Player message"]
    ]
    email_df = pd.DataFrame({"Email copy": email_lines})

    out_elite = EXPORTS / "declining_players_fri_sat_promo_buckets.xlsx"
    out_paths = [
        out_elite,
        EXPORTS / "declining_players_fri_sat_promo_buckets_10_15.xlsx",
        DOWNLOADS_COPY,
        DOWNLOADS_COPY.with_name("declining_players_fri_sat_promo_buckets_10_15.xlsx"),
    ]
    for out_path in out_paths:
        try:
            with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
                players.to_excel(writer, sheet_name="Players", index=False)
                summary.to_excel(writer, sheet_name="Bucket summary", index=False)
                unit.to_excel(writer, sheet_name="Per-player economics", index=False)
                rules.to_excel(writer, sheet_name="Rules", index=False)
                email_df.to_excel(writer, sheet_name="Email copy", index=False)
                unmatched.to_excel(writer, sheet_name="Unmatched", index=False)
            print(f"Wrote {out_path}")
        except PermissionError:
            print(f"LOCKED, skipped {out_path}")

    (EXPORTS / "team_email_copy.txt").write_text(
        "\n".join(email_lines), encoding="utf-8"
    )
    print(f"Wrote {EXPORTS / 'team_email_copy.txt'}")
    print(
        f"Players={len(players)} matched="
        f"{(players['Matched to target list'] == 'yes').sum()} unmatched="
        f"{(players['Matched to target list'] == 'no').sum()}"
    )
    print(
        f"Max 5x: purchase=${summary.loc[summary['Purchase at']=='TOTAL matched', 'Purchase if 5x'].iloc[0]:,} "
        f"rewards=${summary.loc[summary['Purchase at']=='TOTAL matched', 'Rewards if 5x (2 hits)'].iloc[0]:,}"
    )


if __name__ == "__main__":
    main()
