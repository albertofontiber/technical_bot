# -*- coding: utf-8 -*-
"""s322f — Encoge la SECCIÓN 2 del packet E1: los 67 documentos «tier B».

QUÉ RESUELVE
============
`evals/s320_e1_packet_adjudicacion_v1.md` §2 lista 67 DOCUMENTOS activos que, el
12-ago, no tenían entrada en `doc_map` y cuyo `product_model` resolvió de forma
AMBIGUA (paraguas / homónimo / split-parcial / OEM). La pregunta para Alberto,
fila a fila, es una sola: **¿son esos ids los correctos para su entrada en el
doc_map?** Pedirle 67 respuestas es caro; aprobarlas en bloque a ciegas es
peligroso. Este script separa lo que se puede decidir con evidencia dura de lo
que de verdad exige su ojo.

TRES PASADAS, EN ESTE ORDEN (el orden importa: cada una barata mata trabajo caro)
================================================================================
(A) REFRESCO contra el estado de HOY — determinista, sin LLM, gratis.
    El packet se congeló el 12-ago y desde entonces el catálogo se movió
    (s322d: 44 retags + cirugía FD2705; s322e: split ZXr). Una fila del packet
    sólo sigue siendo una pregunta viva si HOY:
      1. el documento sigue existiendo y sigue `active` (uno pasó a
         `superseded`: preguntar por su doc_map es trabajo muerto);
      2. el `document_id` sigue SIN entrada en doc_map (dos ya la tienen: se
         resolvieron entre medias);
      3. no hay YA una entrada para el MISMO `source_file` bajo otro
         `document_id` — esa es exactamente la clase «colisión» de §1, ya
         adjudicada por `scripts/s322f_e1_colisiones_adjudicacion.py`: el
         repunte de §1 le da entrada a este documento y la pregunta de §2 se
         DISUELVE. No es una fila de tier B: es una fila de §1 disfrazada.
    Además re-resuelve el `product_model` con el catálogo de HOY y compara con
    los ids congelados en el packet. Y compara el `product_model` de `documents`
    con el que llevan HOY los CHUNKS: si un retag posterior los separó, los ids
    del packet vienen de un pm caduco (caso real: `mie-mi-431rv2_1`, ZXR50A/
    ZXR50P en `documents` pero `ZXr-A/ZXr-P` en los chunks tras s322e — aplicar
    el packet tal cual escribiría los ids que Alberto acaba de declarar
    DISTINTOS).

(B) EVIDENCIA DIRIGIDA desde chunks_v2 — portada + chunks que MENCIONAN cada
    modelo candidato. La lección ya pagada: mandar los primeros chunks del
    documento no prueba nada, porque la evidencia de qué variantes cubre un
    manual vive en las tablas de modelos de la mitad del PDF. Aquí la selección
    dirigida se hace EN MEMORIA sobre el documento COMPLETO (todos sus chunks se
    descargan igualmente para poder verificar la cita full-text), que es un
    superconjunto de lo que devolvería un `content=ilike.*TERMINO*` y además no
    tropieza con el escapado de comodines del filtro PostgREST. El detector de
    menciones NO es un matcher nuevo: es `catalog._core()` — la misma maquinaria
    separador-insensible que usa el bot en producción.

(C) JUICIO LLM (claude-fable-5) con MENÚ CERRADO de ids. El modelo no conoce el
    catálogo, así que se le da la lista EXACTA de ids elegibles (candidatos de
    hoy + ids del pm de los chunks + productos cuyo nombre canónico aparece
    MENCIONADO en el documento). Un id fuera del menú es una invención y manda
    la fila a individual. Salida JSON estricta: veredicto, ids_propuestos,
    confianza, cita verbatim, razón.

LA CLASE «PARAGUAS» NO ES UN ERROR
==================================
Un manual de familia que cubre varias variantes con secciones propias (los 21
FAQ de `DXc`, las guías `NC-PFx`, `G-100-R`, `VSN-LT`) resuelve a VARIOS ids por
paraguas y eso es MULTI-VALOR LEGÍTIMO, no un fallo de resolución. El prompt lo
dice con esas palabras y el veredicto `MULTI` existe para nombrarlo. Lo que sí
es un fallo es el paraguas que tapa un sujeto único (el manual es de UNA
variante concreta) o el homónimo mal desambiguado.

CRITERIO DE BLOQUE (SECCIÓN 0 = un solo «sí» de Alberto)
========================================================
Todas estas, sin excepción y sin relajar ninguna:
  1. la fila sigue VIVA tras el refresco (A);
  2. veredicto concreto y accionable (no NO_DECIDIBLE) con ids_propuestos ≠ [];
  3. confianza `alta` DESPUÉS de la degradación por cita;
  4. cita verificada a TEXTO COMPLETO contra la concatenación de TODOS los
     chunks del documento, normalizando espacios (verificar sólo un prefijo dejó
     pasar una invención real: la cola parafraseada no estaba en el documento);
  5. todos los ids propuestos están en el MENÚ y son CONSUMIBLES
     (`Catalog._consumable`: activo y no-candidate, siguiendo redirects);
  6. sin ambigüedad ESTRUCTURAL: ningún token del pm queda clasificado como
     «producto real que falta en el catálogo» (esa fila necesita un ALTA antes
     que una entrada de doc_map — es otra decisión, de otro packet);
  7. ACUERDO K=2: una segunda llamada independiente da el MISMO veredicto y el
     MISMO conjunto de ids. Sin `temperature` (deprecada en los modelos 2026) el
     muestreo es no-determinista: una sola pasada no distingue convicción de
     azar. Sólo se re-pregunta a las filas que ya pasaron 1-6, así que el coste
     del control es marginal.
Todo lo demás va a SECCIÓN 1, con la evidencia junta para decidir rápido.

SOLO LECTURA — CONTRATO DURO
============================
No escribe en `data/catalog/*.jsonl`, ni en Supabase (cero PATCH/POST/DELETE),
ni en `data/model_catalog.json`. Su único efecto es el recibo en `evals/`. Las
`entrada_propuesta` que emite son PROPUESTAS para que Alberto adjudique.

USO
===
    python scripts/s322f_e1s2_tierb_docmap.py
    python scripts/s322f_e1s2_tierb_docmap.py --limite 5      # smoke barato
    python scripts/s322f_e1s2_tierb_docmap.py --sin-llm       # sólo refresco (A)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=False)

import anthropic  # noqa: E402

from src.http_pool import abierto  # noqa: E402
from src.rag import catalog as C  # noqa: E402  (_core/_fold: el detector real)
from src.rag import catalog_store as CS  # noqa: E402  (SOLO LECTURA)

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
KEY = os.environ["SUPABASE_SERVICE_KEY"]
H = {"apikey": KEY, "Authorization": f"Bearer {KEY}"}

MODELO = "claude-fable-5"
# max_tokens: lección cara de esta semana — con 400 el JSON del modelo se TRUNCA
# y el parse-fail se lee como incertidumbre del modelo cuando en realidad es un
# corte nuestro. Una lista de 13 ids (FAAST) + cita de 200 chars no cabe en 400.
# Y hay una vuelta de tuerca medida en ESTA sesión: con 1600 fallaron 3 filas con
# `stop_reason=max_tokens` y texto VACÍO — el presupuesto se lo comió el
# razonamiento del modelo antes de emitir un solo carácter de JSON. El síntoma no
# se parece a una truncatura (no hay cola cortada que mirar: no hay nada), y se
# lee como «el modelo no supo». Por eso el presupuesto es holgado Y hay reintento
# automático con el doble cuando el corte es por tope (ver `_pregunta`).
MAX_TOKENS = 4000

FUENTE = ROOT / "evals" / "s320_e1_docmap_derivacion_v2_detalle.json"
RECIBO_E1S1 = ROOT / "evals" / "s322f_e1_colisiones_adjudicacion_v1.json"
SALIDA_DEFAULT = ROOT / "evals" / "s322f_e1s2_tierb_docmap_v1.json"

# Nº de chunks de cabecera que se mandan como PORTADA. La portada dice de qué
# equipo es el manual; el resto de la evidencia va dirigida por menciones.
CHUNKS_PORTADA = 3
# Tope de ids del menú: más allá el prompt se vuelve una lista de la compra y el
# modelo empieza a elegir por parecido léxico en vez de por contenido.
MENU_MAX = 30
# Longitud mínima (caracteres útiles) para que un canónico entre en el escaneo de
# menciones: por debajo, el core matchea dentro de demasiadas palabras.
MENCION_MIN_UTILES = 4


# ─────────────────────────── utilidades de lectura ───────────────────────────

def _norm(texto: str) -> str:
    """Normalización de espacios para verificar citas contra el texto fuente.

    Lección ya pagada: verificar sólo un prefijo de 50 chars dejó pasar una cita
    inventada — la cola parafraseada por el modelo no estaba en el documento.
    Aquí se compara la cita ENTERA contra el contenido COMPLETO del documento.
    """
    return re.sub(r"\s+", " ", (texto or "")).strip().lower()


def _paginado(cliente, tabla: str, params: dict) -> list[dict]:
    """GET paginado. Sin esto un `len(rows)` mentiría al topar el limit de
    PostgREST y un documento largo perdería la cola de sus chunks — justo la
    parte contra la que hay que verificar la cita."""
    filas, off = [], 0
    while True:
        r = cliente.get(f"{SUPABASE_URL}/rest/v1/{tabla}", headers=H,
                        params={**params, "offset": str(off), "limit": "1000"})
        r.raise_for_status()
        lote = r.json()
        filas.extend(lote)
        if len(lote) < 1000:
            return filas
        off += 1000


def _utiles(t: str) -> str:
    return re.sub(r"[^0-9a-z]", "", C._fold(t or ""))


def _patron_mencion(termino: str) -> re.Pattern | None:
    """Regex de mención de UN término, con la MISMA forma que el detector de
    producción (`\\b(core)(?!\\d)`, separadores opcionales entre segmentos). Se
    reutiliza `catalog._core` a propósito: un matcher propio divergiría en
    silencio del que usa el bot, y entonces la evidencia del recibo no
    describiría el sistema real."""
    core = C._core(termino)
    if not core:
        return None
    return re.compile(r"\b(" + core + r")(?!\d)", re.IGNORECASE)


# ───────────────────────── evidencia por documento ─────────────────────────

def _evidencia_dirigida(chunks: list[dict], termino: str,
                        max_frag: int = 2) -> dict:
    """Chunks del documento que MENCIONAN el término + fragmentos alrededor.

    Por qué en memoria y no con `content=ilike.*TERMINO*`: los chunks del
    documento ya están descargados (hacen falta enteros para verificar la cita
    full-text), la selección local es un superconjunto exacto de lo que
    devolvería el ilike, y evita el escapado de `%`/`_`/comodines que en esta
    misma semana produjo cuentas 0 silenciosas (falso «no aparece nunca»).
    """
    pat = _patron_mencion(termino)
    if pat is None:
        return {"termino": termino, "chunks_que_lo_mencionan": 0,
                "fragmentos": []}
    tocados, frags = 0, []
    for ch in chunks:
        txt = ch.get("content") or ""
        m = pat.search(txt)
        if not m:
            continue
        tocados += 1
        if len(frags) < max_frag:
            a, b = max(0, m.start() - 160), min(len(txt), m.end() + 260)
            frags.append({"chunk_index": ch.get("chunk_index"),
                          "pagina": ch.get("page_number"),
                          "texto": re.sub(r"\s+", " ", txt[a:b]).strip()})
    return {"termino": termino, "chunks_que_lo_mencionan": tocados,
            "fragmentos": frags}


def _menu_por_menciones(texto_doc: str, cat: CS.Catalog,
                        obligatorios: list[str]) -> list[dict]:
    """Menú CERRADO de ids elegibles para este documento.

    = candidatos de la resolución (obligatorios, aunque no se mencionen: hay que
      poder confirmarlos o descartarlos)
    + todo producto del catálogo cuyo canónico aparece MENCIONADO en el texto del
      documento (una sola pasada con una alternación de todos los cores, igual
      que hace `catalog._load()` con el snapshot vivo).

    Sin este menú el modelo sólo podría contestar «los candidatos sí/no»: los
    veredictos OTROS_IDS y MULTI serían inaccionables porque no sabría nombrar
    el id correcto. Con menú cerrado, además, la invención es DETECTABLE.
    """
    por_nk: dict[str, list[str]] = {}
    alts: list[str] = []
    for pid, p in cat.products.items():
        can = p.get("canonical_model") or ""
        if len(_utiles(can)) < MENCION_MIN_UTILES:
            continue
        # El namespace `unresolved:` son productos SIN marca adjudicada:
        # ofrecerlos como destino de un doc_map es una decisión de marca, no de
        # documento, y además mete ruido de clase FUEGO ('unresolved:indicator'
        # matchea prosa inglesa en cualquier manual). Fuera del escaneo; si
        # alguno fuera candidato de la resolución entra por `obligatorios`.
        #
        # Los `candidate` SÍ entran (marcados como no-consumibles en el prompt).
        # Excluirlos costó una respuesta FALSA en el smoke: sin ver
        # `notifier:inspire-e15` en el menú, el juez declaró que E15 «es un
        # producto real que falta en el catálogo» cuando existe, pendiente de
        # QA. Un menú incompleto no produce prudencia: produce un hallazgo
        # inventado. El gate 5 sigue mandando a individual cualquier propuesta
        # con ids no consumibles — pero ahora con el motivo REAL.
        if pid.startswith("unresolved:") or p.get("estado") != "activo":
            continue
        core = C._core(can)
        if not core:
            continue
        por_nk.setdefault(C.normkey(can), []).append(pid)
        alts.append(core)
    menciones: dict[str, int] = {}
    if alts:
        # Una sola alternación → una sola pasada sobre el texto del documento.
        gordo = re.compile(r"\b(" + "|".join(sorted(set(alts))) + r")(?!\d)",
                           re.IGNORECASE)
        for m in gordo.finditer(texto_doc):
            nk = C.normkey(m.group(1))
            for pid in por_nk.get(nk, []):
                menciones[pid] = menciones.get(pid, 0) + 1

    ids = list(dict.fromkeys(list(obligatorios) + sorted(
        menciones, key=lambda p: -menciones[p])))
    menu = []
    for pid in ids:
        p = cat.products.get(pid)
        if not p:
            continue
        menu.append({
            "id": pid,
            "canonical": p.get("canonical_model"),
            "estado": p.get("estado"),
            "candidate": bool(p.get("candidate")),
            "consumible": cat._consumable(pid),
            "menciones_en_el_documento": menciones.get(pid, 0),
            "es_candidato_de_la_resolucion": pid in obligatorios,
        })
        if len(menu) >= MENU_MAX:
            break
    return menu


# ───────────────────────────────── el juez ─────────────────────────────────

PROMPT = """Eres el adjudicador de identidad de un corpus de manuales de protección contra incendios (PCI).

Hay que decidir a QUÉ PRODUCTO(S) del catálogo pertenece este documento: es su entrada en el mapa documento→producto (doc_map). Un documento entra con UNO o VARIOS ids.

DOCUMENTO: {filename}
Fabricante declarado: {marca} · tipo: {tipo}
product_model en la ficha del documento: «{pm_doc}»
product_model que llevan HOY sus chunks: «{pm_chunks}»{aviso_retag}
Chunks totales del documento: {n_chunks}{aviso_completo}

RESOLUCIÓN AUTOMÁTICA (la que hay que auditar) — token a token:
{trazas}

MENÚ CERRADO de ids elegibles (id · nombre canónico · nº de chunks del documento que lo mencionan). SOLO puedes proponer ids de esta lista, copiados literalmente:
{menu}

PORTADA (primeros chunks):
---
{portada}
---

EVIDENCIA DIRIGIDA — chunks del documento que mencionan cada modelo candidato:
---
{evidencia}
---

REPARTO DE COMPETENCIAS (léelo antes de puntuar tu confianza)
Tú decides UNA cosa: DE QUÉ TRATA EL DOCUMENTO. Lo que significa cada término del catálogo ya está decidido y no tienes que re-verificarlo en el texto:
  · una resolución marcada ADJUDICADA (exact / alias / paraguas ya validado) es un HECHO del catálogo. Que el manual de la sirena «ExitPoint» nunca escriba la referencia interna «PF24V», o que una guía de la familia «VSN-LT» no enumere sus cuatro variantes, NO es un hueco de evidencia: el catálogo ya declaró que ese término significa exactamente esos ids. Si el documento trata inequívocamente de ese término, tu confianza es ALTA.
  · una resolución marcada PENDIENTE (homónimo, paraguas sin validar) es lo contrario: el catálogo dice que NO lo sabe. Ahí toda la carga de la prueba está en el contenido del documento, y sin menciones propias que desambigüen, tu confianza es baja.

REGLAS DE ADJUDICACIÓN
1. El SUJETO del documento es el equipo del que trata, no todo lo que nombra: un manual de central menciona detectores, y no por eso es su manual.
2. Un manual de FAMILIA que cubre varias variantes es MULTI-VALOR LEGÍTIMO, no un error de resolución: le corresponden VARIOS ids. Dilo así. Basta con que el documento hable a NIVEL DE FAMILIA (nombra la serie, habla de «las centrales X» en plural, o trae tablas por variante): la lista de miembros la pone el catálogo, no el manual.
3. Si el documento trata de UNA sola variante concreta, le corresponde UN id aunque el término del catálogo sea un paraguas.
4. Si el sujeto real es otro producto distinto del candidato (rebrand/OEM, homónimo mal desambiguado, ficha caduca tras un retag), veredicto OTROS_IDS con los ids del menú.
5. Si un token del product_model no tiene id, clasifícalo: es el nombre de la FAMILIA o SERIE, es un PRODUCTO REAL que falta en el catálogo, o no es un producto. Antes de decir que FALTA, búscalo en el MENÚ: puede estar ahí como producto CANDIDATE (existe, pendiente de QA) — en ese caso no falta, y si es el correcto, proponlo.
6. Si la evidencia no permite decidir, NO_DECIDIBLE. Es una respuesta válida y preferible a inventar.

ESCALA DE CONFIANZA (úsala tal cual, no como sensación):
- «alta»: el CONTENIDO del documento identifica su sujeto sin ambigüedad y ese sujeto tiene resolución ADJUDICADA en el catálogo.
- «media»: la respuesta es plausible pero queda un hueco REAL — sólo lo dice la ficha y el contenido no lo respalda, el documento está recortado, o hay dos lecturas posibles del sujeto.
- «baja»: el contenido no permite decidir, o el término está PENDIENTE en el catálogo y nada lo desambigua.
No bajes la confianza por no haber encontrado en el texto la referencia interna de un id ni la lista completa de miembros de una familia: eso lo pone el catálogo (ver reparto de competencias).

QUÉ TIENE QUE SER LA CITA (esto no es un trámite: es el ancla de todo)
La cita es el fragmento donde EL DOCUMENTO IDENTIFICA A SU SUJETO: el título, la portada, o la frase que lo nombra («…de la serie NC», «Sirena Direccional ExitPoint», «para la central DXc»). Copiada EXACTA y CONTIGUA del contenido de arriba, sin elipsis ni retoques, máximo 200 caracteres.
Si en el contenido NO existe ningún fragmento que nombre al sujeto (por ejemplo, sólo hay un diagrama, una tabla de bornes o páginas sueltas de notas), NO fabriques una cita de relleno: pon `cita_nombra_al_sujeto` a false y tu confianza a media como mucho. Una entrada sostenida sólo por la ficha del documento, sin una línea del manual que la respalde, tiene que pasar por revisión humana.

Responde SOLO este JSON, sin texto alrededor:
{{"sujeto": "en pocas palabras, de qué equipo trata el documento",
 "nivel": "familia|variante-concreta|no-claro",
 "cobertura": "uno|varios",
 "veredicto": "IDS_CORRECTOS|OTROS_IDS|MULTI|NO_DECIDIBLE",
 "ids_propuestos": ["ids del MENÚ, literales"],
 "tokens_pendientes": {{"TOKEN": "familia-o-serie|producto-real-que-falta|no-es-producto"}},
 "confianza": "alta|media|baja",
 "cita": "el fragmento verbatim que nombra al sujeto (o null si no existe)",
 "cita_nombra_al_sujeto": true,
 "razon": "una frase"}}

IDS_CORRECTOS = los ids candidatos son exactamente los que le corresponden. MULTI = cubre varios productos con contenido propio y la lista correcta es la que das (multi-valor legítimo). OTROS_IDS = el sujeto real es otro. Sin cita verbatim, tu confianza es baja."""


def _texto_trazas(trazas_hoy: list[dict]) -> str:
    """Las trazas se le enseñan al juez ETIQUETADAS como ADJUDICADA o PENDIENTE.

    No es cosmético: es el reparto de competencias del prompt. Un `paraguas`
    que expande (no-candidate, divergent≠unknown) o un `alias` YA pasaron QA
    humana — su lista de ids es un hecho del catálogo y el juez no debe
    re-verificarla en el texto. Un `homonimo`/`homonimo-candidate`/
    `paraguas-unknown` es justo lo contrario: el catálogo declara que NO lo sabe.
    Sin esta etiqueta el juez baja la confianza por un hueco que no existe.
    """
    out = []
    for t in trazas_hoy:
        via = t["via"] or "NO RESUELVE (token sin id)"
        ids = ", ".join(t["ids"]) if t["ids"] else "—"
        if t["expand"]:
            sello = ("ADJUDICADA: el catálogo ya validó que este término "
                     "significa exactamente estos ids")
        elif t["via"]:
            sello = ("PENDIENTE: el catálogo marca el término como ambiguo a "
                     "la espera de adjudicación humana; los ids son sólo las "
                     "OPCIONES, no una expansión")
        else:
            sello = "sin id en el catálogo: clasifícalo en tokens_pendientes"
        opc = t.get("opciones_pendientes") or []
        extra = (f" · OPCIONES que el catálogo conoce para este término "
                 f"(existen, pendientes de QA): {', '.join(opc)}" if opc else "")
        out.append(f"  · token «{t['token']}» → vía {via} · ids: {ids} · "
                   f"{sello}{extra}")
    return "\n".join(out)


def _pregunta(cliente_llm, fila: dict) -> dict:
    """Una llamada al juez. Devuelve el dict parseado (o un NO_DECIDIBLE con la
    causa del fallo: un parse-fail NO se disfraza de incertidumbre del modelo)."""
    ev = fila["evidencia_dirigida"]
    ev_txt = "\n".join(
        f"### {e['termino']} — lo mencionan {e['chunks_que_lo_mencionan']} chunk(s)\n"
        + ("\n".join(f"  [chunk {f['chunk_index']} · pág {f['pagina']}] {f['texto']}"
                     for f in e["fragmentos"]) or "  (ninguna mención en el documento)")
        for e in ev)
    menu_txt = "\n".join(
        f"  · {m['id']} · «{m['canonical']}» · {m['menciones_en_el_documento']} menciones"
        + ("" if m["consumible"] else
           " · OJO: producto CANDIDATE (existe en el catálogo pero pendiente de "
           "QA humana). Puedes proponerlo si es el correcto — pero NO digas que "
           "«falta en el catálogo»: existe")
        for m in fila["menu"]) or "  (vacío)"
    aviso = ""
    if fila["pm_chunks"] and fila["pm_chunks"] != fila["pm_doc"]:
        aviso = ("\n  ATENCIÓN: la ficha y los chunks NO coinciden — hubo un "
                 "retag posterior. Manda el contenido real, no la ficha.")
    # Un documento de 1-3 chunks NO es «un manual del que ves la portada»: es
    # todo lo que hay ingestado (las FAQ del corpus son así). Sin decírselo, el
    # modelo baja la confianza por un recorte que no existe.
    completo = ("  (es el documento COMPLETO: no hay más contenido ingestado)"
                if fila["n_chunks"] <= CHUNKS_PORTADA else
                f"  (se te muestran los {CHUNKS_PORTADA} primeros como portada; "
                f"el resto llega por la evidencia dirigida)")
    mensaje = PROMPT.format(
        filename=fila["source_file"], marca=fila["manufacturer"],
        tipo=fila["doc_type"] or "sin declarar", pm_doc=fila["pm_doc"],
        pm_chunks=fila["pm_chunks"] or "—", aviso_retag=aviso,
        aviso_completo=completo,
        n_chunks=fila["n_chunks"], trazas=_texto_trazas(fila["trazas_hoy"]),
        menu=menu_txt, portada=fila["portada"][:4000], evidencia=ev_txt[:9000])
    # sin `temperature`: deprecada en los modelos 2026 (error 400).
    for intento, tope in enumerate((MAX_TOKENS, MAX_TOKENS * 2), start=1):
        msg = cliente_llm.messages.create(
            model=MODELO, max_tokens=tope,
            messages=[{"role": "user", "content": mensaje}])
        texto = "".join(b.text for b in msg.content
                        if getattr(b, "type", "") == "text").strip()
        try:
            v = json.loads(texto[texto.index("{"):texto.rindex("}") + 1])
            if intento > 1:
                v["nota_reintento"] = (f"1ª llamada cortada por tope de tokens; "
                                       f"resuelta con max_tokens={tope}")
            return v
        except Exception:                                    # noqa: BLE001
            # Sólo se reintenta el fallo que el reintento puede arreglar: un
            # corte por presupuesto. Un JSON malformado con parada natural es
            # otra cosa y repetirlo sería ruido y coste.
            if getattr(msg, "stop_reason", None) != "max_tokens":
                break
    return {"veredicto": "NO_DECIDIBLE", "confianza": "baja",
            "ids_propuestos": [], "cita": None,
            "razon": "parse-fail (respuesta no-JSON o cortada por tope aun "
                     "tras reintento con el doble de presupuesto)",
            "stop_reason": getattr(msg, "stop_reason", None),
            "raw": texto[:400]}


def _juzga(cliente_llm, fila: dict, texto_norm: str, ids_menu: set[str],
           cat: CS.Catalog) -> dict:
    """Juicio + verificación. La verificación es la mitad que importa."""
    v = _pregunta(cliente_llm, fila)
    cita = v.get("cita")
    # (5) la cita ENTERA contra el documento ENTERO, espacios normalizados.
    cita_ok = bool(cita) and _norm(cita) in texto_norm
    if v.get("confianza") == "alta" and not cita_ok:
        v["confianza"] = "media"
        v["nota_degradacion"] = ("cita NO verificada a texto completo → "
                                 "confianza degradada a media")
    ids_prop = [i for i in (v.get("ids_propuestos") or []) if isinstance(i, str)]
    fuera = [i for i in ids_prop if i not in ids_menu]
    no_consumibles = [i for i in ids_prop
                      if i in ids_menu and not cat._consumable(i)]
    return {"llm": v, "cita_verificada_full_text": cita_ok,
            "ids_propuestos": ids_prop, "ids_fuera_de_menu": fuera,
            "ids_no_consumibles": no_consumibles,
            # Cuántas veces nombra el documento a su presunto sujeto. Es el
            # contraste duro (regex del detector, no opinión) contra el que
            # Alberto puede leer la cita: 0 menciones + cita que sí nombra al
            # sujeto = el manual lo llama por el nombre de familia en prosa;
            # 0 menciones + cita que no lo nombra = no hay evidencia interna.
            "menciones_maximas_en_el_documento": max(
                [e["chunks_que_lo_mencionan"]
                 for e in fila["evidencia_dirigida"]] or [0])}


# ───────────────────────────────── main ─────────────────────────────────

def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                        # noqa: BLE001
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", default=str(SALIDA_DEFAULT))
    ap.add_argument("--limite", type=int, default=0,
                    help="analiza sólo las N primeras filas (smoke barato)")
    ap.add_argument("--solo", default="",
                    help="subcadenas (coma) de source_file: smoke dirigido a "
                         "una CLASE de ambigüedad concreta")
    ap.add_argument("--sin-llm", action="store_true",
                    help="sólo el refresco determinista (A), sin juez")
    ap.add_argument("--hilos", type=int, default=4)
    args = ap.parse_args()

    tier_b = json.loads(FUENTE.read_text(encoding="utf-8"))["tier_b"]
    if args.solo:
        claves = [s.strip().lower() for s in args.solo.split(",") if s.strip()]
        tier_b = [r for r in tier_b
                  if any(k in (r["source_file"] or "").lower() for k in claves)]
    if args.limite:
        tier_b = tier_b[:args.limite]

    cat = CS.load()
    dm_por_id = {r["document_id"]: r for r in cat.doc_map}
    dm_por_sf: dict[str, list[dict]] = {}
    for r in cat.doc_map:
        dm_por_sf.setdefault((r.get("source_file") or "").strip().lower(),
                             []).append(r)
    # §1 ya adjudicada hoy: para poder decir «esta fila se disuelve con el
    # repunte de §1» citando su clase, no afirmándolo de memoria.
    e1s1 = {}
    if RECIBO_E1S1.is_file():
        rec = json.loads(RECIBO_E1S1.read_text(encoding="utf-8"))
        for k in ("seccion_0_bloque", "seccion_1_individual",
                  "seccion_ya_no_aplica"):
            for f in rec.get(k, []):
                e1s1[(f.get("source_file") or "").lower()] = f

    ids_docs = [r["document_id"] for r in tier_b]
    with abierto(timeout=90.0) as cliente:
        docs: dict[str, dict] = {}
        for i in range(0, len(ids_docs), 40):
            lote = ids_docs[i:i + 40]
            r = cliente.get(f"{SUPABASE_URL}/rest/v1/documents", headers=H,
                            params={"select": "id,status,source_pdf_filename,"
                                              "product_model,manufacturer,"
                                              "doc_type,notes",
                                    "id": "in.(" + ",".join(lote) + ")"})
            r.raise_for_status()
            for f in r.json():
                docs[f["id"]] = f
        # Chunks COMPLETOS de cada documento: hacen falta enteros para (a) la
        # selección dirigida en memoria y (b) la verificación full-text de la
        # cita. Se piden por lotes de documentos y paginados.
        chunks_por_doc: dict[str, list[dict]] = {d: [] for d in ids_docs}
        for i in range(0, len(ids_docs), 12):
            lote = ids_docs[i:i + 12]
            for ch in _paginado(cliente, "chunks_v2", {
                    "select": "document_id,chunk_index,page_number,"
                              "product_model,content",
                    "document_id": "in.(" + ",".join(lote) + ")",
                    "order": "document_id.asc,chunk_index.asc"}):
                chunks_por_doc.setdefault(ch["document_id"], []).append(ch)
            print(f"  chunks {min(i+12, len(ids_docs))}/{len(ids_docs)} docs",
                  end="\r")
    print()

    filas: list[dict] = []
    for row in tier_b:
        did = row["document_id"]
        doc = docs.get(did) or {}
        chunks = sorted(chunks_por_doc.get(did, []),
                        key=lambda c: (c.get("chunk_index") or 0))
        texto_doc = " ".join((c.get("content") or "") for c in chunks)
        pm_doc = (doc.get("product_model") or row["pm"] or "").strip()
        pms_chunks = sorted({(c.get("product_model") or "").strip()
                             for c in chunks if c.get("product_model")})
        pm_chunks = pms_chunks[0] if len(pms_chunks) == 1 else "/".join(pms_chunks)

        # --- (A) refresco determinista -----------------------------------
        estado, motivo, extra = "vigente", None, {}
        if not doc:
            estado, motivo = "obsoleta", "el documento ya no existe en documents"
        elif doc.get("status") != "active":
            estado = "obsoleta"
            motivo = (f"el documento ya no está activo (status="
                      f"{doc.get('status')}): su doc_map dejó de ser una "
                      f"pregunta viva")
        elif did in dm_por_id:
            estado = "obsoleta"
            motivo = "el document_id YA tiene entrada en doc_map hoy"
            extra["entrada_existente"] = [e["id"] for e in
                                          dm_por_id[did].get("entries", [])]
        else:
            gemelas = dm_por_sf.get((row["source_file"] or "").lower(), [])
            if gemelas:
                estado = "se_disuelve_con_e1_seccion1"
                motivo = ("ya existe entrada de doc_map para el MISMO "
                          "source_file bajo otro document_id: es la clase "
                          "COLISIÓN de §1 — al repuntar §1, este documento "
                          "hereda la entrada y la pregunta de §2 desaparece")
                extra["entrada_bajo_id_viejo"] = {
                    "document_id": gemelas[0]["document_id"],
                    "ids": [e["id"] for e in gemelas[0].get("entries", [])]}
                adj = e1s1.get((row["source_file"] or "").lower())
                if adj:
                    extra["adjudicacion_e1_seccion1"] = {
                        "clase": adj.get("clase"), "destino": adj.get("destino"),
                        "propuesta": adj.get("propuesta")}

        # resolución de HOY (tokens del pm de la ficha) + del pm de los chunks
        def _trazar(pm: str) -> list[dict]:
            toks = ([pm] if cat.resolve(pm) is not None
                    else [t.strip() for t in pm.split("/") if t.strip()] or [pm])
            out = []
            for tok in toks:
                res = cat.resolve(tok) or {}
                # OPCIONES de un término PENDIENTE. `resolve()` devuelve
                # ids=[] para un homónimo/paraguas candidate (fail-open: no
                # debe expandir), pero el catálogo SÍ sabe cuáles son las
                # opciones — están en la fila de homonyms/umbrellas. Sin
                # exponerlas, el juez no puede ver que el producto EXISTE
                # pendiente de QA y concluye que «falta en el catálogo»: fallo
                # real del smoke con E15 (notifier:inspire-e15 existe).
                nt = CS.norm_token(tok)
                fila_h = cat._by_homonym.get(nt) or {}
                fila_u = cat._by_umbrella.get(nt) or {}
                opciones = [i for i in (fila_h.get("ids") or
                                        fila_u.get("ids") or [])
                            if i not in (res.get("ids") or [])]
                # PROCEDENCIA de la resolución. No todos los «hechos del
                # catálogo» pesan lo mismo: un paraguas/alias con added_by
                # `f1-gt` salió de ground-truth adjudicado por Alberto; uno
                # `f1-bulk` lo auto-importó la fase 1 LEYENDO UN DOCUMENTO. Si
                # el alias se extrajo de este mismo manual, usarlo para
                # atribuir este manual es circular. Se registra para que el
                # gate pueda distinguirlos y para que se vea en el recibo.
                fila_a = ({} if res.get("via") != "alias" else
                          next((a for a in cat.aliases
                                if CS.norm_token(a["alias"]) == nt), {}))
                origen = fila_a or (fila_u if res.get("via") == "paraguas"
                                    else {})
                out.append({"token": tok, "via": res.get("via"),
                            "ids": list(res.get("ids") or []),
                            "expand": bool(res.get("expand")),
                            "opciones_pendientes": opciones,
                            "procedencia": {
                                "added_by": origen.get("added_by"),
                                "provenance": origen.get("provenance")}
                            if origen else None})
            return out

        trazas_hoy = _trazar(pm_doc)
        ids_hoy = sorted({i for t in trazas_hoy for i in t["ids"] if t["expand"]})
        ids_packet = sorted({i for t in row["trazas"]
                             for i in (t.get("ids") or [])})
        trazas_chunks = _trazar(pm_chunks) if pm_chunks and pm_chunks != pm_doc else []
        ids_chunks = sorted({i for t in trazas_chunks
                             for i in t["ids"] if t["expand"]})
        sin_id = [t["token"] for t in trazas_hoy if not t["ids"]]

        fila = {
            "document_id": did, "source_file": row["source_file"],
            "manufacturer": doc.get("manufacturer") or row["manufacturer"],
            "doc_type": doc.get("doc_type") or row["doc_type"],
            "modo_packet": row["modo"],
            "pm_doc": pm_doc, "pm_chunks": pm_chunks,
            "n_chunks": len(chunks),
            "estado_refresco": estado, "motivo_refresco": motivo,
            **extra,
            "ids_packet_12ago": ids_packet,
            "ids_resueltos_hoy": ids_hoy,
            "deriva_de_ids_desde_el_packet": ids_hoy != ids_packet,
            "retag_posterior_de_chunks": bool(pm_chunks and pm_chunks != pm_doc),
            "ids_del_pm_de_los_chunks": ids_chunks,
            "tokens_sin_id": sin_id,
            "trazas_hoy": trazas_hoy,
        }
        if estado == "vigente" and not args.sin_llm:
            obligatorios = list(dict.fromkeys(
                ids_hoy + ids_chunks + ids_packet
                + [i for t in trazas_hoy for i in t["ids"]]
                + [i for t in trazas_hoy for i in t["opciones_pendientes"]]
                + [i for t in trazas_chunks for i in t["opciones_pendientes"]]))
            fila["menu"] = _menu_por_menciones(texto_doc, cat, obligatorios)
            fila["portada"] = re.sub(r"\s+", " ", " ".join(
                (c.get("content") or "") for c in chunks[:CHUNKS_PORTADA]))
            # dianas de la evidencia dirigida = los tokens del pm + el canónico
            # de cada id candidato (el token del pm puede ser un alias y el
            # manual usar el nombre canónico, o al revés).
            dianas = list(dict.fromkeys(
                [t["token"] for t in trazas_hoy]
                + [t["token"] for t in trazas_chunks]
                + [m["canonical"] for m in fila["menu"]
                   if m["es_candidato_de_la_resolucion"]]))
            fila["evidencia_dirigida"] = [_evidencia_dirigida(chunks, d)
                                          for d in dianas[:14]]
            fila["_texto_norm"] = _norm(texto_doc)
        filas.append(fila)

    vigentes = [f for f in filas if f["estado_refresco"] == "vigente"]
    print(f"refresco: {len(filas)} filas · vigentes {len(vigentes)} · "
          f"obsoletas {sum(1 for f in filas if f['estado_refresco']=='obsoleta')} "
          f"· disueltas-en-§1 "
          f"{sum(1 for f in filas if f['estado_refresco']=='se_disuelve_con_e1_seccion1')}")

    # ---------------- (C) juicio LLM + K=2 sobre los candidatos -------------
    if vigentes and not args.sin_llm:
        cliente_llm = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"],
                                          timeout=180.0, max_retries=2)

        def _pasada(f: dict) -> dict:
            ids_menu = {m["id"] for m in f["menu"]}
            return _juzga(cliente_llm, f, f["_texto_norm"], ids_menu, cat)

        print(f"juez pasada 1: {len(vigentes)} llamadas...")
        with ThreadPoolExecutor(max_workers=args.hilos) as pool:
            for f, res in zip(vigentes, pool.map(_pasada, vigentes)):
                f.update(res)
                print(f"  {f['source_file'][:44]:46s} "
                      f"{res['llm'].get('veredicto')} "
                      f"({res['llm'].get('confianza')}) "
                      f"cita={'OK' if res['cita_verificada_full_text'] else 'NO'}",
                      flush=True)

        # candidatos a bloque ANTES del K=2 (gates 1-6)
        def _gates_1a6(f: dict) -> list[str]:
            fallos = []
            v = f["llm"]
            if v.get("veredicto") not in ("IDS_CORRECTOS", "OTROS_IDS", "MULTI"):
                fallos.append("veredicto no accionable")
            if not f["ids_propuestos"]:
                fallos.append("sin ids propuestos")
            if v.get("confianza") != "alta":
                fallos.append(f"confianza {v.get('confianza')}")
            if not f["cita_verificada_full_text"]:
                fallos.append("cita no verificada full-text")
            # ANCLAJE DEL SUJETO. Una cita puede verificar palabra por palabra y
            # aun así no probar NADA sobre la identidad del documento: el caso
            # que lo destapó es `mie-mi-120p`, cuya cita verificada era la
            # etiqueta de un diagrama ('+ ● - ● VISION ● BATTERY') mientras el
            # id venía de un alias `f1-bulk` que se había extraído de ESE MISMO
            # documento — atribución circular con recibo de aspecto impecable.
            # Si el manual no nombra a su sujeto en ninguna parte, la entrada la
            # sostiene la ficha, no el documento: eso lo mira un humano.
            if not v.get("cita_nombra_al_sujeto"):
                fallos.append("la cita verifica pero NO nombra al sujeto: la "
                              "entrada se apoyaría sólo en la ficha del "
                              "documento, no en su contenido")
            # ATRIBUCIÓN CIRCULAR. Si el id sale de un alias/paraguas
            # AUTO-IMPORTADO de un documento (`f1-bulk`) y este documento no
            # nombra al sujeto ni una sola vez, la cadena de evidencia se
            # muerde la cola: el alias se extrajo de un manual como éste, y
            # ahora ese alias «prueba» de qué va el manual. Con menciones
            # propias no hay circularidad (el documento se sostiene solo), y
            # con procedencia `f1-gt` tampoco (lo adjudicó Alberto).
            if f.get("menciones_maximas_en_el_documento", 0) == 0:
                bulk = [t for t in f["trazas_hoy"]
                        if (t.get("procedencia") or {}).get("added_by")
                        == "f1-bulk"]
                if bulk:
                    fallos.append(
                        f"posible atribución circular: el id viene de un "
                        f"alias/paraguas AUTO-IMPORTADO de un documento "
                        f"({bulk[0]['procedencia'].get('provenance')}) y este "
                        f"manual no nombra al sujeto ni una vez")
            if f["ids_fuera_de_menu"]:
                fallos.append(f"ids inventados fuera del menú: "
                              f"{f['ids_fuera_de_menu']}")
            if f["ids_no_consumibles"]:
                fallos.append(
                    f"ids CANDIDATE {f['ids_no_consumibles']}: el producto "
                    f"existe pero está pendiente de QA humana — atestarlo con "
                    f"un documento es promoverlo de hecho, y esa es una "
                    f"decisión de Alberto, no un efecto colateral")
            falta = [t for t, cl in (v.get("tokens_pendientes") or {}).items()
                     if cl == "producto-real-que-falta"]
            if falta:
                fallos.append(f"ambigüedad estructural: el token {falta} sería "
                              f"un producto que NO está en el catálogo (antes "
                              f"que la entrada de doc_map hace falta un ALTA)")
            # Coherencia de MARCA. La derivación original mandó a tier B, entre
            # otras cosas, todo lo multi-marca: una entrada que atesta a la vez
            # productos de dos fabricantes es una decisión de identidad ENTRE
            # MARCAS (rebrand/OEM), no una decisión sobre este documento. Un
            # solo namespace que no coincide con el fabricante de la ficha SÍ
            # puede ir en bloque: el catálogo ya modela eso con `vendido_bajo`.
            marcas = {i.split(":")[0] for i in f["ids_propuestos"]}
            if len(marcas) > 1:
                fallos.append(f"ambigüedad estructural: la entrada atestaría "
                              f"productos de {len(marcas)} marcas {sorted(marcas)} "
                              f"— clase rebrand/OEM, decisión entre marcas")
            # Coherencia interna del propio veredicto: decir «trata de UNA
            # variante concreta» y proponer la familia entera es una respuesta
            # que se contradice; no entra en bloque por muy alta que se puntúe.
            if (v.get("nivel") == "variante-concreta"
                    and len(f["ids_propuestos"]) > 1):
                fallos.append("incoherencia: nivel=variante-concreta pero "
                              "propone varios ids")
            return fallos

        for f in vigentes:
            f["fallos_de_gate"] = _gates_1a6(f)
        candidatos = [f for f in vigentes if not f["fallos_de_gate"]]

        print(f"juez pasada 2 (K=2, sólo candidatos a bloque): "
              f"{len(candidatos)} llamadas...")
        with ThreadPoolExecutor(max_workers=args.hilos) as pool:
            for f, res in zip(candidatos, pool.map(_pasada, candidatos)):
                # El ACUERDO se mide sobre lo que de verdad se decide: el
                # CONJUNTO DE IDS que se escribiría en el doc_map. La etiqueta
                # IDS_CORRECTOS vs MULTI con la MISMA lista de ids es la misma
                # decisión descrita de dos maneras («los candidatos ya eran
                # correctos» / «es multi-valor legítimo») y no cambia ni un
                # carácter de la entrada propuesta; exigir la misma etiqueta
                # generaría residuo falso. Lo que sí se exige por igual en las
                # dos pasadas: veredicto accionable y confianza alta — y como la
                # confianza se degrada sola cuando la cita no verifica, esto
                # obliga además a que la 2ª cita también verifique full-text.
                mismos_ids = set(res["ids_propuestos"]) == set(f["ids_propuestos"])
                accionable = res["llm"].get("veredicto") in (
                    "IDS_CORRECTOS", "OTROS_IDS", "MULTI")
                alta = (res["llm"].get("confianza") == "alta"
                        and bool(res["llm"].get("cita_nombra_al_sujeto")))
                f["k2"] = {
                    "veredicto": res["llm"].get("veredicto"),
                    "ids": res["ids_propuestos"],
                    "confianza": res["llm"].get("confianza"),
                    "cita": res["llm"].get("cita"),
                    "cita_verificada": res["cita_verificada_full_text"],
                    "etiqueta_distinta_misma_decision":
                        mismos_ids and res["llm"].get("veredicto")
                        != f["llm"].get("veredicto"),
                    "acuerdo": bool(mismos_ids and accionable and alta)}
                if not f["k2"]["acuerdo"]:
                    f["fallos_de_gate"] = f.get("fallos_de_gate", []) + [
                        f"K=2 sin acuerdo: 2ª pasada dice "
                        f"{res['llm'].get('veredicto')}/"
                        f"{res['llm'].get('confianza')} con "
                        f"{res['ids_propuestos']}"]

    # ---------------------------- composición ------------------------------
    bloque, individual, fuera = [], [], []
    for f in filas:
        f.pop("_texto_norm", None)
        if f["estado_refresco"] != "vigente":
            fuera.append(f)
            continue
        if args.sin_llm:
            individual.append(f)
            continue
        if not f.get("fallos_de_gate"):
            # BANDERA (no gate) de clase OEM/rebrand: el id propuesto pertenece
            # a una marca distinta de la que declara la ficha del documento.
            # No bloquea — el catálogo ya modela la reventa con `vendido_bajo` y
            # la resolución que lo trajo está adjudicada —, pero Alberto debe
            # verlo de un vistazo: es media docena de las filas de este packet.
            marca_doc = C.normkey(f.get("manufacturer") or "")
            ajenos = [i for i in f["ids_propuestos"]
                      if not marca_doc.startswith(i.split(":")[0])]
            if ajenos:
                f["bandera_oem"] = {
                    "ids_de_otra_marca": ajenos,
                    "fabricante_del_documento": f.get("manufacturer"),
                    "vendido_bajo": {
                        i: (cat.products.get(i) or {}).get("vendido_bajo")
                        for i in ajenos},
                    "lectura": ("reventa/OEM: el documento lo publica una marca "
                                "y el producto vive en el catálogo bajo otra")}
            f["entrada_propuesta"] = {
                "document_id": f["document_id"],
                "source_file": f["source_file"],
                "entries": [{"id": pid, "role": "primary", "scope": "doc",
                             "provenance": "s322f-e1s2 tierB juez+cita "
                                           "verificada full-text + K=2"}
                            for pid in f["ids_propuestos"]]}
            bloque.append(f)
        else:
            individual.append(f)

    def _cuenta(campo, filtro=None, origen=None):
        d: dict[str, int] = {}
        for f in (origen if origen is not None else filas):
            if filtro and not filtro(f):
                continue
            k = str(campo(f))
            d[k] = d.get(k, 0) + 1
        return dict(sorted(d.items(), key=lambda kv: -kv[1]))

    utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    recibo = {
        "que_es": ("s322f — encogido de la SECCIÓN 2 del packet E1 (67 docs "
                   "tier B: resolución ambigua del doc_map). SECCIÓN 0 = un "
                   "solo sí; SECCIÓN 1 = decisión una a una. PROPUESTA: no "
                   "aplica NADA."),
        "utc": utc,
        "solo_lectura": True,
        "fuente": str(FUENTE.relative_to(ROOT)).replace("\\", "/"),
        "modelo_juez": MODELO,
        "estado_de_hoy": {
            "catalogo_productos": len(cat.products),
            "catalogo_doc_map_filas": len(cat.doc_map),
        },
        "criterio_de_bloque": [
            "la fila sigue viva tras el refresco contra el estado de hoy",
            "veredicto accionable (IDS_CORRECTOS|OTROS_IDS|MULTI) con ids != []",
            "confianza alta DESPUÉS de degradar por cita no verificada",
            "cita verificada a TEXTO COMPLETO del documento (espacios normalizados)",
            "todos los ids en el menú cerrado y consumibles (activo, no-candidate)",
            "ningún token del pm clasificado como «producto real que falta»",
            "acuerdo K=2 en veredicto y en conjunto de ids (sin temperature el "
            "muestreo no es determinista: una pasada no distingue convicción de azar)",
        ],
        "totales": {
            "analizadas": len(filas),
            "seccion_0_bloque": len(bloque),
            "seccion_1_individual": len(individual),
            "fuera_del_packet_tras_refresco": len(fuera),
        },
        "por_estado_de_refresco": _cuenta(lambda f: f["estado_refresco"]),
        "por_veredicto": _cuenta(
            lambda f: f"{f['llm'].get('veredicto')}:{f['llm'].get('confianza')}",
            filtro=lambda f: "llm" in f),
        "motivos_de_individual": _cuenta(
            lambda f: "; ".join(f.get("fallos_de_gate") or ["(sin-llm)"]),
            origen=individual),
        "seccion_0_bloque": bloque,
        "seccion_1_individual": individual,
        "seccion_2_fuera_del_packet": fuera,
    }
    salida = Path(args.salida)
    if not salida.is_absolute():
        salida = ROOT / salida
    salida.write_text(json.dumps(recibo, ensure_ascii=False, indent=1),
                      encoding="utf-8")
    print(json.dumps(recibo["totales"], ensure_ascii=False))
    print(f"recibo -> {salida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
