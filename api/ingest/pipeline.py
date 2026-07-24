from core.db import get_client
from core.embeddings import embed
from ingest.chunk import chunk_text
from ingest.parse import extract_text


def process_document(document_id: str) -> None:
    db = get_client()
    try:
        doc_row = db.table("documents").select("*").eq("id", document_id).single().execute().data
        file_bytes = db.storage.from_("documents").download(doc_row["storage_path"])
        pages = extract_text(file_bytes, doc_row["original_filename"])
        chunks = chunk_text(pages)
        texts = [content for _, content in chunks]
        if texts:
            try:
                vectors = embed(texts)
            except Exception:  # noqa: BLE001 -- embedding provider failures are unpredictable (network, auth, quota); any of them must degrade to a null embedding, not block ingest
                # ponytail: chronology/build.py reads chunk text directly and
                # doesn't do similarity search yet, so a missing/failed
                # embedding call must not block ingest -- store the chunk with
                # a null embedding instead. Backfill embeddings once semantic
                # retrieval is actually built and needs them.
                vectors = [None] * len(texts)
        else:
            vectors = []
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
