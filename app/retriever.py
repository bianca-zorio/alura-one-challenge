"""Recuperador semántico: dada una consulta, devuelve los fragmentos de los
PDF más relevantes usando similitud del coseno sobre los embeddings."""
from __future__ import annotations

import json

import numpy as np
from fastembed import TextEmbedding

from app import config


class Recuperador:
    """Carga el índice una sola vez y responde consultas de búsqueda."""

    def __init__(self) -> None:
        if not config.EMBEDDINGS_PATH.exists():
            raise FileNotFoundError(
                "No existe el índice. Ejecuta primero:  python -m app.ingest"
            )
        self.vectores = np.load(config.EMBEDDINGS_PATH)
        self.chunks = json.loads(config.CHUNKS_PATH.read_text(encoding="utf-8"))
        self.modelo = TextEmbedding(model_name=config.EMBEDDING_MODEL)

    def buscar(self, consulta: str, k: int | None = None) -> list[dict]:
        """Devuelve los k fragmentos más relevantes con su fuente y puntuación."""
        k = k or config.TOP_K
        vec = np.array(list(self.modelo.embed([consulta]))[0], dtype=np.float32)
        vec /= np.linalg.norm(vec) + 1e-10
        similitudes = self.vectores @ vec
        mejores = np.argsort(similitudes)[::-1][:k]
        return [
            {
                "fuente": self.chunks[i]["fuente"],
                "texto": self.chunks[i]["texto"],
                "score": float(similitudes[i]),
            }
            for i in mejores
        ]
