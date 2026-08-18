# -*- coding: utf-8 -*-
"""s324g — El margen contra el tope de 1.000 filas de PostgREST (TECH_DEBT #91 E).

QUÉ VIGILA. Varias consultas de serving piden `limit=5000` y **PostgREST devuelve
como mucho 1.000**. Hoy eso no muerde porque ningún modelo ni fichero se acerca:
el mayor, `ID3000`, tiene 665 filas. Pero eso es **una foto, no un invariante**
—lo señaló Fable en el dúo r39— y el día que un modelo cruce el tope, el efecto
NO será un error: será que `_get_source_files_for_model` cuente mal qué fuentes
ganan los slots del diversify. **Un sesgo silencioso en el orden de lo servido.**

POR QUÉ UN TEST Y NO UN ARREGLO. Paginar esas consultas es lo correcto y está
anotado; pero hacerlo hoy toca el camino caliente del retrieval sin ninguna
ganancia medible, y este proyecto no cambia serving sin medir delta. Este test es
el trinquete que convierte «hoy no pasa» en «me entero antes de que pase».

CÓMO SE COMPORTA. Es un test de DATOS: necesita la base. Si no hay credenciales
—CI limpio, portátil sin `.env`— se salta declarándolo, en vez de fallar por algo
que no es el código.
"""
from __future__ import annotations

import os
from collections import Counter

import pytest

#: El tope real del servidor, no el que pide el cliente.
MAX_ROWS_POSTGREST = 1000

#: A partir de aquí, avisa. 800 = 80 % del tope: deja margen para reaccionar
#: (paginar) antes de que el sesgo empiece, en vez de enterarse al cruzarlo.
UMBRAL_AVISO = 800


def _filas():
    import httpx

    # La suite corre SIN RED por contrato (ver `conftest.py`), así que las
    # credenciales no están en el entorno de pytest. Se cargan del `.env` sólo
    # si existe: en un portátil con el proyecto configurado, este test CORRE y
    # avisa; en CI no hay `.env` y se salta declarándolo. Así el trinquete es
    # útil donde puede serlo y no convierte la suite en dependiente de la red.
    try:
        from dotenv import load_dotenv
        load_dotenv(".env")
    except Exception:                                        # noqa: BLE001
        pass

    url = (os.environ.get("SUPABASE_URL") or "").rstrip("/")
    key = os.environ.get("SUPABASE_SERVICE_KEY") or ""
    if not url or not key:
        pytest.skip("sin credenciales de Supabase: este test mide DATOS, no código")
    tabla = os.environ.get("CHUNKS_TABLE", "chunks_v2")
    cab = {"apikey": key, "Authorization": f"Bearer {key}"}
    pm, sf = Counter(), Counter()
    off = 0
    while True:
        r = httpx.get(
            f"{url}/rest/v1/{tabla}",
            params={"select": "product_model,source_file", "order": "id.asc",
                    "limit": "1000", "offset": str(off)},
            headers=cab, timeout=120,
        )
        if r.status_code != 200:
            pytest.skip(f"la base no responde ({r.status_code})")
        filas = r.json()
        if not filas:
            break
        for f in filas:
            pm[f.get("product_model")] += 1
            sf[f.get("source_file")] += 1
        off += 1000
        if off > 200_000:                     # cota de seguridad del propio test
            break
    return pm, sf


def test_ningun_modelo_ni_fichero_se_acerca_al_tope():
    """Si esto se pone rojo, hay que PAGINAR `_get_source_files_for_model` y
    `_get_pm_for_sources` antes de que el conteo empiece a mentir."""
    pm, sf = _filas()
    if not pm:
        pytest.skip("tabla vacía")

    modelo, n_modelo = pm.most_common(1)[0]
    fichero, n_fichero = sf.most_common(1)[0]

    assert n_modelo < UMBRAL_AVISO, (
        f"el modelo {modelo!r} tiene {n_modelo} chunks y el tope de PostgREST son "
        f"{MAX_ROWS_POSTGREST}. Las consultas que piden limit=5000 filtrando por "
        f"modelo van a empezar a TRUNCARSE, y el efecto no es un error: es que el "
        f"conteo por `source_file` que ordena el diversify quede sesgado EN "
        f"SILENCIO. Toca paginarlas (TECH_DEBT #91 E)."
    )
    assert n_fichero < UMBRAL_AVISO, (
        f"el fichero {fichero!r} tiene {n_fichero} chunks; mismo motivo que arriba "
        f"para `_get_pm_for_sources`."
    )
