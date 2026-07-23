import uuid
from datetime import UTC, datetime

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel

from chronology.build import build_chronology
from core.db import get_client
from flags.detect import detect_flags
from ingest.pipeline import process_document

app = FastAPI(title="Chronologix API")

DEV_FIRM_ID = "00000000-0000-0000-0000-000000000001"


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


class CreateCaseRequest(BaseModel):
    name: str


class CaseResponse(BaseModel):
    id: str
    name: str
    firm_id: str


class CaseDetailResponse(BaseModel):
    id: str
    name: str
    firm_id: str
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


@app.post("/cases", response_model=CaseResponse)
def create_case(payload: CreateCaseRequest) -> dict:
    db = get_client()
    result = db.table("cases").insert({"name": payload.name, "firm_id": DEV_FIRM_ID}).execute()
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
