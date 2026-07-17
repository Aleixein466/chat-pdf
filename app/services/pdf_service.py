from pathlib import Path

from PyPDF2 import PdfReader


def extract_text_by_page(file_path: str) -> list[dict]:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"No existe el archivo: {file_path}")

    reader = PdfReader(str(path))
    pages: list[dict] = []

    for index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        pages.append({"page_number": index, "text": text.strip()})

    return pages
