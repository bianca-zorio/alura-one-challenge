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

# --- Modelo de embeddings (local, multilingüe, sin PyTorch) ---
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# --- Claude (Anthropic) ---
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-opus-4-8")

# --- Parámetros de RAG ---
CHUNK_SIZE = 900          # caracteres por fragmento
CHUNK_OVERLAP = 150       # solapamiento entre fragmentos
TOP_K = 4                 # fragmentos recuperados por consulta
