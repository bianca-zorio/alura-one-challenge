"""Servidor web (FastAPI): expone el agente como una API y una página de chat.

Ejecutar en local:  uvicorn app.main:app --reload
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app.agent import Agente

app = FastAPI(title="Alura Agente — Mercado Central 24h")

# El agente se crea una sola vez al arrancar (carga el índice y el modelo).
_agente: Agente | None = None


def obtener_agente() -> Agente:
    global _agente
    if _agente is None:
        _agente = Agente()
    return _agente


class Pregunta(BaseModel):
    pregunta: str


class Respuesta(BaseModel):
    respuesta: str
    fuentes: list[str]


@app.on_event("startup")
def _arranque() -> None:
    obtener_agente()  # precarga índice + modelo de embeddings


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/chat", response_model=Respuesta)
def chat(entrada: Pregunta) -> Respuesta:
    resultado = obtener_agente().responder(entrada.pregunta)
    return Respuesta(**resultado)


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return (Path(__file__).parent / "templates" / "index.html").read_text(encoding="utf-8")
