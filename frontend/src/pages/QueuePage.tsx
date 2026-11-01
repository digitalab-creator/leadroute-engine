import { useEffect, useRef, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import {
  errorMessage,
  fetchLeads,
  fetchOptions,
  postInbound,
  type LeadCard,
  type Options,
} from "../api";

const EMPTY_FORM = {
  fromName: "",
  fromEmail: "",
  linkedinUrl: "",
  channel: "",
  text: "",
  receivedAt: "",
  source: "",
};

export function QueuePage() {
  const [leads, setLeads] = useState<LeadCard[] | null>(null);
  const [options, setOptions] = useState<Options | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [pasteError, setPasteError] = useState<string | null>(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [pasteNote, setPasteNote] = useState<string | null>(null);
  const [pasteOpen, setPasteOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);
  const pasteDialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    let active = true;
    Promise.all([fetchLeads(), fetchOptions()])
      .then(([nextLeads, nextOptions]) => {
        if (!active) {
          return;
        }
        setLeads(nextLeads);
        setOptions(nextOptions);
      })
      .catch((reason: unknown) => {
        if (active) {
          setLoadError(errorMessage(reason));
        }
      });
    return () => {
      active = false;
    };
  }, [reloadKey]);

  useEffect(() => {
    const dialog = pasteDialogRef.current;
    if (!dialog) {
      return;
    }
    if (pasteOpen) {
      if (!dialog.open) {
        dialog.showModal();
      }
      return;
    }
    if (dialog.open) {
      dialog.close();
    }
  }, [pasteOpen]);

  function openPasteModal() {
    setPasteError(null);
    setPasteOpen(true);
  }

  function closePasteModal() {
    setPasteOpen(false);
  }

  async function onPaste(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setPasteError(null);
    try {
      const saved = await postInbound(form);
      setPasteNote(`${saved.statusLabel} — open the new row to read the evidence.`);
      setReloadKey((value) => value + 1);
      setForm(EMPTY_FORM);
      closePasteModal();
    } catch (reason: unknown) {
      setPasteError(errorMessage(reason));
    } finally {
      setSaving(false);
    }
  }

  return (
    <main>
      <h1>Lead queue</h1>
      <p className="muted">Highest score first. Times are Asia/Jerusalem.</p>
      <div className="queue-toolbar">
        <button
          className="primary"
          type="button"
          disabled={!options}
          onClick={openPasteModal}
        >
          Add a message
        </button>
      </div>
      {loadError ? <p className="error">{loadError}</p> : null}
      {pasteNote ? <p className="notice">{pasteNote}</p> : null}
      {leads === null && !loadError ? <p>Loading the queue…</p> : null}
      {leads?.length === 0 ? <p>No inbound leads yet.</p> : null}
      {leads?.map((lead) => (
        <Link className="card" key={lead.personId} to={`/leads/${lead.personId}`}>
          <div className="row">
            <strong>{lead.name}</strong>
            <span className="score" data-band={lead.band}>
              {lead.score} {lead.band}
            </span>
            <span className="status" data-status={lead.status}>
              {lead.statusLabel}
            </span>
          </div>
          <p className="muted">
            {lead.company} · {lead.channelLabel} · {lead.receivedAtIsrael}
          </p>
          <p className="muted">Owner: {lead.owner ?? "No owner"}</p>
        </Link>
      ))}

      <dialog
        ref={pasteDialogRef}
        className="paste-modal"
        onCancel={(event) => {
          event.preventDefault();
          closePasteModal();
        }}
        onClose={() => setPasteOpen(false)}
      >
        <form className="paste-modal__panel" onSubmit={onPaste}>
          <div className="paste-modal__header">
            <div>
              <h2>Paste a message</h2>
              <p className="muted">
                It runs through the same gate as the seed file. A hidden instruction becomes needs
                review.
              </p>
            </div>
            <button
              className="paste-modal__close"
              type="button"
              aria-label="Close"
              onClick={closePasteModal}
            >
              ×
            </button>
          </div>
          {pasteError ? <p className="error">{pasteError}</p> : null}
          <div className="field">
            <label htmlFor="from-name">Name</label>
            <input
              id="from-name"
              value={form.fromName}
              onChange={(event) => setForm({ ...form, fromName: event.target.value })}
            />
          </div>
          <div className="field">
            <label htmlFor="from-email">Email</label>
            <input
              id="from-email"
              value={form.fromEmail}
              onChange={(event) => setForm({ ...form, fromEmail: event.target.value })}
            />
          </div>
          <div className="field">
            <label htmlFor="linkedin">LinkedIn URL</label>
            <input
              id="linkedin"
              value={form.linkedinUrl}
              onChange={(event) => setForm({ ...form, linkedinUrl: event.target.value })}
            />
          </div>
          <div className="field">
            <label htmlFor="channel">Channel</label>
            <select
              id="channel"
              required
              value={form.channel}
              onChange={(event) => setForm({ ...form, channel: event.target.value })}
            >
              <option value="">Choose a channel</option>
              {options?.channels.map((channel) => (
                <option key={channel} value={channel}>
                  {channel}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="source">Source (optional)</label>
            <select
              id="source"
              value={form.source}
              onChange={(event) => setForm({ ...form, source: event.target.value })}
            >
              <option value="">Not recorded</option>
              {options?.sources.map((source) => (
                <option key={source} value={source}>
                  {source}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="received">Received at (optional, with a timezone)</label>
            <input
              id="received"
              placeholder="2026-10-06T10:00:00+03:00"
              value={form.receivedAt}
              onChange={(event) => setForm({ ...form, receivedAt: event.target.value })}
            />
          </div>
          <div className="field">
            <label htmlFor="text">Message</label>
            <textarea
              id="text"
              required
              value={form.text}
              onChange={(event) => setForm({ ...form, text: event.target.value })}
            />
          </div>
          <div className="actions">
            <button type="button" onClick={closePasteModal} disabled={saving}>
              Cancel
            </button>
            <button className="primary" type="submit" disabled={saving || !options}>
              {saving ? "Saving…" : "Add to the queue"}
            </button>
          </div>
        </form>
      </dialog>
    </main>
  );
}
