# 🛒 Alura Agente — Asistente de IA para Mercado Central 24h

Agente de inteligencia artificial que responde preguntas en lenguaje natural sobre
la documentación interna de **Mercado Central 24h** (un supermercado de operación
continua 24/7): políticas, preguntas frecuentes, reglamento interno, manual de
proveedores y el **inventario de productos**.

En lugar de abrir cada documento, cualquier persona colaboradora escribe una
pregunta y el agente encuentra y devuelve la respuesta.

> Proyecto del **Challenge Alura Agente** — del documento al *deploy* en la nube.

---

## 🧠 ¿Qué puede responder?

El agente combina dos fuentes de información y decide cuál usar en cada pregunta:

| Tipo de pregunta | Fuente | Ejemplo |
|---|---|---|
| Políticas, normas, FAQ | 4 PDF | *"¿Cómo funciona la política de devoluciones?"* |
| Datos de productos | Inventario (Excel) | *"¿Cuál es el producto con más stock?"* |

---

## 🏗️ Arquitectura

El proyecto implementa el patrón **RAG (Retrieval-Augmented Generation)** combinado
con un **agente de herramientas**: Claude decide, en cada pregunta, qué herramienta
usar para fundamentar su respuesta.

```
                        Pregunta del usuario
                                │
                                ▼
                ┌───────────────────────────────┐
                │   Google Gemini (API)          │
                │   — decide qué herramienta usar │
                └───────────────┬───────────────┘
                    │                       │
        ┌───────────▼──────────┐   ┌────────▼─────────────┐
        │ buscar_en_documentos │   │ consultar_inventario │
        │  (RAG semántico)     │   │  (consulta pandas)   │
        └───────────┬──────────┘   └────────┬─────────────┘
                    │                       │
        ┌───────────▼──────────┐   ┌────────▼─────────────┐
        │ Índice de embeddings │   │  inventario .xlsx    │
        │  (FastEmbed + NumPy) │   │  (200 productos)     │
        │  ← 4 PDF fragmentados │   │                      │
        └──────────────────────┘   └──────────────────────┘
                    │
                    ▼
        Respuesta en lenguaje natural + fuentes citadas
                    │
                    ▼
         FastAPI (API /chat + página web de chat)
                    │
                    ▼
              Deploy en Oracle Cloud (OCI)
```

### ¿Cómo funciona el RAG?
1. **Ingesta**: los 4 PDF se leen con *PyPDF*, se dividen en fragmentos (~900
   caracteres con solapamiento) y se convierten en vectores (*embeddings*) con un
   modelo multilingüe local.
2. **Búsqueda**: la pregunta se convierte en un vector y se comparan por
   **similitud del coseno** con los fragmentos para recuperar los más relevantes.
3. **Generación**: Claude recibe esos fragmentos como contexto y redacta la
   respuesta, citando la fuente.

Para el **inventario** se usa una herramienta aparte que consulta directamente el
Excel con *pandas* (filtrar, ordenar, buscar), lo que permite responder con
precisión preguntas de datos como "el producto más caro" o "el de mayor stock".

---

## 🧰 Tecnologías utilizadas

| Componente | Herramienta | Motivo |
|---|---|---|
| Lenguaje | **Python 3.12** | Ecosistema de IA |
| Modelo de lenguaje (LLM) | **Google Gemini** (`gemini-2.5-flash`) | Motor del agente y las respuestas |
| Lectura de PDF | **PyPDF** | Extraer texto de los documentos |
| Lectura de Excel | **Pandas + openpyxl** | Consultar el inventario |
| Embeddings | **FastEmbed** (`paraphrase-multilingual-MiniLM-L12-v2`) | Búsqueda semántica **local y gratuita**, en español |
| Búsqueda vectorial | **NumPy** (similitud del coseno) | Ligera, sin dependencias pesadas |
| Backend / Web | **FastAPI + Uvicorn** | API `/chat` y página de chat |
| Deploy | **Oracle Cloud Infrastructure (OCI Compute)** | Aplicación pública en la nube |

> Usa la **API gratuita** de Google Gemini y *embeddings* que corren en local, por
> lo que el proyecto funciona **sin costo**.

---

## 📁 Estructura del proyecto

```
alura-one-challenge/
├── app/
│   ├── config.py        # Rutas y parámetros
│   ├── ingest.py        # Lee PDF y construye el índice de embeddings
│   ├── retriever.py     # Búsqueda semántica (RAG)
│   ├── inventory.py     # Consultas sobre el inventario (Excel)
│   ├── agent.py         # Agente Gemini con 2 herramientas
│   ├── main.py          # API FastAPI + página de chat
│   └── templates/
│       └── index.html   # Interfaz de chat
├── data/
│   └── documents/       # 4 PDF + 1 Excel de Mercado Central 24h
├── requirements.txt
├── .env.example
└── README.md
```

---

## ▶️ Cómo ejecutar el proyecto en local

### 1. Requisitos
- Python 3.10 o superior
- Una clave gratuita de Google Gemini → [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)

### 2. Instalación
```bash
# Clonar el repositorio
git clone https://github.com/bianca-zorio/alura-one-challenge.git
cd alura-one-challenge

# Crear entorno virtual e instalar dependencias
python -m venv .venv
source .venv/bin/activate        # En Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configurar la clave
```bash
cp .env.example .env
# Edita .env y coloca tu GOOGLE_API_KEY
```

### 4. Construir el índice (una sola vez)
```bash
python -m app.ingest
```

### 5. Levantar el servidor
```bash
uvicorn app.main:app --reload
```
Abre **http://localhost:8000** y empieza a preguntar. 🎉

---

## 💬 Ejemplos de preguntas y respuestas

> **P:** ¿Cuál es el producto con más stock?
> **R:** El producto con mayor stock es la *Cerveza Clara Lata 355ml* (marca Corona),
> con 500 unidades disponibles, junto con la *Leche UHT Entera 1L* (Lala) y el
> *Lavaplatos Líquido Neutro 500ml* (Salvo), también con 500 unidades.
> *(Fuente: inventario_supermercado.xlsx)*

> **P:** ¿Cómo funciona la política de devoluciones?
> **R:** Según la política de atención al cliente, las devoluciones se rigen por el
> marco legal aplicable y contemplan cambios estándar y reembolsos según el caso…
> *(Fuente: politica_atencion_devoluciones.pdf)*

> **P:** ¿Qué productos hay de la categoría Abarrotes?
> **R:** En Abarrotes hay productos como Arroz Blanco Tipo 1 5kg (Verde Valle),
> Arroz Parbolizado 5kg (Goya)… *(Fuente: inventario_supermercado.xlsx)*

> **P:** ¿El supermercado atiende las 24 horas?
> **R:** Sí, Mercado Central 24h es un supermercado de operación continua (24/7)…
> *(Fuente: preguntas_frecuentes_faq.pdf)*

---

## ☁️ Deploy en Oracle Cloud (OCI)

La aplicación se despliega en una instancia **OCI Compute** (capa *Always Free*).

**Pasos resumidos:**
1. Crear una VM en OCI (se recomienda la forma **Ampere A1** — ARM, con RAM
   suficiente para el modelo de embeddings) con Ubuntu.
2. Abrir el puerto de la aplicación en la *Security List* / *NSG*.
3. Instalar dependencias, clonar el repositorio y crear el `.env` con la clave.
4. Construir el índice y levantar el servidor:
   ```bash
   python -m app.ingest
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

**Evidencia del deploy:**
- 🔗 Enlace público: _(se completará tras el despliegue)_
- 🖼️ Captura de pantalla: _(se agregará en `docs/`)_

---

## 📌 Notas
- Los documentos usados son de ejemplo, provistos por el challenge, y pueden
  sustituirse por cualquier PDF/CSV colocándolos en `data/documents/` y volviendo
  a ejecutar `python -m app.ingest`.
- El índice de embeddings (`data/index/`) se genera localmente y no se versiona.
