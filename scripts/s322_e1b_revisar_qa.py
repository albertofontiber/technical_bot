# -*- coding: utf-8 -*-
"""s322 — QA del lote «revisar» del E1b: encoger 261 candidates a un bloque + residuo.

QUÉ DECIDE ALBERTO (no este script): de cada uno de los 261 candidates que ya
viven en `data/catalog/products.jsonl` con `candidate=true`, si CONFIRMAR (es un
producto real, se queda) o RETIRAR (es basura de extracción, fuera).

ESTE SCRIPT NO APLICA NADA. Solo LEE (chunks_v2 por PostgREST + catálogo
gobernado) y deja un recibo JSON en evals/. Cero PATCH/POST/DELETE.

────────────────────────────────────────────────────────────────────────────
POR QUÉ CADA COSA
────────────────────────────────────────────────────────────────────────────

1. RECUENTO DE HOY, Y EN DOS MÉTRICAS (no una).
   El dato del lote es del 12-ago y el corpus se ha movido (s321/s322 retagearon
   y partieron documentos), así que hay que recontar. Pero además el recuento
   original usaba `ilike.*MODELO*` — SUBCADENA. Eso cuenta «TG» dentro de
   «voltage», y «020-590» dentro de «1020-5901». Recontamos las dos cosas:
     · n_substring_hoy  → comparable con el dato del 12-ago (mismo método).
     · n_frontera_hoy   → `imatch` con el patrón CANÓNICO del retriever
                          (`model_to_imatch_pattern`, \\y = frontera de palabra),
                          que es el que de verdad usa el bot para localizar.
   La atestación REAL es la de frontera. Un producto con n_substring alto y
   n_frontera 0 no está atestado: está confundido con otra palabra.

2. LA ATESTACIÓN VA CONTRA `content`, JAMÁS CONTRA `product_model` (regla r22
   heredada del E1b). El `product_model` de un chunk es metadata que nació del
   MISMO bulk s83 que parió estos candidates: usarla como prueba sería circular
   (es el fallo que r25-bis ya cazó con el snapshot del detector). Aun así la
   contamos y la reportamos como DIAGNÓSTICO — saber que un término sin
   atestación en contenido es el `product_model` de 40 chunks le dice a Alberto
   de dónde salió, sin que eso vote en el veredicto.

3. CERO MENCIONES ≠ BASURA (regla dura de Alberto, y el eje del recibo).
   Un producto real cuyo manual no tenemos es un HUECO DE CORPUS, no un
   artefacto. Para separar las dos cosas MECÁNICAMENTE (no por opinión del LLM)
   usamos el campo `provenance` del catálogo, que guarda el documento del que se
   extrajo el término en el bulk s83 («s83:MADT190_10 (brand-tier=...)»):
     · provenance ausente del corpus hoy  → el manual del que nació ya no está
       → «hueco de manual» — falta de atestación EXPLICADA, no sospechosa.
     · provenance presente pero el término no aparece en su contenido → el
       término salió del nombre de fichero / metadata de un doc que SÍ tenemos
       → sospechoso de artefacto, pero SIGUE sin ser prueba de inexistencia.
   Ninguno de los dos se puede confirmar ni retirar desde el corpus: los dos van
   a decisión individual, pero etiquetados distinto para que Alberto los despache
   rápido y no confunda un hueco con basura.

4. MUESTREO DIRIGIDO (lección cara): al LLM no se le mandan los primeros chunks
   del documento, se le mandan los chunks que MENCIONAN el término (filtro
   `imatch` en PostgREST). La evidencia de que algo es un modelo suele vivir en
   una tabla de referencias a mitad del manual, no en la portada.

5. AMBIGÜEDAD ESTRUCTURAL: si el patrón del modelo también casa DENTRO de otro
   canónico del catálogo («TG» casa dentro de «TG-1000»), sus menciones podrían
   ser del otro producto. Eso es ambigüedad de verdad → nunca va en bloque, y
   además se le avisa al LLM para que no confirme a ciegas.

6. VERIFICACIÓN DE CITA A TEXTO COMPLETO (lección cara: verificar 50 chars de
   prefijo dejó pasar una invención real, con la cola parafraseada). Se valida la
   cita ENTERA (hasta 200 chars) normalizando espacios, primero contra la
   evidencia mostrada y, si falla, contra el CONTENIDO COMPLETO de los documentos
   de esa evidencia (todos sus chunks concatenados) — así una cita que cruza un
   borde de chunk no se marca como falsa. Confianza «alta» sin cita verificada se
   DEGRADA a «media» y con ello sale del bloque.

────────────────────────────────────────────────────────────────────────────
CRITERIO DE BLOQUE (sección 0) — deliberadamente estrecho
────────────────────────────────────────────────────────────────────────────
CONFIRMAR en bloque exige las cuatro cosas a la vez:
  n_frontera_hoy ≥ 1  ∧  veredicto CONFIRMAR  ∧  confianza alta
  ∧ cita verificada a texto completo  ∧  sin colisión de catálogo.
RETIRAR en bloque exige lo mismo con veredicto RETIRAR, y se reporta en su
PROPIA lista: el «sí» que confirma no puede arrastrar por accidente un borrado.
Todo lo demás va a individual. Un lote grande no vale nada si un solo veredicto
inventado lo contamina.

Coste: ~2 consultas + 1 fetch por fila (261) + 1 llamada al juez por fila con
menciones. Modelo juez: claude-fable-5 (el pin de la casa). Sin `temperature`
(deprecada en los modelos 2026 → error 400) y con max_tokens=800 (400 TRUNCA el
JSON y produce «parse-fail» que parecen incertidumbre).
"""
from __future__ import annotations

import json
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=False)

import os  # noqa: E402

import anthropic  # noqa: E402

from src.http_pool import abierto  # noqa: E402
from src.rag.catalog_store import CATALOG_DIR, _read_jsonl  # noqa: E402
from src.rag.retriever import model_to_imatch_pattern  # noqa: E402

SB = os.environ["SUPABASE_URL"].rstrip("/")
KEY = os.environ["SUPABASE_SERVICE_KEY"]
HS = {"apikey": KEY, "Authorization": f"Bearer {KEY}"}
TABLA = f"{SB}/rest/v1/chunks_v2"
MODELO_JUEZ = "claude-fable-5"

FUENTE = ROOT / "evals" / "s320_e1b_candidates_preclasificacion_v1.json"
DESTINO = ROOT / "evals" / "s322_e1b_revisar_qa_v1.json"

MAX_CHUNKS_EVIDENCIA = 6      # chunks mostrados al juez
MAX_CHARS_CHUNK = 1600        # ventana por chunk, CENTRADA en la mención
MAX_CITA = 200                # lo que se almacena y por tanto lo que se verifica

# max_tokens del juez. OJO: en claude-fable-5 el pensamiento SIEMPRE está activo y
# CONSUME max_tokens (no se puede desactivar: `thinking:{"type":"disabled"}` da 400).
# Medido en este mismo lote con 800: una fila gastó los 800 tokens pensando y
# devolvió CERO texto (stop_reason=max_tokens, bloques=[thinking]) → el JSON vacío
# se registraba como «NO_DECIDIBLE», es decir, un fallo de presupuesto disfrazado
# de incertidumbre. Con 4000 el pensamiento cabe y queda sitio de sobra para el
# JSON. `effort=medium` acota además cuánto piensa (es una clasificación acotada
# con la evidencia delante, no un problema abierto).
MAX_TOKENS_JUEZ = 4000
EFFORT_JUEZ = "medium"
REINTENTOS_JUEZ = 2           # un fallo de parseo JAMÁS se registra como veredicto


# ───────────────────────── utilidades de texto ──────────────────────────────

def _norm(s: str) -> str:
    """Normalización de espacios para comparar citas contra el documento.
    Los chunks se re-juntan con \\n y el LLM reescribe saltos como espacios."""
    return re.sub(r"\s+", " ", (s or "").lower()).strip()


def _ilike(term: str) -> str:
    """Escapa el término para el operador ilike de PostgREST (mismo método que
    el recuento del 12-ago, para que el delta sea comparable)."""
    return term.replace("%", r"\%").replace("_", r"\_").replace("*", "")


def _patron_py(term: str) -> re.Pattern | None:
    """Patrón canónico del retriever, traducido a Python (\\y → \\b)."""
    try:
        return re.compile(model_to_imatch_pattern(term).replace(r"\y", r"\b"),
                          re.IGNORECASE)
    except re.error:
        return None


def _count(client, params: dict, intentos: int = 3) -> int | None:
    """COUNT exacto vía cabecera content-range (no baja filas).

    Devuelve None si NO se pudo medir — nunca un número inventado ni un
    centinela numérico. Un `ilike.*X*` lleva comodín inicial, así que Postgres
    hace recorrido secuencial de los 26k chunks y a veces excede el
    statement_timeout: HTTP 500 con code 57014. Medido en este lote: tres filas
    fallaban así, y como el centinela era -1 aparecían luego como «el conteo
    cambió desde el 12-ago» — un fallo de infraestructura contado como
    movimiento del corpus. Un valor no medido tiene que ser distinguible de un
    cero, porque cero significa «no atestado» y eso decide una fila.
    """
    for intento in range(intentos):
        try:
            r = client.get(TABLA,
                           headers={**HS, "Prefer": "count=exact",
                                    "Range": "0-0"},
                           params={"select": "id", **params})
        except Exception:                                      # noqa: BLE001
            r = None
        if r is not None and r.status_code in (200, 206):
            return int(r.headers.get("content-range", "/0").split("/")[-1])
        # 5xx (timeout de sentencia) o corte de red: reintentar espaciado; el
        # timeout depende de la carga, así que un reintento más lento suele
        # pasar. Un 4xx no se reintenta: es la consulta, no la carga.
        if r is not None and 400 <= r.status_code < 500:
            return None
        time.sleep(1.5 * (intento + 1))
    return None


# ─────────────────── caché de contenido completo por documento ──────────────
# Solo se rellena cuando una cita FALLA contra la evidencia mostrada: bajarse el
# documento entero de las ~200 filas por adelantado sería caro y casi siempre
# inútil (la cita del juez suele estar en el trozo que le enseñamos).

_CACHE_DOC: dict[str, str] = {}
_LOCK_DOC = threading.Lock()


def _doc_completo(client, source_file: str) -> str:
    with _LOCK_DOC:
        if source_file in _CACHE_DOC:
            return _CACHE_DOC[source_file]
    trozos, offset = [], 0
    while True:
        r = client.get(TABLA, headers=HS,
                       params={"select": "content",
                               "source_file": f"eq.{source_file}",
                               "order": "chunk_index.asc",
                               "offset": str(offset), "limit": "100"})
        r.raise_for_status()
        lote = r.json()
        trozos.extend((x.get("content") or "") for x in lote)
        if len(lote) < 100:
            break
        offset += 100
    texto = _norm("\n".join(trozos))
    with _LOCK_DOC:
        _CACHE_DOC[source_file] = texto
    return texto


# ────────────────────────────── prompt del juez ─────────────────────────────

PROMPT = """Eres el auditor de un catálogo de productos de protección contra incendios (PCI).

Decides si una entrada CANDIDATA del catálogo corresponde a un PRODUCTO REAL (un modelo comercial de un fabricante) o es BASURA de extracción (un código que no es un modelo, un fragmento de OCR, una palabra común, un número de página, una referencia normativa, o un trozo del nombre de OTRO producto).

ENTRADA DEL CATÁLOGO
  id: {pid}
  modelo declarado: «{modelo}»
  vendido bajo: {marca}
  procedencia (documento del que lo extrajo el bulk s83): {prov}
  ese documento {prov_estado} en el corpus hoy

EVIDENCIA DEL CORPUS — chunks cuyo CONTENIDO menciona «{modelo}» con frontera de palabra ({n_frontera} chunks en total; se muestran {k}):
---
{evidencia}
---
{aviso}
Responde SOLO con este JSON, sin texto alrededor:
{{"veredicto": "CONFIRMAR|RETIRAR|NO_DECIDIBLE",
 "confianza": "alta|media|baja",
 "cita": "fragmento VERBATIM copiado letra a letra de la evidencia (máximo 200 caracteres) que sostiene el veredicto, o null",
 "razon": "una o dos frases",
 "que_es": "qué es realmente el término si NO es un producto, o null"}}

REGLAS DURAS
- CONFIRMAR solo si la evidencia muestra «{modelo}» usado COMO MODELO DE PRODUCTO: en una tabla de modelos o referencias, una lista de pedido, un título de manual, una tabla de compatibilidad, una especificación técnica. Que el término aparezca no basta; tiene que aparecer COMO producto.
- RETIRAR solo si la evidencia muestra POSITIVAMENTE que el término NO es un modelo. Nunca por ausencia de información.
- Si dudas, NO_DECIDIBLE. No hay premio por decidir; un veredicto flojo cuesta más que un residuo.
- La cita se COPIA, no se redacta. Se verifica carácter a carácter contra el documento: si la parafraseas, tu veredicto se descarta entero.
- Un producto puede ser REAL aunque su manual no esté en este corpus. Aquí solo juzgas lo que la evidencia mostrada sostiene, no si el producto existe en el mundo.
"""


def _juzga(cliente, ctx: dict) -> dict:
    """Una llamada al juez con salida JSON estricta, y reintento ante fallo de
    forma.

    POR QUÉ EL REINTENTO Y POR QUÉ NO DEVUELVE «NO_DECIDIBLE»: un JSON que no
    parsea NO es el juez dudando, es el juez sin responder. Registrarlo como
    NO_DECIDIBLE (que es lo que hacía el patrón anterior) mete un fallo de
    infraestructura en el recuento como si fuera evidencia — y encima lo esconde,
    porque NO_DECIDIBLE es un desenlace legítimo. Aquí se reintenta y, si aun así
    falla, se marca `error_juez` para que se vea.

    Sin `temperature`: eliminada en los modelos 2026 (error 400)."""
    ultimo = ""
    for intento in range(1 + REINTENTOS_JUEZ):
        msg = cliente.messages.create(
            model=MODELO_JUEZ, max_tokens=MAX_TOKENS_JUEZ,
            output_config={"effort": EFFORT_JUEZ},
            messages=[{"role": "user", "content": PROMPT.format(**ctx)}])
        # los clasificadores del modelo pueden declinar (HTTP 200 + refusal):
        # es un desenlace, no un veredicto — se declara, no se disfraza.
        if msg.stop_reason == "refusal":
            return {"veredicto": None, "confianza": None, "cita": None,
                    "razon": "el juez declinó la petición (stop_reason=refusal)",
                    "que_es": None, "error_juez": "refusal"}
        texto = "".join(b.text for b in msg.content
                        if getattr(b, "type", "") == "text").strip()
        try:
            return json.loads(texto[texto.index("{"):texto.rindex("}") + 1])
        except Exception:                                      # noqa: BLE001
            ultimo = (f"stop_reason={msg.stop_reason} "
                      f"texto={texto[:200]!r}")
            time.sleep(0.5 * (intento + 1))
    return {"veredicto": None, "confianza": None, "cita": None,
            "razon": f"sin JSON válido tras {1 + REINTENTOS_JUEZ} intentos",
            "que_es": None, "error_juez": ultimo}


# ──────────────────────────────── fase 1: datos ─────────────────────────────

def _mide(client, fila: dict, prods: dict, terminos_cat: dict[str, set[str]],
          resuelto: dict[str, str]) -> dict:
    """Todo lo MECÁNICO de una fila: recuentos de hoy, evidencia dirigida,
    estado del documento de procedencia y colisiones de catálogo."""
    pid, modelo = fila["id"], fila["modelo"]
    pid_res = resuelto.get(pid, pid)
    prod = prods.get(pid, {})
    patron_pg = model_to_imatch_pattern(modelo) if modelo else None
    pat_py = _patron_py(modelo)

    # El presupuesto de reintentos va en proporción a cuánto DECIDE el número.
    # `n_frontera` es la atestación (decide la sección) y la procedencia separa
    # hueco-de-manual de artefacto: esos se pelean. El conteo por subcadena solo
    # sirve para comparar con la cifra del 12-ago, y su comodín inicial es
    # justamente el que agota el statement_timeout: un intento y, si no sale,
    # se declara no medido en vez de gastar 9 s por fila esperando.
    n_sub = (_count(client, {"content": f"ilike.*{_ilike(modelo)}*"}, intentos=1)
             if modelo else None)
    n_fro = _count(client, {"content": f"imatch.{patron_pg}"}) if patron_pg else 0
    # metadata: DIAGNÓSTICO, no atestación (r22 — el product_model nació del
    # mismo bulk que estos candidates; usarlo como prueba sería circular)
    n_meta = (_count(client, {"product_model": f"ilike.*{_ilike(modelo)}*"},
                     intentos=1) if modelo else None)

    # evidencia DIRIGIDA: los chunks que mencionan el término con frontera de
    # palabra, no los primeros del documento
    evidencia = []
    if n_fro > 0:
        r = client.get(TABLA, headers=HS,
                       params={"select": "content,source_file,document_id,"
                                         "product_model,chunk_index",
                               "content": f"imatch.{patron_pg}",
                               "limit": str(MAX_CHUNKS_EVIDENCIA)})
        if r.status_code in (200, 206):
            evidencia = r.json()

    # documento de procedencia: «s83:<source_file> (brand-tier=...)»
    prov = prod.get("provenance") or ""
    m = re.match(r"^s\d+:(.*?)(?:\s*\(brand-tier=[^)]*\))?$", prov.strip())
    prov_doc = (m.group(1).strip() if m else "")
    # ¿Sigue en el corpus el documento del que nació el candidato? La igualdad
    # EXACTA no vale: el `provenance` guarda el nombre que el doc tenía en el
    # bulk s83, y desde entonces varios se re-ingestaron con sufijo de revisión
    # («… ES FR GB IT» → «… ES FR GB IT_V2»). Con `eq` esos daban 0 y quedaban
    # etiquetados como HUECO DE MANUAL teniendo el manual delante — justo la
    # confusión que hay que evitar. Se comprueba también por PREFIJO y se
    # distingue el caso, porque un doc renombrado no es un doc ausente.
    prov_chunks = prov_pref = None
    if prov_doc:
        prov_chunks = _count(client, {"source_file": f"eq.{prov_doc}"})
        if prov_chunks == 0:
            prov_pref = _count(client,
                               {"source_file": f"ilike.{_ilike(prov_doc)}*"})

    # AMBIGÜEDAD ESTRUCTURAL: ¿el patrón de este modelo casa DENTRO del término
    # de OTRO producto? Entonces una mención podría ser del otro y no de éste.
    # El «de OTRO producto» es la parte que importa: en la primera pasada esto
    # comparaba solo cadenas y marcaba «FSL100-UVIR-W» como colisión con
    # «FSL100-UVIR-W (carcasa blanca)» — que es un ALIAS DEL MISMO producto, no
    # una ambigüedad. Comparar por id de producto (resolviendo redirects) deja
    # pasar los alias propios y conserva las colisiones reales (p. ej. «TG»
    # dentro de un «TG-1000» de otra ficha).
    colisiones = []
    if pat_py:
        for otro, duenos in terminos_cat.items():
            if otro != modelo and duenos - {pid_res} and pat_py.search(otro):
                colisiones.append(otro)
                if len(colisiones) >= 6:
                    break

    return {
        "id": pid, "modelo": modelo,
        "marca": ", ".join(prod.get("vendido_bajo") or []) or "desconocida",
        "chunks_con_mencion_12ago": fila["chunks_con_mencion"],
        "veneno_lexico": fila["veneno_lexico"],
        "n_substring_hoy": n_sub,
        "n_frontera_hoy": n_fro,
        "n_chunks_con_ese_product_model": n_meta,
        "provenance": prov,
        "provenance_doc": prov_doc,
        "provenance_chunks_hoy": prov_chunks,
        "provenance_chunks_por_prefijo": prov_pref,
        "colision_catalogo": colisiones,
        "_evidencia": evidencia,
    }


# ──────────────────────────── fase 2: juicio + cita ─────────────────────────

def _decide(client, cliente_llm, d: dict, reuso: dict | None = None) -> dict:
    """Juicio del LLM + verificación de la cita a texto completo."""
    ev = d.pop("_evidencia")
    if d["n_frontera_hoy"] is None:
        # NO se pudo contar. Es imprescindible no dejar que caiga en la rama de
        # «sin atestación»: un conteo fallido se convertiría en un hueco de
        # manual inventado, que es justo el error que Alberto prohíbe.
        d["clase"] = "medicion_fallida"
        d["llm"] = None
        d["cita_verificada"] = False
        d["seccion"] = "1_individual"
        d["motivo_seccion"] = ("no se pudo contar la atestación hoy (timeout de "
                               "sentencia en Supabase): fila SIN medir, no es "
                               "un cero")
        return d
    if d["n_frontera_hoy"] <= 0:
        # Sin atestación en CONTENIDO. No se pregunta al juez: no hay evidencia
        # que juzgar y una opinión sin evidencia es exactamente lo que esta
        # tarea prohíbe. Se etiqueta el TIPO de falta de atestación.
        prov_n, prov_p = (d["provenance_chunks_hoy"],
                          d["provenance_chunks_por_prefijo"])
        if not d["provenance_doc"]:
            clase = "sin_atestacion_sin_procedencia"
        elif prov_n is None:
            clase = "sin_atestacion_procedencia_no_medida"
        elif prov_n > 0:
            clase = "sin_atestacion_doc_presente"
        elif prov_p:
            # el manual está, con el nombre cambiado por una revisión
            clase = "sin_atestacion_doc_presente_renombrado"
        else:
            clase = "sin_atestacion_hueco_de_manual"
        d["clase"] = clase
        d["llm"] = None
        d["cita_verificada"] = False
        d["seccion"] = "1_individual"
        d["motivo_seccion"] = (
            "sin atestación en contenido: NO es prueba de que el producto no "
            "exista (posible hueco de manual). No decidible desde el corpus.")
        return d

    aviso = ""
    if d["colision_catalogo"]:
        aviso = ("\nATENCIÓN — ambigüedad estructural: «{}» también casa dentro "
                 "de estos otros modelos del catálogo: {}. Comprueba en la "
                 "evidencia si la mención es de ESTE producto o del otro.\n"
                 .format(d["modelo"], ", ".join(d["colision_catalogo"])))

    # VENTANA CENTRADA EN LA MENCIÓN, no los primeros N chars del chunk. Con el
    # recorte por la cabecera, la línea que contiene el término se quedaba fuera
    # y el juez respondía «la porción visible está truncada, no puedo citarlo»:
    # un NO_DECIDIBLE fabricado por el recorte, no por la evidencia. Es la misma
    # lección del muestreo dirigido, aplicada dentro del chunk.
    pat_py = _patron_py(d["modelo"])
    partes = []
    for c in ev:
        cont = c.get("content") or ""
        m = pat_py.search(cont) if pat_py else None
        if m and len(cont) > MAX_CHARS_CHUNK:
            centro = (m.start() + m.end()) // 2
            ini = max(0, centro - MAX_CHARS_CHUNK // 2)
            trozo = (("…" if ini else "") + cont[ini:ini + MAX_CHARS_CHUNK]
                     + ("…" if ini + MAX_CHARS_CHUNK < len(cont) else ""))
        else:
            trozo = cont[:MAX_CHARS_CHUNK]
        partes.append("--- chunk {} de «{}» (product_model: {}) ---\n{}".format(
            c.get("chunk_index"), c.get("source_file"),
            c.get("product_model"), trozo))
    texto_ev = "\n\n".join(partes)

    prov_n = d["provenance_chunks_hoy"]
    prov_estado = ("no consta" if prov_n is None
                   else "SIGUE" if prov_n > 0
                   else "SIGUE (renombrado por revisión)"
                   if d["provenance_chunks_por_prefijo"] else "YA NO ESTÁ")
    # REUSO DE VEREDICTOS (--reusar-veredictos): esta pasada corrige capas
    # MECÁNICAS que no tocan al juez (p. ej. la comprobación de procedencia,
    # que solo afecta a filas SIN atestación y por tanto sin llamada al juez).
    # Volver a pagar 216 llamadas para recalcular algo que no cambia sería
    # además menos fiel: re-juzgar introduce variación donde no hubo cambio.
    previo = (reuso or {}).get(d["id"])
    if previo and previo.get("llm"):
        d["llm"] = previo["llm"]
        d["cita_verificada"] = previo["cita_verificada"]
        d["veredicto_reusado"] = True
        veredicto, verificada = previo["llm"], previo["cita_verificada"]
        ver, conf = veredicto.get("veredicto"), veredicto.get("confianza")
        return _seccionar(d, veredicto, verificada, ver, conf)

    veredicto = _juzga(cliente_llm, {
        "pid": d["id"], "modelo": d["modelo"], "marca": d["marca"],
        "prov": d["provenance_doc"] or "desconocida",
        "prov_estado": prov_estado, "n_frontera": d["n_frontera_hoy"],
        "k": len(ev), "evidencia": texto_ev, "aviso": aviso})

    # ── verificación de la cita a TEXTO COMPLETO ──────────────────────────
    # Se valida la cita ENTERA (lo que se almacenaría), no un prefijo: verificar
    # 50 chars dejó pasar una invención real con la cola parafraseada.
    cita = (veredicto.get("cita") or "")[:MAX_CITA]
    cita_n = _norm(cita)
    verificada = False
    if cita_n:
        if cita_n in _norm(texto_ev):
            verificada = True
        else:
            # 2º intento contra el CONTENIDO COMPLETO de los docs de la
            # evidencia: una cita que cruza un borde de chunk es legítima.
            for sf in {c.get("source_file") for c in ev if c.get("source_file")}:
                if cita_n in _doc_completo(client, sf):
                    verificada = True
                    break
    d["llm"] = veredicto
    d["cita_verificada"] = verificada
    if veredicto.get("confianza") == "alta" and not verificada:
        veredicto["confianza"] = "media"
        veredicto["nota"] = ("cita NO verificada a texto completo → confianza "
                             "degradada a media (fuera de bloque)")

    return _seccionar(d, veredicto, verificada,
                      veredicto.get("veredicto"), veredicto.get("confianza"))


def _seccionar(d: dict, veredicto: dict, verificada: bool, ver, conf) -> dict:
    """Aplica el criterio de bloque. Vive aparte para que la ruta que reusa un
    veredicto y la que acaba de pedirlo pasen por EL MISMO filtro: si el
    criterio se duplicara, un cambio en uno de los dos lados relajaría el
    bloque en silencio."""
    if veredicto.get("error_juez"):
        # El juez no respondió. NO es un veredicto: se separa para que no se
        # cuele en el recuento como si fuera evidencia de nada.
        d["clase"] = "error_juez"
        d["seccion"] = "1_individual"
        d["motivo_seccion"] = ("el juez no devolvió un veredicto legible; la "
                               "fila queda SIN juzgar (no es NO_DECIDIBLE)")
        return d
    en_bloque = (conf == "alta" and verificada and not d["colision_catalogo"]
                 and ver in ("CONFIRMAR", "RETIRAR"))
    if en_bloque and ver == "CONFIRMAR":
        d["seccion"] = "0_bloque_confirmar"
        d["motivo_seccion"] = ("atestado con frontera de palabra + veredicto "
                               "alta + cita verificada full-text + sin colisión")
    elif en_bloque:
        d["seccion"] = "0_bloque_retirar"
        d["motivo_seccion"] = ("evidencia positiva de que el término NO es un "
                               "modelo + cita verificada full-text")
    else:
        d["seccion"] = "1_individual"
        faltas = []
        if conf != "alta":
            faltas.append(f"confianza {conf}")
        if not verificada:
            faltas.append("cita no verificada")
        if d["colision_catalogo"]:
            faltas.append("colisión de catálogo")
        if ver == "NO_DECIDIBLE":
            faltas.append("veredicto NO_DECIDIBLE")
        d["motivo_seccion"] = "; ".join(faltas) or "criterio de bloque no alcanzado"
    d["clase"] = "atestado_en_contenido"
    return d


# ──────────────────────────────────── main ──────────────────────────────────

def main() -> int:
    fuente = json.loads(FUENTE.read_text(encoding="utf-8"))
    filas = fuente["detalle"]["revisar"]
    # `--limit N` = SMOKE (muestra dispersa, no las N primeras: las primeras
    # están ordenadas por marca y no representan el lote). El smoke escribe a
    # otro fichero para no pisar el recibo bueno.
    global DESTINO
    if "--limit" in sys.argv:
        n = int(sys.argv[sys.argv.index("--limit") + 1])
        paso = max(1, len(filas) // n)
        filas = filas[::paso][:n]
        DESTINO = DESTINO.with_name(DESTINO.stem + "_SMOKE.json")
    prods = {r["id"]: r for r in _read_jsonl(CATALOG_DIR / "products.jsonl")}

    # Índice de términos del catálogo (canónicos + alias) → productos DUEÑOS,
    # con los redirects resueltos: dos entradas que redirigen al mismo producto
    # son el mismo producto, y una colisión contra uno mismo no es ambigüedad.
    redirects = {r["id"]: r["redirect_to"] for r in prods.values()
                 if r.get("redirect_to")}

    def _resolver(x: str) -> str:
        visto = set()
        while x in redirects and x not in visto:
            visto.add(x)
            x = redirects[x]
        return x

    resuelto = {pid: _resolver(pid) for pid in prods}
    terminos_cat: dict[str, set[str]] = {}
    for r in prods.values():
        if r.get("canonical_model"):
            terminos_cat.setdefault(r["canonical_model"], set()).add(
                resuelto[r["id"]])
    for a in _read_jsonl(CATALOG_DIR / "aliases.jsonl"):
        if a.get("alias") and a.get("id"):
            terminos_cat.setdefault(a["alias"], set()).add(
                resuelto.get(a["id"], a["id"]))
    print(f"filas {len(filas)} · catálogo {len(prods)} productos · "
          f"{len(terminos_cat)} términos para colisión", flush=True)

    # `--reusar-veredictos <recibo>`: recalcula TODA la capa mecánica pero
    # conserva los veredictos ya emitidos por el juez para las filas atestadas.
    # Para una corrección que solo afecta a filas sin atestación (que nunca
    # llaman al juez), re-juzgar no aportaría nada y además movería veredictos
    # que no han cambiado de evidencia.
    reuso: dict = {}
    if "--reusar-veredictos" in sys.argv:
        prev = json.loads(Path(sys.argv[sys.argv.index("--reusar-veredictos") + 1])
                          .read_text(encoding="utf-8"))
        for rows in prev["secciones"].values():
            for r in rows:
                if r.get("llm"):
                    reuso[r["id"]] = {"llm": r["llm"],
                                      "cita_verificada": r["cita_verificada"]}
        print(f"reuso: {len(reuso)} veredictos previos disponibles", flush=True)

    cliente_llm = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"],
                                      timeout=180.0, max_retries=2)
    hecho = [0]
    lock = threading.Lock()

    with abierto(timeout=60.0) as client:
        def _pipeline(fila: dict) -> dict:
            try:
                d = _mide(client, fila, prods, terminos_cat, resuelto)
                d = _decide(client, cliente_llm, d, reuso)
            except Exception as exc:                            # noqa: BLE001
                # Un fallo NUNCA se traga: la fila viaja a individual con el
                # error visible (silenciarla la haría desaparecer del recuento).
                d = {"id": fila["id"], "modelo": fila["modelo"],
                     "seccion": "1_individual", "clase": "error",
                     "motivo_seccion": f"{type(exc).__name__}: {exc}",
                     "llm": None, "cita_verificada": False}
            with lock:
                hecho[0] += 1
                if hecho[0] % 20 == 0:
                    print(f"  {hecho[0]}/{len(filas)}…", flush=True)
            return d

        # 4 hilos, no más: los COUNT con comodín inicial son recorridos
        # secuenciales y a más concurrencia más timeouts de sentencia (con 6
        # fallaban filas que en solitario responden sin problema).
        with ThreadPoolExecutor(max_workers=4) as pool:
            res = list(pool.map(_pipeline, filas))

    # ── recibo ────────────────────────────────────────────────────────────
    secciones: dict[str, list] = {}
    for d in res:
        secciones.setdefault(d["seccion"], []).append(d)
    for k in secciones:
        secciones[k].sort(key=lambda x: (x.get("clase", ""), x["id"]))

    bloque = (len(secciones.get("0_bloque_confirmar", []))
              + len(secciones.get("0_bloque_retirar", [])))
    individual = len(secciones.get("1_individual", []))
    assert bloque + individual == len(filas), "contabilidad rota"

    por_clase: dict[str, int] = {}
    for d in res:
        por_clase[d.get("clase", "?")] = por_clase.get(d.get("clase", "?"), 0) + 1
    resumen_llm: dict[str, int] = {}
    for d in res:
        if d.get("llm"):
            k = f"{d['llm'].get('veredicto')}:{d['llm'].get('confianza')}"
            resumen_llm[k] = resumen_llm.get(k, 0) + 1

    # delta del recuento: cuánto se movió el corpus desde el 12-ago y cuánto de
    # la «mención» del dato viejo era accidente de subcadena. Las filas NO
    # medidas (None) se excluyen y se cuentan aparte: meterlas aquí fue el fallo
    # que convirtió tres timeouts en «el corpus se movió».
    medidas = [d for d in res if isinstance(d.get("n_substring_hoy"), int)]
    movidos = [d for d in medidas
               if d["n_substring_hoy"] != d.get("chunks_con_mencion_12ago")]
    solo_substring = [d for d in medidas
                      if d["n_substring_hoy"] > 0
                      and d.get("n_frontera_hoy") == 0]
    no_medidas = [d["id"] for d in res
                  if not isinstance(d.get("n_frontera_hoy"), int)]

    recibo = {
        "que_es": (
            "QA del lote «revisar» del E1b (261 candidates ya en el catálogo). "
            "PROPUESTA para Alberto: NADA aplicado, ni catálogo ni Supabase ni "
            "snapshot. Atestación contra CONTENIDO de chunks_v2 con frontera de "
            "palabra (patrón canónico del retriever), nunca contra product_model. "
            "CERO menciones NO es prueba de inexistencia: se separa «sin "
            "atestación (posible hueco de manual)» de «artefacto/basura»."),
        "utc": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "fuente": str(FUENTE.relative_to(ROOT)).replace("\\", "/"),
        "modelo_juez": MODELO_JUEZ,
        "no_se_aplico_nada": True,
        "criterio_bloque": (
            "n_frontera_hoy>=1 ∧ veredicto claro ∧ confianza alta ∧ cita "
            "verificada a texto COMPLETO (hasta 200 chars, espacios "
            "normalizados) ∧ sin colisión de catálogo. El bloque de RETIRAR va "
            "en lista aparte: un «sí» de confirmar no puede arrastrar borrados."),
        "total": len(filas),
        "veredictos_reusados": sum(1 for d in res if d.get("veredicto_reusado")),
        "bloque": bloque,
        "individual": individual,
        "por_seccion": {k: len(v) for k, v in sorted(secciones.items())},
        "por_clase": por_clase,
        "resumen_llm": resumen_llm,
        "recuento": {
            "filas_medidas_hoy": len(medidas),
            "filas_no_medidas": no_medidas,
            "filas_cuyo_conteo_cambio_desde_12ago": len(movidos),
            "filas_con_mencion_solo_por_subcadena": len(solo_substring),
            "nota": ("«solo subcadena» = el conteo del 12-ago las daba por "
                     "mencionadas pero el término no aparece con frontera de "
                     "palabra: no están atestadas, aunque tampoco refutadas. "
                     "«no medidas» = el COUNT dio timeout de sentencia; no son "
                     "ceros y no cuentan como movimiento del corpus."),
        },
        "secciones": secciones,
    }
    DESTINO.write_text(json.dumps(recibo, ensure_ascii=False, indent=1),
                       encoding="utf-8")
    print(f"\ntotal {len(filas)} · bloque {bloque} · individual {individual}")
    print("por_seccion", recibo["por_seccion"])
    print("por_clase", por_clase)
    print("resumen_llm", resumen_llm)
    print("recuento", recibo["recuento"])
    print(f"recibo -> {DESTINO}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
