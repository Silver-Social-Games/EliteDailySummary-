# Zendesk ticket draft rules (Elite daily summary)

## Review-only policy

**Never create or send Zendesk tickets without agent permission.**

- Drafts are generated for **review only** (Ticket column + modal).
- Agent edits Subject and Message, copies into Zendesk, and sends manually.
- No API auto-create, no background ticket creation.
- **Open Zendesk** pre-selects the requester when known; subject/body are not written until the agent pastes and submits.
- Modal fields: **Subject** and **Message** only.

---

## Formatting rules

| Rule | Detail |
|------|--------|
| Subject | Title Case; emojis OK |
| Body | Normal prose; emojis OK; no agent name |
| Sign-off | `Best regards,` (CheckIn / Redemption / LightTouch) or `Have a good one,` (PushPurchase) |
| Banned | Em dash (—) in player copy; RD $ amounts; redeem ID in player copy |

---

## Routing

Family is chosen in order:

1. `redemption_in_progress` → Redemption
2. `big_win_day_before` → LightTouch
3. Recommendation = **Push purchase** → PushPurchase
4. Otherwise → CheckIn (includes Soft check-in only)

---

## Active draft families (4)

### PushPurchase

**When:** Recommendation is **Push purchase** (churn, same-weekday skip with low 7D frequency, etc.)

**Subject:** `You've Been Chosen 🎁`

**Message:**
```
Hey {first_name},

Noticed things were quiet on Jackpota lately, and I wanted to check in personally 👋

I've activated an exclusive offer for you: just grab the {GC_package_name} and reply once you do, I'll personally add a little extra on top 🎁

Sometimes one spin is all you need to win BIG.

Have a good one,
```

`{GC_package_name}` is an **editable placeholder** — agent fills in the modal before sending.

### CheckIn

**When:** Eligible row, not Push purchase (e.g. Soft check-in only)

**Subject:** `Checking In On You 👑`

**Message:**
```
Hi {first_name},

It's been a little while, and I just wanted to check in on how everything's going? 💬
I hope you've been doing well and still enjoying the fun at Jackpota!

If you ever need anything: game recommendations, slot tips or just chat, I am here for you.

I'd love to hear from you and see how I can make your experience even better.

Best regards,
```

### Redemption

**Code:** redemption_in_progress

**Subject:** `Redemption Status 🔄`

**Message:**
```
Hi {first_name},

Congratulations on your win! 🎉

I'm personally keeping an eye on your redemption, and I'll update you as soon as there's news.

In the meantime, drop me a message if you need anything else.

Best regards,
```

### LightTouch

**Code:** big_win_day_before

**Subject:** `Still Buzzing About Your Run 🎉`

**Message:**
```
Hi {first_name},

Hope you've been enjoying your time on Jackpota. Congratulations on your recent run!
I just wanted to check in and see how everything is going.

Let me know if you need anything to improve your experience.

Best regards,
```

---

## Disabled (no ticket draft)

Ticket column shows `—`.

| Reason | Why |
|--------|-----|
| `self_exclusion` | Do not contact |
| `red_flag` | Compliance |
| `account_locked` | Handle via Ops/Zendesk manually |
| `payment_failed` | Handle manually |
| Recommendation: No action / No outreach | Agent decision |
| No purchase push (except post-win LightTouch) | Soft check-in only rows |

Agent context (AID, reason, urgency) remains in the **Reason** and **Recommendation** columns.
