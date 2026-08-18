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
- Two homes: `Downloads\Elite` is the workshop (keep it). User-facing files
  open from `VIP\Elite_Cursor\<project>` via `mirror_to_cursor`. Never write
  to the deleted `VIP\Cursor` folder.
- Reuse BigQuery and canonical Elite-book helpers from `elite_lib`.
- Keep daily reporting, WoW drop analysis, feedback CRO, decline protocol, and
  reference assets in their dedicated top-level initiative folders.
- Treat `daily_summary/generate_daily_elite_summary.py` as shared report
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
- After every daily/weekend summary (Cursor or manual): `python daily_summary/publish_pages_git.py` → live site [EliteDailySummary-](https://silver-social-games.github.io/EliteDailySummary-/)
- Schedule: Sun–Thu at 10:00 AM Israel time (task passes `-EnablePagesAutoPublish`)
- Daily Skill: `@daily-elite-summary`
- AM Brief board: `@elite-am-brief` · `python am_daily_dashboard/generate_am_daily_dashboard.py` · open from `VIP\Elite_Cursor\AM Brief` (not Pages)
- CRM offer playbook board: `python crm_offer_calendar/generate_crm_offer_playbook.py` — edit `crm_offer_calendar/data/current_offers.json` for a new month (local handoff; not Pages)
- Campaign email readers (Sunday, opened only): `python campaign_email_readers/generate_campaign_email_readers.py` · [`campaign_email_readers/CAMPAIGN_EMAIL_READERS.md`](campaign_email_readers/CAMPAIGN_EMAIL_READERS.md) (local; not Pages)
- Elite roster by AM (unlocked, no Take a break): `python exports/generate_elite_roster_by_am.py` → `VIP\Elite_Cursor\Roster and Drop Lists` (AID, email, phone when present, first name; exclude `uam`/`elite_users` locked and lock text containing take a break — TAB is not always already locked)
- Purchase lookup: `@purchase-lookup`
- WoW drop investigation: `@wow-drop-reason-analysis`
- Feedback CRO: `@elite-feedback-cro`
- Birthday gift AID summary: `@birthday-gift-activity`
- After a finished project or successful multi-step task: `@collaboration-wrap`
  (wrap validation with the user when needed; lock learnings; efficiency pass).
  During the task, pick the cheaper path first
  (`.cursor/rules/elite-task-efficiency.mdc`).

Use each Skill for commands, outputs, format baselines, and task-specific checks.

## Scope and safety

- Do not use workshop e-commerce data unless explicitly requested.
- Do not conflate Churn, Active decliner, and same-weekday skip.
- Do not use the tag-only Elite roster for dashboard revenue without explaining
  the known book variance.
- Use Python generators for heavy tables that exceed MCP scan limits.
- Preserve locked daily and weekend format baselines unless the user requests a
  layout change.
