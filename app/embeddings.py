"""Embeddings con la API de Gemini.

Convierte texto en vectores usando el modelo de embeddings de Google. Al ser
por API, la aplicación no necesita descargar ni cargar un modelo pesado en
memoria — ideal para servidores con poca RAM.

Usa 'task_type' para mejorar la búsqueda: los documentos se indexan como
RETRIEVAL_DOCUMENT y las preguntas se codifican como RETRIEVAL_QUERY.
"""
from __future__ import annotations

import time

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from app import config

_cliente: genai.Client | None = None
_LOTE = 50  # cuántos textos enviar por petición
# Códigos transitorios de Gemini que conviene reintentar.
_TRANSITORIOS = {429, 500, 503}


def _cli() -> genai.Client:
    global _cliente
    if _cliente is None:
        if not config.GOOGLE_API_KEY:
            raise RuntimeError("Falta GOOGLE_API_KEY (revisa el archivo .env).")
        _cliente = genai.Client(api_key=config.GOOGLE_API_KEY)
    return _cliente


def _embed_lote(lote: list[str], task_type: str):
    """Llama a la API reintentando ante errores transitorios (429/500/503)."""
    for intento in range(4):
        try:
            return _cli().models.embed_content(
                model=config.EMBEDDING_MODEL,
                contents=lote,
                config=types.EmbedContentConfig(task_type=task_type),
            )
        except genai_errors.APIError as e:
            if getattr(e, "code", None) not in _TRANSITORIOS or intento == 3:
                raise
            time.sleep(min(2 ** intento * 2, 20))


def embed(textos: list[str], task_type: str) -> list[list[float]]:
    """Devuelve el embedding de cada texto. task_type: 'RETRIEVAL_DOCUMENT'
    (para indexar documentos) o 'RETRIEVAL_QUERY' (para la pregunta del usuario)."""
    vectores: list[list[float]] = []
    for i in range(0, len(textos), _LOTE):
        respuesta = _embed_lote(textos[i:i + _LOTE], task_type)
        vectores.extend(e.values for e in respuesta.embeddings)
    return vectores
