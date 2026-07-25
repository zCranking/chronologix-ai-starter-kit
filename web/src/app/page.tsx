"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, CASE_TYPE_LABELS, type Case, type CaseType } from "@/lib/api";
import { CaseTypeBadge } from "@/components/CaseTypeBadge";

export default function Home() {
  const [cases, setCases] = useState<Case[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newCaseName, setNewCaseName] = useState("");
  const [newCaseType, setNewCaseType] = useState<CaseType>("personal_injury");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    api
      .listCases()
      .then(setCases)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  async function handleCreateCase(e: React.FormEvent) {
    e.preventDefault();
    if (!newCaseName.trim()) return;
    setCreating(true);
    setError(null);
    try {
      const created = await api.createCase(newCaseName.trim(), newCaseType);
      setCases((prev) => [...prev, created]);
      setNewCaseName("");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setCreating(false);
    }
  }

  return (
    <main className="flex flex-1 flex-col gap-10 max-w-3xl mx-auto w-full px-6 py-16">
      <header className="flex flex-col gap-3">
        <h1 className="font-[family-name:var(--font-display)] text-4xl font-semibold tracking-tight text-[color:var(--ink)]">
          Chronologix
        </h1>
        <p className="text-[color:var(--muted)] text-base">
          Turn a box of records into a verified, source-cited timeline.
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
        <h2 className="font-[family-name:var(--font-display)] text-lg font-semibold text-[color:var(--ink)] mb-3">
          New case
        </h2>
        <form onSubmit={handleCreateCase} className="flex flex-col sm:flex-row gap-2">
          <label htmlFor="case-name" className="sr-only">
            Case name
          </label>
          <input
            id="case-name"
            type="text"
            value={newCaseName}
            onChange={(e) => setNewCaseName(e.target.value)}
            placeholder="Case name"
            className="flex-1 rounded-[6px] border border-[color:var(--line)] bg-[color:var(--surface)] px-3 py-2 text-[color:var(--ink)] placeholder:text-[color:var(--muted)]"
          />
          <label htmlFor="case-type" className="sr-only">
            Case type
          </label>
          <select
            id="case-type"
            value={newCaseType}
            onChange={(e) => setNewCaseType(e.target.value as CaseType)}
            className="rounded-[6px] border border-[color:var(--line)] bg-[color:var(--surface)] px-3 py-2 text-[color:var(--ink)]"
          >
            {Object.entries(CASE_TYPE_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
          <button
            type="submit"
            disabled={creating}
            className="rounded-[6px] bg-[color:var(--ink)] px-4 py-2 text-white disabled:bg-[color:var(--muted)] disabled:cursor-not-allowed"
          >
            {creating ? "Creating..." : "Create case"}
          </button>
        </form>
      </section>

      <section>
        <h2 className="font-[family-name:var(--font-display)] text-lg font-semibold text-[color:var(--ink)] mb-3">
          All cases
        </h2>
        {loading ? (
          <p className="text-[color:var(--muted)]">Loading cases...</p>
        ) : cases.length === 0 ? (
          <p className="text-[color:var(--muted)]">
            No cases yet — create one above to begin.
          </p>
        ) : (
          <ul className="flex flex-col divide-y divide-[color:var(--line)] rounded-[6px] border border-[color:var(--line)] bg-[color:var(--surface)] overflow-hidden">
            {cases.map((c) => (
              <li key={c.id}>
                <Link
                  href={`/cases/${c.id}`}
                  className="flex items-center justify-between gap-3 px-4 py-3 hover:bg-[color:var(--paper)] transition-colors"
                >
                  <span className="font-[family-name:var(--font-display)] text-[color:var(--ink)]">
                    {c.name}
                  </span>
                  <CaseTypeBadge caseType={c.case_type} />
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
