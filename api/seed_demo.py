"""Seed a rich, synthetic demo case so the app shows a complete workflow
(documents -> chronology -> demand letter) instead of an empty screen.

Run with the API server up:  python seed_demo.py
All data is SYNTHETIC (fictional parties, no real PHI) -- safe to show.
Re-running creates another demo case; it does not delete prior ones.
"""

import io
import time

import fitz  # pymupdf
import httpx

API = "http://localhost:8000"

_MEDICAL_RECORD = """MEMORIAL ORTHOPEDIC ASSOCIATES - MEDICAL RECORD (DEMO / SYNTHETIC)
Patient: Maria Rivera        Provider: Dr. Ellen Park, MD

Visit - March 2, 2024
Ms. Rivera presented to the emergency department on March 2, 2024 after a
rear-end motor vehicle collision. She reported neck pain and headache. CT of
the head was negative. She was diagnosed with cervical strain (whiplash),
prescribed cyclobenzaprine, and referred to physical therapy.

Visit - March 18, 2024
Follow-up on March 18, 2024. Ms. Rivera reported persistent neck pain rated
7 out of 10 and difficulty sleeping. Physical therapy was authorized and
begun. Cyclobenzaprine continued.

Visit - May 6, 2024
Seen May 6, 2024 after twelve physical therapy sessions. Neck pain improved
to 2 out of 10. Range of motion nearly full. Discharged to a home exercise
program with return precautions.
"""

_INCIDENT_REPORT = """CITY POLICE DEPARTMENT - TRAFFIC COLLISION REPORT (DEMO / SYNTHETIC)
Report Date: March 2, 2024

On March 2, 2024 at approximately 5:45 PM, Vehicle 2 (operated by Daniel Deng)
struck Vehicle 1 (operated by Maria Rivera) from behind at the intersection of
3rd Avenue and Palm Street while Vehicle 1 was stopped at a red light. Driver
of Vehicle 2 stated he was distracted by his phone. No citations contested at
scene; officer noted Vehicle 2 at fault for following too closely.
"""

# Phase 4: adjacent verticals (PLANNING.md) -- same document shapes, different
# evaluation standard. Synthetic only, same as the personal-injury demo above.
_WORKERS_COMP_MEDICAL_RECORD = """HARBOR OCCUPATIONAL HEALTH CLINIC - MEDICAL RECORD (DEMO / SYNTHETIC)
Patient: Thomas Okafor        Provider: Dr. Angela Cruz, MD

Visit - January 9, 2025
Mr. Okafor presented after a workplace injury on January 9, 2025 while
lifting a pallet at Westgate Distribution warehouse. He reported acute low
back pain radiating to the left leg. X-ray showed no fracture. Diagnosed with
lumbar strain. Placed on modified duty (no lifting over 10 lbs), prescribed
naproxen, referred to physical therapy.

Visit - February 20, 2025
Follow-up on February 20, 2025. Continued low back pain rated 5 out of 10
with prolonged sitting. Physical therapy ongoing, 8 sessions completed.
Modified duty restriction continued.

Visit - April 14, 2025
Seen April 14, 2025. Pain improved to 2 out of 10. Declared at maximum
medical improvement (MMI) with a 5% whole-person impairment rating. Released
to full duty with no permanent restrictions.
"""

_WORKERS_COMP_INCIDENT_REPORT = """WESTGATE DISTRIBUTION - EMPLOYER INCIDENT REPORT (DEMO / SYNTHETIC)
Report Date: January 9, 2025

On January 9, 2025 at approximately 10:15 AM, employee Thomas Okafor reported
acute low back pain while manually lifting a pallet in aisle 12 of the
warehouse. Supervisor Dana Wells confirmed the incident was witnessed and
occurred during the course of employment. Employee was sent to Harbor
Occupational Health Clinic the same day. Average weekly wage on file: $980.
"""

_MED_MALPRACTICE_MEDICAL_RECORD = """RIVERSIDE GENERAL HOSPITAL - MEDICAL RECORD (DEMO / SYNTHETIC)
Patient: Grace Lin        Provider: Dr. Samuel Okoye, MD

Visit - June 4, 2025
Ms. Lin presented to the emergency department on June 4, 2025 with severe
right lower abdominal pain. Labs showed elevated white blood cell count.
Dr. Okoye's note states appendicitis was considered but ruled unlikely; Ms.
Lin was discharged with a diagnosis of "gastroenteritis" and instructed to
follow up if symptoms worsened, without an ultrasound or CT scan being
ordered.

Visit - June 7, 2025
Ms. Lin returned June 7, 2025 with worsening pain and fever. CT scan showed a
ruptured appendix with peritonitis. Emergency appendectomy performed same
day. Post-operative course complicated by a longer hospital stay for
peritonitis treatment.
"""

_MED_MALPRACTICE_EXPERT_NOTE = """INDEPENDENT MEDICAL REVIEW NOTE (DEMO / SYNTHETIC)
Review Date: July 1, 2025

Reviewing physician notes that the standard of care for a patient presenting
with Ms. Lin's symptoms and lab findings on June 4, 2025 would typically
include imaging (ultrasound or CT) to rule out appendicitis before
discharge. No imaging was ordered on June 4, 2025. The delay between the
June 4, 2025 visit and the June 7, 2025 diagnosis of ruptured appendix is
noted as a departure from that standard.
"""


def _pdf_bytes(text: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 60), text, fontsize=10)
    return doc.tobytes()


def _upload(client: httpx.Client, case_id: str, name: str, text: str) -> str:
    files = {"file": (name, io.BytesIO(_pdf_bytes(text)), "application/pdf")}
    resp = client.post(f"{API}/cases/{case_id}/documents", files=files)
    resp.raise_for_status()
    return resp.json()["id"]


def _wait_processed(client: httpx.Client, case_id: str, doc_ids: list[str], timeout_s: int = 60) -> None:
    deadline = time.time() + timeout_s
    pending = set(doc_ids)
    while pending and time.time() < deadline:
        docs = client.get(f"{API}/cases/{case_id}/documents").json()
        for d in docs:
            if d["id"] in pending and d["status"] in ("processed", "failed"):
                print(f"  document {d['original_filename']}: {d['status']}")
                pending.discard(d["id"])
        if pending:
            time.sleep(2)
    if pending:
        raise RuntimeError(f"documents still not processed after {timeout_s}s: {pending}")


_DEMO_CASES = [
    {
        "name": "Rivera v. Deng (DEMO)",
        "case_type": "personal_injury",
        "documents": {
            "rivera_medical_record.pdf": _MEDICAL_RECORD,
            "collision_report.pdf": _INCIDENT_REPORT,
        },
    },
    {
        "name": "Okafor Workers' Comp Claim (DEMO)",
        "case_type": "workers_comp",
        "documents": {
            "okafor_medical_record.pdf": _WORKERS_COMP_MEDICAL_RECORD,
            "okafor_incident_report.pdf": _WORKERS_COMP_INCIDENT_REPORT,
        },
    },
    {
        "name": "Lin v. Riverside General (DEMO)",
        "case_type": "med_malpractice",
        "documents": {
            "lin_medical_record.pdf": _MED_MALPRACTICE_MEDICAL_RECORD,
            "lin_expert_review.pdf": _MED_MALPRACTICE_EXPERT_NOTE,
        },
    },
]


def _seed_case(client: httpx.Client, spec: dict) -> str:
    case = client.post(
        f"{API}/cases", json={"name": spec["name"], "case_type": spec["case_type"]}
    ).json()
    case_id = case["id"]
    print(f"created {spec['case_type']} case {case_id}: {spec['name']}")

    doc_ids = [
        _upload(client, case_id, filename, text) for filename, text in spec["documents"].items()
    ]
    print(f"  uploaded {len(doc_ids)} documents; waiting for ingest...")
    _wait_processed(client, case_id, doc_ids)

    print("  generating chronology (real LLM call)...")
    entries = client.post(f"{API}/cases/{case_id}/chronology").json()
    print(f"    {len(entries)} chronology entries")

    print("  detecting flags...")
    flags = client.post(f"{API}/cases/{case_id}/flags").json()
    print(f"    {len(flags)} flags")

    print("  signing off + drafting a demand letter...")
    client.post(f"{API}/cases/{case_id}/sign-off").raise_for_status()
    client.post(f"{API}/cases/{case_id}/demand-letter").raise_for_status()

    print(f"  done: http://localhost:3000/cases/{case_id}")
    return case_id


def main() -> None:
    with httpx.Client(timeout=120) as client:
        client.get(f"{API}/health").raise_for_status()
        for spec in _DEMO_CASES:
            _seed_case(client, spec)


if __name__ == "__main__":
    main()
