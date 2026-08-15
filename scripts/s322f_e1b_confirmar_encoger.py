# -*- coding: utf-8 -*-
"""s322f — Encoger el lote «confirmar» del QA E1b (359 candidates atestados).

QUÉ RESUELVE
------------
`evals/s320_e1b_candidates_preclasificacion_v1.json` clasificó 620 candidates del
catálogo en tres lotes. El lote «confirmar» (359 filas) se ganó ese nombre con UN
solo criterio: `COUNT(*) de chunks_v2 WHERE content ilike '*MODELO*' >= 3`.

Ese criterio tiene un agujero que hace que el «sí en bloque» sea un acto de fe:
`ilike` es SUBCADENA SIN FRONTERAS. Un candidato «CAD-250B» cuenta 5 menciones
aunque las cinco vivan dentro de «CAD-250BLED»; «DS 5» cuenta menciones dentro de
«LEDS 5 zonas»; «APIC» cuenta menciones dentro de «APIC-ELE». La atestación puede
ser 100 % parásita y el conteo no lo distingue.

Este script convierte ese lote en algo AUDITABLE y BARATO, priorizando lo
determinista (el LLM solo donde el determinismo no llega):

  (A) REFRESCA hoy el conteo `ilike` de cada modelo contra `chunks_v2` — mismo
      método que s320, para que la cifra sea comparable y se vea la deriva.
  (B) EXTRAE, sin LLM, la evidencia real: descarga hasta N chunks que mencionan
      el término, localiza CADA ocurrencia, la expande al TOKEN TÉCNICO completo
      que la contiene y decide si la mención es EXACTA (el token es el modelo) o
      PARÁSITA (el token es más largo: el modelo solo es una subcadena). De la
      primera mención exacta saca un fragmento de contexto verbatim: eso es lo
      que permite a Alberto auditar el bloque de un vistazo.
  (C) LLAMA a `claude-fable-5` SOLO en el residuo: filas con 0-1 menciones
      exactas hoy, o modelos con forma sospechosa de artefacto de extracción
      (unidades/normas/medidas — «82 mm» → «MM-82» —, ficheros, acrónimos sin
      dígitos, frases multipalabra). Salida JSON estricta, cita verbatim y
      VERIFICACIÓN A TEXTO COMPLETO de la cita.

REGLA SUPREMA: este script NO APLICA NADA. No escribe en `data/catalog/*.jsonl`,
ni en Supabase (solo GET), ni en el snapshot del detector. Su único output es un
recibo JSON en `evals/`. Todo es una PROPUESTA para que Alberto adjudique.

POR QUÉ LA ATESTACIÓN VA CONTRA `content` Y NUNCA CONTRA `product_model`
-----------------------------------------------------------------------
Regla heredada de s320 (r22): estos candidates NACIERON del bulk s83/s91, que se
alimentó de metadata. Usar `product_model` como prueba sería circular: el
candidato se confirmaría a sí mismo. La metadata se REPORTA como corroboración
auxiliar (`corrobora_product_model`) pero NUNCA entra en la puerta del bloque.

CRITERIO DE SALIDA
------------------
- «bloque»  → veredicto claro, evidencia verificada, sin ambigüedad estructural.
              Alberto los aprueba con UN solo sí.
- «individual» → el residuo real, con toda la evidencia junta para decidir rápido.

La puerta del bloque (todas, sin excepción):
  1. sigue atestado hoy: `n_ilike_hoy >= 3` (mismo umbral que s320);
  2. `n_chunks_token_exacto >= 2` — al menos DOS chunks distintos donde el modelo
     aparece como token completo, no como subcadena de otro token;
  3. sin banderas léxicas de artefacto (ver `_banderas_lexicas`);
  4. fragmento de evidencia extraído de contenido real (no derivado, no resumido).
  Un residuo puede entrar al bloque por la vía LLM SOLO si el veredicto es
  «confirmar» + confianza «alta» + cita VERIFICADA a texto completo.

Jamás se aproxima un veredicto para engordar el bloque: lo que no decide la
evidencia va a individual y punto.

USO
---
    python scripts/s322f_e1b_confirmar_encoger.py --limite 12   # smoke barato
    python scripts/s322f_e1b_confirmar_encoger.py               # pasada completa
    python scripts/s322f_e1b_confirmar_encoger.py --sin-llm     # solo fase A+B
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# La consola de Windows llega en cp1252 y revienta con «→» o «·». El recibo va
# en UTF-8 pase lo que pase; lo que se degrada es solo la traza por pantalla.
for _flujo in (sys.stdout, sys.stderr):
    try:
        _flujo.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=False)

from src.http_pool import abierto  # noqa: E402
from src.rag.catalog_store import CATALOG_DIR, _read_jsonl, norm_token  # noqa: E402

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
KEY = os.environ["SUPABASE_SERVICE_KEY"]
H = {"apikey": KEY, "Authorization": f"Bearer {KEY}"}

FUENTE = ROOT / "evals" / "s320_e1b_candidates_preclasificacion_v1.json"
SALIDA = ROOT / "evals" / "s322f_e1b_confirmar_encoger_v1.json"

MODELO_JUEZ = "claude-fable-5"
# LECCIÓN CARA: max_tokens=400 TRUNCA el JSON del modelo y produce «parse-fail»
# que parecen incertidumbre pero son un fallo de NUESTRO lado. Se subió a 1000 y
# aun así 1 de 192 llamadas cortó con stop_reason=max_tokens (una `razon` larga)
# → 1500 + se acota la `razon` en el prompt. El `stop_reason` se registra en el
# recibo justo para que este fallo sea visible y no se disfrace de duda.
MAX_TOKENS = 1500
# El parámetro `temperature` está DEPRECADO en los modelos 2026 (error 400).
# No se pasa. Si algún día vuelve, se pasa aquí y no en 40 sitios.

UMBRAL_ILIKE = 3          # mismo umbral que s320 (comparabilidad)
UMBRAL_EXACTO = 2         # chunks distintos con mención de TOKEN COMPLETO
MUESTRA_DEFECTO = 40      # chunks descargados por modelo para el análisis
VENTANA = 110             # chars de contexto a cada lado del fragmento


# ---------------------------------------------------------------------------
# Léxico de sospecha
# ---------------------------------------------------------------------------
# Unidades y normas: el extractor que fabricó estos candidates confunde una
# medida con una referencia («82 mm» → «MM-82», «EN-54» → norma, no producto).
# Si la parte alfabética del modelo ES una unidad o una norma, el candidato es
# sospechoso de artefacto por CONSTRUCCIÓN, aunque el corpus lo mencione mil
# veces (¡lo menciona porque la unidad aparece en cada tabla de specs!).
UNIDADES_Y_NORMAS = {
    "MM", "CM", "M", "KM", "KG", "G", "MG", "V", "VDC", "VAC", "MV", "MA", "A",
    "MAH", "AH", "W", "KW", "MW", "VA", "KVA", "DB", "DBA", "HZ", "KHZ", "MHZ",
    "S", "MS", "H", "MIN", "SEC", "NM", "UM", "PSI", "BAR", "LPM", "LPS", "C",
    "F", "K", "PA", "KPA", "MPA", "LUX", "PPM", "M2", "M3", "L", "ML",
    "IP", "IK", "EN", "UNE", "ISO", "IEC", "NFPA", "UL", "FM", "CPR", "CE",
    "AWG", "DIN", "VDE", "NF", "BS", "AS", "GB", "RAL",
}

# Palabras genéricas: si el «modelo» ES una palabra común (es/en) no es una
# referencia comercial, es ruido de extracción. Lista corta y conservadora: solo
# marca (ruta al LLM), nunca decide sola.
PALABRAS_GENERICAS = {
    "ADAPTADOR", "ADAPTER", "MODULE", "MODULO", "PANEL", "SYSTEM", "SISTEMA",
    "SERIE", "SERIES", "DISPLAY", "STANDARD", "TIPO", "TYPE", "VIEW", "DUST",
    "OMNI", "NAS", "TMP", "DIA", "LIB", "APP", "TEST", "BOX", "KIT", "PLUS",
    "SMART", "VISION", "SENSOR", "DETECTOR", "CENTRAL", "BASE", "CABLE",
}

EXT_FICHERO = re.compile(r"\.(exe|dll|pdf|zip|msi|jpg|png|xls|xlsx|doc|docx)$",
                         re.IGNORECASE)


# ---------------------------------------------------------------------------
# Utilidades deterministas
# ---------------------------------------------------------------------------
def _pdf_escape(term: str) -> str:
    """Escapa los comodines de `ilike` de PostgREST. IDÉNTICO al de s320 para
    que el conteo refrescado sea COMPARABLE con el de la preclasificación."""
    return term.replace("%", r"\%").replace("_", r"\_").replace("*", "")


def _get(client, url: str, *, headers: dict, params: dict, intentos: int = 4):
    """GET con reintento sobre 5xx y errores de red.

    POR QUÉ (medido, pasada del 15-ago): el COUNT `ilike` sobre `chunks_v2` es un
    seq-scan; con 10 hilos en paralelo Supabase devolvió **HTTP 500 (statement
    timeout) en 56 de 359 filas**. Sin reintento, esas 56 salían con
    `n_ilike_hoy = 0` y el recibo las presentaba como «perdieron atestación
    hoy» — un hallazgo FALSO fabricado por nuestra propia concurrencia. La
    diferencia entre «no atestado» y «no medido» es justo lo que hace o rompe la
    confianza del bloque, así que el reintento no es cosmética: es corrección.

    Solo se reintentan GET (idempotentes). Backoff creciente para dar aire al
    planificador; el fallo definitivo se DECLARA en la fila, nunca se silencia.
    """
    ultimo = None
    for k in range(intentos):
        try:
            r = client.get(url, headers=headers, params=params)
            if r.status_code < 500:
                return r, None
            ultimo = f"HTTP {r.status_code}"
        except Exception as exc:
            ultimo = f"{type(exc).__name__}: {exc}"
        if k < intentos - 1:
            time.sleep(1.5 * (k + 1))
    return None, ultimo


def _norm_ws(t: str) -> str:
    """Normalización de espacios para verificar citas: el mismo texto puede venir
    con saltos de línea de tabla markdown o con espacios simples."""
    return re.sub(r"\s+", " ", t.lower()).strip()


# Caracteres que forman parte de un «token técnico» (referencia comercial):
# alfanuméricos y los separadores internos - _ /. El PUNTO se deja FUERA de la
# expansión a propósito: si no, «CAD-250B.El siguiente» expandiría a
# «CAD-250B.El» y una mención legítima al final de una frase se contaría como
# parásita (falso negativo). El punto interno del propio modelo (ITAC 2.0,
# RHistorico.exe) sí se respeta porque va dentro del texto BUSCADO.
_ALNUM = re.compile(r"[A-Za-z0-9]")
_SEP_TOKEN = "-_/"


def _expandir_token(texto: str, ini: int, fin: int) -> str:
    """Expande [ini,fin) al token técnico máximo que lo contiene.

    POR QUÉ: es la prueba precisa de si la mención ATESTA el modelo o solo lo
    contiene. «CAD-250B» dentro de «CAD-250BLED» no atesta «CAD-250B»; «DS 5»
    dentro de «LEDS 5» no atesta «DS 5». Comparar el token completo (normalizado
    con la MISMA `norm_token` del catálogo, que ignora may/min, acentos y
    separadores) es la diferencia entre evidencia y coincidencia.
    """
    i = ini
    while i > 0:
        ch = texto[i - 1]
        if _ALNUM.match(ch):
            i -= 1
        elif ch in _SEP_TOKEN and i - 2 >= 0 and _ALNUM.match(texto[i - 2]):
            i -= 1
        else:
            break
    j = fin
    n = len(texto)
    while j < n:
        ch = texto[j]
        if _ALNUM.match(ch):
            j += 1
        elif ch in _SEP_TOKEN and j + 1 < n and _ALNUM.match(texto[j + 1]):
            j += 1
        else:
            break
    return texto[i:j]


def _analizar_chunk(contenido: str, modelo: str) -> tuple[bool, list[str], int]:
    """Clasifica TODAS las ocurrencias del modelo en un chunk.

    Devuelve (tiene_mencion_exacta, tokens_parasitos, offset_primera_exacta).
    """
    bajo = contenido.lower()
    buscado = modelo.lower()
    objetivo = norm_token(modelo)
    pos, exacta_en = 0, -1
    parasitos: list[str] = []
    while True:
        k = bajo.find(buscado, pos)
        if k < 0:
            break
        token = _expandir_token(contenido, k, k + len(buscado))
        if norm_token(token) == objetivo:
            if exacta_en < 0:
                exacta_en = k
        else:
            parasitos.append(token)
        pos = k + 1
    return exacta_en >= 0, parasitos, exacta_en


def _fragmento(contenido: str, offset: int, largo: int) -> str:
    """Ventana de contexto real alrededor de la mención (verbatim, solo se
    colapsan espacios para que quepa de un vistazo en el recibo)."""
    ini = max(0, offset - VENTANA)
    fin = min(len(contenido), offset + largo + VENTANA)
    trozo = contenido[ini:fin]
    trozo = re.sub(r"\s+", " ", trozo).strip()
    return ("…" if ini > 0 else "") + trozo + ("…" if fin < len(contenido) else "")


def _banderas_lexicas(modelo: str) -> list[str]:
    """Sospechas que se ven SIN tocar el corpus (forma del propio string).

    Cada bandera es una clase de fallo ya vista: no son manías. Una sola bandera
    saca la fila del bloque determinista y la manda al LLM — que puede
    devolverla al bloque si la evidencia es concluyente.
    """
    b: list[str] = []
    m = modelo.strip()
    mu = m.upper()
    if EXT_FICHERO.search(m):
        b.append("parece_fichero")          # «RHistorico.exe» no es un producto
    if not re.search(r"\d", m):
        b.append("sin_digitos")             # acrónimo/palabra, no referencia
    if len(re.sub(r"[^A-Za-z0-9]", "", m)) <= 4:
        b.append("muy_corto")               # alta colisión léxica
    if " " in m:
        b.append("multipalabra")            # riesgo de frase extraída, no de ref.
    # Parte alfabética = unidad o norma  →  artefacto de medida («82 mm»→«MM-82»)
    mm = re.match(r"^([A-Za-z]{1,4})[-_ ]?(\d{1,4})$", m)
    if mm and mm.group(1).upper() in UNIDADES_Y_NORMAS:
        b.append("unidad_o_norma")
    if mu in UNIDADES_Y_NORMAS:
        b.append("unidad_o_norma")
    if any(p == mu or p in mu.split() for p in PALABRAS_GENERICAS):
        b.append("palabra_generica")
    return sorted(set(b))


def _bandera_medida_en_contexto(modelo: str, fragmento: str) -> bool:
    """Segunda pasada de la sospecha de artefacto, ya CON el contexto real.

    Solo aplica a modelos con forma LETRAS+DÍGITOS «desnuda» (los que un
    extractor puede fabricar dando la vuelta a una medida). Si alrededor de la
    mención el texto es una tabla de medidas/normas y no hay marcas de
    referencia comercial, es candidato a artefacto.
    """
    if not re.match(r"^[A-Za-z]{1,3}[-_ ]?\d{1,4}$", modelo.strip()):
        return False
    f = fragmento.lower()
    unidades = len(re.findall(
        r"\d+\s*(?:mm|cm|m\b|kg|v\b|vdc|ma\b|db|hz|w\b|ah|ms|s\b|ºc|°c|%)", f))
    normas = len(re.findall(r"\b(?:en|une|iso|iec|nfpa)[\s-]?\d", f))
    return (unidades + normas) >= 3


# ---------------------------------------------------------------------------
# Fase A + B — cosecha determinista contra chunks_v2 (SOLO GET)
# ---------------------------------------------------------------------------
_impresas = [0]
_lock = threading.Lock()


def _cosechar(client, fila: dict, n_muestra: int, total: int) -> dict:
    modelo = (fila.get("modelo") or "").strip()
    out = {
        "id": fila.get("id"),
        "modelo": modelo,
        "n_ilike_s320": fila.get("chunks_con_mencion"),
        "n_ilike_hoy": 0,
        "muestra_descargada": 0,
        "muestra_es_censo": False,
        "n_chunks_token_exacto": 0,
        "n_chunks_solo_parasito": 0,
        "docs_distintos_con_exacta": 0,
        "parasitos_top": [],
        "evidencia": None,
        "evidencias_extra": [],
        "corrobora_product_model": False,
        "banderas": _banderas_lexicas(modelo),
        "error": None,
    }
    if not modelo:
        out["error"] = "modelo vacío"
        return out

    term = _pdf_escape(modelo)
    # (A) Conteo refrescado HOY, método idéntico al de s320 (comparabilidad).
    r, err = _get(client, f"{SUPABASE_URL}/rest/v1/chunks_v2",
                  headers={**H, "Prefer": "count=exact", "Range": "0-0"},
                  params={"select": "id", "content": f"ilike.*{term}*"})
    if r is None or r.status_code not in (200, 206):
        out["error"] = f"count {err or ('HTTP ' + str(r.status_code))}"
        out["n_ilike_hoy"] = None        # None = NO MEDIDO (≠ 0 = no atestado)
        return out
    out["n_ilike_hoy"] = int(r.headers.get("content-range", "/0").split("/")[-1])
    if out["n_ilike_hoy"] == 0:
        return out

    # (B) Muestra DIRIGIDA: no los primeros chunks del documento, sino los que
    # MENCIONAN el término — la evidencia vive en las tablas de modelos a mitad
    # de manual, no en la portada. `order=id` para que sea reproducible.
    r, err = _get(client, f"{SUPABASE_URL}/rest/v1/chunks_v2", headers=H,
                  params={"select": "id,document_id,content,product_model,"
                                    "manufacturer,section_title,page_number",
                          "content": f"ilike.*{term}*",
                          "order": "id", "limit": str(n_muestra)})
    if r is None or r.status_code not in (200, 206):
        out["error"] = f"muestra {err or ('HTTP ' + str(r.status_code))}"
        return out
    filas = r.json()

    out["muestra_descargada"] = len(filas)
    # Si el conteo cabe en la muestra, la muestra ES el censo: el análisis de
    # fronteras es EXACTO, no una estimación. Se declara en el recibo.
    out["muestra_es_censo"] = out["n_ilike_hoy"] <= len(filas)

    parasitos = Counter()
    docs_exactos = set()
    evidencias = []
    for ch in filas:
        cont = ch.get("content") or ""
        exacta, paras, off = _analizar_chunk(cont, modelo)
        for p in paras:
            parasitos[p] += 1
        if exacta:
            out["n_chunks_token_exacto"] += 1
            docs_exactos.add(ch.get("document_id"))
            if len(evidencias) < 3:
                evidencias.append({
                    "chunk_id": ch.get("id"),
                    "document_id": ch.get("document_id"),
                    "pagina": ch.get("page_number"),
                    "seccion": ch.get("section_title"),
                    "fragmento": _fragmento(cont, off, len(modelo)),
                })
        elif paras:
            out["n_chunks_solo_parasito"] += 1
        # Corroboración AUXILIAR (nunca puerta): metadata del chunk.
        if norm_token(str(ch.get("product_model") or "")) == norm_token(modelo):
            out["corrobora_product_model"] = True

    out["docs_distintos_con_exacta"] = len(docs_exactos)
    out["parasitos_top"] = [{"token": t, "n": n}
                            for t, n in parasitos.most_common(5)]
    if evidencias:
        out["evidencia"] = evidencias[0]
        out["evidencias_extra"] = evidencias[1:]
        if _bandera_medida_en_contexto(modelo, evidencias[0]["fragmento"]):
            out["banderas"] = sorted(set(out["banderas"] + ["medida_en_contexto"]))

    with _lock:
        _impresas[0] += 1
        if _impresas[0] % 25 == 0:
            print(f"  cosecha {_impresas[0]}/{total}…", flush=True)
    return out


def _metadatos_documentos(client, doc_ids: list[str]) -> dict:
    """Un lote de `documents` para poder enseñar a Alberto DE QUÉ MANUAL sale la
    evidencia (fabricante + fichero). Se pide en tandas con `in.()`."""
    meta: dict[str, dict] = {}
    ids = [d for d in dict.fromkeys(doc_ids) if d]
    for i in range(0, len(ids), 40):
        lote = ids[i:i + 40]
        try:
            r = client.get(
                f"{SUPABASE_URL}/rest/v1/documents",
                headers=H,
                params={"select": "id,manufacturer,product_model,doc_type,"
                                  "source_pdf_filename",
                        "id": "in.(" + ",".join(lote) + ")"})
            if r.status_code in (200, 206):
                for row in r.json():
                    meta[row["id"]] = row
        except Exception:
            continue
    return meta


# ---------------------------------------------------------------------------
# Cruce con el catálogo (SOLO LECTURA) — ¿el parásito ya es OTRO producto?
# ---------------------------------------------------------------------------
def _indice_catalogo() -> dict[str, str]:
    """norm_token -> id, de canónicos + alias. POR QUÉ: si las menciones de «X»
    viven todas dentro de «X-ELE» y «X-ELE» YA es un producto del catálogo, la
    atestación de «X» está explicada: es el otro producto quien la genera. Ese
    dato le ahorra a Alberto abrir el manual."""
    idx: dict[str, str] = {}
    for p in _read_jsonl(CATALOG_DIR / "products.jsonl"):
        cm = (p.get("canonical_model") or "").strip()
        if cm:
            idx.setdefault(norm_token(cm), p.get("id", ""))
    for a in _read_jsonl(CATALOG_DIR / "aliases.jsonl"):
        al = (a.get("alias") or "").strip()
        if al:
            idx.setdefault(norm_token(al), a.get("id", ""))
    return idx


# ---------------------------------------------------------------------------
# Fase C — juez LLM SOLO en el residuo
# ---------------------------------------------------------------------------
PROMPT = """Eres un auditor de catálogo de equipos de protección contra incendios (PCI).

Debes decidir si una REFERENCIA COMERCIAL candidata es un PRODUCTO REAL del
fabricante o un ARTEFACTO de extracción automática (una medida convertida en
referencia — «82 mm» → «MM-82» —, un nombre de norma, una palabra genérica, un
nombre de fichero, o un fragmento de otra referencia más larga).

CANDIDATO
  id de catálogo: {cid}
  modelo:         {modelo}
  menciones (subcadena) en el corpus hoy: {n_ilike}
  menciones donde el modelo es un TOKEN COMPLETO: {n_exacto} (de {n_muestra} chunks analizados)
  tokens más largos que lo contienen (posibles parásitos): {parasitos}
  señales de forma detectadas: {banderas}

EVIDENCIA REAL DEL CORPUS (fragmentos verbatim de manuales ya ingestados)
{evidencia}

TAREA
Responde SOLO con un objeto JSON válido, sin texto alrededor, sin markdown:
{{"veredicto": "confirmar" | "retirar" | "dudoso",
  "confianza": "alta" | "media" | "baja",
  "cita": "<máx 200 caracteres COPIADOS LITERALMENTE de la evidencia de arriba>",
  "razon": "<1-2 frases en español, MÁXIMO 300 caracteres>"}}

REGLAS
- "confirmar" = el modelo es una referencia comercial real del fabricante.
- "retirar"   = es un artefacto: no designa un producto.
- "dudoso"    = la evidencia no alcanza para ninguna de las dos.
- La "cita" debe existir PALABRA POR PALABRA en la evidencia mostrada. NO la
  parafrasees, NO la completes, NO la resumas. Si no puedes copiar una cita
  literal que sostenga tu veredicto, pon "cita": "" y confianza "baja".
- Confianza "alta" solo si la evidencia es inequívoca por sí sola."""


def _juzgar(cliente, fila: dict) -> dict:
    evs = ([fila["evidencia"]] + fila["evidencias_extra"]
           if fila.get("evidencia") else [])
    ev_txt = "\n".join(
        f"[{i + 1}] (doc {str(e.get('document_id') or '')[:8]}, "
        f"pág {e.get('pagina')}) {e['fragmento']}"
        for i, e in enumerate(evs))
    if not ev_txt:
        ev_txt = ("(sin ninguna mención como token completo: todas las "
                  "coincidencias son subcadenas de tokens más largos, o no hay "
                  "coincidencias)")
    prompt = PROMPT.format(
        cid=fila["id"], modelo=fila["modelo"], n_ilike=fila["n_ilike_hoy"],
        n_exacto=fila["n_chunks_token_exacto"],
        n_muestra=fila["muestra_descargada"],
        parasitos=", ".join(f"{p['token']}×{p['n']}"
                            for p in fila["parasitos_top"]) or "ninguno",
        banderas=", ".join(fila["banderas"]) or "ninguna",
        evidencia=ev_txt)
    # OJO: sin `temperature` (deprecado en 2026 → HTTP 400) y con max_tokens
    # holgado (400 truncaba el JSON y fabricaba «parse-fail» falsos).
    r = cliente.messages.create(
        model=MODELO_JUEZ, max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}])
    uso = {"in": getattr(r.usage, "input_tokens", 0),
           "out": getattr(r.usage, "output_tokens", 0),
           "stop": getattr(r, "stop_reason", None)}
    bruto = "".join(b.text for b in r.content if getattr(b, "type", "") == "text")
    m = re.search(r"\{.*\}", bruto, re.DOTALL)
    if not m:
        return {"veredicto": "dudoso", "confianza": "baja", "cita": "",
                "razon": f"parse-fail: sin JSON (stop={uso['stop']})",
                "_bruto": bruto[:300], "_uso": uso}
    try:
        d = json.loads(m.group(0))
    except json.JSONDecodeError as exc:
        return {"veredicto": "dudoso", "confianza": "baja", "cita": "",
                "razon": f"parse-fail: {exc} (stop={uso['stop']})",
                "_bruto": bruto[:300], "_uso": uso}
    d.setdefault("veredicto", "dudoso")
    d.setdefault("confianza", "baja")
    d.setdefault("cita", "")
    d.setdefault("razon", "")
    d["_uso"] = uso
    return d


def _verificar_cita(client, cita: str, textos: list[str],
                    doc_ids: list[str]) -> tuple[bool, str]:
    """VERIFICACIÓN A TEXTO COMPLETO de la cita ENTERA (hasta 200 chars).

    LECCIÓN CARA: verificar solo un prefijo de 50 chars dejó pasar una invención
    real — la COLA parafraseada por el modelo no estaba en el documento. Aquí se
    valida la cita completa contra (1) el contenido íntegro de los chunks de la
    muestra y, si falla, (2) el documento ENTERO reconstruido concatenando todos
    sus chunks. Normalizando espacios en ambos lados.
    """
    c = _norm_ws(cita)
    if len(c) < 8:
        return False, "cita vacía o demasiado corta"
    universo = _norm_ws(" \n ".join(textos))
    if c in universo:
        return True, "verificada en los fragmentos de evidencia mostrados"
    # Fallback CANÓNICO: el documento ENTERO, reconstruido concatenando TODOS
    # sus chunks en orden. Cubre el caso legítimo de que el modelo copiara texto
    # que quedaba fuera del recorte de ±110 chars que se le enseñó.
    for doc_id in [d for d in dict.fromkeys(doc_ids) if d]:
        try:
            r = client.get(f"{SUPABASE_URL}/rest/v1/chunks_v2", headers=H,
                           params={"select": "content,chunk_index",
                                   "document_id": f"eq.{doc_id}",
                                   "order": "chunk_index", "limit": "3000"})
            if r.status_code in (200, 206):
                doc = _norm_ws(" ".join((x.get("content") or "")
                                        for x in r.json()))
                if c in doc:
                    return True, f"verificada en el documento completo {doc_id[:8]}"
        except Exception as exc:
            return False, f"no verificable (error al leer el doc): {exc}"
    return False, "NO aparece literal en el corpus (posible paráfrasis)"


# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limite", type=int, default=0,
                    help="procesa solo las N primeras filas (smoke barato)")
    ap.add_argument("--muestra", type=int, default=MUESTRA_DEFECTO)
    ap.add_argument("--hilos", type=int, default=8)
    ap.add_argument("--sin-llm", action="store_true")
    ap.add_argument("--reintentar-errores", action="store_true",
                    help="reaprovecha el recibo de --salida y vuelve a medir "
                         "SOLO las filas que quedaron con error de red")
    ap.add_argument("--salida", default=str(SALIDA))
    args = ap.parse_args()

    t0 = time.time()
    fuente = json.loads(FUENTE.read_text(encoding="utf-8"))
    filas = fuente["detalle"]["confirmar"]
    if args.limite:
        filas = filas[:args.limite]

    destino = Path(args.salida)
    previas: dict[str, dict] = {}
    reintentos = 0
    if args.reintentar_errores:
        # MODO REINTENTO: reaprovecha un recibo anterior y vuelve a medir SOLO
        # las filas que quedaron sin medir (error de red). Evita repagar el
        # LLM de las 300 filas sanas y, sobre todo, evita dejar publicado un
        # «cayó la atestación» que en realidad era un timeout nuestro.
        prev = json.loads(destino.read_text(encoding="utf-8"))
        for r in prev["detalle"]["bloque"] + prev["detalle"]["individual"]:
            previas[r["id"]] = r
        pendientes = [f for f in filas if previas.get(f["id"], {}).get("error")]
        # Un «parse-fail» NO es una duda del juez: es una respuesta que nosotros
        # cortamos (max_tokens) o no supimos parsear. Se le retira el veredicto
        # para que se vuelva a juzgar; dejarlo como «dudoso» sería contar un
        # fallo propio como incertidumbre del modelo.
        repescadas = 0
        for r in previas.values():
            if "parse-fail" in str(r.get("por_que", "")):
                r.pop("veredicto", None)
                r.pop("ruta", None)
                repescadas += 1
        reintentos = len(pendientes)
        print(f"s322f · REINTENTO: {reintentos} filas sin medir + "
              f"{repescadas} parse-fail a rejuzgar (de {len(filas)} del lote)",
              flush=True)
        filas_a_cosechar = pendientes
    else:
        print(f"s322f · lote «confirmar» = {len(filas)} filas "
              f"(fuente {FUENTE.name}, utc {fuente['utc']})", flush=True)
        filas_a_cosechar = filas

    # --- Fase A+B: cosecha determinista -----------------------------------
    with abierto(timeout=45.0) as client:
        with ThreadPoolExecutor(max_workers=args.hilos) as ex:
            frescas = list(ex.map(
                lambda f: _cosechar(client, f, args.muestra,
                                    len(filas_a_cosechar)), filas_a_cosechar))

        if args.reintentar_errores:
            # Las filas remedidas SUSTITUYEN a las anteriores; el resto se
            # conserva tal cual (misma cosecha, mismo veredicto).
            for r in frescas:
                previas[r["id"]] = r
            res = [previas[f["id"]] for f in filas if f["id"] in previas]
        else:
            res = frescas

        docs = [r["evidencia"]["document_id"] for r in res
                if r.get("evidencia")]
        meta = _metadatos_documentos(client, docs)

    idx_cat = _indice_catalogo()
    for r in res:
        if r.get("evidencia"):
            m = meta.get(r["evidencia"]["document_id"] or "", {})
            r["evidencia"]["documento"] = {
                "fabricante": m.get("manufacturer"),
                "product_model": m.get("product_model"),
                "doc_type": m.get("doc_type"),
                "fichero": m.get("source_pdf_filename"),
            }
            # ¿el fabricante del manual coincide con el prefijo del id?
            pref = (r["id"] or "").split(":")[0]
            fab = norm_token(str(m.get("manufacturer") or ""))
            r["coherencia_fabricante"] = (
                "sin_dato" if not fab else
                "coincide" if pref and (pref in fab or fab in pref) else
                "distinto")
        else:
            r["coherencia_fabricante"] = "sin_dato"
        # ¿algún token parásito ES otro producto ya catalogado?
        r["parasitos_ya_en_catalogo"] = [
            {"token": p["token"], "id_catalogo": idx_cat[norm_token(p["token"])]}
            for p in r["parasitos_top"]
            if norm_token(p["token"]) in idx_cat]

    # --- Ruteo determinista ------------------------------------------------
    bloque, a_llm = [], []
    for r in res:
        motivos = []
        if r.get("error"):
            # NO MEDIDO ≠ NO ATESTADO. Se declara como lo que es.
            motivos.append(f"NO MEDIDO (error de red): {r['error']}")
        elif r["n_ilike_hoy"] is None:
            motivos.append("NO MEDIDO: sin conteo")
        elif r["n_ilike_hoy"] < UMBRAL_ILIKE:
            motivos.append(f"atestación cayó hoy: {r['n_ilike_hoy']} < {UMBRAL_ILIKE}")
        if r["n_chunks_token_exacto"] < UMBRAL_EXACTO:
            motivos.append(
                f"solo {r['n_chunks_token_exacto']} chunk(s) con el modelo como "
                f"token completo (el resto son subcadenas de otros tokens)")
        if r["banderas"]:
            motivos.append("forma sospechosa: " + ", ".join(r["banderas"]))
        r["motivos_no_determinista"] = motivos
        if motivos:
            a_llm.append(r)
        else:
            r["ruta"] = "determinista"
            r["veredicto"] = "confirmar"
            r["confianza"] = "alta"
            r["por_que"] = (
                f"{r['n_chunks_token_exacto']} chunks del corpus mencionan "
                f"«{r['modelo']}» como token completo "
                f"({'censo' if r['muestra_es_censo'] else 'muestra'} de "
                f"{r['muestra_descargada']}; {r['n_ilike_hoy']} coincidencias "
                f"totales), en {r['docs_distintos_con_exacta']} documento(s).")
            bloque.append(r)

    print(f"determinista → bloque {len(bloque)} · a-LLM {len(a_llm)}"
          f"  [{time.time() - t0:.0f}s]", flush=True)

    # --- Fase C: LLM sobre el residuo --------------------------------------
    # En modo reintento solo se juzga lo que NO tiene ya veredicto de LLM: las
    # filas sanas de la pasada anterior conservan el suyo (mismo prompt, misma
    # evidencia → repagarlo no añadiría información).
    a_juzgar = [r for r in a_llm
                if r.get("ruta") != "llm" or not r.get("veredicto")]
    coste = {"llamadas": 0, "in": 0, "out": 0, "parse_fail": 0,
             "reutilizadas_de_pasada_previa": len(a_llm) - len(a_juzgar)}
    if a_juzgar and not args.sin_llm:
        import anthropic
        cliente = anthropic.Anthropic()
        hechas = [0]

        def _una(client, r: dict) -> None:
            try:
                d = _juzgar(cliente, r)
            except Exception as exc:
                d = {"veredicto": "dudoso", "confianza": "baja", "cita": "",
                     "razon": f"error LLM: {type(exc).__name__}: {exc}"}
            evs = (([r["evidencia"]] if r.get("evidencia") else [])
                   + r["evidencias_extra"])
            textos = [e["fragmento"] for e in evs]
            # La verificación primero mira los fragmentos mostrados y, si falla,
            # el DOCUMENTO COMPLETO: si el modelo copió texto de más allá del
            # recorte, sigue siendo texto real del corpus y no debe penalizarse.
            ok, detalle = _verificar_cita(
                client, d.get("cita", ""), textos,
                [e.get("document_id") for e in evs])
            conf = d.get("confianza", "baja")
            if not ok and conf == "alta":
                # LECCIÓN: confianza «alta» con cita que no verifica se DEGRADA.
                # La cita es el contrato; el adjetivo, no.
                conf = "media"
                d["razon"] = (d.get("razon", "") +
                              " [confianza degradada: la cita no verifica]")
            r["ruta"] = "llm"
            r["veredicto"] = d.get("veredicto", "dudoso")
            r["confianza"] = conf
            r["confianza_declarada"] = d.get("confianza")
            r["cita"] = d.get("cita", "")
            r["cita_verificada"] = ok
            r["cita_verificacion_detalle"] = detalle
            r["por_que"] = d.get("razon", "")
            with _lock:
                uso = d.get("_uso") or {}
                coste["llamadas"] += 1
                coste["in"] += int(uso.get("in") or 0)
                coste["out"] += int(uso.get("out") or 0)
                if "parse-fail" in str(d.get("razon", "")):
                    coste["parse_fail"] += 1
                hechas[0] += 1
                if hechas[0] % 20 == 0:
                    print(f"  llm {hechas[0]}/{len(a_juzgar)}…", flush=True)

        with abierto(timeout=30.0) as client:
            with ThreadPoolExecutor(max_workers=4) as ex:
                list(ex.map(lambda r: _una(client, r), a_juzgar))

    # Un residuo vuelve al BLOQUE solo con veredicto claro + alta + cita
    # verificada. Cualquier otra cosa es individual: no se aproxima nada.
    individual = []
    for r in a_llm:
        if (r.get("veredicto") == "confirmar" and r.get("confianza") == "alta"
                and r.get("cita_verificada")):
            bloque.append(r)
        else:
            individual.append(r)

    # --- Avisos sobre el propio bloque -------------------------------------
    # Un «sí en bloque» defendible no es solo «todos pasaron la puerta»: es
    # enseñar DÓNDE es más fino. Estos tres avisos no sacan a nadie del bloque
    # (la puerta ya está declarada), pero le dicen a Alberto qué mirar si quiere
    # mirar algo antes de decir que sí.
    por_nombre: dict[str, list[str]] = {}
    for r in bloque:
        por_nombre.setdefault(norm_token(r["modelo"]), []).append(r["id"])
    avisos = {
        "que_son": ("no bloquean nada; señalan los puntos más finos del bloque "
                    "para que el «sí» sea informado"),
        "colisiones_de_nombre": [
            {"nombre_normalizado": k, "ids": v,
             "riesgo": "confirmar los dos crea DOS productos para un mismo "
                       "nombre (posible duplicado o alias, no alta separada)"}
            for k, v in sorted(por_nombre.items()) if len(v) > 1],
        "evidencia_minima": [
            {"id": r["id"], "modelo": r["modelo"],
             "n_chunks_token_exacto": r["n_chunks_token_exacto"],
             "por_que": r.get("por_que", "")}
            for r in bloque
            if r["n_chunks_token_exacto"] < UMBRAL_EXACTO],
        "fabricante_del_manual_distinto_al_id": sum(
            1 for r in bloque if r.get("coherencia_fabricante") == "distinto"),
    }

    # --- Recibo ------------------------------------------------------------
    utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    por_bandera = Counter(b for r in res for b in r["banderas"])
    recibo = {
        "que_es": (
            "s322f: encogimiento AUDITABLE del lote «confirmar» del QA E1b. "
            "PROPUESTA — no se aplicó nada (0 escrituras en catálogo/Supabase/"
            "snapshot). La atestación de s320 era `ilike` sin fronteras; aquí "
            "cada mención se expande al token técnico completo y se separa "
            "mención EXACTA de mención PARÁSITA, con fragmento verbatim del "
            "corpus para auditar. El LLM (claude-fable-5) solo interviene en el "
            "residuo que el determinismo no cierra."),
        "utc": utc,
        "fuente": str(FUENTE.relative_to(ROOT)).replace("\\", "/"),
        "fuente_utc": fuente["utc"],
        "parametros": {"umbral_ilike": UMBRAL_ILIKE,
                       "umbral_chunks_token_exacto": UMBRAL_EXACTO,
                       "muestra_max": args.muestra, "modelo_juez": MODELO_JUEZ,
                       "max_tokens": MAX_TOKENS, "temperature": "no enviada"},
        "puerta_del_bloque": [
            f"n_ilike_hoy >= {UMBRAL_ILIKE} (sigue atestado hoy)",
            f"n_chunks_token_exacto >= {UMBRAL_EXACTO} (token completo, no subcadena)",
            "sin banderas léxicas de artefacto",
            "fragmento de evidencia verbatim extraído del corpus",
            "vía LLM: veredicto=confirmar + confianza=alta + cita verificada a "
            "texto completo",
        ],
        "total": len(res),
        "bloque": len(bloque),
        "individual": len(individual),
        "desglose_bloque": {
            "determinista": sum(1 for r in bloque if r["ruta"] == "determinista"),
            "llm_alta_verificada": sum(1 for r in bloque if r["ruta"] == "llm"),
        },
        "desglose_individual": dict(Counter(
            r.get("veredicto", "sin_veredicto") for r in individual)),
        "banderas_lexicas": dict(por_bandera),
        "deriva_conteo": {
            "subio": sum(1 for r in res if r["n_ilike_hoy"] > (r["n_ilike_s320"] or 0)),
            "bajo": sum(1 for r in res if r["n_ilike_hoy"] < (r["n_ilike_s320"] or 0)),
            "igual": sum(1 for r in res if r["n_ilike_hoy"] == (r["n_ilike_s320"] or 0)),
            "cayo_bajo_umbral": sum(1 for r in res if r["n_ilike_hoy"] < UMBRAL_ILIKE),
        },
        "avisos_bloque": avisos,
        "errores_red": [r["id"] for r in res if r.get("error")],
        "filas_remedidas_en_este_reintento": reintentos,
        "coste_llm": coste,
        "segundos": round(time.time() - t0, 1),
        "detalle": {"bloque": bloque, "individual": individual},
    }
    destino = Path(args.salida)
    destino.write_text(json.dumps(recibo, ensure_ascii=False, indent=1),
                       encoding="utf-8")
    print(f"\nTOTAL {len(res)} · BLOQUE {len(bloque)} "
          f"(det {recibo['desglose_bloque']['determinista']} + llm "
          f"{recibo['desglose_bloque']['llm_alta_verificada']}) · "
          f"INDIVIDUAL {len(individual)}")
    print(f"recibo -> {destino}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
