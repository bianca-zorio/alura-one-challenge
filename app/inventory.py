"""Herramienta de inventario: consultas estructuradas sobre el Excel de
productos (filtrar, ordenar, buscar). Responde preguntas de datos como
'¿cuál es el producto con más stock?' o '¿qué productos hay de la marca X?'.
"""
from __future__ import annotations

import functools

import pandas as pd

from app import config

# Nombres "amigables" que el agente puede pedir -> columna real del Excel.
COLUMNAS_ORDEN = {
    "stock_actual": "Stock Actual",
    "precio": "Precio de Venta Unitario",
    "costo": "Costo Unitario",
    "vencimiento": "Fecha de Vencimiento",
    "stock_minimo": "Stock Mínimo",
}

# Columnas donde se busca texto libre.
COLUMNAS_BUSQUEDA = ["Descripción", "Marca", "Categoría", "Subcategoría", "Proveedor Principal"]

# Columnas que se muestran en cada resultado.
COLUMNAS_SALIDA = [
    "SKU", "Descripción", "Marca", "Categoría",
    "Stock Actual", "Precio de Venta Unitario", "Proveedor Principal", "Fecha de Vencimiento",
]


@functools.lru_cache(maxsize=1)
def _df() -> pd.DataFrame:
    """Carga el inventario una sola vez (en caché)."""
    df = pd.read_excel(config.INVENTORY_FILE)
    df.columns = [str(c).strip() for c in df.columns]
    return df


def consultar(
    busqueda: str | None = None,
    categoria: str | None = None,
    marca: str | None = None,
    proveedor: str | None = None,
    ordenar_por: str | None = None,
    orden: str = "desc",
    limite: int = 5,
) -> str:
    """Filtra y ordena el inventario, devolviendo el resultado como texto."""
    df = _df().copy()

    if busqueda:
        mascara = pd.Series(False, index=df.index)
        for col in COLUMNAS_BUSQUEDA:
            if col in df.columns:
                mascara |= df[col].astype(str).str.contains(busqueda, case=False, na=False)
        df = df[mascara]
    if categoria:
        df = df[df["Categoría"].astype(str).str.contains(categoria, case=False, na=False)]
    if marca:
        df = df[df["Marca"].astype(str).str.contains(marca, case=False, na=False)]
    if proveedor:
        df = df[df["Proveedor Principal"].astype(str).str.contains(proveedor, case=False, na=False)]

    if ordenar_por:
        col = COLUMNAS_ORDEN.get(ordenar_por)
        if col and col in df.columns:
            df = df.sort_values(col, ascending=(orden == "asc"))

    limite = max(1, min(int(limite), 25))
    df = df.head(limite)

    if df.empty:
        return "No se encontraron productos que cumplan esos criterios en el inventario."

    columnas = [c for c in COLUMNAS_SALIDA if c in df.columns]
    filas = []
    for _, fila in df[columnas].iterrows():
        filas.append(" | ".join(f"{c}: {fila[c]}" for c in columnas))
    return f"{len(filas)} producto(s) encontrado(s):\n" + "\n".join(filas)


def resumen() -> str:
    """Devuelve un resumen general del inventario (para contexto)."""
    df = _df()
    return (
        f"El inventario tiene {len(df)} productos. "
        f"Categorías: {', '.join(sorted(df['Categoría'].dropna().unique())[:15])}."
    )
