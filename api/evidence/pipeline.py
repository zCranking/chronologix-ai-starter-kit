from core.db import get_client
from core.embeddings import embed
from core.transcription import transcribe


def process_evidence(evidence_id: str) -> None:
    db = get_client()
    try:
        evidence_row = (
            db.table("evidence").select("*").eq("id", evidence_id).single().execute().data
        )
        file_bytes = db.storage.from_("evidence").download(evidence_row["storage_path"])
        utterances = transcribe(file_bytes)
        texts = [u["text"] for u in utterances]
        if texts:
            try:
                vectors = embed(texts)
            except Exception:  # noqa: BLE001 -- embedding provider failures are unpredictable (network, auth, quota); any of them must degrade to a null embedding, not block transcript storage
                # ponytail: chronology generation reads segment content
                # directly and doesn't do similarity search yet, so a
                # missing/failed embedding must not block the pipeline --
                # store the segment with a null embedding instead. Backfill
                # once semantic retrieval needs it.
                vectors = [None] * len(texts)
        else:
            vectors = []
        rows = [
            {
                "evidence_id": evidence_id,
                "start_time_seconds": u["start"],
                "end_time_seconds": u["end"],
                "speaker_label": (f"Speaker {u['speaker']}" if u["speaker"] is not None else None),
                "content": u["text"],
                "embedding": vector,
            }
            for u, vector in zip(utterances, vectors)
        ]
        if rows:
            db.table("evidence_segments").insert(rows).execute()
        db.table("evidence").update({"status": "transcribed"}).eq("id", evidence_id).execute()
    except Exception:
        db.table("evidence").update({"status": "failed"}).eq("id", evidence_id).execute()
        raise
