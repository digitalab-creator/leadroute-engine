import { useEffect, useState } from "react";
import { BriefProse } from "../BriefProse";
import {
  errorMessage,
  fetchVisibility,
  postVisibilityFeedback,
  type Visibility,
} from "../api";

function yesNo(value: boolean): string {
  return value ? "yes" : "no";
}

function briefSnapshotForFeedback(brief: Visibility["brief"]): Record<string, unknown> {
  return {
    mode: brief.mode,
    label: brief.label,
    blocked: brief.blocked,
    block_reasons: brief.blockReasons,
    prompt_id: brief.promptId,
    title: brief.title,
    direct_answer: brief.directAnswer,
    direct_answer_words: brief.directAnswerWords,
    sections: brief.sections.map((section) => ({
      heading: section.heading,
      body: section.body,
    })),
    faq: brief.faq.map((item) => ({
      question: item.question,
      answer: item.answer,
    })),
    schema_org_type: brief.schemaOrgType,
    removed_sentences: brief.removedSentences,
  };
}

function SummaryItem({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="bi-summary-item">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

export function VisibilityPage() {
  const [snapshot, setSnapshot] = useState<Visibility | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [briefRating, setBriefRating] = useState<"up" | "down" | null>(null);
  const [feedbackComment, setFeedbackComment] = useState("");
  const [ratingSaving, setRatingSaving] = useState(false);
  const [note, setNote] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setSnapshot(null);
    setError(null);
    fetchVisibility()
      .then((next) => {
        if (!active) {
          return;
        }
        setSnapshot(next);
        setBriefRating(next.brief.feedbackRating);
        setFeedbackComment(next.brief.feedbackComment ?? "");
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

  async function rateBrief(rating: "up" | "down") {
    if (!snapshot) {
      return;
    }
    setRatingSaving(true);
    setError(null);
    try {
      await postVisibilityFeedback({
        promptId: snapshot.brief.promptId,
        briefFingerprint: snapshot.brief.briefFingerprint,
        briefSnapshot: briefSnapshotForFeedback(snapshot.brief),
        rating,
        comment: feedbackComment,
      });
      setBriefRating(rating);
      setNote(rating === "up" ? "Saved as helpful." : "Saved as not helpful.");
    } catch (reason: unknown) {
      setError(errorMessage(reason));
    } finally {
      setRatingSaving(false);
    }
  }

  if (error && !snapshot) {
    return <p className="error">{error}</p>;
  }
  if (!snapshot) {
    return <p>Loading AI visibility…</p>;
  }

  const brief = snapshot.brief;
  const o = snapshot.overview;
  return (
    <main className="bi-dashboard">
      <header className="bi-header">
        <h1>AI visibility</h1>
        <p className="bi-period muted">Top prompt: {o.topPrompt}</p>
      </header>
      <section className="bi-summary-strip" aria-label="Week at a glance">
        <SummaryItem label="Prompts" value={o.promptCount} />
        <SummaryItem label="Engines" value={o.engineCount} />
        <SummaryItem label="Top gap" value={o.topGapScore} />
        <SummaryItem label="Mention rate" value={`${o.mentionRatePct}%`} />
        <SummaryItem label="stargo.co cites" value={`${o.ownedCiteRatePct}%`} />
        <SummaryItem label="Stargo misses" value={o.stargoMissTotal} />
        <SummaryItem label="Competitor gaps" value={o.competitorGapTotal} />
        <SummaryItem label="Wrong claims" value={o.wrongClaimTotal} />
      </section>
      {error ? <p className="error">{error}</p> : null}
      {note ? <p className="notice">{note}</p> : null}
      {snapshot.gaps.map((gap) => (
        <article className="card" key={gap.promptId}>
          <div className="row">
            <strong>Score {gap.score}</strong>
            <span className="muted">P{gap.priority}</span>
          </div>
          <h2>{gap.prompt}</h2>
          <p className="muted">{gap.cluster}</p>
          <ul className="bi-engine-list">
            {gap.engines.map((engine) => (
              <li key={engine.engine}>
                <strong>{engine.engine}</strong> · Stargo {yesNo(engine.mentioned)} · Owned cite{" "}
                {yesNo(engine.citedOwned)}
                {engine.wrongClaim ? " · wrong claim" : ""}
              </li>
            ))}
          </ul>
        </article>
      ))}

      <article className={brief.blocked ? "card blocked" : "card"}>
        <h2>Brief for the top gap</h2>
        {brief.label ? (
          <p className={brief.blocked ? "error" : "notice"}>{brief.label}</p>
        ) : null}
        {brief.blocked
          ? brief.blockReasons.map((reason) => (
              <p key={reason} className="error">
                Blocked: {reason}
              </p>
            ))
          : null}
        <p className="muted cite-legend">
          Tags like BC-1 or PP-1 are approved claim ids from brand context — not errors.
        </p>
        <h3>{brief.title}</h3>
        {brief.directAnswer ? (
          <p>
            <BriefProse text={brief.directAnswer} />
          </p>
        ) : (
          <p>No direct answer remains.</p>
        )}
        {brief.sections.map((section) => (
          <section key={section.heading}>
            <h3>{section.heading}</h3>
            <p>
              <BriefProse text={section.body} />
            </p>
          </section>
        ))}
        {brief.faq.length ? <h3>FAQ</h3> : null}
        {brief.faq.map((item) => (
          <section key={item.question}>
            <h3>{item.question}</h3>
            <p>
              <BriefProse text={item.answer} />
            </p>
          </section>
        ))}
        {!brief.blocked ? (
          <>
            <div className="field">
              <label htmlFor="brief-feedback-note">Optional note for weekly learning</label>
              <textarea
                id="brief-feedback-note"
                className="feedback-note"
                rows={2}
                value={feedbackComment}
                onChange={(event) => setFeedbackComment(event.target.value)}
                placeholder="What should change in the next brief?"
              />
            </div>
            <div className="actions thumb-row">
              <button
                type="button"
                className={briefRating === "up" ? "primary" : ""}
                disabled={ratingSaving}
                aria-pressed={briefRating === "up"}
                onClick={() => rateBrief("up")}
              >
                Helpful brief
              </button>
              <button
                type="button"
                className={briefRating === "down" ? "primary" : ""}
                disabled={ratingSaving}
                aria-pressed={briefRating === "down"}
                onClick={() => rateBrief("down")}
              >
                Not helpful
              </button>
            </div>
          </>
        ) : null}
      </article>
    </main>
  );
}
