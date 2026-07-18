"""Ingesta de documentos: lee los PDF, los fragmenta y construye el índice
semántico (embeddings) que usará el agente para buscar respuestas.

Ejecutar con:  python -m app.ingest
"""
from __future__ import annotations

import json

import numpy as np
from fastembed import TextEmbedding
from pypdf import PdfReader

from app import config


def _leer_pdf(ruta) -> str:
    """Extrae todo el texto de un PDF, página por página."""
    lector = PdfReader(str(ruta))
    partes = []
    for pagina in lector.pages:
        texto = pagina.extract_text() or ""
        if texto.strip():
            partes.append(texto)
    return "\n".join(partes)


def _fragmentar(texto: str, tam: int, solapamiento: int) -> list[str]:
    """Divide el texto en fragmentos con solapamiento, respetando párrafos."""
    texto = " ".join(texto.split())  # normaliza espacios/saltos
    fragmentos = []
    inicio = 0
    while inicio < len(texto):
        fin = inicio + tam
        fragmentos.append(texto[inicio:fin])
        inicio = fin - solapamiento
    return [f for f in fragmentos if f.strip()]


def construir_indice() -> None:
    """Lee todos los PDF de data/documents y guarda embeddings + metadatos."""
    pdfs = sorted(config.DOCS_DIR.glob("*.pdf"))
    if not pdfs:
        raise SystemExit(f"No se encontraron PDF en {config.DOCS_DIR}")

    chunks: list[dict] = []
    for pdf in pdfs:
        print(f"Leyendo {pdf.name} ...")
        texto = _leer_pdf(pdf)
        for fragmento in _fragmentar(texto, config.CHUNK_SIZE, config.CHUNK_OVERLAP):
            chunks.append({"fuente": pdf.name, "texto": fragmento})

    print(f"Total de fragmentos: {len(chunks)}")
    print(f"Generando embeddings con {config.EMBEDDING_MODEL} ...")

    modelo = TextEmbedding(model_name=config.EMBEDDING_MODEL)
    vectores = np.array(list(modelo.embed([c["texto"] for c in chunks])), dtype=np.float32)
    # Normaliza para poder usar producto punto como similitud del coseno.
    vectores /= np.linalg.norm(vectores, axis=1, keepdims=True) + 1e-10

    config.INDEX_DIR.mkdir(parents=True, exist_ok=True)
    np.save(config.EMBEDDINGS_PATH, vectores)
    config.CHUNKS_PATH.write_text(
        json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Índice guardado en {config.INDEX_DIR} ({vectores.shape[0]} vectores).")


if __name__ == "__main__":
    construir_indice()
