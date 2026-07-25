import { CASE_TYPE_LABELS, type CaseType } from "@/lib/api";

const CASE_TYPE_STYLES: Record<CaseType, string> = {
  personal_injury:
    "border-[color:var(--case-personal-injury)]/40 bg-[color:var(--case-personal-injury)]/10 text-[color:var(--case-personal-injury)]",
  workers_comp:
    "border-[color:var(--case-workers-comp)]/40 bg-[color:var(--case-workers-comp)]/10 text-[color:var(--case-workers-comp)]",
  med_malpractice:
    "border-[color:var(--case-med-malpractice)]/40 bg-[color:var(--case-med-malpractice)]/10 text-[color:var(--case-med-malpractice)]",
};

export function CaseTypeBadge({ caseType }: { caseType: CaseType }) {
  return (
    <span
      className={`w-fit rounded-full border px-2 py-0.5 font-[family-name:var(--font-mono)] text-xs uppercase tracking-wide ${CASE_TYPE_STYLES[caseType]}`}
    >
      {CASE_TYPE_LABELS[caseType]}
    </span>
  );
}
