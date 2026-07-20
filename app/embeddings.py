"""Embeddings con la API de Gemini.

Convierte texto en vectores usando el modelo de embeddings de Google. Al ser
por API, la aplicación no necesita descargar ni cargar un modelo pesado en
memoria — ideal para servidores con poca RAM.

Usa 'task_type' para mejorar la búsqueda: los documentos se indexan como
RETRIEVAL_DOCUMENT y las preguntas se codifican como RETRIEVAL_QUERY.
"""
from __future__ import annotations

from google import genai
from google.genai import types

from app import config

_cliente: genai.Client | None = None
_LOTE = 50  # cuántos textos enviar por petición


def _cli() -> genai.Client:
    global _cliente
    if _cliente is None:
        if not config.GOOGLE_API_KEY:
            raise RuntimeError("Falta GOOGLE_API_KEY (revisa el archivo .env).")
        _cliente = genai.Client(api_key=config.GOOGLE_API_KEY)
    return _cliente


def embed(textos: list[str], task_type: str) -> list[list[float]]:
    """Devuelve el embedding de cada texto. task_type: 'RETRIEVAL_DOCUMENT'
    (para indexar documentos) o 'RETRIEVAL_QUERY' (para la pregunta del usuario)."""
    vectores: list[list[float]] = []
    for i in range(0, len(textos), _LOTE):
        lote = textos[i:i + _LOTE]
        respuesta = _cli().models.embed_content(
            model=config.EMBEDDING_MODEL,
            contents=lote,
            config=types.EmbedContentConfig(task_type=task_type),
        )
        vectores.extend(e.values for e in respuesta.embeddings)
    return vectores
