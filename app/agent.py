"""El agente de IA: usa Google Gemini con dos herramientas para responder
preguntas sobre Mercado Central 24h.

  1. buscar_en_documentos  -> RAG semántico sobre los PDF (políticas, FAQ, etc.)
  2. consultar_inventario  -> consultas estructuradas sobre el Excel de productos

Implementa un "bucle de herramientas" manual: Gemini pide una herramienta,
nosotros la ejecutamos y le devolvemos el resultado; se repite hasta que redacta
la respuesta. En la última ronda se le quitan las herramientas para forzar el
cierre y garantizar siempre una respuesta.
"""
from __future__ import annotations

import time

from google import genai
from google.genai import errors as genai_errors
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
- Para preguntas de "el que más/menos ..." (mayor stock, más caro, etc.), usa \
"consultar_inventario" con el parámetro "ordenar_por".
- Normalmente basta con UNA o DOS llamadas a las herramientas. En cuanto tengas \
información suficiente, redacta la respuesta.
- No inventes datos. Si la información no está en los documentos ni en el \
inventario, dilo con honestidad.
- Cuando uses datos del inventario o citas de un documento, menciónalo brevemente.
"""

# Declaración de las herramientas que Gemini puede pedir (nombre, descripción y
# parámetros). Es el "contrato" que el modelo lee para saber cómo llamarlas.
HERRAMIENTAS = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="buscar_en_documentos",
            description=(
                "Busca información en los documentos internos de Mercado Central 24h: "
                "políticas, preguntas frecuentes, reglamento interno y manual de "
                "proveedores. Úsala para normas, devoluciones, atención al cliente, "
                "horarios, procedimientos o condiciones de compra."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "consulta": types.Schema(
                        type=types.Type.STRING,
                        description="La pregunta o tema a buscar en los documentos.",
                    )
                },
                required=["consulta"],
            ),
        ),
        types.FunctionDeclaration(
            name="consultar_inventario",
            description=(
                "Consulta el inventario de 200 productos del supermercado. Úsala para "
                "stock, precios, marcas, categorías, proveedores o vencimientos. "
                "Permite filtrar, buscar y ordenar."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "busqueda": types.Schema(type=types.Type.STRING, description="Texto a buscar en descripción, marca o categoría."),
                    "categoria": types.Schema(type=types.Type.STRING, description="Filtra por categoría (ej. Abarrotes, Bebidas)."),
                    "marca": types.Schema(type=types.Type.STRING, description="Filtra por marca."),
                    "proveedor": types.Schema(type=types.Type.STRING, description="Filtra por proveedor principal."),
                    "ordenar_por": types.Schema(
                        type=types.Type.STRING,
                        enum=["stock_actual", "precio", "costo", "vencimiento", "stock_minimo"],
                        description="Columna por la que ordenar los resultados.",
                    ),
                    "orden": types.Schema(type=types.Type.STRING, enum=["asc", "desc"], description="asc (menor a mayor) o desc (mayor a menor)."),
                    "limite": types.Schema(type=types.Type.INTEGER, description="Cantidad de productos a devolver (1-25)."),
                },
            ),
        ),
    ]
)

MAX_RONDAS = 4  # rondas de conversación con el modelo (incluye la de cierre)


def _segundos_de_espera(error: genai_errors.ClientError) -> float:
    """Lee cuántos segundos pide esperar Gemini en un error 429 (por defecto 20)."""
    try:
        for d in (error.details or {}).get("error", {}).get("details", []):
            if "retryDelay" in d:
                return min(float(str(d["retryDelay"]).rstrip("s")) + 1, 35)
    except (ValueError, AttributeError):
        pass
    return 20.0


class Agente:
    def __init__(self) -> None:
        if not config.GOOGLE_API_KEY:
            raise RuntimeError(
                "Falta GOOGLE_API_KEY. Copia .env.example a .env y añade tu clave "
                "de Google AI Studio (https://aistudio.google.com/app/apikey)."
            )
        self.cliente = genai.Client(api_key=config.GOOGLE_API_KEY)
        self.recuperador = Recuperador()

    def _ejecutar(self, nombre: str, args: dict, fuentes: set[str]) -> str:
        """Ejecuta la herramienta pedida por Gemini y devuelve su resultado."""
        if nombre == "buscar_en_documentos":
            resultados = self.recuperador.buscar(args.get("consulta", ""))
            for r in resultados:
                fuentes.add(r["fuente"])
            return "\n\n---\n\n".join(
                f"[Fuente: {r['fuente']}]\n{r['texto']}" for r in resultados
            )
        if nombre == "consultar_inventario":
            fuentes.add("inventario_supermercado.xlsx")
            return inventory.consultar(
                busqueda=args.get("busqueda") or None,
                categoria=args.get("categoria") or None,
                marca=args.get("marca") or None,
                proveedor=args.get("proveedor") or None,
                ordenar_por=args.get("ordenar_por") or None,
                orden=args.get("orden") or "desc",
                limite=int(args.get("limite") or 5),
            )
        return f"Herramienta desconocida: {nombre}"

    def _generar(self, contents: list, cfg: types.GenerateContentConfig):
        """Llama a Gemini reintentando ante errores transitorios: 429 (límite de
        peticiones) y 500/503 (modelo saturado del lado de Google)."""
        for intento in range(4):
            try:
                return self.cliente.models.generate_content(
                    model=config.GOOGLE_MODEL, contents=contents, config=cfg
                )
            except genai_errors.APIError as e:
                codigo = getattr(e, "code", None)
                if codigo not in (429, 500, 503) or intento == 3:
                    raise
                # 429 dice cuánto esperar; para 500/503 usamos espera creciente.
                espera = _segundos_de_espera(e) if codigo == 429 else min(2 ** intento * 2, 20)
                time.sleep(espera)

    def _redactar_final(self, pregunta: str, contexto: list[str], fuentes: set[str]) -> dict:
        """Cierre limpio: sin herramientas ni historial de llamadas, solo la
        pregunta y la información ya recopilada. Garantiza una respuesta en texto."""
        prompt = (
            f"Pregunta: {pregunta}\n\n"
            "Información recopilada de las herramientas:\n"
            + "\n\n".join(contexto)
            + "\n\nCon esa información, responde la pregunta de forma clara y directa. "
            "Si no es suficiente, dilo con honestidad."
        )
        respuesta = self._generar(
            [types.Content(role="user", parts=[types.Part(text=prompt)])],
            types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
        )
        texto = (respuesta.text or "").strip()
        return {
            "respuesta": texto or "No encontré esa información en los documentos.",
            "fuentes": sorted(fuentes),
        }

    def responder(self, pregunta: str) -> dict:
        """Devuelve {'respuesta': str, 'fuentes': list[str]} para una pregunta.
        Si Gemini falla de forma transitoria (tras los reintentos), responde con
        un mensaje amable en vez de reventar."""
        try:
            return self._responder(pregunta)
        except genai_errors.APIError as e:
            codigo = getattr(e, "code", None)
            if codigo in (429, 500, 503):
                aviso = (
                    "El servicio de Gemini está saturado en este momento. "
                    "Espera unos segundos e inténtalo de nuevo."
                )
            else:
                aviso = "Ocurrió un error al procesar tu pregunta. Inténtalo de nuevo."
            return {"respuesta": aviso, "fuentes": []}

    def _responder(self, pregunta: str) -> dict:
        fuentes: set[str] = set()
        contexto: list[str] = []  # resultados acumulados de las herramientas
        contents: list = [types.Content(role="user", parts=[types.Part(text=pregunta)])]
        cfg_tools = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT, tools=[HERRAMIENTAS]
        )

        for _ in range(MAX_RONDAS):
            respuesta = self._generar(contents, cfg_tools)
            partes = respuesta.candidates[0].content.parts or []
            llamadas = [p.function_call for p in partes if getattr(p, "function_call", None)]

            if not llamadas:  # el modelo respondió con texto: terminamos
                texto = (respuesta.text or "").strip()
                if texto:
                    return {"respuesta": texto, "fuentes": sorted(fuentes)}
                break

            # Ejecutamos cada herramienta pedida y guardamos su resultado.
            contents.append(respuesta.candidates[0].content)
            resultados = []
            for llamada in llamadas:
                salida = self._ejecutar(llamada.name, dict(llamada.args or {}), fuentes)
                contexto.append(salida)
                resultados.append(
                    types.Part.from_function_response(
                        name=llamada.name, response={"result": salida}
                    )
                )
            contents.append(types.Content(role="user", parts=resultados))

        # Si el modelo no cerró por su cuenta, forzamos la redacción final.
        if contexto:
            return self._redactar_final(pregunta, contexto, fuentes)
        return {
            "respuesta": "No pude completar la respuesta. Intenta reformular la pregunta.",
            "fuentes": sorted(fuentes),
        }
