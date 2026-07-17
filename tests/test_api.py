from __future__ import annotations

from fastapi import HTTPException, status

from app.services.document_processor import PageText, TextChunk


def test_healthcheck_returns_ok(client) -> None:
    response = client.get("/health")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "ok"}


def test_upload_pdf_returns_processing_summary(client, fake_db, monkeypatch, tmp_path) -> None:
    from app.core.config import settings
    from app.services import ingestion_service
    from app.services.ollama_service import OllamaService

    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))
    monkeypatch.setattr(
        ingestion_service,
        "process_pdf",
        lambda *args, **kwargs: (
            [
                PageText(page_number=1, text="Contenido de la primera pagina"),
                PageText(page_number=2, text="Contenido de la segunda pagina"),
            ],
            [
                TextChunk(page_number=1, chunk_index=0, content="Primer fragmento"),
                TextChunk(page_number=2, chunk_index=0, content="Segundo fragmento"),
            ],
        ),
    )
    monkeypatch.setattr(
        OllamaService,
        "generate_embedding",
        lambda self, text: [0.1] * 768,
    )

    files = {"file": ("manual.pdf", b"%PDF-1.4 fake pdf", "application/pdf")}
    response = client.post("/api/v1/documents/upload", files=files)
    body = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert body["file_name"] == "manual.pdf"
    assert body["pages_processed"] == 2
    assert body["chunks_created"] == 2
    assert body["message"] == "Documento procesado correctamente."
    assert any(obj.__class__.__name__ == "Document" for obj in fake_db.objects)
    assert sum(obj.__class__.__name__ == "DocumentChunk" for obj in fake_db.objects) == 2


def test_upload_rejects_non_pdf_file(client) -> None:
    files = {"file": ("notes.txt", b"hola mundo", "text/plain")}
    response = client.post("/api/v1/documents/upload", files=files)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Solo se permiten archivos PDF."


def test_ask_returns_answer_with_sources(client, monkeypatch) -> None:
    from app.services.chat_service import OllamaService
    from app.services.semantic_search import SemanticSearchService

    monkeypatch.setattr(
        SemanticSearchService,
        "search",
        lambda self, question, top_k=None: type(
            "SearchResponse",
            (),
            {
                "results": [
                    type(
                        "ChunkResult",
                        (),
                        {
                            "file_name": "manual.pdf",
                            "page_number": 4,
                            "content": "El sistema utiliza autenticacion con tokens JWT.",
                        },
                    )(),
                    type(
                        "ChunkResult",
                        (),
                        {
                            "file_name": "manual.pdf",
                            "page_number": 5,
                            "content": "Los tokens tienen expiracion de 60 minutos.",
                        },
                    )(),
                ]
            },
        )(),
    )
    monkeypatch.setattr(
        OllamaService,
        "generate_answer",
        lambda self, question, context: "El documento indica que la autenticacion usa JWT y expira en 60 minutos.",
    )

    response = client.post(
        "/api/v1/chat/ask",
        json={"question": "Como funciona la autenticacion?", "top_k": 3},
    )
    body = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert "JWT" in body["answer"]
    assert len(body["sources"]) == 2
    assert body["sources"][0]["file_name"] == "manual.pdf"
    assert body["sources"][0]["page_number"] == 4
    assert "autenticacion" in body["sources"][0]["snippet"]


def test_ask_rejects_short_question(client) -> None:
    response = client.post("/api/v1/chat/ask", json={"question": "hi"})

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_ask_returns_not_found_when_no_chunks_exist(client, monkeypatch) -> None:
    from app.services.semantic_search import SemanticSearchService

    monkeypatch.setattr(
        SemanticSearchService,
        "search",
        lambda self, question, top_k=None: (_ for _ in ()).throw(
            HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No se encontraron fragmentos indexados para la busqueda.",
            )
        ),
    )

    response = client.post(
        "/api/v1/chat/ask",
        json={"question": "Que dice el documento sobre pagos?"},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "No se encontraron fragmentos indexados para la busqueda."
