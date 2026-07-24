"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, type Case } from "@/lib/api";

export default function Home() {
  const [cases, setCases] = useState<Case[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newCaseName, setNewCaseName] = useState("");
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
      const created = await api.createCase(newCaseName.trim());
      setCases((prev) => [...prev, created]);
      setNewCaseName("");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setCreating(false);
    }
  }

  return (
    <main className="flex flex-1 flex-col gap-8 max-w-3xl mx-auto w-full px-6 py-12">
      <h1 className="text-2xl font-semibold text-zinc-900">Cases</h1>

      {error && (
        <p role="alert" className="rounded border border-red-300 bg-red-50 px-4 py-2 text-red-800">
          {error}
        </p>
      )}

      <section>
        <h2 className="text-lg font-medium text-zinc-900 mb-2">New case</h2>
        <form onSubmit={handleCreateCase} className="flex gap-2">
          <label htmlFor="case-name" className="sr-only">
            Case name
          </label>
          <input
            id="case-name"
            type="text"
            value={newCaseName}
            onChange={(e) => setNewCaseName(e.target.value)}
            placeholder="Case name"
            className="flex-1 rounded border border-zinc-300 px-3 py-2"
          />
          <button
            type="submit"
            disabled={creating}
            className="rounded bg-zinc-900 px-4 py-2 text-white disabled:bg-zinc-400 disabled:cursor-not-allowed"
          >
            {creating ? "Creating..." : "Create case"}
          </button>
        </form>
      </section>

      <section>
        <h2 className="text-lg font-medium text-zinc-900 mb-2">All cases</h2>
        {loading ? (
          <p className="text-zinc-600">Loading cases...</p>
        ) : cases.length === 0 ? (
          <p className="text-zinc-600">No cases yet.</p>
        ) : (
          <ul className="flex flex-col gap-2">
            {cases.map((c) => (
              <li key={c.id} className="rounded border border-zinc-200 px-4 py-2">
                <Link href={`/cases/${c.id}`} className="text-zinc-900 underline">
                  {c.name}
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
