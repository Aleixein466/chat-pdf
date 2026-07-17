from collections.abc import Iterable


def split_text_into_chunks(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    cleaned = " ".join(text.split())
    if not cleaned:
        return []
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap debe ser menor a chunk_size")

    chunks: list[str] = []
    start = 0
    text_length = len(cleaned)

    while start < text_length:
        end = min(start + chunk_size, text_length)
        chunk = cleaned[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == text_length:
            break
        start = end - chunk_overlap

    return chunks


def flatten_page_chunks(page_chunks: Iterable[tuple[int, list[str]]]) -> list[dict]:
    flattened: list[dict] = []
    for page_number, chunks in page_chunks:
        for chunk_index, chunk in enumerate(chunks):
            flattened.append(
                {
                    "page_number": page_number,
                    "chunk_index": chunk_index,
                    "content": chunk,
                }
            )
    return flattened
