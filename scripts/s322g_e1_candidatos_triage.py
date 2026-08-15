#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""s322g — Encoge la SECCIÓN 3 del packet E1: los 133 productos NUEVOS «candidate».

QUÉ RESUELVE
============
`evals/s320_e1_candidates_draft.jsonl` propone dar de alta 133 términos como productos
`candidate=true` del catálogo gobernado. Cada término salió de `documents.product_model`
de un manual — es decir, de un EXTRACTOR, no de un humano. La pregunta que Alberto tiene
que contestar 133 veces es siempre la misma:

    ¿esto es un PRODUCTO de verdad, o es un ARTEFACTO de extracción?

Y no es una pregunta retórica: esta misma semana el corpus ha parido artefactos reales de
esa clase — «TO-3200M» nacido de la distancia «hasta 3200 m», «MM-82» de la cota «82 mm»,
«OF-48V» de una nota sobre cables, «EN-54-25» que es una NORMA, «LOCAL-360» de la frase
«local 360 degree indication». Dar de alta un artefacto no es un error cosmético: el
término entra en el detector, ensucia el contexto de TODAS las consultas y hay que
desandarlo con cirugía.

CÓMO LO DECIDE (y por qué así)
==============================
Tres capas, de la más barata y dura a la más cara y blanda. Ninguna decide sola.

  (1) REFRESCO. El draft se congeló el 12-ago y el corpus se ha movido (s322d/e). Una fila
      sólo sigue siendo un alta viva si su documento de origen sigue ACTIVO hoy y sigue
      declarando ese product_model. Si el doc está retirado o cambió de pm, la fila NO se
      juzga como si nada: se marca y va a individual. (Medido: 7 filas de 133.)

  (2) SEÑALES DURAS, medidas contra `chunks_v2` — el corazón del método. Cuatro contadores
      distintos porque la diferencia ENTRE ellos es justo lo que separa producto de
      artefacto:
        · ESTRICTAS  — el término tal cual se escribe (mismos separadores). «DE-80».
        · FLEXIBLES  — tolerando separadores: «DE-80» ≡ «De 80» ≡ «DE 80».
        · MAYÚSCULAS — flexibles cuyo texto casado va TODO en mayúsculas.
        · FRAGMENTO  — menciones seguidas de MÁS código: «S20» dentro de «S20/20MI».
      Un producto real aparece estricto y/o en mayúsculas y no como fragmento. Un artefacto
      aparece SÓLO en la forma flexible y en minúsculas, porque nació de una frase
      corriente: el probe de diseño lo confirmó — «SOME-58» ← «some 58 home departments»,
      «DE-80» ← «De 80 columnas» / «80 Gb». Estas señales no son un adorno del prompt: son
      el GUARDARRAÍL que puede contradecir al juez (ver `clasificar`) — y la de FRAGMENTO
      sacó ella sola del bloque un alta que iba a entrar con nombre falso («S20»).

  (3) JUICIO LLM (claude-fable-5) con MUESTREO DIRIGIDO: al juez NO se le mandan los
      primeros chunks del documento, se le mandan los pasajes que MENCIONAN el término
      (la evidencia vive en tablas de modelos a mitad de manual, no en la portada). Salida
      JSON estricta con veredicto, ROL EN EL TEXTO (sujeto vs frase técnica) y CITA
      VERBATIM.

VERIFICACIÓN DE CITAS — lección ya pagada
=========================================
La cita se valida ENTERA (hasta 200 chars) contra el CONTENIDO COMPLETO del material
(todos los chunks del doc de origen + el contenido íntegro de cada chunk muestreado),
normalizando espacios y caja. Verificar sólo un prefijo de 50 chars dejó pasar una
invención real: la cola parafraseada por el modelo no estaba en el documento. Si el
modelo dice confianza «alta» y su cita no verifica, la confianza se DEGRADA a «media» y
la fila cae a individual.

CRITERIO DE SALIDA
==================
SECCIÓN 0 (bloque, un solo sí de Alberto), en dos sub-bloques:
    0A ALTA      — PRODUCTO_REAL, confianza alta, cita verificada, sin ambigüedad.
    0B RETIRAR   — ARTEFACTO_EXTRACCION / NORMA_O_CERTIFICACION con las mismas garantías.
SECCIÓN 1 (individual) — el residuo real, cada fila con TODA su evidencia junta y la lista
    EXPLÍCITA de motivos por los que no entra en bloque (para que se discuta la REGLA, no
    la fila).

El objetivo es maximizar el bloque SIN relajar el criterio. Jamás se aproxima un veredicto
ni se acepta una cita no verificada para engordar el bloque: eso destruiría la confianza
del sistema entero, que es el único activo que este packet tiene.

SOLO LECTURA — CONTRATO DURO
============================
Este script NO escribe en `data/catalog/*.jsonl`, NI en Supabase (cero PATCH/POST/DELETE:
todas las llamadas son GET), NI en `data/model_catalog.json`. Su único efecto es el recibo
JSON en `evals/` (+ una caché temporal para poder reanudar). Es una PROPUESTA.

USO
===
    python scripts/s322g_e1_candidatos_triage.py
    python scripts/s322g_e1_candidatos_triage.py --limite 5      # smoke barato
    python scripts/s322g_e1_candidatos_triage.py --sin-llm       # sólo señales duras
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import threading
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=False)

import anthropic  # noqa: E402

from src.http_pool import abierto  # noqa: E402
from src.rag.catalog_store import CATALOG_DIR, _read_jsonl  # noqa: E402  (SOLO LECTURA)

SB = os.environ["SUPABASE_URL"].rstrip("/")
KEY = os.environ["SUPABASE_SERVICE_KEY"]
H = {"apikey": KEY, "Authorization": f"Bearer {KEY}"}

MODELO = "claude-fable-5"
DRAFT = ROOT / "evals" / "s320_e1_candidates_draft.jsonl"
DESTINO = ROOT / "evals" / "s322g_e1_candidatos_triage_v1.json"
CACHE = Path(tempfile.gettempdir()) / "s322g_e1_candidatos_triage_cache.json"

# Nº de pasajes que viajan al juez. 8 × ~500 chars ≈ 4K chars: suficiente para ver si el
# término es sujeto de una tabla de modelos sin inflar el coste ni enterrar la señal.
CONTEXTOS_MAX = 8
VENTANA = 240          # chars a cada lado del match en cada pasaje
MUESTRA_GLOBAL = 40    # filas que se bajan por variante antes de filtrar en local
HILOS = 6
# Umbral de «radio de impacto»: nº de chunks etiquetados EXACTAMENTE con el término a
# partir del cual retirar el alta deja huérfanos a demasiados chunks como para decidirlo
# en bloque (ver `clasificar`).
PM_MASIVO = 50

_LOCK_CACHE = threading.Lock()


# ─────────────────────────── normalización y regex ───────────────────────────

def _norm(texto: str) -> str:
    """Normalización canónica para comparar citas contra el texto fuente: espacios
    colapsados y minúsculas. Es la MISMA en toda la verificación — una segunda definición
    divergente es justo cómo se cuela una cita inventada."""
    return re.sub(r"\s+", " ", (texto or "")).strip().lower()


def _segmentos(term: str) -> list[str]:
    """Parte el término en segmentos alfanuméricos. «MOD.RS-232» → ['MOD','RS','232']."""
    return [s for s in re.split(r"[^0-9A-Za-zÀ-ÿ]+", term) if s]


def _rx_flexible(term: str) -> re.Pattern | None:
    """Regex TOLERANTE A SEPARADORES con frontera de palabra.

    «DE-80» casa «DE-80», «DE 80», «De 80» y «de80». Es deliberadamente laxa: sirve para
    ENCONTRAR el pasaje del que pudo nacer un artefacto (su valor probatorio real). Por sí
    sola NO prueba que el término sea un producto — de ahí que exista `_rx_estricta`.
    """
    segs = _segmentos(term)
    if not segs:
        return None
    # Separador = CUALQUIER run corto de no-alfanuméricos, no una lista blanca: con
    # `[\s\-\./_]*` el término «ID²NET» daba 0 menciones flexibles y 61 estrictas — la
    # flexible tiene que ser SUPERCONJUNTO de la estricta o el contador miente.
    cuerpo = r"[^0-9A-Za-z]{0,3}".join(re.escape(s) for s in segs)
    return re.compile(r"(?<![0-9A-Za-z])" + cuerpo + r"(?![0-9A-Za-z])", re.I)


def _rx_estricta(term: str) -> re.Pattern | None:
    """Regex del término TAL CUAL se escribe (mismos separadores), con frontera.

    Es la señal fuerte: si el corpus contiene literalmente «KE-DP3021B», hay una referencia
    comercial. Si sólo contiene «De 80» pero nunca «DE-80», el término no existe como
    cadena en ningún manual — no puede ser un producto atestado por este corpus.
    """
    t = term.strip()
    if not t:
        return None
    return re.compile(r"(?<![0-9A-Za-z])" + re.escape(t) + r"(?![0-9A-Za-z])", re.I)


def _es_mayusculas(txt: str) -> bool:
    """¿El texto casado va en mayúsculas? (letras≥1 y todas mayúsculas).

    Discrimina «MOD. RS-232» (producto escrito con otro separador) de «De 80 columnas»
    (frase corriente). Los modelos de PCI se imprimen en mayúsculas casi sin excepción.
    """
    letras = [c for c in txt if c.isalpha()]
    return bool(letras) and all(c.isupper() for c in letras)


def _fold(s: str) -> str:
    """Clave de comparación laxa: sólo alfanuméricos en minúscula."""
    return re.sub(r"[^0-9a-z]", "", (s or "").lower())


# ─────────────────────────── acceso a datos (GET) ───────────────────────────

def _get(c, tabla: str, params: dict) -> list[dict]:
    r = c.get(f"{SB}/rest/v1/{tabla}", headers=H, params=params)
    r.raise_for_status()
    return r.json()


def _contar(c, tabla: str, params: dict) -> int:
    """COUNT exacto por cabecera Content-Range: no baja filas y no miente al topar el
    limit por defecto (un `len(rows)` sí lo haría)."""
    h = dict(H, **{"Prefer": "count=exact", "Range-Unit": "items", "Range": "0-0"})
    r = c.get(f"{SB}/rest/v1/{tabla}", headers=h, params={**params, "select": "id"})
    if r.status_code >= 400:
        return -1
    return int(r.headers["content-range"].split("/")[-1])


def _resolver_documento(c, stem: str) -> list[dict]:
    """Localiza la fila de `documents` del manual del que salió el término.

    Escalera de patrones porque el `provenance` guarda el filename normalizado (minúsculas,
    a veces sin `.pdf`): exacto → exacto+.pdf → contiene. Se devuelven TODAS las filas que
    casan, no sólo una: cuando el mismo fichero tiene varias filas con product_model
    DISTINTO, esa discrepancia es evidencia de primera (el caso MADT015_01, donde las filas
    hermanas dicen «NFS2-8» y la activa dice «MADT-015»).
    """
    for pat in (stem, stem + ".pdf", "*" + stem + "*"):
        filas = _get(c, "documents", {
            "select": "id,source_pdf_filename,status,product_model,manufacturer,doc_type,"
                      "language,revision",
            "source_pdf_filename": "ilike." + pat})
        if filas:
            return filas
    return []


def _variantes_ilike(term: str) -> list[str]:
    """Variantes de escritura para el filtro PostgREST `content=ilike.*X*`.

    PostgREST no tiene frontera de palabra, así que el filtro sólo PRE-SELECCIONA: el
    recorte fino lo hace la regex en local. Se buscan la forma tal cual, la compacta y las
    separadas por espacio/guion para no perder el pasaje que originó un artefacto.
    """
    segs = _segmentos(term)
    v = {term.strip()}
    if segs:
        v.add("".join(segs))
        v.add(" ".join(segs))
        v.add("-".join(segs))
    return [x for x in v if len(x) >= 2]


# ─────────────────────────── recolección de evidencia ───────────────────────────

# El término va seguido de MÁS código de modelo: «S20» dentro de «S20/20MI». La frontera
# de palabra no lo detecta (una barra no es alfanumérica), y sin esto un FRAGMENTO de
# modelo entra como producto — el fallo caro de la familia ZXr-A/ZXR50A.
RX_CONTINUACION = re.compile(r"^[/\-.][0-9A-Za-z]")


def _menciones(rx_flex, rx_estr, texto: str) -> tuple[int, int, int, int, list]:
    """Cuenta menciones flexibles / estrictas / en-mayúsculas / como-fragmento."""
    spans = [(m.start(), m.end(), _es_mayusculas(m.group(0)),
              bool(RX_CONTINUACION.match(texto[m.end():m.end() + 2])))
             for m in rx_flex.finditer(texto)] if rx_flex else []
    n_estr = len(rx_estr.findall(texto)) if rx_estr else 0
    # `if may` NO es opcional: sin él se contaban TODAS las menciones como mayúsculas, el
    # contador quedaba idéntico al flexible y el guardarraíl «producto real sin mención
    # estricta ni en mayúsculas» no podía dispararse nunca (y el juez recibía un número
    # falso). Cazado comparando el recibo con su propia cita: «de 80 Gb» contado como
    # mayúsculas.
    n_may = sum(1 for _, _, may, _f in spans if may)
    n_frag = sum(1 for _, _, _m, f in spans if f)
    return len(spans), n_estr, n_may, n_frag, spans


def _pasajes(texto: str, spans, etiqueta: str, tope: int) -> list[dict]:
    """Ventanas de ±VENTANA chars alrededor de cada mención, con el término marcado.

    El marcado «» es lo que permite al juez ver el ROL del término (encabezado de tabla vs
    mitad de frase) sin tener que buscarlo dentro de un muro de texto."""
    out = []
    for ini, fin, may, frag in spans[:tope]:
        a, b = max(0, ini - VENTANA), min(len(texto), fin + VENTANA)
        out.append({"etiqueta": etiqueta, "mayusculas": may, "es_fragmento": frag,
                    "texto": (texto[a:ini] + "«" + texto[ini:fin] + "»" + texto[fin:b]).strip()})
    return out


def recolectar(fila: dict) -> dict:
    """Toda la evidencia de un candidato. SOLO GETs."""
    term = fila["canonical_model"].strip()
    stem = fila["provenance"].split("documents.pm de ", 1)[1]
    rx_f, rx_e = _rx_flexible(term), _rx_estricta(term)
    ev: dict = {"termino": term, "stem": stem}

    with abierto(timeout=45.0) as c:
        docs = _resolver_documento(c, stem)
        # La fila «buena» es la ACTIVA cuyo product_model coincide con el término; si no
        # existe, la activa cualquiera; si tampoco, la primera. El resto se guardan como
        # hermanas: su discrepancia de pm es evidencia.
        act = [d for d in docs if d.get("status") == "active"]
        pref = [d for d in act if _fold(d.get("product_model") or "") == _fold(term)]
        doc = (pref or act or docs or [None])[0]
        ev["documento"] = doc
        ev["filas_mismo_fichero"] = [
            {"filename": d["source_pdf_filename"], "status": d["status"],
             "product_model": d.get("product_model")} for d in docs]
        # REFRESCO (capa 1): ¿sigue viva la premisa del draft?
        ev["doc_activo"] = bool(doc and doc.get("status") == "active")
        ev["pm_del_doc_hoy"] = (doc or {}).get("product_model")
        ev["pm_sigue_siendo_el_termino"] = _fold(ev["pm_del_doc_hoy"] or "") == _fold(term)

        # --- texto COMPLETO del documento de origen (base de verificación de citas) ---
        chunks = []
        if doc:
            chunks = _get(c, "chunks_v2", {
                "select": "chunk_index,section_title,product_model,page_number,content",
                "document_id": "eq." + doc["id"],
                "order": "chunk_index.asc", "limit": "800"})
        texto_doc = re.sub(r"\s+", " ", " ".join((x.get("content") or "") for x in chunks))
        ev["n_chunks_doc"] = len(chunks)
        ev["portada"] = texto_doc[:900]
        ev["secciones"] = sorted({(x.get("section_title") or "").strip()
                                  for x in chunks if (x.get("section_title") or "").strip()})[:12]

        n_f, n_e, n_m, n_fr, spans = _menciones(rx_f, rx_e, texto_doc)
        ev["menciones_doc"] = {"flexibles": n_f, "estrictas": n_e, "mayusculas": n_m,
                               "como_fragmento": n_fr}
        pasajes = _pasajes(texto_doc, spans, f"DOC ORIGEN · {stem}", CONTEXTOS_MAX)

        # --- MUESTREO DIRIGIDO global: chunks que MENCIONAN el término -------------
        # No los primeros chunks del corpus: los que contienen el término. La evidencia de
        # «es un producto» vive en tablas de modelos a mitad de manual.
        vistos: dict[str, dict] = {}
        for var in _variantes_ilike(term):
            try:
                for x in _get(c, "chunks_v2", {
                        "select": "document_id,source_file,section_title,chunk_index,"
                                  "product_model,content",
                        "content": f"ilike.*{var}*", "limit": str(MUESTRA_GLOBAL)}):
                    vistos.setdefault(f"{x['document_id']}:{x['chunk_index']}", x)
            except Exception:                                        # noqa: BLE001
                continue  # una variante rara que PostgREST rechace no puede tumbar la fila

        # Recorte fino en local (PostgREST no tiene \b) + reparto por documento para no
        # gastar los 8 huecos de contexto en 8 chunks del mismo manual.
        globales, por_doc = [], Counter()
        n_f_g = n_e_g = n_m_g = n_fr_g = 0
        docs_con_mencion: set[str] = set()
        for x in vistos.values():
            txt = re.sub(r"\s+", " ", x.get("content") or "")
            f_, e_, m_, fr_, sp = _menciones(rx_f, rx_e, txt)
            if not sp:
                continue
            n_f_g += f_; n_e_g += e_; n_m_g += m_; n_fr_g += fr_
            docs_con_mencion.add(x["document_id"])
            if x["document_id"] == (doc or {}).get("id"):
                continue  # ya cubierto por el pase del doc de origen
            globales.append((x, txt, sp, m_))
        # Prioridad: menciones en MAYÚSCULAS primero (señal de referencia comercial) y
        # máximo 2 pasajes por documento.
        globales.sort(key=lambda t: (-t[3], t[0].get("source_file") or ""))
        for x, txt, sp, _m in globales:
            if len(pasajes) >= CONTEXTOS_MAX or por_doc[x["document_id"]] >= 2:
                continue
            por_doc[x["document_id"]] += 1
            pasajes += _pasajes(txt, sp, f"OTRO DOC · {x.get('source_file')} "
                                          f"· seccion={x.get('section_title')} "
                                          f"· pm={x.get('product_model')}", 1)
        ev["menciones_muestra_global"] = {"flexibles": n_f_g, "estrictas": n_e_g,
                                          "mayusculas": n_m_g, "como_fragmento": n_fr_g,
                                          "documentos": len(docs_con_mencion)}
        ev["pasajes"] = pasajes[:CONTEXTOS_MAX]

        # --- contadores de corpus (baratos, exactos) --------------------------------
        # DOS medidas de product_model, y la distinción importa: la EXACTA (`eq`) mide el
        # radio de impacto real del término como etiqueta; la PARECIDA (`ilike`) es
        # substring y se contamina entre parientes («2X-A» cuenta también los de «2X-A
        # Táctil»). El guardarraíl usa la exacta; la parecida sólo informa.
        ev["chunks_pm_exacto"] = _contar(c, "chunks_v2", {"product_model": f"eq.{term}"})
        ev["chunks_pm_parecido"] = _contar(c, "chunks_v2", {"product_model": f"ilike.*{term}*"})
        ev["docs_con_pm"] = _contar(c, "documents", {"product_model": f"ilike.*{term}*"})
        # El nombre de fichero no usa una convención única de separadores: se prueban la
        # forma tal cual y la compacta y se toma la mayor (con la compacta sola, «2X-A»
        # daba 0 sobre ficheros que lo llevan literalmente).
        ev["docs_con_termino_en_filename"] = max(
            _contar(c, "documents", {"source_pdf_filename": f"ilike.*{term}*"}),
            _contar(c, "documents",
                    {"source_pdf_filename": f"ilike.*{''.join(_segmentos(term))}*"}))

        # Texto de VERIFICACIÓN de citas: doc de origen ENTERO + contenido ÍNTEGRO de cada
        # chunk muestreado. Superconjunto de lo que ve el juez: si su cita no está aquí,
        # no está en el corpus.
        ev["_texto_verificacion"] = _norm(
            texto_doc + " " + " ".join((x.get("content") or "") for x in vistos.values()))

    ev["termino_en_filename"] = _fold("".join(_segmentos(term))) in _fold(stem)
    return ev


# ─────────────────────────── juicio LLM ───────────────────────────

PROMPT = """Eres el adjudicador de identidad de producto de un corpus de manuales de protección contra incendios (PCI).

Un extractor automático propuso dar de alta el término de abajo como PRODUCTO NUEVO. Tu trabajo es decidir si es un producto DE VERDAD o un ARTEFACTO del extractor.

ARTEFACTOS REALES ya cazados en este mismo corpus (calíbrate con ellos):
- «TO-3200M» nació de la distancia «hasta 3200 m».
- «MM-82» nació de la cota «82 mm».
- «OF-48V» nació de una nota sobre cables de 48 V.
- «EN-54-25» es una NORMA, no un producto.
- «LOCAL-360» nació de la frase «local 360 degree indication».
- Un CÓDIGO DE DOCUMENTO (p. ej. «MA-DT-015», «MNDT690») es la referencia del manual, no un producto.
- El nombre de un FABRICANTE o de una MARCA/GAMA (p. ej. «SPECTREX», «VESDA») no es un modelo.

TÉRMINO PROPUESTO: «{term}»
Fabricante propuesto por el extractor: {fab}
Documento de origen: {filename}
Ficha del documento hoy: estado={status} · product_model={pm_doc} · fabricante={fab_doc} · tipo={doc_type}
Otras filas de `documents` con ese mismo fichero: {hermanas}

SEÑALES DURAS medidas en el corpus (son hechos, no opiniones — úsalas):
- Menciones del término en el DOCUMENTO DE ORIGEN: {md_flex} tolerando separadores, {md_estr} escritas exactamente igual, {md_may} en MAYÚSCULAS.
- Menciones en la muestra del RESTO DEL CORPUS: {mg_flex} tolerando separadores, {mg_estr} exactas, {mg_may} en MAYÚSCULAS, repartidas en {mg_docs} documentos.
- Menciones en las que el término va seguido de MÁS código de modelo (como «S20» dentro de «S20/20MI»): {frag} en el documento, {frag_g} en el resto. Si son la mayoría, el término es un FRAGMENTO de un modelo más largo, no el modelo.
- Chunks etiquetados con ese product_model exacto: {n_pm}. Documentos con ese product_model: {n_docs_pm}.
- El término aparece en el NOMBRE DEL FICHERO del documento: {en_filename}.

(Interpretación: un producto real suele aparecer escrito EXACTAMENTE igual y en mayúsculas. Un artefacto sólo aparece en la forma «tolerando separadores» y en minúsculas, porque nació de una frase corriente.)

INICIO DEL DOCUMENTO DE ORIGEN:
---
{portada}
---

PASAJES QUE MENCIONAN EL TÉRMINO (el término va marcado con «»):
---
{pasajes}
---

PREGUNTA CLAVE: ¿el término aparece como SUJETO —título de manual o de sección, fila de una tabla de modelos, referencia comercial o de pedido— o sólo DENTRO de una frase técnica (una medida, una distancia, una tensión, una norma, un código de documento)?
  · Sujeto  -> PRODUCTO_REAL.
  · Sólo dentro de una frase -> ARTEFACTO_EXTRACCION.
  · Si NO aparece verbatim en ninguna parte, no está atestado por este corpus: ARTEFACTO_EXTRACCION (o NO_DECIDIBLE si el material no deja ver de dónde salió), y cita el pasaje del que probablemente se derivó.

Responde SOLO con este JSON, sin markdown y sin texto fuera del JSON:
{{"veredicto": "PRODUCTO_REAL|ARTEFACTO_EXTRACCION|NORMA_O_CERTIFICACION|ACCESORIO_DE_OTRO|NO_DECIDIBLE",
 "rol_en_texto": "TITULO|TABLA_DE_MODELOS|REFERENCIA_COMERCIAL|FRASE_TECNICA|CODIGO_DE_DOCUMENTO|NOMBRE_DE_FABRICANTE_O_GAMA|NO_APARECE",
 "confianza": "alta|media|baja",
 "cita": "fragmento VERBATIM copiado LETRA A LETRA del material de arriba que fundamenta tu veredicto (máx 200 caracteres), o null",
 "producto_padre": "si es ACCESORIO_DE_OTRO, de qué producto depende; si no, null",
 "termino_real": "si el modelo correcto se escribe de otra forma en el texto, esa forma; si no, null",
 "razon": "una frase de MENOS DE 25 PALABRAS"}}

La cita debe existir LETRA A LETRA en el material de arriba (sin los marcadores «»): si la parafraseas, mientes y se detecta. Sin cita verificable, tu confianza es "baja"."""


def juzgar(cliente, fila: dict, ev: dict) -> dict:
    doc = ev.get("documento") or {}
    pasajes = "\n\n".join(f"[{p['etiqueta']}]\n{p['texto']}" for p in ev["pasajes"]) or \
              "(el término NO aparece en ningún pasaje del corpus)"
    prompt = PROMPT.format(
        term=ev["termino"], fab=fila["id"].split(":")[0],
        filename=doc.get("source_pdf_filename") or ev["stem"],
        status=doc.get("status"), pm_doc=doc.get("product_model"),
        fab_doc=doc.get("manufacturer"), doc_type=doc.get("doc_type"),
        hermanas=json.dumps(ev["filas_mismo_fichero"], ensure_ascii=False)[:400],
        md_flex=ev["menciones_doc"]["flexibles"], md_estr=ev["menciones_doc"]["estrictas"],
        md_may=ev["menciones_doc"]["mayusculas"],
        mg_flex=ev["menciones_muestra_global"]["flexibles"],
        mg_estr=ev["menciones_muestra_global"]["estrictas"],
        mg_may=ev["menciones_muestra_global"]["mayusculas"],
        mg_docs=ev["menciones_muestra_global"]["documentos"],
        frag=ev["menciones_doc"]["como_fragmento"],
        frag_g=ev["menciones_muestra_global"]["como_fragmento"],
        n_pm=ev["chunks_pm_exacto"], n_docs_pm=ev["docs_con_pm"],
        en_filename="sí" if ev["termino_en_filename"] else "no",
        portada=ev["portada"], pasajes=pasajes[:9000])

    def _llamar(p: str, tope: int) -> tuple[dict | None, str]:
        # Sin `temperature`: deprecada en los modelos 2026 (error 400).
        msg = cliente.messages.create(model=MODELO, max_tokens=tope,
                                      messages=[{"role": "user", "content": p}])
        txt = "".join(b.text for b in msg.content
                      if getattr(b, "type", "") == "text").strip()
        try:
            return json.loads(txt[txt.index("{"):txt.rindex("}") + 1]), txt
        except Exception:                                            # noqa: BLE001
            return None, txt

    # max_tokens=1400: con 400 el JSON se TRUNCA y el parse-fail se disfraza de
    # incertidumbre (lección cara ya pagada); el smoke demostró que 800 TAMBIÉN trunca
    # cuando la razón se alarga — y un veredicto perdido por truncamiento es una fila
    # empujada a individual sin motivo real.
    v, crudo = _llamar(prompt, 1400)
    if v is None:
        # Reintento acotado: el fallo típico es longitud, no incapacidad. Se recorta lo
        # único que puede crecer sin límite (la razón) antes de rendirse.
        v, crudo = _llamar(prompt + "\n\nIMPORTANTE: responde SOLO el JSON, con \"razon\" "
                                    "de menos de 12 palabras y \"cita\" de menos de 150 "
                                    "caracteres.", 1400)
    if v is None:
        return {"veredicto": "NO_DECIDIBLE", "rol_en_texto": None, "confianza": "baja",
                "cita": None, "razon": "parse-fail tras reintento", "raw": crudo[:400]}
    return v


def verificar_cita(v: dict, ev: dict) -> bool:
    """Verificación FULL-TEXT de la cita ENTERA (hasta 200 chars) contra el contenido
    completo del material. Un prefijo de 50 chars ya dejó pasar una invención real."""
    cita = (v.get("cita") or "").replace("«", "").replace("»", "")
    if len(_norm(cita)) < 12:      # una "cita" de 3 palabras no fundamenta nada
        return False
    return _norm(cita[:200]) in ev["_texto_verificacion"]


# ─────────────────────────── clasificación bloque / individual ───────────────────────────

def clasificar(fila: dict, ev: dict, v: dict, cita_ok: bool, ctx: dict) -> list[str]:
    """Devuelve la lista de MOTIVOS por los que la fila NO puede ir en bloque.

    Lista vacía = bloque. Se devuelven TODOS los motivos (no el primero) para que Alberto
    vea el perfil completo de la fila y pueda discutir la REGLA en vez de la fila.
    """
    m: list[str] = []
    term = ev["termino"]

    # --- (1) refresco: la premisa del draft ya no vive -------------------------------
    if not ev["doc_activo"]:
        m.append("obsoleta:doc-fuente-no-activo")
    if not ev["pm_sigue_siendo_el_termino"]:
        m.append("obsoleta:el-doc-ya-no-declara-ese-product_model")

    # --- (2) ambigüedad ESTRUCTURAL del alta (independiente del veredicto) -----------
    # Un término con barras o «y» no es un alta: son varias. Qué producto es cuál es una
    # decisión de forma que sólo Alberto puede tomar.
    if re.search(r"[/,]| y ", term):
        m.append("ambiguedad:termino-multi-modelo")
    if fila["id"] in ctx["ids_en_catalogo"]:
        m.append("colision:id-ya-existe-en-el-catalogo-gobernado")
    if _fold(term) in ctx["alias_ajenos"] and ctx["alias_ajenos"][_fold(term)] != fila["id"]:
        m.append("colision:el-texto-ya-es-alias-de-otro-producto")
    if len(ctx["grafias_por_id"].get(fila["id"], set())) > 1:
        m.append("ambiguedad:mismo-id-con-grafias-distintas-en-el-draft")
    if len(ctx["fabricantes_por_termino"].get(_fold(term), set())) > 1:
        m.append("ambiguedad:mismo-termino-propuesto-a-dos-fabricantes")
    # RIESGO LÉXICO (lección del fabricante «FUEGO», s322f): el coste de un alta no es
    # simétrico. Un acrónimo de 2-3 letras sin dígitos («TG», «MIW», «VSN») acaba en el
    # detector y matchea dentro de palabras y de siglas ajenas, envenenando el contexto de
    # consultas que no van de eso. Que el producto EXISTA no elimina ese coste: es una
    # decisión de Alberto, no del juez.
    if len(_fold(term)) <= 3 and not any(ch.isdigit() for ch in term):
        m.append("riesgo-lexico:acronimo-corto-sin-digitos")

    # --- (3) calidad del juicio -------------------------------------------------------
    ver = (v.get("veredicto") or "").upper()
    if ver not in {"PRODUCTO_REAL", "ARTEFACTO_EXTRACCION", "NORMA_O_CERTIFICACION"}:
        m.append(f"juez:veredicto-no-bloqueable({ver or 'vacio'})")
    if v.get("confianza") != "alta":
        m.append(f"juez:confianza-{v.get('confianza')}")
    if not cita_ok:
        m.append("cita:no-verificada-a-texto-completo")

    # --- (4) GUARDARRAÍLES: el juez contra las señales duras --------------------------
    # El juez no puede declarar producto lo que el corpus no escribe nunca tal cual ni en
    # mayúsculas: sería exactamente el fallo «TO-3200M».
    estr = ev["menciones_doc"]["estrictas"] + ev["menciones_muestra_global"]["estrictas"]
    may = ev["menciones_doc"]["mayusculas"] + ev["menciones_muestra_global"]["mayusculas"]
    if ver == "PRODUCTO_REAL":
        if estr == 0 and may == 0:
            m.append("contradiccion:producto-real-sin-mencion-estricta-ni-en-mayusculas")
        if (v.get("rol_en_texto") or "").upper() in {"FRASE_TECNICA", "CODIGO_DE_DOCUMENTO",
                                                     "NOMBRE_DE_FABRICANTE_O_GAMA",
                                                     "NO_APARECE"}:
            m.append("contradiccion:producto-real-con-rol-de-no-producto")
        # El propio juez propone OTRA grafía para el modelo: entonces el término del alta
        # no es el nombre del producto (caso «S20» ← «S20/20MI»). Dar de alta la grafía
        # equivocada es peor que no darla: queda un producto con nombre falso y hay que
        # desandarlo. Sólo aplica a PRODUCTO_REAL — en un ARTEFACTO, `termino_real` nombra
        # el producto que el manual sí trata, y eso es un extra, no una duda.
        tr = v.get("termino_real")
        if tr and _fold(str(tr)) != _fold(term):
            m.append(f"juez:propone-otra-grafia({str(tr)[:40]})")
        # FRAGMENTO: el término aparece casi siempre seguido de más código de modelo.
        flex = ev["menciones_doc"]["flexibles"] + ev["menciones_muestra_global"]["flexibles"]
        frag = (ev["menciones_doc"]["como_fragmento"]
                + ev["menciones_muestra_global"]["como_fragmento"])
        if frag >= 2 and flex and frag / flex >= 0.5:
            m.append("sospecha:el-termino-es-prefijo-de-un-modelo-mas-largo")
        # El fabricante del alta tiene que ser el de la ficha del manual; si no, el alta
        # colocaría el producto bajo la marca equivocada (caso LT-200 notifier vs xtralis).
        fab_id, fab_doc = fila["id"].split(":")[0], (ev.get("documento") or {}).get("manufacturer")
        if fab_doc and _fold(fab_id) not in _fold(fab_doc) and _fold(fab_doc) not in _fold(fab_id):
            m.append("fabricante:discrepa-de-la-ficha-del-documento")
    # Y a la inversa: no se retira en bloque un término que el corpus escribe como sujeto
    # en varios documentos. Ahí el «artefacto» pide ojo humano.
    if ver in {"ARTEFACTO_EXTRACCION", "NORMA_O_CERTIFICACION"}:
        if estr >= 3 and ev["menciones_muestra_global"]["documentos"] >= 2 and \
                (v.get("rol_en_texto") or "").upper() not in {"FRASE_TECNICA", "NO_APARECE"}:
            m.append("contradiccion:artefacto-con-fuerte-senal-de-sujeto")
        # RADIO DE IMPACTO: si ese término etiqueta ya cientos de chunks como
        # product_model, no darlo de alta deja esos chunks apuntando a un producto que no
        # existe en el catálogo. La pregunta «producto o artefacto» no cubre esa
        # consecuencia — y es de Alberto, no del juez. Umbral deliberadamente alto para
        # no vaciar el bloque por unos pocos chunks.
        if ev["chunks_pm_exacto"] >= PM_MASIVO and estr == 0 and may == 0:
            m.append(f"atencion:etiqueta-{ev['chunks_pm_exacto']}-chunks-sin-aparecer-"
                     f"verbatim")
    return m


# ─────────────────────────── orquestación ───────────────────────────

def _cargar_cache() -> dict:
    if CACHE.exists():
        try:
            return json.loads(CACHE.read_text(encoding="utf-8"))
        except Exception:                                            # noqa: BLE001
            return {}
    return {}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limite", type=int, default=0, help="smoke: primeras N filas")
    ap.add_argument("--sin-llm", action="store_true", help="sólo señales duras")
    ap.add_argument("--salida", default=str(DESTINO))
    args = ap.parse_args()

    filas = [json.loads(l) for l in DRAFT.read_text(encoding="utf-8").splitlines() if l.strip()]
    if args.limite:
        filas = filas[:args.limite]

    # --- contexto de colisiones (catálogo gobernado, SOLO LECTURA) + del propio draft --
    prods = {p["id"] for p in _read_jsonl(CATALOG_DIR / "products.jsonl")}
    alias_ajenos = {_fold(a["alias"]): a["id"]
                    for a in _read_jsonl(CATALOG_DIR / "aliases.jsonl") if a.get("alias")}
    grafias, fabs = defaultdict(set), defaultdict(set)
    for f in filas:
        grafias[f["id"]].add(f["canonical_model"].strip())
        fabs[_fold(f["canonical_model"])].add(f["id"].split(":")[0])
    ctx = {"ids_en_catalogo": prods, "alias_ajenos": alias_ajenos,
           "grafias_por_id": grafias, "fabricantes_por_termino": fabs}

    cliente = None if args.sin_llm else anthropic.Anthropic(
        api_key=os.environ["ANTHROPIC_API_KEY"], timeout=180.0, max_retries=2)
    cache = _cargar_cache()
    hechas = [0]

    def procesar(i_f):
        i, f = i_f
        clave = f"{f['id']}|{f['provenance']}"
        ev = recolectar(f)
        if clave in cache and not args.sin_llm:
            v = cache[clave]
        elif args.sin_llm:
            v = {"veredicto": "NO_DECIDIBLE", "confianza": "baja", "cita": None,
                 "razon": "modo --sin-llm"}
        else:
            try:
                v = juzgar(cliente, f, ev)
            except Exception as exc:                                 # noqa: BLE001
                v = {"veredicto": "NO_DECIDIBLE", "confianza": "baja", "cita": None,
                     "razon": f"error-llm: {type(exc).__name__}: {exc}"[:200]}
            with _LOCK_CACHE:
                cache[clave] = v
                CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
        cita_ok = verificar_cita(v, ev)
        if v.get("confianza") == "alta" and not cita_ok:
            # Regla de la casa: alta-sin-cita-verificada NO es alta.
            v["confianza"] = "media"
            v["nota_degradacion"] = "cita no verificada a texto completo → alta degradada a media"
        motivos = clasificar(f, ev, v, cita_ok, ctx)
        hechas[0] += 1
        print(f"  {hechas[0]}/{len(filas)} {ev['termino']!r} -> {v.get('veredicto')} "
              f"({v.get('confianza')}) cita={'ok' if cita_ok else 'NO'} "
              f"{'BLOQUE' if not motivos else motivos[0]}", flush=True)
        return {
            "id": f["id"], "canonical_model": f["canonical_model"],
            "provenance": f["provenance"],
            "documento": {k: (ev.get("documento") or {}).get(k)
                          for k in ("id", "source_pdf_filename", "status",
                                    "product_model", "manufacturer", "doc_type")},
            "senales": {
                "menciones_doc": ev["menciones_doc"],
                "menciones_muestra_global": ev["menciones_muestra_global"],
                "chunks_con_product_model_exacto": ev["chunks_pm_exacto"],
                "chunks_con_product_model_parecido": ev["chunks_pm_parecido"],
                "documentos_con_product_model": ev["docs_con_pm"],
                "documentos_con_termino_en_filename": ev["docs_con_termino_en_filename"],
                "termino_en_filename_del_doc": ev["termino_en_filename"],
                "n_chunks_doc": ev["n_chunks_doc"],
                "filas_mismo_fichero": ev["filas_mismo_fichero"],
            },
            "llm": v, "cita_verificada": cita_ok,
            "pasajes": ev["pasajes"],
            "motivos_individual": motivos,
            "seccion": 0 if not motivos else 1,
        }

    with ThreadPoolExecutor(HILOS) as ex:
        res = list(ex.map(procesar, enumerate(filas)))

    # --- post-pase de COHERENCIA POR ID -------------------------------------------
    # La unidad de decisión es el ID del catálogo, no la fila del draft: las 133 filas
    # encierran 99 ids (el mismo producto propuesto desde varios manuales). Aprobar en
    # bloque una fila cuyo gemelo está en individual sería pedirle a Alberto la MISMA alta
    # dos veces, con dos respuestas distintas. Un id que no es unánime va entero a
    # individual.
    por_id = defaultdict(list)
    for r in res:
        por_id[r["id"]].append(r)
    for grupo in por_id.values():
        if len({r["llm"].get("veredicto") for r in grupo}) > 1:
            for r in grupo:
                if "ambiguedad:veredictos-discordantes-para-el-mismo-id" not in r["motivos_individual"]:
                    r["motivos_individual"].append(
                        "ambiguedad:veredictos-discordantes-para-el-mismo-id")
        elif any(r["motivos_individual"] for r in grupo):
            for r in grupo:
                if not r["motivos_individual"]:
                    r["motivos_individual"].append(
                        "coherencia:otra-fila-del-mismo-id-no-entra-en-bloque")
        for r in grupo:
            r["seccion"] = 0 if not r["motivos_individual"] else 1

    bloque = [r for r in res if r["seccion"] == 0]
    individual = [r for r in res if r["seccion"] == 1]
    bloque_alta = [r for r in bloque if r["llm"]["veredicto"] == "PRODUCTO_REAL"]
    bloque_retirar = [r for r in bloque if r["llm"]["veredicto"] != "PRODUCTO_REAL"]

    por_veredicto = Counter(r["llm"].get("veredicto") for r in res)
    por_rol = Counter(r["llm"].get("rol_en_texto") for r in res)
    por_motivo = Counter(m for r in individual for m in r["motivos_individual"])

    # --- HALLAZGOS: lo que Alberto quiere ver aunque no cambie ninguna casilla ------
    # La clase de fallo importa más que el recuento: un artefacto nacido de una frase
    # («some 58») y uno nacido del código del propio manual («MA-DT-015») se previenen en
    # sitios distintos del extractor.
    artefactos = [r for r in res
                  if r["llm"].get("veredicto") in {"ARTEFACTO_EXTRACCION",
                                                   "NORMA_O_CERTIFICACION"}]
    def _muestra(rol):
        return [{"termino": r["canonical_model"], "id": r["id"],
                 "doc": r["documento"]["source_pdf_filename"],
                 "cita": r["llm"].get("cita"), "razon": r["llm"].get("razon"),
                 "chunks_etiquetados": r["senales"]["chunks_con_product_model_exacto"]}
                for r in artefactos if (r["llm"].get("rol_en_texto") or "") == rol]
    hallazgos = {
        "artefactos_detectados": len(artefactos),
        "ids_unicos_afectados": len({r["id"] for r in artefactos}),
        "por_clase": {
            "codigo_del_propio_documento": _muestra("CODIGO_DE_DOCUMENTO"),
            "frase_tecnica_o_corriente": _muestra("FRASE_TECNICA"),
            "nombre_de_fabricante_o_gama": _muestra("NOMBRE_DE_FABRICANTE_O_GAMA"),
            "no_aparece_en_ningun_sitio": _muestra("NO_APARECE"),
        },
        "chunks_etiquetados_por_terminos_artefacto": sum(
            r["senales"]["chunks_con_product_model_exacto"]
            for r in {r["id"]: r for r in artefactos}.values()),
    }

    recibo = {
        "que_es": ("PROPUESTA de triage de la SECCIÓN 3 del packet E1 (133 altas "
                   "candidate). NADA aplicado: ni catálogo, ni Supabase, ni el snapshot "
                   "del detector. SECCIÓN 0 = un solo sí de Alberto; SECCIÓN 1 = residuo "
                   "individual con la evidencia junta."),
        "utc": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "modelo_juez": MODELO, "fuente": str(DRAFT.relative_to(ROOT)),
        "metodo": {
            "muestreo": "dirigido — chunks que MENCIONAN el término (ilike + recorte por "
                        "regex con frontera de palabra), no los primeros del documento",
            "senales_duras": "menciones estrictas / flexibles(separadores) / en MAYÚSCULAS: "
                             "la diferencia entre ellas separa producto de artefacto",
            "verificacion_citas": "cita ENTERA (≤200 chars) contra el contenido COMPLETO "
                                  "del doc de origen + los chunks muestreados, normalizando "
                                  "espacios y caja",
            "degradacion": "confianza alta sin cita verificada → media → fuera del bloque",
        },
        "resumen": {
            "total": len(res),
            "seccion_0_bloque": len(bloque),
            "seccion_0a_alta_en_bloque": len(bloque_alta),
            "seccion_0b_retirar_en_bloque": len(bloque_retirar),
            "seccion_1_individual": len(individual),
            "por_veredicto": dict(por_veredicto.most_common()),
            "por_rol_en_texto": dict(por_rol.most_common()),
            "motivos_individual": dict(por_motivo.most_common()),
            "ids_unicos_en_el_draft": len({r["id"] for r in res}),
            "ids_unicos_en_bloque": len({r["id"] for r in bloque}),
            "ids_unicos_en_individual": len({r["id"] for r in individual}),
        },
        "hallazgos": hallazgos,
        "seccion_0a_alta_en_bloque": sorted(bloque_alta, key=lambda r: r["id"]),
        "seccion_0b_retirar_en_bloque": sorted(bloque_retirar, key=lambda r: r["id"]),
        "seccion_1_individual": sorted(
            individual, key=lambda r: (r["motivos_individual"][0], r["id"])),
    }
    destino = Path(args.salida)
    destino.write_text(json.dumps(recibo, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\ntotal {len(res)} · bloque {len(bloque)} "
          f"(alta {len(bloque_alta)} / retirar {len(bloque_retirar)}) · "
          f"individual {len(individual)}")
    print(f"recibo -> {destino}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
