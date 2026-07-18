"""El agente de IA: usa Claude (Anthropic) con dos herramientas para responder
preguntas sobre Mercado Central 24h.

  1. buscar_en_documentos  -> RAG semántico sobre los PDF (políticas, FAQ, etc.)
  2. consultar_inventario  -> consultas estructuradas sobre el Excel de productos

Claude decide qué herramienta usar según la pregunta (bucle de "tool use").
"""
from __future__ import annotations

import anthropic

from app import config, inventory
from app.retriever import Recuperador

SYSTEM_PROMPT = """Eres el asistente interno de "Mercado Central 24h", un \
supermercado de operación continua (24/7). Ayudas a las personas colaboradoras \
a encontrar información en la documentación de la empresa.

Reglas:
- Responde SIEMPRE en español, de forma clara y directa.
- Usa las herramientas disponibles para fundamentar tus respuestas:
    * "buscar_en_documentos" para políticas, FAQ, reglamento interno y proveedores.
    * "consultar_inventario" para preguntas sobre productos, stock, precios y marcas.
- No inventes datos. Si la información no está en los documentos ni en el \
inventario, dilo con honestidad.
- Cuando uses datos del inventario o citas de un documento, menciónalo brevemente.
"""

TOOLS = [
    {
        "name": "buscar_en_documentos",
        "description": (
            "Busca información en los documentos de políticas, preguntas frecuentes, "
            "reglamento interno y manual de proveedores de Mercado Central 24h. "
            "Úsala para preguntas sobre normas, devoluciones, atención al cliente, "
            "horarios, procedimientos, condiciones de compra, etc."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "consulta": {
                    "type": "string",
                    "description": "La pregunta o tema a buscar en los documentos.",
                }
            },
            "required": ["consulta"],
        },
    },
    {
        "name": "consultar_inventario",
        "description": (
            "Consulta el inventario de productos del supermercado (200 productos). "
            "Úsala para preguntas sobre stock, precios, marcas, categorías, "
            "proveedores o vencimientos. Puedes filtrar, buscar y ordenar."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "busqueda": {"type": "string", "description": "Texto a buscar en descripción, marca o categoría."},
                "categoria": {"type": "string", "description": "Filtra por categoría (ej. Abarrotes)."},
                "marca": {"type": "string", "description": "Filtra por marca."},
                "proveedor": {"type": "string", "description": "Filtra por proveedor principal."},
                "ordenar_por": {
                    "type": "string",
                    "enum": ["stock_actual", "precio", "costo", "vencimiento", "stock_minimo"],
                    "description": "Columna por la que ordenar los resultados.",
                },
                "orden": {"type": "string", "enum": ["asc", "desc"], "description": "asc (menor a mayor) o desc (mayor a menor)."},
                "limite": {"type": "integer", "description": "Cantidad de productos a devolver (1-25)."},
            },
        },
    },
]


class Agente:
    def __init__(self) -> None:
        if not config.ANTHROPIC_API_KEY:
            raise RuntimeError(
                "Falta ANTHROPIC_API_KEY. Copia .env.example a .env y añade tu clave."
            )
        self.cliente = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        self.recuperador = Recuperador()

    def _ejecutar_herramienta(self, nombre: str, args: dict, fuentes: set[str]) -> str:
        """Ejecuta la herramienta pedida por Claude y devuelve el resultado."""
        if nombre == "buscar_en_documentos":
            resultados = self.recuperador.buscar(args["consulta"])
            for r in resultados:
                fuentes.add(r["fuente"])
            return "\n\n---\n\n".join(
                f"[Fuente: {r['fuente']}]\n{r['texto']}" for r in resultados
            )
        if nombre == "consultar_inventario":
            fuentes.add("inventario_supermercado.xlsx")
            return inventory.consultar(**args)
        return f"Herramienta desconocida: {nombre}"

    def responder(self, pregunta: str) -> dict:
        """Devuelve {'respuesta': str, 'fuentes': list[str]} para una pregunta."""
        mensajes = [{"role": "user", "content": pregunta}]
        fuentes: set[str] = set()

        for _ in range(6):  # límite de iteraciones de seguridad
            respuesta = self.cliente.messages.create(
                model=config.ANTHROPIC_MODEL,
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=mensajes,
            )

            if respuesta.stop_reason != "tool_use":
                texto = "".join(b.text for b in respuesta.content if b.type == "text")
                return {"respuesta": texto.strip(), "fuentes": sorted(fuentes)}

            mensajes.append({"role": "assistant", "content": respuesta.content})
            resultados = []
            for bloque in respuesta.content:
                if bloque.type == "tool_use":
                    salida = self._ejecutar_herramienta(bloque.name, bloque.input, fuentes)
                    resultados.append({
                        "type": "tool_result",
                        "tool_use_id": bloque.id,
                        "content": salida,
                    })
            mensajes.append({"role": "user", "content": resultados})

        return {
            "respuesta": "No pude completar la respuesta. Intenta reformular la pregunta.",
            "fuentes": sorted(fuentes),
        }
