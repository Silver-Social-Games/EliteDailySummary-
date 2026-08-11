"""Build the shareable CRM offer playbook board from a monthly offer plan.

The offer plan lives in JSON so a new month is a data swap, not a rebuild:

    python crm_offer_calendar/generate_crm_offer_playbook.py
    python crm_offer_calendar/generate_crm_offer_playbook.py --offers data/2026-09_offers.json

Output is one self-contained HTML file under handoffs/ with no external assets,
so it can be emailed, opened from a local web server, or printed to PDF.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_OFFERS = BASE_DIR / "data" / "current_offers.json"
DEFAULT_OUTPUT = BASE_DIR / "handoffs" / "crm_weekday_offer_playbook.html"

DAY_ORDER = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

# Bands are ordered high to low; a cell takes the first band its opening
# percentage reaches. Ranges band on their lower guaranteed number.
BANDS = [
    {"id": "40plus", "label": "40% and above", "min": 40, "hue": "var(--green)", "rgb": "31,138,101"},
    {"id": "30to39", "label": "30% to 39%", "min": 30, "hue": "var(--blue)", "rgb": "54,133,191"},
    {"id": "20to29", "label": "20% to 29%", "min": 20, "hue": "var(--yellow)", "rgb": "192,133,50"},
    {"id": "below20", "label": "Below 20%", "min": 0, "hue": "var(--orange)", "rgb": "219,112,75"},
]

REQUIRED_CELL_KEYS = ("day", "campaign", "lead", "lead_low")

TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>__TITLE__</title>
<style>
  :root {
    --text: #14141aef;
    --text-2: #14141abd;
    --text-3: #1414148a;
    --page: #ffffff;
    --stroke: #1414141f;
    --stroke-2: #14141433;
    --green: #1f8a65;
    --blue: #3685bf;
    --yellow: #c08532;
    --orange: #db704b;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    padding: 32px 28px 56px;
    background: var(--page);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    font-size: 14px;
    line-height: 20px;
    -webkit-text-size-adjust: 100%;
  }
  .wrap { max-width: 1400px; margin: 0 auto; }
  h1 { font-size: 24px; line-height: 30px; font-weight: 600; margin: 0; }
  .title-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
  .sub { color: var(--text-2); margin: 6px 0 0; max-width: 900px; }
  .filters { display: flex; flex-wrap: wrap; gap: 26px; margin: 24px 0 10px; }
  .filter-label { font-size: 12px; line-height: 16px; color: var(--text-3); margin-bottom: 7px; }
  .chips { display: flex; flex-wrap: wrap; gap: 7px; }
  .chip {
    display: inline-flex; align-items: center; gap: 6px;
    padding: 3px 10px; border-radius: 999px; cursor: pointer;
    border: 1px solid var(--stroke-2); background: transparent;
    font: inherit; font-size: 12px; line-height: 18px; color: var(--text-2);
    -webkit-tap-highlight-color: transparent;
  }
  .chip[aria-pressed="true"] { background: #1414141a; color: var(--text); }
  .dot { width: 8px; height: 8px; border-radius: 999px; display: inline-block; flex-shrink: 0; }
  .state { font-size: 12px; line-height: 16px; color: var(--text-3); margin: 0 0 16px; }
  .nav { display: flex; gap: 8px; margin-bottom: 18px; }
  .nav a {
    text-decoration: none; color: var(--text-2); font-weight: 600; font-size: 13px;
    padding: 5px 14px; border: 1px solid var(--stroke-2); border-radius: 999px;
  }
  .nav a.active { color: #fff; background: var(--green); border-color: var(--green); }

  .board.desktop { display: grid; column-gap: 10px; row-gap: 10px; align-items: stretch; }
  .day-head {
    text-align: center; padding-bottom: 7px; border-bottom: 2px solid var(--stroke-2);
    font-weight: 600;
  }
  .cycle-label { display: flex; flex-direction: column; justify-content: center; }
  .cycle-label strong { font-size: 12px; line-height: 16px; color: var(--text-2); }
  .cycle-label span { font-size: 12px; line-height: 16px; color: var(--text-3); }

  .box {
    min-height: 152px; border-radius: 8px; overflow: hidden;
    display: flex; flex-direction: column;
    border: 1px solid var(--stroke-2); border-left-width: 3px;
  }
  .box.muted { opacity: .5; background: #1414140f; border-color: var(--stroke); }
  .box-head {
    height: 46px; flex-shrink: 0; padding: 0 12px; display: flex; align-items: center;
    justify-content: center; text-align: center;
    border-bottom: 1px solid var(--stroke-2);
  }
  .box.muted .box-head { background: #14141414; border-color: var(--stroke); }
  .box-head span, .box-head a {
    display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
    font-size: 12px; line-height: 16px; font-weight: 600;
  }
  /* The offer name is the click target for its campaign sheet. */
  .box-head a { width: 100%; color: inherit; text-decoration: none; cursor: pointer; }
  .box-head a:hover { text-decoration: underline; text-underline-offset: 2px; }
  .box-body { flex: 1; display: flex; flex-direction: column; padding: 10px 12px 11px; }
  .caption { font-size: 12px; line-height: 16px; color: var(--text-3); }
  .lead { font-size: 21px; line-height: 26px; font-weight: 600; padding-top: 2px; }
  .follow {
    margin-top: auto; padding-top: 9px; border-top: 1px solid var(--stroke);
    font-size: 12px; line-height: 16px; color: var(--text-2);
  }
  .follow b { color: var(--text); }

  /* Phones and small tablets: the seven column calendar cannot fit, so each
     weekday becomes its own block with both rotations side by side. */
  .board.mobile { display: block; }
  .day-block { margin-bottom: 18px; }
  .day-block-title {
    font-weight: 600; padding-bottom: 6px; margin-bottom: 8px;
    border-bottom: 2px solid var(--stroke-2);
  }
  .pair { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
  .cycle-tag { font-size: 12px; line-height: 16px; color: var(--text-3); margin-bottom: 4px; }
  .board.mobile .box-head { height: auto; min-height: 46px; padding: 8px 10px; }
  .board.mobile .box-head span { -webkit-line-clamp: 3; }
  .board.mobile .lead { font-size: 19px; line-height: 24px; }

  @media (max-width: 900px) {
    body { padding: 20px 16px 40px; }
    h1 { font-size: 20px; line-height: 26px; }
    .filters { gap: 16px; margin: 18px 0 8px; }
    .chip { padding: 8px 14px; font-size: 13px; line-height: 18px; }
  }

  @media print {
    body { padding: 12px; }
    .filters, .state, .title-row .chips { display: none; }
    .box, .day-block { break-inside: avoid; }
  }
</style>
</head>
<body>
<div class="wrap">
  __NAV__
  <div class="title-row">
    <h1>__TITLE__</h1>
    <div class="chips">
      <button class="chip" id="quick-all">All days</button>
      <button class="chip" id="quick-weekend">Weekend</button>
    </div>
  </div>
  <p class="sub">__SUBTITLE__</p>

  <div class="filters">
    <div>
      <div class="filter-label">Days</div>
      <div class="chips" id="day-chips"></div>
    </div>
    <div>
      <div class="filter-label">First offer %</div>
      <div class="chips" id="band-chips"></div>
    </div>
  </div>

  <p class="state" id="state"></p>
  <div class="board" id="board"></div>
</div>

<script>
const dayOrder = __DAY_ORDER__;
const bands = __BANDS__;
const cycles = __CYCLES__;

let selectedDays = dayOrder.slice();
let selectedBands = bands.map(band => band.id);

const bandFor = leadLow => bands.find(band => leadLow >= band.min) || bands[bands.length - 1];
const isNarrow = () => window.matchMedia("(max-width: 900px)").matches;
const escapeHtml = value => String(value).replace(/[&<>"]/g, ch =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch]));

function renderChips() {
  document.getElementById("day-chips").innerHTML = dayOrder.map(day => `
    <button class="chip" data-day="${day}" aria-pressed="${selectedDays.includes(day)}">${day}</button>
  `).join("");

  document.getElementById("band-chips").innerHTML = bands.map(band => `
    <button class="chip" data-band="${band.id}" aria-pressed="${selectedBands.includes(band.id)}">
      <span class="dot" style="background:${band.hue}"></span>${escapeHtml(band.label)}
    </button>
  `).join("");
}

function boxHtml(cell, muted) {
  const band = bandFor(cell.lead_low);
  const tint = muted ? "" :
    `background: rgba(${band.rgb}, .07); border-color: rgba(${band.rgb}, .55); border-left-color: ${band.hue};`;
  const headTint = muted ? "" : `background: rgba(${band.rgb}, .16); border-color: rgba(${band.rgb}, .5);`;
  const follow = cell.follow_label
    ? `<div class="follow">${escapeHtml(cell.follow_label)} <b>${escapeHtml(cell.follow_value)}</b></div>`
    : "";
  const name = escapeHtml(cell.campaign);
  const heading = cell.link
    ? `<a href="${escapeHtml(cell.link)}" target="_blank" rel="noopener noreferrer"
          title="Open ${name} in ${escapeHtml(cell.link_label || "the campaign sheet")}">${name}</a>`
    : `<span>${name}</span>`;

  return `
    <div class="box ${muted ? "muted" : ""}" style="${tint}">
      <div class="box-head" style="${headTint}">
        ${heading}
      </div>
      <div class="box-body">
        <div class="caption">First offer</div>
        <div class="lead">${escapeHtml(cell.lead)}</div>
        ${follow}
      </div>
    </div>`;
}

function cellFor(cycle, day) {
  return cycle.cells.find(entry => entry.day === day);
}

function desktopHtml(days, activeBands) {
  let html = "<span></span>" + days.map(day => `<div class="day-head">${day}</div>`).join("");

  for (const cycle of cycles) {
    html += `<div class="cycle-label"><strong>${escapeHtml(cycle.title)}</strong>` +
            `<span>${escapeHtml(cycle.note || "")}</span></div>`;
    html += days.map(day => {
      const cell = cellFor(cycle, day);
      return boxHtml(cell, !activeBands.includes(bandFor(cell.lead_low).id));
    }).join("");
  }
  return html;
}

function mobileHtml(days, activeBands) {
  return days.map(day => `
    <section class="day-block">
      <div class="day-block-title">${day}</div>
      <div class="pair">
        ${cycles.map(cycle => {
          const cell = cellFor(cycle, day);
          return `<div>
            <div class="cycle-tag">${escapeHtml(cycle.title)}</div>
            ${boxHtml(cell, !activeBands.includes(bandFor(cell.lead_low).id))}
          </div>`;
        }).join("")}
      </div>
    </section>`).join("");
}

function render() {
  const chosen = dayOrder.filter(day => selectedDays.includes(day));
  const days = chosen.length ? chosen : dayOrder;
  const activeBands = selectedBands.length ? selectedBands : bands.map(band => band.id);

  document.getElementById("state").textContent =
    `Showing ${days.length} of ${dayOrder.length} days` +
    (activeBands.length === bands.length
      ? ", all first offer bands highlighted"
      : `, ${activeBands.length} of ${bands.length} first offer bands highlighted`);

  const board = document.getElementById("board");
  const narrow = isNarrow();
  board.className = narrow ? "board mobile" : "board desktop";
  board.style.gridTemplateColumns = narrow ? "" : `92px repeat(${days.length}, minmax(0, 1fr))`;
  board.innerHTML = narrow ? mobileHtml(days, activeBands) : desktopHtml(days, activeBands);

  renderChips();
}

document.addEventListener("click", event => {
  const chip = event.target.closest(".chip");
  if (!chip) return;

  if (chip.id === "quick-all") {
    selectedDays = dayOrder.slice();
  } else if (chip.id === "quick-weekend") {
    selectedDays = ["Friday", "Saturday"];
  } else if (chip.dataset.day) {
    const day = chip.dataset.day;
    selectedDays = selectedDays.includes(day)
      ? selectedDays.filter(entry => entry !== day)
      : selectedDays.concat(day);
  } else if (chip.dataset.band) {
    const id = chip.dataset.band;
    selectedBands = selectedBands.includes(id)
      ? selectedBands.filter(entry => entry !== id)
      : selectedBands.concat(id);
  }
  render();
});

window.matchMedia("(max-width: 900px)").addEventListener("change", render);
render();
</script>
</body>
</html>
"""


def load_plan(path: Path) -> dict[str, Any]:
    """Read and validate the offer plan, failing with an actionable message."""
    if not path.exists():
        raise SystemExit(f"Offer plan not found: {path}")

    try:
        plan = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Offer plan is not valid JSON ({path}): {exc}") from exc

    for key in ("title", "subtitle", "cycles"):
        if not plan.get(key):
            raise SystemExit(f"Offer plan is missing '{key}': {path}")

    for cycle in plan["cycles"]:
        if not cycle.get("title"):
            raise SystemExit(f"Every cycle needs a 'title': {path}")

        days = [cell.get("day") for cell in cycle.get("cells", [])]
        missing = [day for day in DAY_ORDER if day not in days]
        if missing:
            raise SystemExit(
                f"Cycle '{cycle['title']}' is missing {', '.join(missing)}: {path}"
            )

        for cell in cycle["cells"]:
            absent = [key for key in REQUIRED_CELL_KEYS if cell.get(key) in (None, "")]
            if absent:
                raise SystemExit(
                    f"Cycle '{cycle['title']}' {cell.get('day', '?')} is missing "
                    f"{', '.join(absent)}: {path}"
                )
            if not isinstance(cell["lead_low"], (int, float)):
                raise SystemExit(
                    f"Cycle '{cycle['title']}' {cell['day']} has a non numeric "
                    f"'lead_low': {cell['lead_low']!r}"
                )
            if cell.get("follow_label") and not cell.get("follow_value"):
                raise SystemExit(
                    f"Cycle '{cycle['title']}' {cell['day']} has a 'follow_label' "
                    "without a 'follow_value'"
                )
            link = cell.get("link")
            if link and not str(link).startswith(("http://", "https://")):
                raise SystemExit(
                    f"Cycle '{cycle['title']}' {cell['day']} has a 'link' that is not "
                    f"an http(s) URL: {link!r}"
                )

    return plan


def build_html(plan: dict[str, Any], *, nav_home: str | None = None) -> str:
    # The nav only makes sense when the board sits beside the Pages index. A
    # standalone copy that gets emailed around must not show a broken tab.
    nav = (
        '<nav class="nav">'
        f'<a href="{nav_home}">Daily Summary</a>'
        '<a class="active" href="./">CRM</a>'
        "</nav>"
        if nav_home
        else ""
    )
    replacements = {
        "__NAV__": nav,
        "__TITLE__": plan["title"],
        "__SUBTITLE__": plan["subtitle"],
        "__DAY_ORDER__": json.dumps(DAY_ORDER),
        "__BANDS__": json.dumps(BANDS),
        "__CYCLES__": json.dumps(plan["cycles"], indent=2),
    }
    html = TEMPLATE
    for token, value in replacements.items():
        html = html.replace(token, value)
    return html


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--offers",
        type=Path,
        default=DEFAULT_OFFERS,
        help=f"Offer plan JSON (default: {DEFAULT_OFFERS.name} in data/)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Destination HTML (default: handoffs/{DEFAULT_OUTPUT.name})",
    )
    parser.add_argument(
        "--nav-home",
        default=None,
        help="Relative URL of the Pages index; adds the Daily Summary / CRM tabs",
    )
    args = parser.parse_args(argv)

    plan = load_plan(args.offers)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(build_html(plan, nav_home=args.nav_home), encoding="utf-8")

    days = sum(len(cycle["cells"]) for cycle in plan["cycles"])
    print(f"Wrote {args.output} ({len(plan['cycles'])} cycles, {days} offer days)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
