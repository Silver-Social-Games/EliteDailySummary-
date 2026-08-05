# Elite Decline Protocol

On-demand rolling 7-day analysis for Elite players who purchased in both the
latest and prior 7-day windows but purchased less in the latest window.

Run from the repository root:

```bash
python decline_protocol/generate_decline_protocol.py
python decline_protocol/generate_decline_protocol.py --date YYYY-MM-DD
```

Generated reports are written to
`decline_protocol/decline_protocols/YYYY-MM-DD_decline_protocol.md`.
Definitions and reason priority remain canonical in [`Elite.MD`](../Elite.MD).
