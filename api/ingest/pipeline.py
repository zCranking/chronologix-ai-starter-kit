from core.db import get_client
from core.embeddings import embed
from ingest.chunk import chunk_text
from ingest.parse import extract_text


def process_document(document_id: str) -> None:
    db = get_client()
    doc_row = db.table("documents").select("*").eq("id", document_id).single().execute().data
    try:
        file_bytes = db.storage.from_("documents").download(doc_row["storage_path"])
        pages = extract_text(file_bytes, doc_row["original_filename"])
        chunks = chunk_text(pages)
        texts = [content for _, content in chunks]
        vectors = embed(texts) if texts else []
        rows = [
            {
                "document_id": document_id,
                "page_number": page_number,
                "content": content,
                "embedding": vector,
            }
            for (page_number, content), vector in zip(chunks, vectors)
        ]
        if rows:
            db.table("chunks").insert(rows).execute()
        db.table("documents").update({"status": "processed"}).eq("id", document_id).execute()
    except Exception:
        db.table("documents").update({"status": "failed"}).eq("id", document_id).execute()
        raise
