import { useEffect, useMemo, useState } from "react";

function wowClass(value) {
  const v = String(value || "").trim();
  const m = v.match(/\(([+-]?\d+(?:\.\d+)?)%\)/);
  const n = m ? Number(m[1]) : NaN;
  const up = (!Number.isNaN(n) && n > 0) || (v.startsWith("+") && !v.startsWith("+$0"));
  const down = (!Number.isNaN(n) && n < 0) || v.startsWith("-") || v.startsWith("$-");
  if (up) return "up";
  if (down) return "down";
  return "flat";
}

const URGENCY_RANK = { Today: 0, "48h": 1, Watch: 2, None: 3 };

export default function App() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [agent, setAgent] = useState("all");
  const [sortBy, setSortBy] = useState("urgency");
  const [selectedAid, setSelectedAid] = useState(null);

  useEffect(() => {
    fetch("/latest_daily.json")
      .then((r) => {
        if (!r.ok) throw new Error(`Failed to load payload (${r.status})`);
        return r.json();
      })
      .then((payload) => {
        setData(payload);
        const first = payload.players?.[0];
        if (first) setSelectedAid(String(first.aid));
      })
      .catch((e) => setError(String(e.message || e)));
  }, []);

  const report = data?.report || {};
  const segments = data?.segments || report.segments || [];
  const players = data?.players || [];
  const day = report.weekday || "";
  const dayShort = data?.dayShort || day.slice(0, 3);
  const titles = data?.titles || {};
  const agents = data?.agents || [];

  const byLabel = Object.fromEntries(segments.map((s) => [s.label, s]));
  const elite = byLabel.Elite || {};
  const jack = byLabel.Jackpota || {};

  const filtered = useMemo(() => {
    let rows = [...players];
    const q = search.trim().toLowerCase();
    if (q) {
      rows = rows.filter((p) =>
        [p.name, p.aid, p.agent, p.agentName, p.reason, p.reasonTable, p.recommendation]
          .join(" ")
          .toLowerCase()
          .includes(q)
      );
    }
    if (agent !== "all") rows = rows.filter((p) => p.agent === agent);
    rows.sort((a, b) => {
      if (sortBy === "prior") return (b.priorPriorNum || 0) - (a.priorPriorNum || 0);
      if (sortBy === "lifetime") return (b.lifetimePurchasedNum || 0) - (a.lifetimePurchasedNum || 0);
      if (sortBy === "gap") return (b.sortGap || 0) - (a.sortGap || 0);
      const ra = URGENCY_RANK[a.urgency] ?? 9;
      const rb = URGENCY_RANK[b.urgency] ?? 9;
      if (ra !== rb) return ra - rb;
      return (b.sortGap || 0) - (a.sortGap || 0);
    });
    return rows;
  }, [players, search, agent, sortBy]);

  const selected = filtered.find((p) => String(p.aid) === String(selectedAid)) || filtered[0];

  if (error) {
    return (
      <div className="app">
        <h1>Elite Daily Summary</h1>
        <p className="headline">Could not load React demo payload: {error}</p>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="app">
        <p className="muted">Loading latest daily payload…</p>
      </div>
    );
  }

  return (
    <div className="app">
      <header className="hero">
        <div>
          <h1>Elite Daily Summary</h1>
          <div className="sub">
            {day} {report.date} · vs prior {report.priorDate} · React demo
          </div>
        </div>
        <div className="badge">Payload from canvas · no BigQuery in the browser</div>
      </header>

      <section className="metrics">
        <div className="metric">
          <div className="label">Elite purchase</div>
          <div className="value">{elite.revThis || "—"}</div>
          <div className={`delta ${wowClass(elite.revWow)}`}>{elite.revWow || "—"}</div>
        </div>
        <div className="metric">
          <div className="label">Elite purchased players</div>
          <div className="value">{elite.plyThis || "—"}</div>
          <div className={`delta ${wowClass(elite.plyWow)}`}>{elite.plyWow || "—"}</div>
        </div>
        <div className="metric">
          <div className="label">Jackpota purchase</div>
          <div className="value">{jack.revThis || "—"}</div>
          <div className={`delta ${wowClass(jack.revWow)}`}>{jack.revWow || "—"}</div>
        </div>
        <div className="metric">
          <div className="label">Elite share</div>
          <div className="value" style={{ fontSize: 18 }}>{elite.share || "—"}</div>
          <div className="delta flat">of Jackpota</div>
        </div>
      </section>

      <section className="panel">
        <h2>{day} vs last {day} · Elite & Jackpota</h2>
        {report.headline ? <p className="headline">{report.headline}</p> : null}
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Segment</th>
                <th className="num">This {dayShort} Purchase</th>
                <th className="num">Prior {dayShort} Purchase</th>
                <th className="num">Purchase WoW</th>
                <th className="num">This {dayShort} Purchased Players</th>
                <th className="num">Prior {dayShort} Purchased Players</th>
                <th className="num">Purchased Players WoW</th>
                <th>Share</th>
              </tr>
            </thead>
            <tbody>
              {segments.map((s) => (
                <tr key={s.label}>
                  <td>{s.label}</td>
                  <td className="num">{s.revThis}</td>
                  <td className="num">{s.revPrior}</td>
                  <td className={`num delta ${wowClass(s.revWow)}`}>{s.revWow}</td>
                  <td className="num">{s.plyThis}</td>
                  <td className="num">{s.plyPrior}</td>
                  <td className={`num delta ${wowClass(s.plyWow)}`}>{s.plyWow}</td>
                  <td>{s.share || ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel">
        <h2>Top 20 Same Day Comparison</h2>
        {data.urgencyLegend ? <p className="muted" style={{ marginTop: -4, marginBottom: 10 }}>{data.urgencyLegend}</p> : null}
        <div className="toolbar">
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search name, AID, agent, reason…"
          />
          <select value={agent} onChange={(e) => setAgent(e.target.value)}>
            <option value="all">All agents</option>
            {agents.map((a) => (
              <option key={a} value={a}>{a}</option>
            ))}
          </select>
          <select value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
            <option value="urgency">Sort: Urgency + gap</option>
            <option value="prior">Prior purchase ↓</option>
            <option value="lifetime">Lifetime purchase ↓</option>
            <option value="gap">WoW gap ↓</option>
          </select>
        </div>
        <p className="muted">Showing {filtered.length} of {players.length}</p>
        <div className="table-wrap" style={{ maxHeight: 360 }}>
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>AID</th>
                <th>Name</th>
                <th>Agent</th>
                <th className="num">{titles.lifetimePurchase || "LT Purchase"}</th>
                <th className="num">{titles.thisPurchase || `This ${day}`}</th>
                <th className="num">{titles.priorPurchase || `Prior ${day}`}</th>
                <th>Urgency</th>
                <th>Reason</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((p, i) => (
                <tr
                  key={p.aid}
                  className={String(selected?.aid) === String(p.aid) ? "active" : ""}
                  onClick={() => setSelectedAid(String(p.aid))}
                  style={{ cursor: "pointer" }}
                >
                  <td>{i + 1}</td>
                  <td>
                    {p.aidUrl ? <a href={p.aidUrl} target="_blank" rel="noreferrer" onClick={(e) => e.stopPropagation()}>{p.aid}</a> : p.aid}
                  </td>
                  <td>{p.name}</td>
                  <td>{p.agentName || p.agent}</td>
                  <td className="num">{p.lifetimePurchase}</td>
                  <td className="num">{p.thisDay}</td>
                  <td className="num">{p.priorDay}</td>
                  <td>
                    <span className={`pill ${p.urgency === "Today" ? "today" : p.urgency === "Watch" ? "watch" : ""}`}>
                      {p.urgency}
                    </span>
                  </td>
                  <td style={{ maxWidth: 280 }}>{p.reason || p.reasonTable}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {selected ? (
        <section className="panel">
          <h2>Player detail · {selected.name}</h2>
          <div className="detail">
            <div>
              <h3>Snapshot</h3>
              <div className="box">
                <div><strong>AID:</strong> {selected.aidUrl ? <a href={selected.aidUrl} target="_blank" rel="noreferrer">{selected.aid}</a> : selected.aid}</div>
                <div><strong>Agent:</strong> {selected.agentName || selected.agent}</div>
                <div><strong>Urgency:</strong> {selected.urgency}</div>
                <div><strong>This / Prior:</strong> {selected.thisDay} · {selected.priorDay}</div>
                <div><strong>7D:</strong> {selected.purchase7d}</div>
              </div>
            </div>
            <div>
              <h3>Reason</h3>
              <div className="box">{selected.reasonTable || selected.reason || "—"}</div>
              <h3 style={{ marginTop: 12 }}>Recommendation</h3>
              <div className="box">{selected.recommendation || "—"}</div>
            </div>
          </div>
        </section>
      ) : null}
    </div>
  );
}
