import uuid

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel

from core.db import get_client
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


class DocumentResponse(BaseModel):
    id: str
    case_id: str
    status: str
    original_filename: str


@app.post("/cases", response_model=CaseResponse)
def create_case(payload: CreateCaseRequest) -> dict:
    db = get_client()
    result = db.table("cases").insert({"name": payload.name, "firm_id": DEV_FIRM_ID}).execute()
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
