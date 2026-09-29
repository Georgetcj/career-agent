"""Provider boundary for generating OpenAI-compatible text embeddings."""

from __future__ import annotations

from openai import APIConnectionError, APIStatusError, OpenAI

from career_agent.core.config import get_settings


class EmbeddingError(Exception):
    """Raised when an embedding provider cannot return usable vectors."""


class OpenAICompatibleEmbeddingClient:
    """Use an OpenAI-compatible `/v1/embeddings` service behind explicit settings."""

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.embedding_api_key or not settings.embedding_base_url:
            raise EmbeddingError("Embedding API credentials are not configured.")
        self._settings = settings
        self._client = OpenAI(
            api_key=settings.embedding_api_key,
            base_url=settings.embedding_base_url,
        )

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch and reject responses that do not match the configured dimension."""

        if not texts:
            return []
        try:
            response = self._client.embeddings.create(
                model=self._settings.embedding_model,
                input=texts,
            )
        except (APIConnectionError, APIStatusError) as error:
            raise EmbeddingError("The embedding provider request failed.") from error

        vectors = [list(item.embedding) for item in response.data]
        if len(vectors) != len(texts):
            raise EmbeddingError("The embedding provider returned an unexpected result count.")
        if any(len(vector) != self._settings.embedding_dimensions for vector in vectors):
            raise EmbeddingError("The embedding dimension does not match project configuration.")
        return vectors
