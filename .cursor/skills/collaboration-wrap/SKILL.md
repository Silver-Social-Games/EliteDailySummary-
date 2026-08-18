---
name: collaboration-wrap
description: After a finished project or successful task, run wrap validation with the user when needed, lock learnings, then make the next run faster and write it into the owning Cursor rule or Skill. Use when the user says wrap up, wrap validation, lock this in, what did we learn, memorize this, or confirms a multi-step task is done / good.
---

# Collaboration wrap

Run this at the end of a **project** or a **successful multi-step task**. Skip one-line edits and failed/abandoned work.

Do not create a new status or learnings Markdown file. Chat is the recap. Durable behavior goes into an existing `.cursor/rules/*.mdc` or `.cursor/skills/*/SKILL.md`.

## Steps

1. Name what we finished in one sentence.
2. Pull **1–3** learnings that should change the next run. Keep only:
   - Where files live / what to tell the user
   - A workflow order that was wrong or missing
   - A preference the user had to repeat
   - A check that would have prevented rework
3. **Wrap validation (required check).** Ask the user **one short question** when a preference still needs their call. Ask when:
   - Two valid defaults exist (e.g. keep a copy vs delete)
   - A new habit would change every future run
   - You are unsure whether to automate something
   Do **not** ask when the answer is already clear from this session. Max one question. If nothing needs a call, say wrap validation is clear and skip the question.
4. **Efficiency pass (required).** Find **one** way the next run of this task is faster or simpler. Look for:
   - Repeated questions you can default
   - Extra folders / copies / steps the user does not use
   - A helper, flag, or Skill line that would skip work
   - A command order that avoids a second pass
   Pick the highest-leverage change. If it is small and safe, implement it now. If it is a process change, write it into the owning Skill or rule. Skip cosmetic refactors.
5. Drop trivia: typos, one-off paths, things already in a rule.
6. Write each learning and the efficiency change into the **owning** rule or Skill (short bullet). Create a new always-apply rule only if no owner exists and the behavior is cross-cutting.
7. Reply in chat with this shape:

```
Wrapped: <what we finished>

Locked in:
- <learning> → <rule or skill path>

Faster next time:
- <what changed> → <file or skill>

Wrap validation:
- <one short question>
  OR
- Clear — nothing to decide

Next time I will: <one sentence>
```

When the user answers wrap validation, update the owning rule/Skill immediately and confirm in one line.

## Owners (this repo)

| If the learning is about | Write it here |
|---|---|
| Where to open generated files | `.cursor/rules/elite-export-destination.mdc` |
| Daily / weekend / Pages / Slack | `@daily-elite-summary` + morning-send / Pages rules |
| AM Brief | `@elite-am-brief` |
| Offer economy / buckets | `.cursor/rules/elite-offer-economy.mdc` |
| Definitions / Elite vs VIP / AID | `.cursor/rules/elite-core.mdc` |
| How we wrap and collaborate | this Skill + `.cursor/rules/elite-collaboration-wrap.mdc` |
