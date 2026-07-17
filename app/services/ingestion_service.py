from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.db.models import Document, DocumentChunk
from app.schemas.document import UploadDocumentResponse
from app.services.document_processor import process_pdf
from app.services.ollama_service import OllamaService


class DocumentIngestionService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.ollama_service = OllamaService()

    def ingest_pdf(self, file: UploadFile) -> UploadDocumentResponse:
        if file.content_type not in {"application/pdf", "application/octet-stream"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Solo se permiten archivos PDF.",
            )

        upload_dir = Path(settings.upload_dir)
        upload_dir.mkdir(parents=True, exist_ok=True)

        safe_name = file.filename or "document.pdf"
        destination = upload_dir / f"{uuid4()}_{safe_name}"

        try:
            with destination.open("wb") as output:
                output.write(file.file.read())

            pages, chunks = process_pdf(
                file_path=str(destination),
                chunk_size=settings.chunk_size,
                chunk_overlap=settings.chunk_overlap,
            )
            if not chunks:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No se pudo extraer contenido util del PDF.",
                )

            destination_size = destination.stat().st_size
            document = Document(
                file_name=safe_name,
                file_path=str(destination),
                file_size_bytes=destination_size,
                mime_type=file.content_type or "application/pdf",
                total_pages=len(pages),
            )
            self.db.add(document)
            self.db.flush()

            for chunk in chunks:
                embedding = self.ollama_service.generate_embedding(chunk.content)
                self.db.add(
                    DocumentChunk(
                        document_id=document.id,
                        page_number=chunk.page_number,
                        chunk_index=chunk.chunk_index,
                        content=chunk.content,
                        embedding=embedding,
                    )
                )

            self.db.commit()
            self.db.refresh(document)

            return UploadDocumentResponse(
                document_id=document.id,
                file_name=document.file_name,
                pages_processed=len(pages),
                chunks_created=len(chunks),
                message="Documento procesado correctamente.",
            )
        except HTTPException:
            self.db.rollback()
            raise
        except SQLAlchemyError as exc:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error de base de datos al procesar el documento: {exc}",
            ) from exc
        except Exception as exc:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error inesperado al procesar el PDF: {exc}",
            ) from exc
        finally:
            file.file.close()
