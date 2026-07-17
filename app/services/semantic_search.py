from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.schemas.search import SemanticSearchResponse, SemanticSearchResult
from app.services.ollama_service import OllamaService


SEMANTIC_SEARCH_SQL = """
SELECT
    dc.id AS chunk_id,
    dc.document_id,
    d.file_name,
    dc.page_number,
    dc.chunk_index,
    dc.content,
    dc.embedding <-> CAST(:embedding AS vector) AS distance
FROM document_chunks AS dc
JOIN documents AS d
    ON d.id = dc.document_id
WHERE (:document_id IS NULL OR dc.document_id = :document_id)
ORDER BY dc.embedding <-> CAST(:embedding AS vector)
LIMIT :limit;
"""


class SemanticSearchService:
    """Servicio reutilizable para busqueda semantica sobre pgvector."""

    def __init__(self, db: Session, ollama_service: OllamaService | None = None) -> None:
        self.db = db
        self.ollama_service = ollama_service or OllamaService()

    def search(
        self,
        question: str,
        top_k: int | None = None,
        document_id: int | None = None,
    ) -> SemanticSearchResponse:
        """
        Busca los fragmentos mas relevantes para una pregunta.

        Flujo:
        - genera el embedding de la pregunta
        - ejecuta una consulta SQL optimizada con pgvector y el operador <-> 
        - retorna una salida estructurada con metadatos del fragmento
        """

        normalized_question = question.strip()
        if not normalized_question:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La pregunta no puede estar vacia.",
            )

        limit = top_k or settings.top_k
        question_embedding = self.ollama_service.generate_embedding(normalized_question)
        embedding_literal = self._to_pgvector_literal(question_embedding)

        rows = self.db.execute(
            text(SEMANTIC_SEARCH_SQL),
            {"embedding": embedding_literal, "limit": limit, "document_id": document_id},
        ).mappings().all()

        if not rows:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No se encontraron fragmentos indexados para la busqueda.",
            )

        results = [self._map_row(row) for row in rows]
        return SemanticSearchResponse(question=normalized_question, top_k=limit, results=results)

    @staticmethod
    def _to_pgvector_literal(embedding: list[float]) -> str:
        """Convierte un embedding a literal compatible con pgvector."""

        return "[" + ",".join(f"{value:.12f}" for value in embedding) + "]"

    @staticmethod
    def _map_row(row: Any) -> SemanticSearchResult:
        """Transforma una fila SQL en una salida estructurada."""

        return SemanticSearchResult(
            chunk_id=row["chunk_id"],
            document_id=row["document_id"],
            file_name=row["file_name"],
            page_number=row["page_number"],
            chunk_index=row["chunk_index"],
            content=row["content"],
            distance=float(row["distance"]),
        )
