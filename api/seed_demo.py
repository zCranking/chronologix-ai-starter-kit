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


def main() -> None:
    with httpx.Client(timeout=120) as client:
        client.get(f"{API}/health").raise_for_status()

        case = client.post(f"{API}/cases", json={"name": "Rivera v. Deng (DEMO)"}).json()
        case_id = case["id"]
        print(f"created case {case_id}")

        doc_ids = [
            _upload(client, case_id, "rivera_medical_record.pdf", _MEDICAL_RECORD),
            _upload(client, case_id, "collision_report.pdf", _INCIDENT_REPORT),
        ]
        print("uploaded 2 documents; waiting for ingest...")
        _wait_processed(client, case_id, doc_ids)

        print("generating chronology (real LLM call)...")
        entries = client.post(f"{API}/cases/{case_id}/chronology").json()
        print(f"  {len(entries)} chronology entries")

        print("detecting flags...")
        flags = client.post(f"{API}/cases/{case_id}/flags").json()
        print(f"  {len(flags)} flags")

        print("signing off + drafting a demand letter...")
        client.post(f"{API}/cases/{case_id}/sign-off").raise_for_status()
        client.post(f"{API}/cases/{case_id}/demand-letter").raise_for_status()

        print(f"\nDone. Open http://localhost:3000/cases/{case_id}")


if __name__ == "__main__":
    main()
