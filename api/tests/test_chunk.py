from ingest.chunk import chunk_text


def test_chunk_text_splits_long_page_into_multiple_chunks_preserving_page_number():
    pages = [(1, "a" * 5000)]

    chunks = chunk_text(pages, max_chars=2000)

    assert len(chunks) == 3
    assert all(page_number == 1 for page_number, _ in chunks)


def test_chunk_text_skips_blank_pages():
    pages = [(1, "   "), (2, "real content")]

    chunks = chunk_text(pages)

    assert chunks == [(2, "real content")]


def test_chunk_text_preserves_none_page_number_for_docx():
    pages = [(None, "some text")]

    chunks = chunk_text(pages)

    assert chunks == [(None, "some text")]
