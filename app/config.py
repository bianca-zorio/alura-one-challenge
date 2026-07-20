"""Configuración central del proyecto: rutas y parámetros del modelo."""
from pathlib import Path
import os

from dotenv import load_dotenv

load_dotenv()

# --- Rutas ---
BASE_DIR = Path(__file__).resolve().parent.parent
DOCS_DIR = BASE_DIR / "data" / "documents"
INDEX_DIR = BASE_DIR / "data" / "index"
EMBEDDINGS_PATH = INDEX_DIR / "embeddings.npy"
CHUNKS_PATH = INDEX_DIR / "chunks.json"
INVENTORY_FILE = DOCS_DIR / "inventario_supermercado.xlsx"

# --- Modelo de embeddings (API de Gemini, multilingüe) ---
EMBEDDING_MODEL = "gemini-embedding-001"

# --- Google Gemini ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_MODEL = os.getenv("GOOGLE_MODEL", "gemini-flash-latest")

# --- Parámetros de RAG ---
CHUNK_SIZE = 900          # caracteres por fragmento
CHUNK_OVERLAP = 150       # solapamiento entre fragmentos
TOP_K = 4                 # fragmentos recuperados por consulta
