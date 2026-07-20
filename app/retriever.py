"""Recuperador semántico: dada una consulta, devuelve los fragmentos de los
PDF más relevantes usando similitud del coseno sobre los embeddings de Gemini."""
from __future__ import annotations

import json

import numpy as np

from app import config
from app.embeddings import embed


class Recuperador:
    """Carga el índice una sola vez y responde consultas de búsqueda."""

    def __init__(self) -> None:
        if not config.EMBEDDINGS_PATH.exists():
            raise FileNotFoundError(
                "No existe el índice. Ejecuta primero:  python -m app.ingest"
            )
        self.vectores = np.load(config.EMBEDDINGS_PATH)
        self.chunks = json.loads(config.CHUNKS_PATH.read_text(encoding="utf-8"))

    def buscar(self, consulta: str, k: int | None = None) -> list[dict]:
        """Devuelve los k fragmentos más relevantes con su fuente y puntuación."""
        k = k or config.TOP_K
        crudo = embed([consulta], task_type="RETRIEVAL_QUERY")[0]
        vec = np.array(crudo, dtype=np.float32)
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
