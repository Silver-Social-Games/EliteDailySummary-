# AGENTS.md — Elite Analytics

BigQuery analytics for the managed Elite book in
`silver-social-games-data` (EU).

## Sources of truth

- Definitions and methodology: [`Elite.MD`](Elite.MD)
- Project rules: [`.cursor/rules/`](.cursor/rules/)
- Repeatable workflows: [`.cursor/skills/`](.cursor/skills/)
- Daily operations: [`daily_summary/DAILY_SUMMARY.md`](daily_summary/DAILY_SUMMARY.md)

Do not duplicate detailed workflows here. Update the owning document or Skill.

## Repository organization

- Create one top-level folder per initiative.
- Keep initiative generators, documentation, `exports/`, `handoffs/`, and
  optional `data/` together.
- Reuse BigQuery and canonical Elite-book helpers from `elite_lib`.
- Do not add unrelated deliverables to `decline_check/`.
- Treat `decline_check/generate_daily_elite_summary.py` as shared report
  implementation, not the scheduled entry point.
- Do not create extra status or summary Markdown files; report status in chat.

## Mandatory reporting rules

- Say **Elite**, not VIP. Display `account_id` as **AID**.
- Say **Purchased players** for distinct account-day `purchased > 0`.
- Aggregate `daily_player_revenue_kpis` by `account_id, date` before totals.
- Use `dbt_aninditac.elite` for dashboard-parity revenue.
- Use latest `dbt_utils.elite_account_tags.tag_agent_1` for Agent labels.
- Check `uam_accounts.locked` and `lock_reason` before drop conclusions.
- TID means Zendesk ticket ID; purchase identifiers are Order IDs or UUIDs.
- Never expose credentials or commit credential files.

The complete definitions and examples live in `Elite.MD` and the focused rules.

## Active workflows

- Morning report: `python daily_summary/generate_morning_elite.py`
- Schedule: Sun–Thu at 10:00 AM Israel time
- Daily Skill: `@daily-elite-summary`
- AM Brief board: `@elite-am-brief` · `python am_daily_dashboard/generate_am_daily_dashboard.py` · [`am_daily_dashboard/AM_DAILY_DASHBOARD.md`](am_daily_dashboard/AM_DAILY_DASHBOARD.md)
- Purchase lookup: `@purchase-lookup`
- WoW drop investigation: `@wow-drop-reason-analysis`
- Feedback CRO: `@elite-feedback-cro`
- Birthday gift AID summary: `@birthday-gift-activity`

Use each Skill for commands, outputs, format baselines, and task-specific checks.

## Scope and safety

- Do not use workshop e-commerce data unless explicitly requested.
- Do not conflate Churn, Active decliner, and same-weekday skip.
- Do not use the tag-only Elite roster for dashboard revenue without explaining
  the known book variance.
- Use Python generators for heavy tables that exceed MCP scan limits.
- Preserve locked daily and weekend format baselines unless the user requests a
  layout change.
