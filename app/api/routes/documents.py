from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db.models import Document, DocumentChunk
from app.schemas.document import (
    BatchUploadDocumentResponse,
    DocumentListItemResponse,
    DocumentListResponse,
    DocumentPagesResponse,
    PageContent,
    UploadDocumentResponse,
)
from app.services.ingestion_service import DocumentIngestionService


router = APIRouter()


@router.post("/upload", response_model=UploadDocumentResponse)
def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)) -> UploadDocumentResponse:
    service = DocumentIngestionService(db)
    return service.ingest_pdf(file)


@router.post("/upload-many", response_model=BatchUploadDocumentResponse)
def upload_documents(files: list[UploadFile] = File(...), db: Session = Depends(get_db)) -> BatchUploadDocumentResponse:
    service = DocumentIngestionService(db)
    documents = [service.ingest_pdf(file) for file in files]
    return BatchUploadDocumentResponse(processed_count=len(documents), documents=documents)


@router.get("", response_model=DocumentListResponse)
def list_documents(db: Session = Depends(get_db)) -> DocumentListResponse:
    statement = (
        select(
            Document.id,
            Document.file_name,
            Document.total_pages,
            func.count(DocumentChunk.id).label("chunks_count"),
        )
        .outerjoin(DocumentChunk, DocumentChunk.document_id == Document.id)
        .group_by(Document.id, Document.file_name, Document.total_pages)
        .order_by(Document.created_at.desc())
    )
    rows = db.execute(statement).all()
    documents = [
        DocumentListItemResponse(
            document_id=row.id,
            file_name=row.file_name,
            total_pages=row.total_pages,
            chunks_count=row.chunks_count,
        )
        for row in rows
    ]
    return DocumentListResponse(total_documents=len(documents), documents=documents)


@router.get("/{document_id}/pages", response_model=DocumentPagesResponse)
def get_document_pages(document_id: int, db: Session = Depends(get_db)) -> DocumentPagesResponse:
    """
    Devuelve el texto completo del documento agrupado por página,
    reconstruido desde los chunks almacenados en la base de datos.
    """
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró el documento solicitado.",
        )

    chunks_stmt = (
        select(DocumentChunk.page_number, DocumentChunk.chunk_index, DocumentChunk.content)
        .where(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.page_number, DocumentChunk.chunk_index)
    )
    rows = db.execute(chunks_stmt).all()

    # Agrupar chunks por página y unir su contenido
    pages_map: dict[int, list[str]] = {}
    for row in rows:
        pages_map.setdefault(row.page_number, []).append(row.content)

    pages = [
        PageContent(page=page_num, text="\n\n".join(texts))
        for page_num, texts in sorted(pages_map.items())
    ]

    return DocumentPagesResponse(
        document_id=document.id,
        file_name=document.file_name,
        total_pages=document.total_pages,
        pages=pages,
    )


@router.delete("/{document_id}")
def delete_document(document_id: int, db: Session = Depends(get_db)) -> dict[str, str]:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontro el documento solicitado.",
        )

    file_path = Path(document.file_path)
    db.delete(document)
    db.commit()

    if file_path.exists():
        file_path.unlink()

    return {"message": "Documento eliminado correctamente."}
