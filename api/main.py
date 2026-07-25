import uuid
from datetime import UTC, datetime

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from chronology.build import build_chronology
from core.config import settings
from core.db import get_client
from demands.draft import draft_demand_letter
from evidence.pipeline import process_evidence
from flags.detect import detect_flags
from ingest.pipeline import process_document

app = FastAPI(title="Chronologix API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)

DEV_FIRM_ID = "00000000-0000-0000-0000-000000000001"


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


_CASE_TYPES = {"personal_injury", "workers_comp", "med_malpractice"}


class CreateCaseRequest(BaseModel):
    name: str
    case_type: str = "personal_injury"


class CaseResponse(BaseModel):
    id: str
    name: str
    firm_id: str
    case_type: str


class CaseDetailResponse(BaseModel):
    id: str
    name: str
    firm_id: str
    case_type: str
    chronology_signed_off: bool
    chronology_signed_off_at: str | None


class DocumentResponse(BaseModel):
    id: str
    case_id: str
    status: str
    original_filename: str


class UpdateChronologyEntryRequest(BaseModel):
    summary: str | None = None
    event_date: str | None = None


class EvidenceResponse(BaseModel):
    id: str
    case_id: str
    status: str
    original_filename: str
    media_type: str
    confirmed_by_attorney: bool


class DemandLetterResponse(BaseModel):
    id: str
    case_id: str
    body: str
    version: int
    edited_by_attorney: bool


class UpdateDemandLetterRequest(BaseModel):
    body: str


_VIDEO_EXTENSIONS = {"mp4", "mov", "avi", "mkv", "webm"}
_AUDIO_EXTENSIONS = {"mp3", "wav", "m4a", "ogg", "flac"}


def _infer_media_type(filename: str) -> str:
    ext = filename.lower().rsplit(".", 1)[-1]
    if ext in _VIDEO_EXTENSIONS:
        return "video"
    if ext in _AUDIO_EXTENSIONS:
        return "audio"
    raise HTTPException(status_code=400, detail=f"unsupported evidence file type: {ext}")


@app.post("/cases", response_model=CaseResponse)
def create_case(payload: CreateCaseRequest) -> dict:
    if payload.case_type not in _CASE_TYPES:
        raise HTTPException(status_code=400, detail=f"unsupported case_type: {payload.case_type}")
    db = get_client()
    result = (
        db.table("cases")
        .insert({"name": payload.name, "firm_id": DEV_FIRM_ID, "case_type": payload.case_type})
        .execute()
    )
    return result.data[0]


@app.get("/cases", response_model=list[CaseResponse])
def list_cases() -> list[dict]:
    db = get_client()
    return db.table("cases").select("*").execute().data


@app.get("/cases/{case_id}", response_model=CaseDetailResponse)
def get_case(case_id: str) -> dict:
    db = get_client()
    result = db.table("cases").select("*").eq("id", case_id).maybe_single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="case not found")
    return result.data


@app.post("/cases/{case_id}/sign-off", response_model=CaseDetailResponse)
def sign_off_case(case_id: str) -> dict:
    db = get_client()
    result = (
        db.table("cases")
        .update(
            {
                "chronology_signed_off": True,
                "chronology_signed_off_at": datetime.now(UTC).isoformat(),
            }
        )
        .eq("id", case_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="case not found")
    return result.data[0]


@app.post("/cases/{case_id}/documents", response_model=DocumentResponse)
async def upload_document(
    case_id: str, background_tasks: BackgroundTasks, file: UploadFile = File(...)  # noqa: B008
) -> dict:
    db = get_client()
    file_bytes = await file.read()
    storage_path = f"{case_id}/{uuid.uuid4()}_{file.filename}"
    db.storage.from_("documents").upload(storage_path, file_bytes)
    result = (
        db.table("documents")
        .insert(
            {
                "case_id": case_id,
                "storage_path": storage_path,
                "original_filename": file.filename,
                "status": "pending",
            }
        )
        .execute()
    )
    document = result.data[0]
    background_tasks.add_task(process_document, document["id"])
    return document


@app.get("/cases/{case_id}/documents", response_model=list[DocumentResponse])
def list_documents(case_id: str) -> list[dict]:
    db = get_client()
    return db.table("documents").select("*").eq("case_id", case_id).execute().data


@app.get("/cases/{case_id}/documents/{document_id}", response_model=DocumentResponse)
def get_document(case_id: str, document_id: str) -> dict:
    db = get_client()
    result = (
        db.table("documents")
        .select("*")
        .eq("id", document_id)
        .eq("case_id", case_id)
        .maybe_single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="document not found")
    return result.data


@app.get("/cases/{case_id}/chronology")
def list_chronology(case_id: str) -> list[dict]:
    db = get_client()
    return (
        db.table("chronology_entries")
        .select("*")
        .eq("case_id", case_id)
        .order("event_date")
        .execute()
        .data
    )


@app.post("/cases/{case_id}/chronology")
def generate_chronology(case_id: str) -> list[dict]:
    return build_chronology(case_id)


@app.patch("/cases/{case_id}/chronology/{entry_id}")
def update_chronology_entry(case_id: str, entry_id: str, payload: UpdateChronologyEntryRequest) -> dict:
    db = get_client()
    existing = (
        db.table("chronology_entries")
        .select("*")
        .eq("id", entry_id)
        .eq("case_id", case_id)
        .maybe_single()
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="chronology entry not found")
    changes = payload.model_dump(exclude_none=True)
    changes["version"] = existing.data["version"] + 1
    changes["edited_by_attorney"] = True
    result = db.table("chronology_entries").update(changes).eq("id", entry_id).execute()
    return result.data[0]


@app.get("/cases/{case_id}/flags")
def list_flags(case_id: str) -> list[dict]:
    db = get_client()
    return db.table("flags").select("*").eq("case_id", case_id).execute().data


@app.post("/cases/{case_id}/flags")
def generate_flags(case_id: str) -> list[dict]:
    return detect_flags(case_id)


@app.post("/cases/{case_id}/evidence", response_model=EvidenceResponse)
async def upload_evidence(
    case_id: str, background_tasks: BackgroundTasks, file: UploadFile = File(...)  # noqa: B008
) -> dict:
    media_type = _infer_media_type(file.filename)
    db = get_client()
    file_bytes = await file.read()
    storage_path = f"{case_id}/{uuid.uuid4()}_{file.filename}"
    db.storage.from_("evidence").upload(storage_path, file_bytes)
    result = (
        db.table("evidence")
        .insert(
            {
                "case_id": case_id,
                "storage_path": storage_path,
                "original_filename": file.filename,
                "media_type": media_type,
                "status": "pending",
            }
        )
        .execute()
    )
    evidence_row = result.data[0]
    background_tasks.add_task(process_evidence, evidence_row["id"])
    return evidence_row


@app.get("/cases/{case_id}/evidence", response_model=list[EvidenceResponse])
def list_evidence(case_id: str) -> list[dict]:
    db = get_client()
    return db.table("evidence").select("*").eq("case_id", case_id).execute().data


@app.post("/cases/{case_id}/evidence/{evidence_id}/confirm", response_model=EvidenceResponse)
def confirm_evidence(case_id: str, evidence_id: str) -> dict:
    db = get_client()
    result = (
        db.table("evidence")
        .update({"confirmed_by_attorney": True})
        .eq("id", evidence_id)
        .eq("case_id", case_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="evidence not found")
    return result.data[0]


@app.post("/cases/{case_id}/demand-letter", response_model=DemandLetterResponse)
def generate_demand_letter(case_id: str) -> dict:
    try:
        return draft_demand_letter(case_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/cases/{case_id}/demand-letters", response_model=list[DemandLetterResponse])
def list_demand_letters(case_id: str) -> list[dict]:
    db = get_client()
    return (
        db.table("demand_letters")
        .select("*")
        .eq("case_id", case_id)
        .order("version", desc=True)
        .execute()
        .data
    )


@app.patch("/cases/{case_id}/demand-letters/{letter_id}", response_model=DemandLetterResponse)
def update_demand_letter(case_id: str, letter_id: str, payload: UpdateDemandLetterRequest) -> dict:
    db = get_client()
    existing = (
        db.table("demand_letters")
        .select("*")
        .eq("id", letter_id)
        .eq("case_id", case_id)
        .maybe_single()
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="demand letter not found")
    result = (
        db.table("demand_letters")
        .update(
            {
                "body": payload.body,
                "version": existing.data["version"] + 1,
                "edited_by_attorney": True,
            }
        )
        .eq("id", letter_id)
        .execute()
    )
    return result.data[0]
