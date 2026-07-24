"use client";

import { use, useEffect, useState } from "react";
import {
  api,
  type CaseDetail,
  type ChronologyEntry,
  type DemandLetter,
  type Document,
  type Evidence,
  type Flag,
} from "@/lib/api";

export default function CaseDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id: caseId } = use(params);

  const [caseDetail, setCaseDetail] = useState<CaseDetail | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [chronology, setChronology] = useState<ChronologyEntry[]>([]);
  const [flags, setFlags] = useState<Flag[]>([]);
  const [evidence, setEvidence] = useState<Evidence[]>([]);
  const [demandLetters, setDemandLetters] = useState<DemandLetter[]>([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [uploading, setUploading] = useState(false);
  const [generatingChronology, setGeneratingChronology] = useState(false);
  const [generatingFlags, setGeneratingFlags] = useState(false);
  const [signingOff, setSigningOff] = useState(false);
  const [uploadingEvidence, setUploadingEvidence] = useState(false);
  const [confirmingEvidenceId, setConfirmingEvidenceId] = useState<string | null>(null);
  const [generatingLetter, setGeneratingLetter] = useState(false);

  const [editingEntryId, setEditingEntryId] = useState<string | null>(null);
  const [editSummary, setEditSummary] = useState("");
  const [editDate, setEditDate] = useState("");
  const [savingEdit, setSavingEdit] = useState(false);

  const [editingLetter, setEditingLetter] = useState(false);
  const [editLetterBody, setEditLetterBody] = useState("");
  const [savingLetterEdit, setSavingLetterEdit] = useState(false);

  useEffect(() => {
    Promise.all([
      api.getCase(caseId),
      api.listDocuments(caseId),
      api.listChronology(caseId),
      api.listFlags(caseId),
      api.listEvidence(caseId),
      api.listDemandLetters(caseId),
    ])
      .then(([detail, docs, entries, flagList, evidenceList, letters]) => {
        setCaseDetail(detail);
        setDocuments(docs);
        setChronology(entries);
        setFlags(flagList);
        setEvidence(evidenceList);
        setDemandLetters(letters);
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, [caseId]);

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      await api.uploadDocument(caseId, file);
      const docs = await api.listDocuments(caseId);
      setDocuments(docs);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  }

  async function handleUploadEvidence(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadingEvidence(true);
    setError(null);
    try {
      await api.uploadEvidence(caseId, file);
      const evidenceList = await api.listEvidence(caseId);
      setEvidence(evidenceList);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setUploadingEvidence(false);
      e.target.value = "";
    }
  }

  async function handleConfirmEvidence(evidenceId: string) {
    setConfirmingEvidenceId(evidenceId);
    setError(null);
    try {
      const updated = await api.confirmEvidence(caseId, evidenceId);
      setEvidence((prev) => prev.map((ev) => (ev.id === updated.id ? updated : ev)));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setConfirmingEvidenceId(null);
    }
  }

  async function handleGenerateChronology() {
    setGeneratingChronology(true);
    setError(null);
    try {
      const entries = await api.generateChronology(caseId);
      setChronology(entries);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setGeneratingChronology(false);
    }
  }

  async function handleGenerateFlags() {
    setGeneratingFlags(true);
    setError(null);
    try {
      const flagList = await api.generateFlags(caseId);
      setFlags(flagList);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setGeneratingFlags(false);
    }
  }

  async function handleSignOff() {
    setSigningOff(true);
    setError(null);
    try {
      const updated = await api.signOffCase(caseId);
      setCaseDetail(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSigningOff(false);
    }
  }

  function startEdit(entry: ChronologyEntry) {
    setEditingEntryId(entry.id);
    setEditSummary(entry.summary);
    setEditDate(entry.event_date);
  }

  function cancelEdit() {
    setEditingEntryId(null);
  }

  async function saveEdit(entry: ChronologyEntry) {
    const changes: { summary?: string; event_date?: string } = {};
    if (editSummary !== entry.summary) changes.summary = editSummary;
    if (editDate !== entry.event_date) changes.event_date = editDate;
    if (Object.keys(changes).length === 0) {
      setEditingEntryId(null);
      return;
    }
    setSavingEdit(true);
    setError(null);
    try {
      const updated = await api.updateChronologyEntry(caseId, entry.id, changes);
      setChronology((prev) => prev.map((e) => (e.id === updated.id ? updated : e)));
      setEditingEntryId(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSavingEdit(false);
    }
  }

  async function handleGenerateDemandLetter() {
    setGeneratingLetter(true);
    setError(null);
    try {
      await api.generateDemandLetter(caseId);
      const letters = await api.listDemandLetters(caseId);
      setDemandLetters(letters);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setGeneratingLetter(false);
    }
  }

  function startEditLetter(letter: DemandLetter) {
    setEditingLetter(true);
    setEditLetterBody(letter.body);
  }

  function cancelEditLetter() {
    setEditingLetter(false);
  }

  async function saveEditLetter(letter: DemandLetter) {
    if (editLetterBody === letter.body) {
      setEditingLetter(false);
      return;
    }
    setSavingLetterEdit(true);
    setError(null);
    try {
      await api.updateDemandLetter(caseId, letter.id, editLetterBody);
      const letters = await api.listDemandLetters(caseId);
      setDemandLetters(letters);
      setEditingLetter(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSavingLetterEdit(false);
    }
  }

  if (loading) {
    return (
      <main className="max-w-3xl mx-auto w-full px-6 py-12">
        <p className="text-[color:var(--muted)]">Loading case...</p>
      </main>
    );
  }

  if (!caseDetail) {
    return (
      <main className="max-w-3xl mx-auto w-full px-6 py-12">
        <p
          role="alert"
          className="rounded-[6px] border border-[color:var(--flag)]/40 bg-[color:var(--flag)]/5 px-4 py-2 text-[color:var(--flag)]"
        >
          {error ?? "Case not found."}
        </p>
      </main>
    );
  }

  return (
    <main className="flex flex-1 flex-col gap-10 max-w-3xl mx-auto w-full px-6 py-12">
      <header className="flex flex-col gap-1">
        <h1 className="font-[family-name:var(--font-display)] text-3xl font-semibold tracking-tight text-[color:var(--ink)]">
          {caseDetail.name}
        </h1>
        <p
          className={
            caseDetail.chronology_signed_off
              ? "font-[family-name:var(--font-mono)] text-sm text-[color:var(--verified)]"
              : "font-[family-name:var(--font-mono)] text-sm text-[color:var(--muted)]"
          }
        >
          {caseDetail.chronology_signed_off
            ? `Signed off at ${caseDetail.chronology_signed_off_at}`
            : "Draft — not signed off"}
        </p>
      </header>

      {error && (
        <p
          role="alert"
          className="rounded-[6px] border border-[color:var(--flag)]/40 bg-[color:var(--flag)]/5 px-4 py-2 text-[color:var(--flag)]"
        >
          {error}
        </p>
      )}

      <section>
        <p className="font-[family-name:var(--font-mono)] text-xs uppercase tracking-wide text-[color:var(--muted)] mb-1">
          Records
        </p>
        <h2 className="font-[family-name:var(--font-display)] text-lg font-semibold text-[color:var(--ink)] mb-3">
          Documents
        </h2>
        <label htmlFor="document-upload" className="block text-sm text-[color:var(--muted)] mb-1">
          Upload document
        </label>
        <input
          id="document-upload"
          type="file"
          onChange={handleUpload}
          disabled={uploading}
          className="mb-3 text-sm"
        />
        {uploading && (
          <p className="text-[color:var(--muted)] text-sm mb-2">Uploading...</p>
        )}
        {documents.length === 0 ? (
          <p className="text-[color:var(--muted)]">
            No documents yet — upload a record to begin.
          </p>
        ) : (
          <ul className="flex flex-col gap-2">
            {documents.map((doc) => (
              <li
                key={doc.id}
                className="rounded-[6px] border border-[color:var(--line)] bg-[color:var(--surface)] px-4 py-3 flex items-center justify-between gap-3"
              >
                <span className="text-[color:var(--ink)]">{doc.original_filename}</span>
                <span className="font-[family-name:var(--font-mono)] text-xs uppercase tracking-wide text-[color:var(--muted)] rounded-full border border-[color:var(--line)] px-2 py-0.5">
                  {doc.status}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section>
        <p className="font-[family-name:var(--font-mono)] text-xs uppercase tracking-wide text-[color:var(--muted)] mb-1">
          Records
        </p>
        <h2 className="font-[family-name:var(--font-display)] text-lg font-semibold text-[color:var(--ink)] mb-3">
          Evidence
        </h2>
        <p className="text-sm text-[color:var(--muted)] mb-2">
          Video and audio evidence must be confirmed by an attorney before it
          appears in the generated chronology — unconfirmed transcripts are
          ignored.
        </p>
        <label htmlFor="evidence-upload" className="block text-sm text-[color:var(--muted)] mb-1">
          Upload video or audio
        </label>
        <input
          id="evidence-upload"
          type="file"
          accept=".mp4,.mov,.avi,.mkv,.webm,.mp3,.wav,.m4a,.ogg,.flac"
          onChange={handleUploadEvidence}
          disabled={uploadingEvidence}
          className="mb-3 text-sm"
        />
        {uploadingEvidence && (
          <p className="text-[color:var(--muted)] text-sm mb-2">Uploading...</p>
        )}
        {evidence.length === 0 ? (
          <p className="text-[color:var(--muted)]">
            No evidence yet — upload audio or video to begin.
          </p>
        ) : (
          <ul className="flex flex-col gap-2">
            {evidence.map((ev) => (
              <li
                key={ev.id}
                className="rounded-[6px] border border-[color:var(--line)] bg-[color:var(--surface)] px-4 py-3 flex flex-wrap items-center justify-between gap-3"
              >
                <span className="text-[color:var(--ink)]">{ev.original_filename}</span>
                <span className="font-[family-name:var(--font-mono)] text-xs uppercase tracking-wide text-[color:var(--muted)]">
                  {ev.media_type}
                </span>
                <span className="font-[family-name:var(--font-mono)] text-xs uppercase tracking-wide text-[color:var(--muted)] rounded-full border border-[color:var(--line)] px-2 py-0.5">
                  {ev.status}
                </span>
                <button
                  type="button"
                  onClick={() => handleConfirmEvidence(ev.id)}
                  disabled={ev.confirmed_by_attorney || confirmingEvidenceId === ev.id}
                  className="rounded-[6px] bg-[color:var(--ink)] px-3 py-1 text-sm text-white disabled:bg-[color:var(--muted)] disabled:cursor-not-allowed"
                >
                  {ev.confirmed_by_attorney
                    ? "Confirmed"
                    : confirmingEvidenceId === ev.id
                      ? "Confirming..."
                      : "Confirm transcript"}
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section>
        <div className="flex items-center justify-between mb-3 gap-3 flex-wrap">
          <div>
            <p className="font-[family-name:var(--font-mono)] text-xs uppercase tracking-wide text-[color:var(--muted)] mb-1">
              Timeline
            </p>
            <h2 className="font-[family-name:var(--font-display)] text-lg font-semibold text-[color:var(--ink)]">
              Chronology
            </h2>
          </div>
          <button
            type="button"
            onClick={handleGenerateChronology}
            disabled={generatingChronology}
            className="rounded-[6px] bg-[color:var(--ink)] px-4 py-2 text-white disabled:bg-[color:var(--muted)] disabled:cursor-not-allowed"
          >
            {generatingChronology ? "Generating..." : "Generate chronology"}
          </button>
        </div>
        {chronology.length === 0 ? (
          <p className="text-[color:var(--muted)]">
            No chronology entries yet — generate one from uploaded records.
          </p>
        ) : (
          <ol className="relative flex flex-col gap-6 border-l border-[color:var(--line)] pl-6 sm:pl-8">
            {chronology.map((entry) => {
              const sourceColor = entry.source_document_id ? "var(--doc)" : "var(--evidence)";
              return (
                <li key={entry.id} className="relative">
                  <span
                    aria-hidden="true"
                    className="absolute -left-[calc(1.5rem+5px)] sm:-left-[calc(2rem+5px)] top-1.5 h-[9px] w-[9px] rounded-full ring-4 ring-[color:var(--paper)]"
                    style={{ backgroundColor: sourceColor }}
                  />
                  {editingEntryId === entry.id ? (
                    <div className="flex flex-col gap-2 rounded-[6px] border border-[color:var(--line)] bg-[color:var(--surface)] px-4 py-3">
                      <label htmlFor={`date-${entry.id}`} className="text-sm text-[color:var(--muted)]">
                        Event date
                      </label>
                      <input
                        id={`date-${entry.id}`}
                        type="text"
                        value={editDate}
                        onChange={(e) => setEditDate(e.target.value)}
                        className="rounded-[6px] border border-[color:var(--line)] px-3 py-1 font-[family-name:var(--font-mono)] text-sm"
                      />
                      <label htmlFor={`summary-${entry.id}`} className="text-sm text-[color:var(--muted)]">
                        Summary
                      </label>
                      <textarea
                        id={`summary-${entry.id}`}
                        value={editSummary}
                        onChange={(e) => setEditSummary(e.target.value)}
                        className="rounded-[6px] border border-[color:var(--line)] px-3 py-1"
                        rows={3}
                      />
                      <div className="flex gap-2">
                        <button
                          type="button"
                          onClick={() => saveEdit(entry)}
                          disabled={savingEdit}
                          className="rounded-[6px] bg-[color:var(--ink)] px-3 py-1 text-white disabled:bg-[color:var(--muted)] disabled:cursor-not-allowed"
                        >
                          {savingEdit ? "Saving..." : "Save"}
                        </button>
                        <button
                          type="button"
                          onClick={cancelEdit}
                          disabled={savingEdit}
                          className="rounded-[6px] border border-[color:var(--line)] px-3 py-1 disabled:opacity-50"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="flex flex-col gap-1.5 rounded-[6px] border border-[color:var(--line)] bg-[color:var(--surface)] px-4 py-3">
                      <div className="flex items-center justify-between gap-3 flex-wrap">
                        <span className="font-[family-name:var(--font-mono)] text-sm text-[color:var(--ink)]">
                          {entry.event_date}
                        </span>
                        <button
                          type="button"
                          onClick={() => startEdit(entry)}
                          className="text-sm underline text-[color:var(--muted)] hover:text-[color:var(--ink)]"
                        >
                          Edit
                        </button>
                      </div>
                      <p className="text-[color:var(--ink)]">{entry.summary}</p>
                      <p className="font-[family-name:var(--font-mono)] text-xs text-[color:var(--muted)]">
                        {entry.source_document_id
                          ? `doc ${entry.source_document_id}, page ${entry.source_location}`
                          : `evidence ${entry.source_evidence_id}, at ${entry.source_location}`}
                      </p>
                      {entry.edited_by_attorney ? (
                        <span className="w-fit rounded-full border border-[color:var(--verified)]/40 bg-[color:var(--verified)]/10 px-2 py-0.5 font-[family-name:var(--font-mono)] text-xs uppercase tracking-wide text-[color:var(--verified)]">
                          Attorney-verified
                        </span>
                      ) : (
                        <span className="w-fit rounded-full border border-[color:var(--line)] px-2 py-0.5 font-[family-name:var(--font-mono)] text-xs uppercase tracking-wide text-[color:var(--muted)]">
                          AI draft
                        </span>
                      )}
                    </div>
                  )}
                </li>
              );
            })}
          </ol>
        )}
      </section>

      <section>
        <div className="flex items-center justify-between mb-3 gap-3 flex-wrap">
          <div>
            <p className="font-[family-name:var(--font-mono)] text-xs uppercase tracking-wide text-[color:var(--muted)] mb-1">
              Review
            </p>
            <h2 className="font-[family-name:var(--font-display)] text-lg font-semibold text-[color:var(--ink)]">
              Flags
            </h2>
          </div>
          <button
            type="button"
            onClick={handleGenerateFlags}
            disabled={generatingFlags}
            className="rounded-[6px] bg-[color:var(--ink)] px-4 py-2 text-white disabled:bg-[color:var(--muted)] disabled:cursor-not-allowed"
          >
            {generatingFlags ? "Detecting..." : "Detect flags"}
          </button>
        </div>
        {flags.length === 0 ? (
          <p className="text-[color:var(--muted)]">No flags.</p>
        ) : (
          <ul className="flex flex-col gap-2">
            {flags.map((flag) => (
              <li
                key={flag.id}
                className="rounded-[6px] border border-[color:var(--flag)]/30 bg-[color:var(--flag)]/5 px-4 py-2 text-[color:var(--ink)]"
              >
                {flag.description}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section>
        <div className="flex items-center justify-between mb-3 gap-3 flex-wrap">
          <div>
            <p className="font-[family-name:var(--font-mono)] text-xs uppercase tracking-wide text-[color:var(--muted)] mb-1">
              Output
            </p>
            <h2 className="font-[family-name:var(--font-display)] text-lg font-semibold text-[color:var(--ink)]">
              Demand Letter
            </h2>
          </div>
          <button
            type="button"
            onClick={handleGenerateDemandLetter}
            disabled={generatingLetter}
            className="rounded-[6px] bg-[color:var(--ink)] px-4 py-2 text-white disabled:bg-[color:var(--muted)] disabled:cursor-not-allowed"
          >
            {generatingLetter ? "Generating..." : "Generate demand letter draft"}
          </button>
        </div>
        <p className="text-sm text-[color:var(--muted)] mb-2">
          This is a starting draft, not a finished letter — review, complete
          the bracketed placeholders, and edit before sending.
        </p>
        {demandLetters.length === 0 ? (
          <p className="text-[color:var(--muted)]">No demand letter drafted yet.</p>
        ) : (
          (() => {
            const letter = demandLetters[0];
            return (
              <div className="rounded-[6px] border border-[color:var(--line)] bg-[color:var(--surface)] px-4 py-3">
                {editingLetter ? (
                  <div className="flex flex-col gap-2">
                    <label htmlFor="letter-body" className="text-sm text-[color:var(--muted)]">
                      Draft body
                    </label>
                    <textarea
                      id="letter-body"
                      value={editLetterBody}
                      onChange={(e) => setEditLetterBody(e.target.value)}
                      className="rounded-[6px] border border-[color:var(--line)] px-3 py-1 font-[family-name:var(--font-mono)] text-sm"
                      rows={16}
                    />
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => saveEditLetter(letter)}
                        disabled={savingLetterEdit}
                        className="rounded-[6px] bg-[color:var(--ink)] px-3 py-1 text-white disabled:bg-[color:var(--muted)] disabled:cursor-not-allowed"
                      >
                        {savingLetterEdit ? "Saving..." : "Save"}
                      </button>
                      <button
                        type="button"
                        onClick={cancelEditLetter}
                        disabled={savingLetterEdit}
                        className="rounded-[6px] border border-[color:var(--line)] px-3 py-1 disabled:opacity-50"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="flex flex-col gap-2">
                    <div className="flex items-center justify-between gap-3 flex-wrap">
                      <span className="font-[family-name:var(--font-mono)] text-sm text-[color:var(--muted)]">
                        DRAFT · Version {letter.version}
                      </span>
                      <button
                        type="button"
                        onClick={() => startEditLetter(letter)}
                        className="text-sm underline text-[color:var(--muted)] hover:text-[color:var(--ink)]"
                      >
                        Edit
                      </button>
                    </div>
                    <p className="whitespace-pre-wrap text-[color:var(--ink)] text-sm">{letter.body}</p>
                    {letter.edited_by_attorney && (
                      <span className="w-fit rounded-full border border-[color:var(--verified)]/40 bg-[color:var(--verified)]/10 px-2 py-0.5 font-[family-name:var(--font-mono)] text-xs uppercase tracking-wide text-[color:var(--verified)]">
                        Attorney-verified
                      </span>
                    )}
                  </div>
                )}
              </div>
            );
          })()
        )}
      </section>

      <section>
        <button
          type="button"
          onClick={handleSignOff}
          disabled={signingOff || caseDetail.chronology_signed_off}
          className="rounded-[6px] bg-[color:var(--verified)] px-4 py-2 text-white disabled:bg-[color:var(--muted)] disabled:cursor-not-allowed"
        >
          {caseDetail.chronology_signed_off
            ? "Signed off"
            : signingOff
              ? "Signing off..."
              : "Sign off"}
        </button>
      </section>
    </main>
  );
}
