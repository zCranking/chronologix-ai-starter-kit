const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type CaseType = "personal_injury" | "workers_comp" | "med_malpractice";

export const CASE_TYPE_LABELS: Record<CaseType, string> = {
  personal_injury: "Personal Injury",
  workers_comp: "Workers' Comp",
  med_malpractice: "Medical Malpractice",
};

export type Case = {
  id: string;
  name: string;
  firm_id: string;
  case_type: CaseType;
};

export type CaseDetail = Case & {
  chronology_signed_off: boolean;
  chronology_signed_off_at: string | null;
};

export type Document = {
  id: string;
  case_id: string;
  status: "pending" | "processing" | "processed" | "failed";
  original_filename: string;
};

export type ChronologyEntry = {
  id: string;
  case_id: string;
  event_date: string;
  summary: string;
  source_document_id: string | null;
  source_evidence_id: string | null;
  source_location: string;
  version: number;
  edited_by_attorney: boolean;
};

export type Evidence = {
  id: string;
  case_id: string;
  status: "pending" | "processing" | "transcribed" | "failed";
  original_filename: string;
  media_type: string;
  confirmed_by_attorney: boolean;
};

export type Flag = {
  id: string;
  case_id: string;
  description: string;
  related_entry_ids: string[];
  resolved: boolean;
};

export type DemandLetter = {
  id: string;
  case_id: string;
  body: string;
  version: number;
  edited_by_attorney: boolean;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, init);
  if (!response.ok) {
    // Surface FastAPI's `detail` message (e.g. "sign off the chronology
    // first") so the attorney sees why, not just a bare status code. Falls
    // back to the status line if the body isn't the expected JSON shape.
    let detail = "";
    try {
      const body = await response.json();
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      // non-JSON error body; fall through to the status-only message
    }
    throw new Error(
      detail || `Request to ${path} failed with status ${response.status}`
    );
  }
  return response.json() as Promise<T>;
}

function json(method: string, body: unknown): RequestInit {
  return {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  };
}

export const api = {
  listCases: () => request<Case[]>("/cases"),

  createCase: (name: string, caseType: CaseType) =>
    request<Case>("/cases", json("POST", { name, case_type: caseType })),

  getCase: (caseId: string) => request<CaseDetail>(`/cases/${caseId}`),

  signOffCase: (caseId: string) =>
    request<CaseDetail>(`/cases/${caseId}/sign-off`, { method: "POST" }),

  listDocuments: (caseId: string) => request<Document[]>(`/cases/${caseId}/documents`),

  uploadDocument: (caseId: string, file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return request<Document>(`/cases/${caseId}/documents`, {
      method: "POST",
      body: formData,
    });
  },

  listChronology: (caseId: string) =>
    request<ChronologyEntry[]>(`/cases/${caseId}/chronology`),

  generateChronology: (caseId: string) =>
    request<ChronologyEntry[]>(`/cases/${caseId}/chronology`, { method: "POST" }),

  updateChronologyEntry: (
    caseId: string,
    entryId: string,
    changes: { summary?: string; event_date?: string }
  ) =>
    request<ChronologyEntry>(
      `/cases/${caseId}/chronology/${entryId}`,
      json("PATCH", changes)
    ),

  listFlags: (caseId: string) => request<Flag[]>(`/cases/${caseId}/flags`),

  generateFlags: (caseId: string) =>
    request<Flag[]>(`/cases/${caseId}/flags`, { method: "POST" }),

  listEvidence: (caseId: string) => request<Evidence[]>(`/cases/${caseId}/evidence`),

  uploadEvidence: (caseId: string, file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return request<Evidence>(`/cases/${caseId}/evidence`, {
      method: "POST",
      body: formData,
    });
  },

  confirmEvidence: (caseId: string, evidenceId: string) =>
    request<Evidence>(`/cases/${caseId}/evidence/${evidenceId}/confirm`, {
      method: "POST",
    }),

  listDemandLetters: (caseId: string) =>
    request<DemandLetter[]>(`/cases/${caseId}/demand-letters`),

  generateDemandLetter: (caseId: string) =>
    request<DemandLetter>(`/cases/${caseId}/demand-letter`, { method: "POST" }),

  updateDemandLetter: (caseId: string, letterId: string, body: string) =>
    request<DemandLetter>(
      `/cases/${caseId}/demand-letters/${letterId}`,
      json("PATCH", { body })
    ),
};
