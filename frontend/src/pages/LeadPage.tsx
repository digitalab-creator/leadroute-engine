import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { errorMessage, fetchLead, postDecision, postDraftFeedback, saveLeadDraft, type DraftCompose, type LeadDetail } from "../api";

export function LeadPage() {
  const { personId = "" } = useParams();
  const [lead, setLead] = useState<LeadDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [decidedAt, setDecidedAt] = useState("");
  const [saving, setSaving] = useState(false);
  const [note, setNote] = useState<string | null>(null);
  const [draftRating, setDraftRating] = useState<"up" | "down" | null>(null);
  const [ratingSaving, setRatingSaving] = useState(false);
  const [draftText, setDraftText] = useState("");
  const [compose, setCompose] = useState<DraftCompose>({
    to: null,
    subject: null,
    gmailUrl: null,
    zohoUrl: null,
  });
  const [draftDirty, setDraftDirty] = useState(false);
  const [draftSaving, setDraftSaving] = useState(false);
  const [feedbackComment, setFeedbackComment] = useState("");

  useEffect(() => {
    let active = true;
    setLead(null);
    setError(null);
    fetchLead(personId)
      .then((next) => {
        if (!active) {
          return;
        }
        setLead(next);
        setDecidedAt(next.nowIsrael);
        setDraftRating(next.draftFeedback.rating);
        setFeedbackComment(next.draftFeedback.comment ?? "");
        setDraftText(next.draft ?? "");
        setCompose(next.compose);
        setDraftDirty(false);
      })
      .catch((reason: unknown) => {
        if (active) {
          setError(errorMessage(reason));
        }
      });
    return () => {
      active = false;
    };
  }, [personId]);

  async function decide(decision: "accepted" | "rejected") {
    setSaving(true);
    setError(null);
    setNote("Saving your decision and writing the reply…");
    try {
      const saved = await postDecision(personId, decision, decidedAt);
      const next = await fetchLead(personId);
      setLead(next);
      setDraftText(next.draft ?? "");
      setCompose(next.compose);
      setDraftDirty(false);
      setNote(saved.note);
    } catch (reason: unknown) {
      setNote(null);
      setError(errorMessage(reason));
    } finally {
      setSaving(false);
    }
  }

  async function rateDraft(rating: "up" | "down") {
    if (!draftText.trim()) {
      return;
    }
    setRatingSaving(true);
    setError(null);
    try {
      await postDraftFeedback(personId, rating, feedbackComment);
      setDraftRating(rating);
      setNote(
        rating === "up"
          ? "Thanks — saved as helpful."
          : "Thanks — saved as not helpful.",
      );
    } catch (reason: unknown) {
      setError(errorMessage(reason));
    } finally {
      setRatingSaving(false);
    }
  }

  async function saveDraft() {
    if (!draftText.trim()) {
      setError("Draft is empty.");
      return;
    }
    setDraftSaving(true);
    setError(null);
    try {
      const saved = await saveLeadDraft(personId, draftText);
      setDraftText(saved.draft);
      setCompose(saved.compose);
      setDraftDirty(false);
      if (lead) {
        setLead({
          ...lead,
          draft: saved.draft,
          compose: saved.compose,
          draftState: saved.draftState,
          draftStateLabel: saved.draftStateLabel,
        });
      }
    } catch (reason: unknown) {
      setError(errorMessage(reason));
    } finally {
      setDraftSaving(false);
    }
  }

  if (error && !lead) {
    return (
      <main>
        <p className="error">{error}</p>
        <Link to="/">Back to the queue</Link>
      </main>
    );
  }
  if (!lead) {
    return <p>Loading this lead…</p>;
  }

  return (
    <main>
      <p>
        <Link to="/">Queue</Link>
      </p>
      <h1>{lead.name}</h1>
      <p className="muted">{lead.company}</p>
      <div className="row">
        <span className="score" data-band={lead.band}>
          {lead.score} {lead.band}
        </span>
        <span className="status" data-status={lead.status}>
          {lead.statusLabel}
        </span>
        <span>Owner: {lead.owner ?? "No owner"}</span>
      </div>
      <p className="muted">Analysis: {lead.analysisModeLabel}</p>
      {error ? <p className="error">{error}</p> : null}
      {note ? <p className="notice">{note}</p> : null}

      <section className="card">
        <h2>Sales decision</h2>
        <p>
          {lead.salesDecision
            ? `Current decision: ${lead.salesDecision.decisionLabel} on ${lead.salesDecision.decidedAtIsrael} (Israel time).`
            : "No sales decision yet."}
        </p>
        <div className="field">
          <label htmlFor="decided-at">Decision time (Israel)</label>
          <input
            id="decided-at"
            value={decidedAt}
            onChange={(event) => setDecidedAt(event.target.value)}
            placeholder="2026-10-05T09:40:00+03:00"
            autoComplete="off"
          />
        </div>
        <div className="actions">
          <button className="primary" type="button" disabled={saving} onClick={() => decide("accepted")}>
            {saving ? "Saving…" : "Accept"}
          </button>
          <button type="button" disabled={saving} onClick={() => decide("rejected")}>
            {saving ? "Saving…" : "Reject"}
          </button>
        </div>
      </section>

      <section className="card">
        <h2>Why this status</h2>
        <p>{lead.rationale}</p>
      </section>

      <section className="card">
        <h2>Five conditions</h2>
        {lead.conditions.map((condition) => (
          <p className="check" key={condition.key}>
            <strong className={condition.passed ? "pass" : "fail"}>
              {condition.passed ? "Pass" : "Fail"}
            </strong>{" "}
            {condition.label}. {condition.evidence}
          </p>
        ))}
      </section>

      <section className="card">
        <h2>Score breakdown</h2>
        <ul>
          {lead.factors.map((factor) => (
            <li key={factor.key}>
              {factor.label}: {factor.points}
            </li>
          ))}
        </ul>
      </section>

      {lead.messages.map((message) => (
        <section className="card" key={message.inboundId}>
          <h2>Message · {message.receivedAtIsrael}</h2>
          <p className="muted">
            {message.channelLabel}
            {message.source ? ` · ${message.source}` : " · source not recorded"}
            {message.analysisModeLabel ? ` · ${message.analysisModeLabel}` : ""}
            {message.analysisFailed ? " · analysis failed" : ""}
            {message.injection ? " · instruction flag" : ""}
          </p>
          {message.subject ? <p dir={message.direction}>{message.subject}</p> : null}
          <blockquote dir={message.direction} lang={message.direction === "rtl" ? "he" : undefined}>
            {message.body}
          </blockquote>
          {message.extraction ? (
            <>
              <p>
                Intent: {message.extraction.intentLabel}. Language: {message.extraction.languageLabel}.
              </p>
              {message.extraction.statedProblemLabel ? (
                <p>Problem: {message.extraction.statedProblemLabel}</p>
              ) : null}
              {message.extraction.statedProblemQuote ? (
                <blockquote dir={message.direction} lang={message.direction === "rtl" ? "he" : undefined}>
                  {message.extraction.statedProblemQuote}
                </blockquote>
              ) : null}
              {message.extraction.instructionOverrideAttempt ? (
                <p className="notice">The extraction flagged an instruction override.</p>
              ) : null}
            </>
          ) : (
            <p className="notice">No extraction was stored for this message.</p>
          )}
        </section>
      ))}

      <section className="card">
        <h2>Unsent draft</h2>
        {draftText ? (
          <>
            <label className="sr-only" htmlFor="draft-edit">
              Edit draft
            </label>
            <textarea
              id="draft-edit"
              className="draft-edit"
              dir={lead.draftDirection}
              lang={lead.draftDirection === "rtl" ? "he" : undefined}
              value={draftText}
              onChange={(event) => {
                setDraftText(event.target.value);
                setDraftDirty(true);
              }}
            />
            <div className="actions">
              <button
                type="button"
                className="primary"
                disabled={draftSaving || !draftDirty}
                onClick={() => saveDraft()}
              >
                {draftSaving ? "Saving…" : "Save draft"}
              </button>
            </div>
            {compose.gmailUrl || compose.zohoUrl ? (
              <div className="actions">
                {compose.gmailUrl ? (
                  <a
                    className={`button-link primary${draftDirty ? " disabled" : ""}`}
                    href={draftDirty ? undefined : compose.gmailUrl}
                    aria-disabled={draftDirty}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={(event) => {
                      if (draftDirty) {
                        event.preventDefault();
                        setError("Save the draft before opening Gmail.");
                      }
                    }}
                  >
                    Open in Gmail
                  </a>
                ) : null}
                {compose.zohoUrl ? (
                  <a
                    className={`button-link${draftDirty ? " disabled" : ""}`}
                    href={draftDirty ? undefined : compose.zohoUrl}
                    aria-disabled={draftDirty}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={(event) => {
                      if (draftDirty) {
                        event.preventDefault();
                        setError("Save the draft before opening Zoho Mail.");
                      }
                    }}
                  >
                    Open in Zoho Mail
                  </a>
                ) : null}
              </div>
            ) : null}
            <div className="field">
              <label htmlFor="draft-feedback-note">Optional note for weekly learning</label>
              <textarea
                id="draft-feedback-note"
                className="feedback-note"
                rows={2}
                value={feedbackComment}
                onChange={(event) => setFeedbackComment(event.target.value)}
                placeholder="What worked or what felt wrong? Any language is fine."
              />
            </div>
            <div className="actions thumb-row">
              <button
                type="button"
                className={draftRating === "up" ? "primary" : ""}
                disabled={ratingSaving}
                aria-pressed={draftRating === "up"}
                onClick={() => rateDraft("up")}
              >
                Helpful draft
              </button>
              <button
                type="button"
                className={draftRating === "down" ? "primary" : ""}
                disabled={ratingSaving}
                aria-pressed={draftRating === "down"}
                onClick={() => rateDraft("down")}
              >
                Not helpful
              </button>
            </div>
          </>
        ) : (
          <p>No draft text.</p>
        )}
        <p className="muted">{lead.draftStateLabel}. Nothing is sent.</p>
        {draftDirty ? <p className="notice">Unsaved changes — save before mail compose.</p> : null}
      </section>
    </main>
  );
}
