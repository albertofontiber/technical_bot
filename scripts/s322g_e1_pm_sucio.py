#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""s322g — §4 del packet E1: los 4 documentos con `product_model` SUCIO.

QUÉ RESUELVE
------------
`evals/s320_e1_packet_adjudicacion_v1.md` §4 aparta 4 manuales cuyo `product_model` no es
un producto sino BASURA ESTRUCTURAL: una norma (`EN54 2-8 Zone`, `EN-54-3`), una fecha
(`MARCH-2011`) o el literal `unknown`. El filtro léxico de E1a los mandó al cubo
«no_producto» y ahí se quedaron, sin fila en `doc_map`.

El riesgo NO es el que parece. Que el pm sea basura es lo de menos: lo grave es que un
pm-norma puede estar TAPANDO un producto real. El caso histórico del repo se ve en el
propio nombre del cuarto fichero — `d686 ema1224b4r_w ns4r` con pm `EN-54-3`: el modelo
está en el nombre y en el título del documento, y el pm dice «norma». Esta clase de fallo
es silenciosa: el documento existe, se ingesta, y queda inalcanzable por su modelo.

POR QUÉ ESTE DISEÑO (y no «pregúntale al LLM y ya»)
---------------------------------------------------
Un juez suelto sobre el texto inventa modelos plausibles. Aquí el LLM sólo PROPONE, y la
decisión bloque/individual la toman gates DETERMINISTAS sobre evidencia dura:

  1. **Texto completo, no muestra.** Los 4 documentos son pequeños (27, 2, 1 y 1 chunks):
     caben enteros en el prompt. El muestreo dirigido (lección: mandar los chunks que
     MENCIONAN el término diana, no los primeros del documento) queda implementado en
     `_muestra_para_prompt` para el caso en que un documento no quepa — pero con estos 4
     no se activa, y el recibo declara cuál de las dos ramas se usó.
  2. **Censo de corpus por token.** Para cada candidato a modelo que aparece IMPRESO en el
     documento se mide cuántos OTROS documentos lo mencionan y con qué pm. Un modelo que
     sólo existe en este documento y otro que aparece en 30 no son la misma evidencia.
  3. **Hermanos por nombre de fichero.** Los documentos de una misma serie comercial
     comparten tokens de nombre. Es el seam que destapa la convención ya vigente: el
     hermano `I560849010EMA24ALRANS4REng` («EMA24ALR AND EMA24ALW») ya está adjudicado en
     `doc_map` como DOS productos (R y W) — o sea, el patrón R/W del cuarto fichero tiene
     precedente resuelto en el propio repo, no hay que inventarlo.
  4. **Serie de códigos de documento.** Cuando el documento NO imprime ningún modelo (caso
     `997-493-002-2`), el único ancla externo es su código de documento: se censa la SERIE
     completa (`997-*`) en el corpus para ver qué producto documenta cada número vecino.
  5. **K=3 con unanimidad.** Un solo pase de un juez no es un veredicto. Se corre 3 veces y
     sólo el acuerdo unánime (veredicto + conjunto de modelos) puede ir a bloque.

GATES DE BLOQUE (los relaja nadie; si uno falla, la fila va a individual y punto)
--------------------------------------------------------------------------------
  G1 `k_unanime`            — 3/3 el mismo veredicto y el mismo conjunto de modelos.
  G2 `citas_verificadas`    — la cita ENTERA (hasta 200 chars) de las 3 pasadas aparece en
                              el texto COMPLETO del documento, con espacios normalizados.
                              Verificar sólo un prefijo dejó pasar una invención real: la
                              cola parafraseada por el modelo no estaba en el documento.
  G3 `confianza_alta`       — las 3 pasadas dicen «alta». Si una dice alta pero su cita NO
                              verifica, se DEGRADA a media antes de mirar el gate.
  G4 `modelos_atestiguados` — cada modelo propuesto aparece VERBATIM en el documento. Un
                              modelo deducido de otro documento (por vecindad de código,
                              por familia) es una HIPÓTESIS, no un hecho: va a individual
                              con toda su evidencia, nunca a bloque.
  G5 `mantener_sin_tapado`  — para MANTENER: el documento no puede contener NINGÚN
                              candidato que el catálogo resuelva. Si lo contuviera, el pm
                              actual podría estar tapando un producto real, que es
                              exactamente el fallo que esta sección existe para cazar.

SOLO LECTURA — CONTRATO DURO
----------------------------
No escribe en `data/catalog/*.jsonl`, ni en Supabase (cero PATCH/POST/DELETE), ni en
`data/model_catalog.json`. Todas las llamadas HTTP son GET. Único efecto: el recibo en
`evals/`. Es una PROPUESTA para que Alberto adjudique.

USO
---
    python scripts/s322g_e1_pm_sucio.py
    python scripts/s322g_e1_pm_sucio.py --k 3 --salida evals/otro.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=False)

import anthropic  # noqa: E402

from src.http_pool import abierto  # noqa: E402
# Catálogo gobernado: SOLO LECTURA. Se reutiliza el resolver CANÓNICO (`Catalog.resolve`)
# en vez de reimplementar el matching: una segunda definición de «este token es un
# producto» divergiría en silencio de la que usa el serving.
from src.rag.catalog_store import load as cargar_catalogo, norm_token  # noqa: E402

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
H = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}

MODELO = "claude-fable-5"
# max_tokens: 800 es el mínimo ya pagado (con 400 el JSON del modelo se TRUNCA y produce
# «parse-fail» que se confunden con incertidumbre). Aquí pedimos además `razon` y
# `residuo` largos, así que 1600. NUNCA se pasa `temperature`: deprecado en los modelos
# 2026 (error 400).
MAX_TOKENS = 1600

FUENTE = ROOT / "evals" / "s320_e1_docmap_derivacion_v2_detalle.json"
PACKET = ROOT / "evals" / "s320_e1_packet_adjudicacion_v1.md"
SALIDA_DEFAULT = ROOT / "evals" / "s322g_e1_pm_sucio_v1.json"

# Gate de DRIFT: el packet §4 nombra estos 4 y sólo estos. Si el fichero fuente ya no los
# tiene (porque alguien aplicó algo entre medias), el recibo lo DECLARA en vez de trabajar
# en silencio sobre un censo caducado.
ESPERADOS = {
    "997-493-002-2",
    "asd in rail transportation applications_es",
    "compatibilidad-entre-equipos-notifier-y-morley",
    "d686 ema1224b4r_w ns4r",
}

# Techo de texto que se manda entero al juez. Por encima, muestreo DIRIGIDO (chunks que
# mencionan los candidatos), nunca «los primeros N chunks»: la evidencia de modelo suele
# vivir en tablas a mitad de manual, no en la portada.
TECHO_TEXTO_ENTERO = 45_000


# ─────────────────────────── utilidades de lectura ───────────────────────────

def _norm(texto: str) -> str:
    """Normalización de espacios para comparar citas contra el texto fuente: minúsculas y
    espacios colapsados. Es la única transformación admisible — cualquier otra (quitar
    puntuación, acentos) haría pasar paráfrasis por citas."""
    return re.sub(r"\s+", " ", (texto or "")).strip().lower()


def _get(cliente, tabla: str, params: dict) -> list[dict]:
    r = cliente.get(f"{SUPABASE_URL}/rest/v1/{tabla}", headers=H, params=params)
    r.raise_for_status()
    return r.json()


def _paginado(cliente, tabla: str, params: dict, pagina: int = 1000) -> list[dict]:
    """GET paginado. Sin esto, un `limit` por defecto miente por omisión: devolvería un
    subconjunto y el censo contaría de menos sin avisar."""
    filas, offset = [], 0
    while True:
        lote = _get(cliente, tabla, {**params, "limit": str(pagina), "offset": str(offset)})
        filas.extend(lote)
        if len(lote) < pagina:
            return filas
        offset += pagina


def _chunks_del_doc(cliente, document_id: str) -> list[dict]:
    return _paginado(cliente, "chunks_v2", {
        "select": "chunk_index,page_number,source_file,content,product_model,"
                  "manufacturer,category,language",
        "document_id": f"eq.{document_id}", "order": "chunk_index.asc"}, pagina=200)


def _escapa_ilike(t: str) -> str:
    """PostgREST usa `*` como comodín en ilike; `%` y `_` son comodines de SQL. Un token
    con `_` (los hay: nombres de fichero) buscaría de más si no se escapa."""
    return t.replace("%", r"\%").replace("_", r"\_")


# ─────────────────── candidatos a modelo impresos en el documento ───────────────────

# Un «candidato a modelo» es un token alfanumérico con forma de referencia comercial:
# letras seguidas de dígitos (EMA1224B4R, NFS8REL, FL2011EI), opcionalmente con guiones o
# barras. Se extrae del TEXTO (nunca de la metadata: la metadata es justo lo que estamos
# auditando y creerla sería razonar en círculo).
RX_CANDIDATO = re.compile(r"\b[A-Z][A-Z]{1,6}[0-9]{2,5}[A-Z0-9]{0,6}(?:[/\-][A-Z0-9]{1,8})*\b")
# Códigos de documento: 997-493-002-2, MI-DT-015, D686, I56-6575-005, A05-7030-000.
RX_CODIGO_DOC = re.compile(r"\b(?:[A-Z]{1,4}[\- ]?)?\d{2,4}(?:-\d{1,4}){1,3}\b")

# Blocklist DECLARADA (con motivo) de tokens con forma de modelo que NO son productos.
# Se mantiene explícita y corta: cada entrada es una clase de falso positivo observada en
# el corpus de PCI, no una lista defensiva inventada.
NO_SON_MODELOS = {
    # normas y sus partes: la clase que da nombre a esta sección
    "EN54", "EN540", "EN5420", "EN5411", "EN542", "EN543", "EN544", "EN5414",
    "EN5416", "EN5417", "EN5418", "EN5425", "EN5426", "EN5427", "EN12094",
    "UNE23007", "ISO7240", "BS5839", "IEC60529", "NFPA72",
    # unidades, grados de protección y protocolos genéricos
    "IP21C", "IP54", "IP65", "IP66", "IP67", "VDC", "VAC", "RS485", "RS232",
    "MODBUS", "RJ45", "USB20", "IP64", "IP44", "IP30",
}
# Meses: `MARCH-2011` es literalmente uno de los 4 pm sucios de esta sección (salió de una
# nota al pie «Manchester Evening News, March 2011»). El diagnóstico del bucket unknown
# (`scripts/diagnose_unknown_bucket.py`) ya tenía censada esta clase.
RX_FECHA = re.compile(
    r"^(ENERO|FEBRERO|MARZO|ABRIL|MAYO|JUNIO|JULIO|AGOSTO|SEPTIEMBRE|OCTUBRE|NOVIEMBRE|"
    r"DICIEMBRE|JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|"
    r"NOVEMBER|DECEMBER)[\-\s]?\d{4}$", re.I)


# Segunda fuente de candidatos: PALABRAS que el catálogo gobernado reconoce. La regex de
# arriba exige dígitos, así que se le escapan las familias puramente alfabéticas — y una de
# ellas (`FAAST`) es justo el nombre del producto del segundo documento de esta sección. El
# primer pase de este script salió `candidatos: []` para ese documento y el juez razonó "el
# catálogo no lo resolvió" sobre una lista vacía que era un artefacto de MI regex.
RX_PALABRA = re.compile(r"\b[A-Za-z][A-Za-z0-9]{2,}(?:[/\-][A-Za-z0-9]+)*\b")
# Pero una palabra suelta NO puede consumirse por cualquier vía: el catálogo arrastra alias
# `nombre-largo` de f1-bulk que son palabras corrientes ("Light", "ONE", "Solo", "verde",
# "amarillo", "CARGADOR"). Medido sobre estos 4 documentos, la vía `alias` metió 6 falsos
# positivos y 0 verdaderos; `exact` y `paraguas` metieron 1 verdadero (FAAST) y 0 falsos.
# Un modelo real que sólo viva como alias NO se pierde: tiene forma de modelo y lo caza
# RX_CANDIDATO, que sí acepta cualquier vía.
VIAS_FIABLES_PARA_PALABRA = {"exact", "paraguas"}


def _candidatos_impresos(texto: str, cat=None) -> list[str]:
    """Tokens que aparecen IMPRESOS en el texto y pueden ser un producto.

    Dos fuentes complementarias: forma de modelo (regex) y reconocimiento por el catálogo
    gobernado (palabras). Ninguna metadata entra aquí: la metadata es justo lo que estamos
    auditando, y usarla sería razonar en círculo."""
    vistos: dict[str, str] = {}
    negros = {norm_token(x) for x in NO_SON_MODELOS}
    for m in RX_CANDIDATO.finditer(texto):
        t = m.group(0)
        n = norm_token(t)
        if n in negros or RX_FECHA.match(t):
            continue
        if re.match(r"^EN\-?54", t, re.I):          # EN54-3, EN-54-20, EN5420…
            continue
        vistos.setdefault(n, t)                     # conserva la PRIMERA grafía impresa
    if cat is not None:
        for m in RX_PALABRA.finditer(texto):
            t = m.group(0)
            n = norm_token(t)
            if n in vistos or n in negros or RX_FECHA.match(t):
                continue
            r = cat.resolve(t)
            if r and r.get("ids") and r.get("via") in VIAS_FIABLES_PARA_PALABRA:
                vistos[n] = t
    return list(vistos.values())


def _codigos_documento(texto: str) -> list[str]:
    vistos: dict[str, str] = {}
    for m in RX_CODIGO_DOC.finditer(texto):
        t = m.group(0).strip()
        if RX_FECHA.match(t) or re.match(r"^EN", t, re.I):
            continue
        vistos.setdefault(norm_token(t), t)
    return list(vistos.values())


# ───────────────────────── evidencia de corpus (censos) ─────────────────────────

def _censo_token(cliente, token: str, document_id: str, tope: int = 400) -> dict:
    """¿Qué OTROS documentos del corpus mencionan este token, y con qué pm?

    Es la diferencia entre «modelo real que vive en el corpus» y «cadena que sólo aparece
    en este PDF». No decide por sí sola (un modelo puede ser legítimo y único), pero es la
    señal que separa una referencia comercial de un artefacto de extracción."""
    filas = _paginado(cliente, "chunks_v2", {
        "select": "document_id,source_file,product_model",
        "content": f"ilike.*{_escapa_ilike(token)}*"}, pagina=tope)
    otros: dict[str, str] = {}
    propio = 0
    for f in filas:
        if f["document_id"] == document_id:
            propio += 1
        else:
            otros.setdefault(f.get("source_file") or "?", f.get("product_model") or "∅")
    return {"chunks_en_este_doc": propio,
            "otros_documentos": len(otros),
            "muestra_otros": [{"source_file": k, "pm": v}
                              for k, v in list(otros.items())[:8]]}


# Palabras de nombre de fichero que no identifican serie alguna (buscar por ellas traería
# medio corpus). Lista corta y declarada; el gate real es el tope de resultados.
RUIDO_NOMBRE = {
    "manual", "manu", "user", "usuario", "guide", "guia", "instalacion", "installation",
    "eng", "esp", "ita", "fra", "spanish", "english", "italiano", "issue", "rev",
    "applications", "aplicaciones", "entre", "equipos", "para", "con", "los", "las",
    "product", "sheet", "data", "technical", "tecnico", "lores", "a4",
}


def _hermanos_por_nombre(cliente, source_file: str, document_id: str,
                         doc_map_por_id: dict) -> list[dict]:
    """Documentos cuyo NOMBRE DE FICHERO comparte un token con el nuestro.

    Los fabricantes de PCI nombran los PDF de una misma serie con el mismo prefijo o el
    mismo código. Este censo es el que hace visible la CONVENCIÓN YA VIGENTE del repo:
    cómo están etiquetados los hermanos de este documento. Sin él, cada fila se decidiría
    de cero e inventaríamos criterios nuevos en cada sesión.

    Dos cosas aprendidas en el primer pase de este mismo script:

    - **Longitud mínima 3, no 4.** Los tokens que identifican SERIE son cortos: `ASD` (la
      colección de folletos de aplicación) y `997` (la numeración de documento de Notifier
      España). Con el corte en 4 caracteres, dos de los cuatro documentos salieron con
      `hermanos: []` y el juez decidió a ciegas sobre una serie que sí existe en el corpus.
    - **Se adjunta el `doc_map` del hermano, no sólo su `product_model`.** El pm del hermano
      puede estar TAN sucio como el nuestro (el hermano de `d686` lleva pm `ECO-2000`, que
      es el sistema con el que se instala, no el producto), mientras que su fila de
      `doc_map` ya está ADJUDICADA. La convención gobernada vive en el doc_map."""
    tokens = [t for t in re.split(r"[^A-Za-z0-9]+", source_file)
              if len(t) >= 3 and t.lower() not in RUIDO_NOMBRE]
    salida: dict[str, dict] = {}
    for t in tokens:
        filas = _get(cliente, "documents", {
            "select": "id,source_pdf_filename,product_model,manufacturer,status",
            "source_pdf_filename": f"ilike.*{_escapa_ilike(t)}*", "limit": "40"})
        if len(filas) >= 40:      # token demasiado genérico: no identifica serie
            continue
        for f in filas:
            if f["id"] == document_id:
                continue
            dm = doc_map_por_id.get(f["id"])
            salida.setdefault(f["id"], {
                "por_token": t,
                **{k: f.get(k) for k in ("source_pdf_filename", "product_model",
                                         "manufacturer", "status")},
                "doc_map_adjudicado": ([e.get("id") for e in (dm.get("entries") or [])]
                                       if dm else None)})
    return list(salida.values())[:20]


def _serie_de_codigos(cliente, codigos: list[str]) -> dict:
    """Censo de la SERIE de códigos de documento del fabricante (p.ej. `997-*`).

    Sólo se activa cuando el documento NO imprime ningún candidato a modelo: ahí el código
    de documento es el ÚNICO ancla externo, y saber qué producto documenta cada número
    vecino de la serie es lo que convierte un «ni idea» en una hipótesis con nombre. Nunca
    es prueba de identidad (un número vecino NO es el mismo número), y por eso su resultado
    jamás abre el gate de bloque: alimenta la fila individual."""
    fuera: dict[str, dict] = {}
    for cod in codigos:
        prefijo = cod.split("-")[0]
        if not re.fullmatch(r"\d{3,4}", prefijo):
            continue
        filas = _paginado(cliente, "chunks_v2", {
            "select": "source_file,product_model,content",
            "content": f"ilike.*{_escapa_ilike(prefijo)}-*"}, pagina=1000)
        rx = re.compile(rf"\b{re.escape(prefijo)}-\d{{2,4}}(?:-\d{{2,4}})*(?:-\d)?\b")
        mapa: dict[str, dict] = {}
        for f in filas:
            for c in set(rx.findall(f.get("content") or "")):
                mapa.setdefault(c, {"source_file": f.get("source_file"),
                                    "pm": f.get("product_model")})
        fuera[prefijo] = {"n_codigos": len(mapa),
                          "mapa": dict(sorted(mapa.items())[:40])}
    return fuera


def _resolver_en_catalogo(cat, token: str) -> dict | None:
    """¿El catálogo gobernado conoce este token? Devuelve la traza del resolver canónico."""
    r = cat.resolve(token)
    return None if r is None else {"token": token, **{k: v for k, v in r.items()}}


# ───────────────────────────── juez (LLM) ─────────────────────────────

PROMPT = """Eres un técnico de PCI (protección contra incendios) auditando la METADATA de
un corpus documental. Un documento tiene el campo `product_model` SUCIO: en vez de un
producto contiene basura (una norma, una fecha, o el literal "unknown").

Tu tarea: decidir cuál DEBERÍA ser el `product_model` de este documento.

REGLA INNEGOCIABLE — un modelo sólo cuenta si está IMPRESO en el texto del documento que
te doy. Si el modelo sólo se DEDUCE (de otro documento, de la familia, de la vecindad de
un código), el veredicto es NO_DECIDIBLE y explicas la hipótesis en `razon`. Inventar o
aproximar un modelo destruye la confianza del sistema entero. La cita se verifica después
carácter a carácter contra el documento completo: si no la copias literal, se detecta.

DOCUMENTO
  fichero .......... {source_file}
  product_model .... {pm_actual}   <-- el valor SUCIO que hay que juzgar
  fabricante ....... {manufacturer}
  nº de chunks ..... {n_chunks}

TEXTO DEL DOCUMENTO ({modo_muestra})
<<<
{texto}
>>>

CANDIDATOS A MODELO impresos en el texto (extraídos por regex; censo del resto del corpus
y resolución contra el catálogo gobernado):
{candidatos}

HERMANOS por nombre de fichero (cómo está etiquetado lo que se le parece — es la
convención ya vigente del repo, úsala). OJO: `product_model` del hermano puede estar tan
sucio como el nuestro; `doc_map_adjudicado` es la verdad GOBERNADA (null = sin adjudicar):
{hermanos}

CONTEXTO ADICIONAL (puede estar vacío; NUNCA basta por sí solo para un RETAG):
{extra}

VEREDICTOS POSIBLES
  RETAG        — el documento imprime UN producto claro: `product_model` debe ser ese.
  MULTI        — el documento imprime VARIOS productos al mismo nivel (lista completa).
  MANTENER     — el valor actual es el correcto posible: el documento NO trata de ningún
                 producto concreto (p.ej. una FAQ de marca a marca). "unknown" puede ser
                 la respuesta HONESTA; no fuerces un modelo donde no lo hay.
  NO_DECIDIBLE — hay hipótesis pero ningún modelo impreso que la sostenga.

Responde SOLO con este JSON, sin texto alrededor:
{{"veredicto": "RETAG|MULTI|MANTENER|NO_DECIDIBLE",
  "product_model_propuesto": ["..."],
  "cita": "fragmento VERBATIM del texto de arriba, <=200 caracteres, que sostiene el veredicto",
  "confianza": "alta|media|baja",
  "razon": "por qué; si hay hipótesis no probada, nómbrala aquí explícitamente",
  "residuo": "pregunta abierta que tu veredicto NO cubre, o null"}}"""


def _muestra_para_prompt(chunks: list[dict], texto: str, candidatos: list[str]) -> tuple[str, str]:
    """Texto entero si cabe; si no, muestreo DIRIGIDO a los chunks que mencionan los
    candidatos (jamás «los primeros N»: la evidencia de modelo vive en tablas a mitad de
    manual). Devuelve (texto, etiqueta del modo) — el recibo declara cuál se usó."""
    if len(texto) <= TECHO_TEXTO_ENTERO:
        return texto, f"documento COMPLETO, {len(texto)} chars, {len(chunks)} chunks"
    diana = [c for c in chunks
             if any(t.lower() in (c.get("content") or "").lower() for t in candidatos)]
    if not diana:
        diana = chunks[:6]
    trozos = [f"[chunk {c['chunk_index']} p{c.get('page_number')}]\n{c.get('content') or ''}"
              for c in diana[:20]]
    return ("\n...\n".join(trozos)[:TECHO_TEXTO_ENTERO],
            f"muestreo DIRIGIDO a {len(diana)} chunks que mencionan candidatos")


def _juzgar(cliente_llm, prompt: str) -> dict:
    msg = cliente_llm.messages.create(
        model=MODELO, max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}])
    texto = "".join(b.text for b in msg.content
                    if getattr(b, "type", "") == "text").strip()
    try:
        return json.loads(texto[texto.index("{"):texto.rindex("}") + 1])
    except Exception:                                        # noqa: BLE001
        # Un parse-fail es un NO_DECIDIBLE honesto, no una incertidumbre del modelo: se
        # marca como tal para que no se confunda con un juicio real (y se guarda el crudo).
        return {"veredicto": "NO_DECIDIBLE", "product_model_propuesto": [], "cita": None,
                "confianza": "baja", "razon": "parse-fail", "residuo": None,
                "raw": texto[:400]}


def _firma(v: dict) -> tuple:
    """Firma comparable de un juicio: veredicto + conjunto normalizado de modelos. Es lo
    que tiene que coincidir en las K pasadas para que la fila pueda ir a bloque."""
    modelos = v.get("product_model_propuesto") or []
    if isinstance(modelos, str):
        modelos = [modelos]
    return (str(v.get("veredicto")), tuple(sorted(norm_token(str(m)) for m in modelos)))


# ───────────────────────── gates deterministas ─────────────────────────

def _atestiguado(modelo: str, texto_norm: str, texto_compacto: str) -> dict:
    """¿El modelo propuesto está IMPRESO en el documento?

    - `estricto`: la cadena tal cual (minúsculas, espacios colapsados). Es el gate.
    - `laxo`: sin espacios ni separadores (norm_token). Sólo INFORMA — un match laxo puede
      venir de un corte de OCR ("EN54 2- 8") y no basta para escribir metadata."""
    m = (modelo or "").strip()
    return {"modelo": m,
            "estricto": bool(m) and _norm(m) in texto_norm,
            "laxo": bool(m) and norm_token(m) in texto_compacto}


def _decidir(juicios: list[dict], texto_norm: str, texto_compacto: str,
             candidatos_resueltos: list[dict]) -> dict:
    """LOS GATES. Devuelve `{destino, gates, motivo}` — nunca los decide el LLM."""
    firmas = {_firma(v) for v in juicios}
    g1 = len(firmas) == 1
    g2 = all(v.get("_cita_verificada") for v in juicios)
    g3 = all(v.get("confianza") == "alta" for v in juicios)

    principal = juicios[0]
    veredicto = str(principal.get("veredicto"))
    modelos = principal.get("product_model_propuesto") or []
    if isinstance(modelos, str):
        modelos = [modelos]
    atest = [_atestiguado(m, texto_norm, texto_compacto) for m in modelos]

    if veredicto in {"RETAG", "MULTI"}:
        g4 = bool(atest) and all(a["estricto"] for a in atest)
    else:
        g4 = True                          # no hay modelo que atestiguar
    # G5: un MANTENER sólo es seguro si NO hay ningún candidato que el catálogo reconozca;
    # si lo hubiera, el pm actual podría estar TAPANDO un producto real.
    g5 = veredicto != "MANTENER" or not candidatos_resueltos

    gates = {"k_unanime": g1, "citas_verificadas": g2, "confianza_alta": g3,
             "modelos_atestiguados": g4, "mantener_sin_tapado": g5}
    fallidos = [k for k, v in gates.items() if not v]
    if veredicto == "NO_DECIDIBLE":
        return {"destino": "individual", "gates": gates, "atestacion": atest,
                "motivo": "NO_DECIDIBLE: ningún modelo impreso sostiene la hipótesis"}
    if fallidos:
        return {"destino": "individual", "gates": gates, "atestacion": atest,
                "motivo": "gates que fallan: " + ", ".join(fallidos)}
    return {"destino": "bloque", "gates": gates, "atestacion": atest,
            "motivo": "veredicto unánime K=3, cita verificada full-text y modelo(s) "
                      "impresos verbatim en el documento"}


def _propuesta_de_aplicacion(fila: dict, veredicto: str, modelos: list[str],
                             n_chunks: int, en_doc_map: bool,
                             ids_catalogo: list[str], vias: set[str]) -> dict:
    """Qué se escribiría EXACTAMENTE si Alberto dice que sí. Explicitarlo es parte del
    contrato: un «sí» en bloque tiene que ser un sí a algo concreto, no a una intención.

    El `doc_map` es una capa DISTINTA del `product_model` y no se propone en automático:

    - Vía **paraguas**: `resolve('FAAST')` devuelve los 13 miembros de la familia, y la
      primera versión de esta función los volcaba como 13 `primary/scope:doc`. Eso es
      FALSO y contaminaría el retrieval: un folleto de familia no documenta cada SKU. Los
      hermanos ya adjudicados de esa misma colección (`ASD Harsh Environments_SP`,
      `ASD Cold Environments_SP`) no tienen fila de doc_map — la convención vigente es
      dejarlos sin mapear. Además `entries[].id` exige un id de PRODUCTO (`marca:slug`) y
      un paraguas no lo es: es un `termino`.
    - Vía **exact/alias**: el id es unívoco y la propuesta es concreta.
    - **Sin resolver**: alta bloqueada hasta dar de alta el producto (decisión aparte)."""
    if veredicto in {"MANTENER", "NO_DECIDIBLE"}:
        return {"documents.product_model": "SIN CAMBIO",
                "chunks_v2.product_model": "SIN CAMBIO",
                "doc_map": ("sin fila (correcto: no hay producto que mapear)"
                            if not en_doc_map else "fila existente intacta"),
                "aviso": "NADA que aplicar; el valor actual se conserva."}
    nuevo = modelos[0] if len(modelos) == 1 else "/".join(modelos)
    if "paraguas" in vias:
        doc_map = ("NO se propone alta. El modelo es un PARAGUAS (familia) y "
                   f"resolve() expande {len(ids_catalogo)} miembros que este documento NO "
                   "documenta uno a uno; entries[].id exige id de producto, no un término "
                   "de paraguas. Sus hermanos de colección tampoco tienen fila. "
                   "Mapear la familia es una decisión APARTE.")
    elif ids_catalogo:
        doc_map = "alta de fila " + json.dumps(
            {"document_id": fila["document_id"], "source_file": fila["source_file"],
             "entries": [{"id": i, "role": "primary", "scope": "doc"} for i in ids_catalogo]},
            ensure_ascii=False)
    else:
        doc_map = ("alta de fila BLOQUEADA: el modelo no existe en el catálogo gobernado → "
                   "requiere primero alta de producto (decisión aparte)")
    return {
        "documents.product_model": f"{fila['pm']!r} → {nuevo!r}",
        "chunks_v2.product_model": f"{fila['pm']!r} → {nuevo!r} en {n_chunks} chunks",
        "doc_map": doc_map,
        "aviso": "NADA de esto está aplicado; es la propuesta.",
    }


# ───────────────────────────────── main ─────────────────────────────────

def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                        # noqa: BLE001
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=3, help="pasadas del juez (unanimidad)")
    ap.add_argument("--salida", default=str(SALIDA_DEFAULT))
    args = ap.parse_args()

    detalle = json.loads(FUENTE.read_text(encoding="utf-8"))
    objetivo = detalle["no_producto"]
    drift = {
        "esperados": sorted(ESPERADOS),
        "encontrados": sorted(f["source_file"] for f in objetivo),
        "coinciden": {f["source_file"] for f in objetivo} == ESPERADOS,
    }

    cat = cargar_catalogo()
    doc_map_por_id = {r["document_id"]: r for r in cat.doc_map}
    doc_map_ids = set(doc_map_por_id)

    cliente_llm = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"],
                                      timeout=180.0, max_retries=2)
    filas_salida: list[dict] = []

    with abierto(timeout=90.0) as c:
        for i, fila in enumerate(objetivo, 1):
            did, sf = fila["document_id"], fila["source_file"]
            print(f"[{i}/{len(objetivo)}] {sf}", flush=True)

            doc = (_get(c, "documents", {"select": "*", "id": f"eq.{did}"}) or [None])[0]
            chunks = _chunks_del_doc(c, did)
            texto = "\n".join((x.get("content") or "") for x in chunks)
            texto_norm = _norm(texto)
            texto_compacto = norm_token(texto)

            candidatos = _candidatos_impresos(texto, cat)
            codigos = _codigos_documento(texto)

            # Evidencia dura por candidato: censo en el corpus + resolución en el catálogo.
            evidencia_cand = []
            resueltos = []
            for t in candidatos[:12]:
                res = _resolver_en_catalogo(cat, t)
                if res and res.get("ids"):
                    resueltos.append(res)
                evidencia_cand.append({"token": t, "catalogo": res,
                                       "corpus": _censo_token(c, t, did)})

            hermanos = _hermanos_por_nombre(c, sf, did, doc_map_por_id)

            # La serie de códigos SÓLO se censa cuando el documento no imprime ningún
            # candidato: es caro y sólo aporta donde no hay ancla interna.
            serie = _serie_de_codigos(c, codigos[:4]) if not candidatos else {}

            muestra, modo = _muestra_para_prompt(chunks, texto, candidatos)
            extra = []
            if serie:
                extra.append("Serie de códigos de documento del fabricante en el corpus "
                             "(qué producto documenta cada número vecino). OJO: un número "
                             "VECINO no es el mismo número — esto es hipótesis, no prueba:\n"
                             + json.dumps(serie, ensure_ascii=False, indent=1)[:4000])
            prompt = PROMPT.format(
                source_file=sf, pm_actual=fila["pm"],
                manufacturer=fila.get("manufacturer"), n_chunks=len(chunks),
                modo_muestra=modo, texto=muestra,
                candidatos=json.dumps(evidencia_cand, ensure_ascii=False, indent=1)[:6000]
                           or "ninguno",
                hermanos=json.dumps(hermanos, ensure_ascii=False, indent=1)[:6000]
                         or "ninguno",
                extra="\n\n".join(extra) or "(nada)")

            juicios = []
            for k in range(args.k):
                v = _juzgar(cliente_llm, prompt)
                cita = (v.get("cita") or "")[:200]
                ok = bool(_norm(cita)) and _norm(cita) in texto_norm
                # Lección ya pagada: «alta» con cita que no verifica se DEGRADA a media.
                if v.get("confianza") == "alta" and not ok:
                    v["confianza"] = "media"
                    v["nota"] = "cita no verificada full-text → confianza degradada"
                v["_cita_verificada"] = ok
                juicios.append(v)
                print(f"    pase {k+1}/{args.k}: {v.get('veredicto')} "
                      f"{v.get('product_model_propuesto')} ({v.get('confianza')}"
                      f"{', cita ✓' if ok else ', cita ✗'})", flush=True)
                time.sleep(0.3)

            fallo = _decidir(juicios, texto_norm, texto_compacto, resueltos)
            principal = juicios[0]
            modelos = principal.get("product_model_propuesto") or []
            if isinstance(modelos, str):
                modelos = [modelos]
            ids_cat, vias = [], set()
            for m in modelos:
                r = cat.resolve(m)
                if r and r.get("ids"):
                    ids_cat.extend(r["ids"])
                    vias.add(str(r.get("via")))

            filas_salida.append({
                "source_file": sf,
                "document_id": did,
                "pm_actual": fila["pm"],
                "manufacturer_actual": fila.get("manufacturer"),
                "n_chunks": len(chunks),
                "chars_texto": len(texto),
                "en_doc_map": did in doc_map_ids,
                "source_url": (doc or {}).get("source_url"),
                "status": (doc or {}).get("status"),
                "veredicto": principal.get("veredicto"),
                "product_model_propuesto": modelos,
                "confianza": principal.get("confianza"),
                "cita": (principal.get("cita") or "")[:200],
                "cita_verificada_full_text": principal.get("_cita_verificada"),
                "razon": principal.get("razon"),
                "residuo": principal.get("residuo"),
                "destino": fallo["destino"],
                "motivo_destino": fallo["motivo"],
                "gates": fallo["gates"],
                "atestacion_modelos": fallo["atestacion"],
                "propuesta_de_aplicacion": _propuesta_de_aplicacion(
                    fila, str(principal.get("veredicto")), modelos, len(chunks),
                    did in doc_map_ids, sorted(set(ids_cat)), vias),
                "ids_catalogo_resueltos": sorted(set(ids_cat)),
                "via_resolucion_catalogo": sorted(vias),
                "evidencia": {
                    "modo_muestra": modo,
                    "candidatos_impresos": evidencia_cand,
                    "codigos_documento": codigos[:10],
                    "hermanos_por_nombre": hermanos,
                    "serie_de_codigos": serie,
                    "pm_distintos_en_chunks": sorted(
                        {x.get("product_model") for x in chunks if x.get("product_model")}),
                    "categorias_en_chunks": sorted(
                        {x.get("category") for x in chunks if x.get("category")}),
                },
                "k_pasadas": [{k: v for k, v in j.items() if k != "raw"} for j in juicios],
            })

    bloque = [f for f in filas_salida if f["destino"] == "bloque"]
    individual = [f for f in filas_salida if f["destino"] == "individual"]

    recibo = {
        "que_es": ("s322g — §4 del packet E1: adjudicación propuesta de los 4 documentos "
                   "con product_model SUCIO. PROPUESTA: nada aplicado."),
        "utc": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "solo_lectura": True,
        "fuente": str(FUENTE.relative_to(ROOT)).replace("\\", "/"),
        "packet": str(PACKET.relative_to(ROOT)).replace("\\", "/"),
        "drift_de_la_fuente": drift,
        "metodo": {
            "juez": MODELO, "max_tokens": MAX_TOKENS, "k_pasadas": args.k,
            "temperature": "NO se pasa (deprecado en los modelos 2026)",
            "verificacion_de_cita": "cita ENTERA (<=200 chars) contra el texto COMPLETO "
                                    "del documento, espacios colapsados y minúsculas",
            "gates_de_bloque": ["k_unanime", "citas_verificadas", "confianza_alta",
                                "modelos_atestiguados", "mantener_sin_tapado"],
        },
        "totales": {"analizadas": len(filas_salida),
                    "bloque": len(bloque), "individual": len(individual)},
        "seccion_0_bloque": bloque,
        "seccion_1_individual": individual,
    }

    salida = Path(args.salida)
    if not salida.is_absolute():
        salida = ROOT / salida
    salida.write_text(json.dumps(recibo, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nrecibo -> {salida}")
    print(json.dumps(recibo["totales"], ensure_ascii=False))
    for f in filas_salida:
        print(f"  [{f['destino']:10}] {f['source_file']:48} {f['pm_actual']!r} → "
              f"{f['veredicto']} {f['product_model_propuesto']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
