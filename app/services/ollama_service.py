from __future__ import annotations

from collections.abc import Sequence

import httpx
from fastapi import HTTPException, status

from app.core.config import settings
from app.services.prompt_builder import build_chat_prompt


class OllamaEmbeddingError(Exception):
    """Error base para problemas relacionados con embeddings en Ollama."""


class OllamaService:
    """
    Cliente reutilizable para interactuar con Ollama.

    Buenas practicas aplicadas:
    - reusa configuracion centralizada
    - valida entradas vacias
    - soporta endpoints nuevos y legacy de embeddings
    - convierte fallos de red o respuestas invalidas en errores claros
    """

    def __init__(
        self,
        base_url: str | None = None,
        embed_model: str | None = None,
        chat_model: str | None = None,
        timeout: float | None = None,
    ) -> None:
        self.base_url = settings.ollama_base_url.rstrip("/")
        self.embed_model = embed_model or settings.ollama_embed_model
        self.chat_model = chat_model or settings.ollama_chat_model
        self.timeout = timeout if timeout is not None else settings.ollama_timeout
        if base_url:
            self.base_url = base_url.rstrip("/")

    def generate_embedding(self, text: str) -> list[float]:
        """
        Genera el embedding de un texto usando Ollama.

        Args:
            text: Texto a vectorizar.

        Returns:
            Lista de floats correspondiente al embedding.

        Raises:
            HTTPException: Si el servicio no esta disponible, responde con error
            o retorna un embedding vacio o invalido.
        """

        normalized_text = text.strip()
        if not normalized_text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se puede generar un embedding a partir de un texto vacio.",
            )

        payload = {"model": self.embed_model, "input": normalized_text}

        try:
            response = httpx.post(f"{self.base_url}/api/embed", json=payload, timeout=self.timeout)
            if response.status_code == status.HTTP_404_NOT_FOUND:
                legacy_payload = {"model": self.embed_model, "prompt": normalized_text}
                response = httpx.post(
                    f"{self.base_url}/api/embeddings",
                    json=legacy_payload,
                    timeout=self.timeout,
                )
            response.raise_for_status()
            body = response.json()
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"No fue posible conectar con Ollama: {exc}",
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Ollama devolvio un error al generar embeddings: {exc.response.text}",
            ) from exc

        return self._parse_embedding_response(body)

    def generate_answer(self, question: str, context: str) -> str:
        """
        Genera una respuesta usando un prompt restringido al contexto recuperado.

        Args:
            question: Pregunta del usuario.
            context: Fragmentos relevantes provenientes de la busqueda semantica.

        Returns:
            Respuesta textual generada por el modelo.
        """

        if not question.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La pregunta no puede estar vacia.",
            )
        if not context.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El contexto no puede estar vacio para generar la respuesta.",
            )

        prompt = build_chat_prompt(question=question, context=context)
        messages = [
            {
                "role": "system",
                "content": prompt.system_message,
            },
            {
                "role": "user",
                "content": prompt.user_message,
            },
        ]

        try:
            response = httpx.post(
                f"{self.base_url}/api/chat",
                json={"model": self.chat_model, "messages": messages, "stream": False},
                timeout=self.timeout,
            )
            response.raise_for_status()
            body = response.json()
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"No fue posible conectar con Ollama: {exc}",
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Ollama devolvio un error al generar la respuesta: {exc.response.text}",
            ) from exc

        message = body.get("message", {})
        content = message.get("content")
        if not content:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Ollama no devolvio contenido para la respuesta.",
            )
        return content.strip()

    def _parse_embedding_response(self, body: dict) -> list[float]:
        """Extrae y valida un embedding desde la respuesta JSON de Ollama."""

        embeddings = body.get("embeddings")
        if isinstance(embeddings, Sequence) and embeddings and isinstance(embeddings[0], list):
            parsed = [float(value) for value in embeddings[0]]
            if parsed:
                return parsed

        embedding = body.get("embedding")
        if isinstance(embedding, Sequence) and not isinstance(embedding, (str, bytes)):
            parsed = [float(value) for value in embedding]
            if parsed:
                return parsed

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="La respuesta de Ollama no contiene un embedding valido o llego vacia.",
        )
