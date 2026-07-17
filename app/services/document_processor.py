from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from PyPDF2 import PdfReader


WHITESPACE_RE = re.compile(r"\s+")


@dataclass(slots=True)
class PageText:
    """Representa el texto extraido y normalizado de una pagina del PDF."""

    page_number: int
    text: str


@dataclass(slots=True)
class TextChunk:
    """Representa un fragmento de texto con trazabilidad a su pagina de origen."""

    page_number: int
    chunk_index: int
    content: str


def clean_text(text: str) -> str:
    """
    Normaliza el texto extraido de un PDF.

    Aplica limpieza ligera para mantener el contenido util:
    - colapsa espacios en blanco consecutivos
    - elimina saltos de linea redundantes
    - recorta espacios al inicio y final

    Args:
        text: Texto bruto extraido del PDF.

    Returns:
        Texto limpio y compacto.
    """

    return WHITESPACE_RE.sub(" ", text).strip()


def extract_pdf_pages(file_path: str | Path) -> list[PageText]:
    """
    Extrae el texto del PDF pagina por pagina.

    Args:
        file_path: Ruta al archivo PDF.

    Returns:
        Lista de paginas con su numero y texto limpio.

    Raises:
        FileNotFoundError: Si el archivo no existe.
        ValueError: Si el PDF no contiene paginas legibles.
    """

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"No existe el archivo: {path}")

    reader = PdfReader(str(path))
    pages: list[PageText] = []

    for page_number, page in enumerate(reader.pages, start=1):
        raw_text = page.extract_text() or ""
        pages.append(PageText(page_number=page_number, text=clean_text(raw_text)))

    if not pages:
        raise ValueError("El PDF no contiene paginas legibles.")

    return pages


def split_text_into_chunks(text: str, chunk_size: int = 800, chunk_overlap: int = 150) -> list[str]:
    """
    Divide un texto en fragmentos con solapamiento.

    El algoritmo intenta cortar en limites naturales cercanos al tamano
    objetivo para evitar partir palabras o frases de forma agresiva.

    Args:
        text: Texto ya limpio.
        chunk_size: Tamano maximo aproximado del chunk.
        chunk_overlap: Cantidad de caracteres compartidos entre chunks vecinos.

    Returns:
        Lista de fragmentos de texto.

    Raises:
        ValueError: Si los parametros de chunking no son validos.
    """

    if chunk_size < 500 or chunk_size > 1000:
        raise ValueError("chunk_size debe estar entre 500 y 1000 caracteres.")
    if chunk_overlap < 0:
        raise ValueError("chunk_overlap no puede ser negativo.")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap debe ser menor a chunk_size.")

    normalized = clean_text(text)
    if not normalized:
        return []

    chunks: list[str] = []
    start = 0
    text_length = len(normalized)

    while start < text_length:
        target_end = min(start + chunk_size, text_length)
        if target_end == text_length:
            chunk = normalized[start:].strip()
            if chunk:
                chunks.append(chunk)
            break

        end = normalized.rfind(" ", start, target_end + 1)
        if end <= start:
            end = target_end

        chunk = normalized[start:end].strip()
        if chunk:
            chunks.append(chunk)

        start = max(end - chunk_overlap, start + 1)

    return chunks


def build_page_chunks(
    pages: list[PageText],
    chunk_size: int = 800,
    chunk_overlap: int = 150,
) -> list[TextChunk]:
    """
    Genera chunks por pagina manteniendo trazabilidad.

    Args:
        pages: Lista de paginas extraidas del PDF.
        chunk_size: Tamano maximo aproximado por chunk.
        chunk_overlap: Solapamiento entre chunks consecutivos.

    Returns:
        Lista plana de chunks con pagina y posicion de origen.
    """

    page_chunks: list[TextChunk] = []

    for page in pages:
        chunks = split_text_into_chunks(
            text=page.text,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        for chunk_index, chunk in enumerate(chunks):
            page_chunks.append(
                TextChunk(
                    page_number=page.page_number,
                    chunk_index=chunk_index,
                    content=chunk,
                )
            )

    return page_chunks


def process_pdf(
    file_path: str | Path,
    chunk_size: int = 800,
    chunk_overlap: int = 150,
) -> tuple[list[PageText], list[TextChunk]]:
    """
    Ejecuta el flujo completo de procesamiento sobre un PDF.

    Args:
        file_path: Ruta al archivo PDF.
        chunk_size: Tamano maximo aproximado por chunk.
        chunk_overlap: Solapamiento entre fragmentos consecutivos.

    Returns:
        Una tupla con:
        - paginas extraidas y limpias
        - chunks listos para indexacion
    """

    pages = extract_pdf_pages(file_path)
    chunks = build_page_chunks(
        pages=pages,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    return pages, chunks
