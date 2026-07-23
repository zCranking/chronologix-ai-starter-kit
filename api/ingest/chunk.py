def chunk_text(pages: list[tuple[int | None, str]], max_chars: int = 2000) -> list[tuple[int | None, str]]:
    chunks: list[tuple[int | None, str]] = []
    for page_number, text in pages:
        text = text.strip()
        if not text:
            continue
        for start in range(0, len(text), max_chars):
            piece = text[start : start + max_chars].strip()
            if piece:
                chunks.append((page_number, piece))
    return chunks
