"""El agente de IA: usa Google Gemini con dos herramientas para responder
preguntas sobre Mercado Central 24h.

  1. buscar_en_documentos  -> RAG semántico sobre los PDF (políticas, FAQ, etc.)
  2. consultar_inventario  -> consultas estructuradas sobre el Excel de productos

Gemini decide qué herramienta usar según la pregunta. Usamos la "llamada
automática de funciones": el SDK ejecuta nuestras funciones cuando el modelo
las pide y repite hasta obtener la respuesta final.
"""
from __future__ import annotations

from google import genai
from google.genai import types

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


class Agente:
    def __init__(self) -> None:
        if not config.GOOGLE_API_KEY:
            raise RuntimeError(
                "Falta GOOGLE_API_KEY. Copia .env.example a .env y añade tu clave "
                "de Google AI Studio (https://aistudio.google.com/app/apikey)."
            )
        self.cliente = genai.Client(api_key=config.GOOGLE_API_KEY)
        self.recuperador = Recuperador()

    def responder(self, pregunta: str) -> dict:
        """Devuelve {'respuesta': str, 'fuentes': list[str]} para una pregunta."""
        fuentes: set[str] = set()

        # Las herramientas son funciones locales que "recuerdan" las fuentes
        # usadas (guardándolas en el conjunto 'fuentes').
        def buscar_en_documentos(consulta: str) -> str:
            """Busca información en los documentos internos de Mercado Central 24h:
            políticas, preguntas frecuentes, reglamento interno y manual de
            proveedores. Úsala para preguntas sobre normas, devoluciones, atención
            al cliente, horarios, procedimientos o condiciones de compra.

            Args:
                consulta: La pregunta o tema a buscar en los documentos.
            """
            resultados = self.recuperador.buscar(consulta)
            for r in resultados:
                fuentes.add(r["fuente"])
            return "\n\n---\n\n".join(
                f"[Fuente: {r['fuente']}]\n{r['texto']}" for r in resultados
            )

        def consultar_inventario(
            busqueda: str = "",
            categoria: str = "",
            marca: str = "",
            proveedor: str = "",
            ordenar_por: str = "",
            orden: str = "desc",
            limite: int = 5,
        ) -> str:
            """Consulta el inventario de productos del supermercado (200 productos).
            Úsala para preguntas sobre stock, precios, marcas, categorías,
            proveedores o vencimientos.

            Args:
                busqueda: Texto a buscar en descripción, marca o categoría.
                categoria: Filtra por categoría (por ejemplo "Abarrotes").
                marca: Filtra por marca.
                proveedor: Filtra por proveedor principal.
                ordenar_por: Columna para ordenar. Valores válidos: "stock_actual",
                    "precio", "costo", "vencimiento", "stock_minimo".
                orden: "asc" (menor a mayor) o "desc" (mayor a menor).
                limite: Cantidad de productos a devolver (1 a 25).
            """
            fuentes.add("inventario_supermercado.xlsx")
            return inventory.consultar(
                busqueda=busqueda or None,
                categoria=categoria or None,
                marca=marca or None,
                proveedor=proveedor or None,
                ordenar_por=ordenar_por or None,
                orden=orden,
                limite=limite,
            )

        respuesta = self.cliente.models.generate_content(
            model=config.GOOGLE_MODEL,
            contents=pregunta,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                tools=[buscar_en_documentos, consultar_inventario],
            ),
        )

        texto = (respuesta.text or "").strip()
        if not texto:
            texto = "No pude generar una respuesta. Intenta reformular la pregunta."
        return {"respuesta": texto, "fuentes": sorted(fuentes)}
