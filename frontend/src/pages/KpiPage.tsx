import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { errorMessage, fetchKpi, type CountLine, type KpiPack } from "../api";

function progressPct(line: CountLine): number | null {
  if (line.unknown || line.actual === null || line.target === null || line.target <= 0) {
    return null;
  }
  return Math.min(100, Math.round((line.actual / line.target) * 100));
}

function BiTile({ title, line }: { title: string; line: CountLine }) {
  const pct = progressPct(line);
  const showTarget = line.target !== null && line.target > 0;
  let actualDisplay: string;
  if (line.unknown || line.actual === null) {
    actualDisplay = "Feed not received";
  } else {
    actualDisplay = String(line.actual);
  }
  return (
    <article className="bi-tile">
      <p className="bi-tile-label">{title}</p>
      <p className="bi-tile-value">
        {actualDisplay}
        {showTarget ? (
          <span className="bi-tile-target"> / {line.target}</span>
        ) : null}
      </p>
      {pct !== null ? (
        <div className="bi-bar" aria-hidden="true">
          <div className="bi-bar-fill" style={{ width: `${pct}%` }} />
        </div>
      ) : null}
      {line.unknown ? (
        <p className="bi-tile-meta muted">
          This source feed did not arrive for the week, so the count is not zero.
        </p>
      ) : null}
      {line.records.length > 0 ? (
        <ul className="bi-records">
          {line.records.slice(0, 6).map((record) => (
            <li key={record.id}>
              {record.personId ? (
                <Link to={`/leads/${record.personId}`}>{record.label}</Link>
              ) : (
                record.label
              )}
            </li>
          ))}
        </ul>
      ) : null}
    </article>
  );
}

export function KpiPage() {
  const [pack, setPack] = useState<KpiPack | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    fetchKpi()
      .then((next) => {
        if (active) {
          setPack(next);
        }
      })
      .catch((reason: unknown) => {
        if (active) {
          setError(errorMessage(reason));
        }
      });
    return () => {
      active = false;
    };
  }, []);

  if (error) {
    return <p className="error">{error}</p>;
  }
  if (!pack) {
    return <p>Loading the week pack…</p>;
  }

  return (
    <main className="bi-dashboard">
      <header className="bi-header">
        <h1>KPI pack</h1>
        <p className="bi-period">
          {pack.weekStart} → {pack.weekEnd}
        </p>
      </header>
      <section className="bi-grid">
        <BiTile title="Qualified leads" line={pack.qls} />
        <BiTile title="Meetings booked" line={pack.meetingsBooked} />
        <BiTile title="Meetings held" line={pack.meetingsHeld} />
        <BiTile title="Opportunities" line={pack.opportunities} />
      </section>
      <h2 className="bi-section-title">By first-touch source</h2>
      <section className="bi-grid bi-grid--source">
        {pack.bySource.map((row) => (
          <BiTile key={row.source} title={row.source} line={row.line} />
        ))}
      </section>
      <h2 className="bi-section-title">Expansion</h2>
      <section className="bi-grid">
        <BiTile title="Expansion meetings booked" line={pack.expansionMeetingsBooked} />
        <BiTile title="Expansion meetings held" line={pack.expansionMeetingsHeld} />
        <BiTile title="Expansion opportunities" line={pack.expansionOpportunities} />
      </section>
    </main>
  );
}
