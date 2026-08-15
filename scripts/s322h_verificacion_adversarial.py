# -*- coding: utf-8 -*-
"""s322h — VERIFICACIÓN ADVERSARIAL del «encogido» de packets de s322f/s322g.

QUÉ ES
======
Ocho agentes hermanos encogieron tres packets de adjudicación (E1, E1b, E2)
convirtiendo ~2.100 casillas en un puñado de decisiones: una SECCIÓN 0 que
Alberto aprueba «en bloque» con un solo sí, y una SECCIÓN 1 que sigue siendo
fila-a-fila. Este script NO les cree. Asume que hay un fallo y lo busca.

POR QUÉ ASÍ (y no leyendo los recibos y asintiendo)
---------------------------------------------------
El bloque es un multiplicador de confianza: un solo sí de Alberto aplica cientos
de filas. Si UNA sola cita del bloque no existe en el corpus, el criterio entero
del bloque queda invalidado — no esa fila, EL CRITERIO — porque el bloque se
vende precisamente como «esto ya está verificado, no lo mires uno a uno». Por eso
aquí la cita no se «revisa»: se REEJECUTA contra `chunks_v2` desde cero, sin
reutilizar ni una línea de la verificación original de los agentes.

LAS SEIS COMPROBACIONES
-----------------------
A. NADA APLICADO — `git status/diff` sobre los ficheros protegidos
   (`data/catalog/*.jsonl`, `data/model_catalog.json`) + comprobación ESTÁTICA de
   que ninguno de los 8 scripts contiene un verbo HTTP mutante ni escribe fuera
   de `evals/`. El git prueba el estado de HOY; el grep prueba que el estado de
   hoy no fue suerte.
B. CUADRE DE CONTEOS — el total declarado en la cabecera de cada recibo contra
   `len()` de sus listas reales. Un recibo que se equivoca contando es un recibo
   que no se puede usar para decidir.
C. CRITERIO DEL BLOQUE — filas en bloque con confianza != alta, cita vacía,
   veredicto NO_DECIDIBLE o `cita_verificada` falsa. No debería haber NINGUNA.
D. CITAS REALES — dos capas:
   D1) la muestra que manda el encargo: 12 filas de bloque AL AZAR (semilla fija
       para que Alberto pueda repetir el sorteo), repartidas entre recibos;
   D2) el CENSO COMPLETO de todas las citas de bloque, porque un muestreo de 12
       sobre ~370 filas solo detecta un fallo aislado con ~3% de probabilidad —
       muestrear aquí sería teatro de rigor.
   Cada cita se valida ENTERA (hasta 200 chars) contra el documento ATRIBUIDO
   reconstruido concatenando TODOS sus chunks, normalizando espacios y caja
   (lección cara: verificar un prefijo de 50 chars dejó pasar una invención real,
   la cola parafraseada no estaba en el documento).
   La distinción que importa y que ningún recibo hace: verifica en el DOC
   ATRIBUIDO, o solo en el universo ancho (otros documentos que el juez también
   vio)? Lo segundo no es una invención, pero tampoco es lo que la fila dice.
E. PACKETS — las cabeceras («562 altas», «19 lotes») contra las filas realmente
   escritas en el .md, y cobertura: que cada término del recibo esté LISTADO en
   el packet y no solo contado.
F. FRAMING — afirmaciones narrativas de los recibos contrastadas contra sus
   propios números.

NO APLICA NADA. Escribe UN fichero: `evals/s322h_verificacion_adversarial_v1.json`.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import random
import re
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

from dotenv import load_dotenv

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env", override=False)

from src.http_pool import abierto  # noqa: E402

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
KEY = os.environ["SUPABASE_SERVICE_KEY"]
H = {"apikey": KEY, "Authorization": "Bearer " + KEY}

EVALS = ROOT / "evals"
DESTINO = EVALS / "s322h_verificacion_adversarial_v1.json"

# Los 7 recibos hermanos + el ensamblador de packets.
RECIBOS = {
    "e1_colisiones": "s322f_e1_colisiones_adjudicacion_v1.json",
    "e1b_encoger": "s322f_e1b_confirmar_encoger_v1.json",
    "e1s2_tierb": "s322f_e1s2_tierb_docmap_v1.json",
    "e2_altas": "s322f_e2_altas_split_v1.json",
    "g1_triage": "s322g_e1_candidatos_triage_v1.json",
    "g1_pm_sucio": "s322g_e1_pm_sucio_v1.json",
    "e1b_qa": "s322_e1b_revisar_qa_v1.json",
    "packets": "s322_packets_v2_recibo.json",
}
SCRIPTS = [
    "s322f_e1_colisiones_adjudicacion.py", "s322f_e1b_confirmar_encoger.py",
    "s322f_e1s2_tierb_docmap.py", "s322f_e2_altas_split.py",
    "s322g_e1_candidatos_triage.py", "s322g_e1_pm_sucio.py",
    "s322_e1b_revisar_qa.py", "s322_packets_v2.py",
]
PROTEGIDOS = ["data/catalog", "data/model_catalog.json"]
PACKETS_MD = {
    "E1": EVALS / "s320_e1_packet_adjudicacion_v2.md",
    "E1b": EVALS / "s320_e1b_packet_adjudicacion_v2.md",
    "E2": EVALS / "s320_e2_packet_adjudicacion_v2.md",
}

MAX_CITA = 200          # lo que realmente se almacenaría de la cita
CITA_MIN = 12           # una "cita" de 3 palabras no fundamenta nada


def _sin_puntos_suspensivos(t: str) -> str:
    """Quita los marcadores de RECORTE de los bordes («…» / «...»).

    POR QUÉ EXISTE ESTA FUNCIÓN (y por qué es un aviso, no un detalle): la
    primera pasada de este mismo script marcó 196 fragmentos como «NO VERIFICA»
    — todos falsos. Los fragmentos deterministas que los agentes guardan llevan
    «…» pegado cuando se recortó una ventana centrada en la mención, y ese
    carácter NO está en el corpus. Un adversario que no lo hubiera notado habría
    reportado una catástrofe inexistente y quemado la credibilidad del control.
    El texto ENTRE los marcadores sí es substring exacto del chunk.
    """
    t = (t or "").strip()
    for marca in ("…", "..."):
        while t.startswith(marca):
            t = t[len(marca):]
        while t.endswith(marca):
            t = t[: -len(marca)]
    return t.strip()


def _norm(t: str) -> str:
    """Normalización canónica: espacios colapsados + minúsculas.

    Es la MISMA que usaron los agentes. Usar una distinta (p. ej. quitando
    puntuación) haría que mis fallos no fueran comparables con sus éxitos: el
    adversario tiene que jugar en el mismo tablero para que su veredicto valga.
    """
    return re.sub(r"\s+", " ", (t or "")).strip().lower()


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=str(ROOT), capture_output=True,
                          text=True, encoding="utf-8", errors="replace").stdout


def _cargar(nombre: str) -> dict:
    return json.loads((EVALS / RECIBOS[nombre]).read_text(encoding="utf-8"))


# ═══════════════════════ A. NADA APLICADO ═══════════════════════

def bloque_a() -> dict:
    """El estado del árbol + la prueba estática de que los scripts son de lectura.

    `git diff` prueba que HOY los ficheros protegidos son los del commit. El grep
    prueba algo distinto y complementario: que el código que corrió no TENÍA cómo
    escribir. Sin lo segundo, un `git checkout` posterior taparía una escritura.
    """
    status = _git("status", "--short")
    diff = _git("diff", "--stat")
    diff_cached = _git("diff", "--cached", "--stat")
    protegidos = {}
    for p in PROTEGIDOS:
        d = _git("diff", "HEAD", "--stat", "--", p).strip()
        protegidos[p] = {"diff_vs_HEAD": d, "limpio": d == ""}
    # Ficheros del catálogo listados uno a uno (un diff vacío sobre el directorio
    # también sería vacío si el directorio no existiera: lo comprobamos aparte).
    catalogo = sorted(x.name for x in (ROOT / "data" / "catalog").glob("*.jsonl"))
    # Verbos HTTP mutantes en los scripts que corrieron.
    MUTANTES = re.compile(r"\.(post|patch|put|delete)\s*\(")
    escrituras = re.compile(r"(write_text|write_bytes|open\([^)]*['\"][wa])")
    est = {}
    for s in SCRIPTS:
        txt = (ROOT / "scripts" / s).read_text(encoding="utf-8")
        # Se ignoran comentarios y docstrings de cabecera para no contar prosa.
        codigo = "\n".join(l for l in txt.splitlines()
                           if not l.lstrip().startswith("#"))
        est[s] = {
            "verbos_mutantes": sorted({m.group(0) for m in MUTANTES.finditer(codigo)}),
            "lineas_de_escritura": [l.strip()[:120] for l in codigo.splitlines()
                                    if escrituras.search(l)],
        }
    return {
        "git_status_short": status.strip().splitlines(),
        "git_diff_stat": diff.strip(),
        "git_diff_cached_stat": diff_cached.strip(),
        "ficheros_protegidos": protegidos,
        "catalogo_presente": catalogo,
        "estatico_scripts": est,
    }


# ═══════════════════════ Extracción normalizada de filas ═══════════════════════
# Cada recibo tiene su propio esquema. Aquí se traducen todos a una fila común
# para poder auditarlos con UN solo criterio. La traducción declara, por fila:
#   sujeto · cita · doc_atribuido · docs_universo · confianza · veredicto ·
#   cita_verificada_por_el_agente · tiene_cita_por_diseno

def _filas_e1b_encoger(d: dict, seccion: str) -> list[dict]:
    out = []
    for i, r in enumerate(d["detalle"][seccion]):
        ev = r.get("evidencia") or {}
        universo = [ev.get("document_id")] + [
            x.get("document_id") for x in (r.get("evidencias_extra") or [])]
        # Dos rutas distintas y hay que auditarlas distinto:
        #  - determinista: la "cita" es el FRAGMENTO extraído del corpus por el
        #    propio script (no hay LLM). Se audita igual: tiene que existir.
        #  - llm: la cita la escribió el modelo. Es la que puede inventarse.
        es_llm = r.get("ruta") == "llm"
        cita = r.get("cita") if es_llm else ev.get("fragmento")
        out.append({
            "sujeto": r.get("id"), "modelo": r.get("modelo"),
            "cita": cita, "origen_cita": "llm" if es_llm else "fragmento_corpus",
            # El fragmento determinista declara el chunk EXACTO del que salió:
            # es la comprobación de procedencia más fuerte disponible (más que
            # el documento entero), así que se usa primero cuando existe.
            "chunk_id": ev.get("chunk_id"),
            "doc_atribuido_id": ev.get("document_id"),
            "docs_universo": [x for x in universo if x],
            "confianza": r.get("confianza"), "veredicto": r.get("veredicto"),
            "verificada_por_agente": r.get("cita_verificada"),
            "idx": i,
        })
    return out


def _filas_tierb(d: dict, seccion: str) -> list[dict]:
    out = []
    for i, r in enumerate(d[seccion]):
        llm = r.get("llm") or {}
        out.append({
            "sujeto": r.get("document_id"), "modelo": r.get("source_file"),
            "cita": llm.get("cita"), "origen_cita": "llm",
            "doc_atribuido_id": r.get("document_id"),
            "docs_universo": [r.get("document_id")],
            "confianza": llm.get("confianza"), "veredicto": llm.get("veredicto"),
            "verificada_por_agente": r.get("cita_verificada_full_text"),
            "idx": i,
        })
    return out


def _filas_triage(d: dict, seccion: str) -> list[dict]:
    out = []
    for i, r in enumerate(d[seccion]):
        llm = r.get("llm") or {}
        out.append({
            "sujeto": r.get("id"), "modelo": r.get("canonical_model"),
            "cita": llm.get("cita"), "origen_cita": "llm",
            "doc_atribuido_id": (r.get("documento") or {}).get("id"),
            # El universo REAL que usó el agente: doc de origen + TODOS los
            # chunks muestreados, que vienen de otros documentos. Es el punto
            # débil que hay que medir, no asumir.
            "docs_universo": [(r.get("documento") or {}).get("id")],
            "pasajes": [p.get("texto") for p in (r.get("pasajes") or [])],
            "confianza": llm.get("confianza"), "veredicto": llm.get("veredicto"),
            "verificada_por_agente": r.get("cita_verificada"),
            "idx": i,
        })
    return out


def _filas_pm_sucio(d: dict, seccion: str) -> list[dict]:
    out = []
    for i, r in enumerate(d[seccion]):
        out.append({
            "sujeto": r.get("document_id"), "modelo": r.get("source_file"),
            "cita": r.get("cita"), "origen_cita": "llm",
            "doc_atribuido_id": r.get("document_id"),
            "docs_universo": [r.get("document_id")],
            "confianza": r.get("confianza"), "veredicto": r.get("veredicto"),
            "verificada_por_agente": r.get("cita_verificada_full_text"),
            "idx": i,
        })
    return out


def _filas_qa(d: dict, seccion: str) -> list[dict]:
    out = []
    for i, r in enumerate(d["secciones"][seccion]):
        llm = r.get("llm") or {}
        out.append({
            "sujeto": r.get("id"), "modelo": r.get("modelo"),
            "cita": llm.get("cita"), "origen_cita": "llm",
            # Este recibo NO guarda document_id: solo el nombre del manual de
            # procedencia. Hay que resolverlo a id, y eso ya es un hallazgo de
            # trazabilidad por sí mismo.
            "doc_atribuido_nombre": r.get("provenance_doc"),
            "doc_atribuido_id": None, "docs_universo": [],
            "confianza": llm.get("confianza"), "veredicto": llm.get("veredicto"),
            "verificada_por_agente": r.get("cita_verificada"),
            "idx": i,
        })
    return out


def _filas_sin_cita(d: dict, seccion: str, campo_id: str) -> list[dict]:
    """Recibos cuyo bloque es DETERMINISTA y no lleva cita (e1_colisiones, e2).

    No es un defecto por sí mismo — su criterio no es documental sino de gates /
    de resolución en el catálogo. Pero hay que decirlo en voz alta: en esas filas
    el «bloque» NO descansa en ninguna cita verificada, y el encargo pedía
    comprobar exactamente eso.
    """
    out = []
    for i, r in enumerate(d[seccion]):
        out.append({
            "sujeto": r.get(campo_id) or r.get("model"),
            "modelo": r.get("model") or r.get("source_file"),
            "cita": None, "origen_cita": "sin_cita_por_diseno",
            "doc_atribuido_id": (r.get("doc_map") or {}).get("document_id"),
            "docs_universo": [], "confianza": None, "veredicto": None,
            "verificada_por_agente": None, "idx": i, "crudo": r,
        })
    return out


def cosechar() -> dict:
    """Devuelve {clave_bloque: [filas normalizadas]} para TODO el bloque."""
    e1b = _cargar("e1b_encoger")
    tb = _cargar("e1s2_tierb")
    tr = _cargar("g1_triage")
    pm = _cargar("g1_pm_sucio")
    qa = _cargar("e1b_qa")
    col = _cargar("e1_colisiones")
    e2 = _cargar("e2_altas")
    return {
        "e1b_encoger/bloque": _filas_e1b_encoger(e1b, "bloque"),
        "e1s2_tierb/seccion_0_bloque": _filas_tierb(tb, "seccion_0_bloque"),
        "g1_triage/0a_alta": _filas_triage(tr, "seccion_0a_alta_en_bloque"),
        "g1_triage/0b_retirar": _filas_triage(tr, "seccion_0b_retirar_en_bloque"),
        "g1_pm_sucio/seccion_0_bloque": _filas_pm_sucio(pm, "seccion_0_bloque"),
        "e1b_qa/0_bloque_confirmar": _filas_qa(qa, "0_bloque_confirmar"),
        "e1b_qa/0_bloque_retirar": _filas_qa(qa, "0_bloque_retirar"),
        "e1_colisiones/seccion_0_bloque": _filas_sin_cita(col, "seccion_0_bloque",
                                                          "source_file"),
        "e2_altas/seccion_0_bloque": _filas_sin_cita(e2, "seccion_0_bloque", "model"),
    }


# ═══════════════════════ B. CUADRE DE CONTEOS ═══════════════════════

def bloque_b() -> dict:
    """Cabecera declarada vs `len()` real. Cada recibo declara distinto."""
    res = {}

    col = _cargar("e1_colisiones")
    res["e1_colisiones"] = {
        "declarado": col["totales"],
        "real": {"seccion_0_bloque": len(col["seccion_0_bloque"]),
                 "seccion_1_individual": len(col["seccion_1_individual"]),
                 "seccion_ya_no_aplica": len(col["seccion_ya_no_aplica"])},
        "cuadra_total": (col["totales"]["analizadas"]
                         == len(col["seccion_0_bloque"])
                         + len(col["seccion_1_individual"])
                         + len(col["seccion_ya_no_aplica"])),
    }

    e = _cargar("e1b_encoger")
    res["e1b_encoger"] = {
        "declarado": {"total": e["total"], "bloque": e["bloque"],
                      "individual": e["individual"],
                      "desglose_bloque": e["desglose_bloque"],
                      "desglose_individual": e["desglose_individual"]},
        "real": {"bloque": len(e["detalle"]["bloque"]),
                 "individual": len(e["detalle"]["individual"])},
        "cuadra_total": e["total"] == len(e["detalle"]["bloque"]) + len(e["detalle"]["individual"]),
        "cuadra_desglose_bloque": sum(e["desglose_bloque"].values()) == len(e["detalle"]["bloque"]),
        "cuadra_desglose_individual": sum(e["desglose_individual"].values()) == len(e["detalle"]["individual"]),
    }

    t = _cargar("e1s2_tierb")
    res["e1s2_tierb"] = {
        "declarado": t["totales"],
        "real": {"bloque": len(t["seccion_0_bloque"]),
                 "individual": len(t["seccion_1_individual"]),
                 "fuera": len(t["seccion_2_fuera_del_packet"])},
        # OJO: aquí «analizadas» NO es bloque+individual, hay una TERCERA bolsa.
        "cuadra_total_con_tercera_bolsa": (
            t["totales"]["analizadas"] == len(t["seccion_0_bloque"])
            + len(t["seccion_1_individual"]) + len(t["seccion_2_fuera_del_packet"])),
        "cuadra_total_estricto_bloque_mas_individual": (
            t["totales"]["analizadas"] == len(t["seccion_0_bloque"])
            + len(t["seccion_1_individual"])),
    }

    a = _cargar("e2_altas")
    r = a["resumen"]
    res["e2_altas"] = {
        "declarado": {k: r[k] for k in ("total_packet", "seccion_0_bloque",
                                        "seccion_1_individual",
                                        "obsoletas_por_refresco")},
        "real": {"bloque": len(a["seccion_0_bloque"]),
                 "individual": len(a["seccion_1_individual"]),
                 "obsoletas": len(a["obsoletas"])},
        "cuadra_total": (r["total_packet"] == len(a["seccion_0_bloque"])
                         + len(a["seccion_1_individual"]) + len(a["obsoletas"])),
        "cuadra_individual_por_clase": (
            sum(r["individual_por_clase"].values()) == len(a["seccion_1_individual"])),
    }

    g = _cargar("g1_triage")
    rg = g["resumen"]
    res["g1_triage"] = {
        "declarado": {k: rg[k] for k in ("total", "seccion_0_bloque",
                                         "seccion_0a_alta_en_bloque",
                                         "seccion_0b_retirar_en_bloque",
                                         "seccion_1_individual")},
        "real": {"0a": len(g["seccion_0a_alta_en_bloque"]),
                 "0b": len(g["seccion_0b_retirar_en_bloque"]),
                 "individual": len(g["seccion_1_individual"])},
        "cuadra_total": (rg["total"] == len(g["seccion_0a_alta_en_bloque"])
                         + len(g["seccion_0b_retirar_en_bloque"])
                         + len(g["seccion_1_individual"])),
        "cuadra_por_veredicto": sum(rg["por_veredicto"].values()) == rg["total"],
    }

    p = _cargar("g1_pm_sucio")
    res["g1_pm_sucio"] = {
        "declarado": p["totales"],
        "real": {"bloque": len(p["seccion_0_bloque"]),
                 "individual": len(p["seccion_1_individual"])},
        "cuadra_total": (p["totales"]["analizadas"] == len(p["seccion_0_bloque"])
                         + len(p["seccion_1_individual"])),
    }

    q = _cargar("e1b_qa")
    res["e1b_qa"] = {
        "declarado": {"total": q["total"], "bloque": q["bloque"],
                      "individual": q["individual"], "por_seccion": q["por_seccion"],
                      "por_clase": q["por_clase"], "resumen_llm": q["resumen_llm"]},
        "real": {"0_bloque_confirmar": len(q["secciones"]["0_bloque_confirmar"]),
                 "0_bloque_retirar": len(q["secciones"]["0_bloque_retirar"]),
                 "individual": len(q["secciones"]["1_individual"])},
        "cuadra_total": (q["total"] == len(q["secciones"]["0_bloque_confirmar"])
                         + len(q["secciones"]["0_bloque_retirar"])
                         + len(q["secciones"]["1_individual"])),
        "cuadra_bloque": (q["bloque"] == len(q["secciones"]["0_bloque_confirmar"])
                          + len(q["secciones"]["0_bloque_retirar"])),
        # por_clase solo cubre las filas SIN llamada al juez + las reusadas:
        # se comprueba que no exceda el total.
        "suma_por_clase": sum(q["por_clase"].values()),
        "suma_resumen_llm": sum(q["resumen_llm"].values()),
    }
    return res


# ═══════════════════════ C. CRITERIO DEL BLOQUE ═══════════════════════

VEREDICTOS_PROHIBIDOS = {"NO_DECIDIBLE", "no_decidible", "DUDOSO", "dudoso"}


def bloque_c(cosecha: dict) -> dict:
    """Filas de bloque que NO cumplen el criterio que el propio packet promete."""
    fallos, resumen = [], {}
    for clave, filas in cosecha.items():
        v = {"n": len(filas), "confianza_no_alta": 0, "cita_vacia": 0,
             "veredicto_prohibido": 0, "no_verificada_por_agente": 0,
             "sin_cita_por_diseno": 0}
        for f in filas:
            if f["origen_cita"] == "sin_cita_por_diseno":
                v["sin_cita_por_diseno"] += 1
                continue
            malo = []
            if f["origen_cita"] == "llm":
                # El fragmento del corpus no lleva confianza: no lo juzgó nadie.
                if f["confianza"] != "alta":
                    v["confianza_no_alta"] += 1
                    malo.append(f"confianza={f['confianza']!r}")
                if f["verificada_por_agente"] is not True:
                    v["no_verificada_por_agente"] += 1
                    malo.append(f"cita_verificada={f['verificada_por_agente']!r}")
            if not (f["cita"] or "").strip():
                v["cita_vacia"] += 1
                malo.append("cita vacía")
            elif len(_norm(f["cita"])) < CITA_MIN:
                v["cita_vacia"] += 1
                malo.append(f"cita de {len(_norm(f['cita']))} chars (<{CITA_MIN})")
            if (f["veredicto"] or "") in VEREDICTOS_PROHIBIDOS:
                v["veredicto_prohibido"] += 1
                malo.append(f"veredicto={f['veredicto']!r}")
            if malo:
                fallos.append({"bolsa": clave, "idx": f["idx"],
                               "sujeto": f["sujeto"], "modelo": f["modelo"],
                               "problemas": malo})
        resumen[clave] = v
    return {"resumen_por_bolsa": resumen, "filas_que_fallan_el_criterio": fallos}


# ═══════════════════════ D. CITAS REALES (reejecución) ═══════════════════════

_CACHE_DOC: dict[str, str] = {}
_CACHE_NOMBRE: dict[str, list[str]] = {}
_LOCK = threading.Lock()


def _doc_texto(cliente, doc_id: str) -> str:
    """Documento ENTERO reconstruido concatenando TODOS sus chunks, normalizado.

    Se pagina de verdad: un `limit` implícito de PostgREST (1000) truncaría los
    manuales largos y produciría falsos «no verifica» — exactamente el falso
    positivo que haría ruidoso este informe.
    """
    if not doc_id:
        return ""
    with _LOCK:
        if doc_id in _CACHE_DOC:
            return _CACHE_DOC[doc_id]
    partes, off = [], 0
    while True:
        r = cliente.get(f"{SUPABASE_URL}/rest/v1/chunks_v2", headers=H, params={
            "select": "content,chunk_index", "document_id": f"eq.{doc_id}",
            "order": "chunk_index.asc", "limit": "1000", "offset": str(off)})
        if r.status_code not in (200, 206):
            break
        filas = r.json()
        partes += [(x.get("content") or "") for x in filas]
        if len(filas) < 1000:
            break
        off += 1000
    txt = _norm(" ".join(partes))
    with _LOCK:
        _CACHE_DOC[doc_id] = txt
    return txt


def _chunk_texto(cliente, chunk_id: str) -> str:
    """Contenido de UN chunk por su id. `chunks_v2` usa `id` como clave."""
    if not chunk_id:
        return ""
    with _LOCK:
        k = "chunk:" + chunk_id
        if k in _CACHE_DOC:
            return _CACHE_DOC[k]
    txt = ""
    r = cliente.get(f"{SUPABASE_URL}/rest/v1/chunks_v2", headers=H, params={
        "select": "content", "id": f"eq.{chunk_id}", "limit": "1"})
    if r.status_code in (200, 206) and r.json():
        txt = _norm(r.json()[0].get("content") or "")
    with _LOCK:
        _CACHE_DOC[k] = txt
    return txt


def _texto_por_source_file(cliente, nombre: str) -> str:
    """Texto de todos los chunks cuyo `source_file` casa con ese nombre.

    `chunks_v2.source_file` y `documents.source_pdf_filename` NO siempre están
    en correspondencia 1:1 — hay ficheros servidos en chunks sin fila resoluble
    en `documents`. Esta vía cierra ese hueco.
    """
    if not nombre:
        return ""
    with _LOCK:
        k = "sf:" + nombre
        if k in _CACHE_DOC:
            return _CACHE_DOC[k]
    seguro = nombre.replace("%", r"\%").replace("_", r"\_").replace("*", "")
    r = cliente.get(f"{SUPABASE_URL}/rest/v1/chunks_v2", headers=H, params={
        "select": "content", "source_file": f"ilike.{seguro}*", "limit": "1000"})
    txt = ""
    if r.status_code in (200, 206):
        txt = _norm(" ".join((x.get("content") or "") for x in r.json()))
    with _LOCK:
        _CACHE_DOC[k] = txt
    return txt


def _limpia_nombre_doc(nombre: str) -> str:
    """El campo `provenance_doc` del recibo E1b-QA NO siempre es un nombre.

    En unas filas vale «AM-8200-manu-prog-spa» y en otras arrastra la anotación
    entera: «AM-8200-manu-prog-spa (brand-tier=mecanico) | typo-merge:SDX-751TEM
    | alias-canonical-collision→candidate». Un campo llamado «doc» que a veces no
    es un doc rompe cualquier consumidor automático — se corta por el primer
    paréntesis o barra para poder resolverlo, y se reporta como defecto aparte.
    """
    n = (nombre or "").strip()
    for corte in (" (", " |", "|"):
        if corte in n:
            n = n.split(corte)[0].strip()
    return n


def _patron_ilike(texto: str) -> str:
    """Convierte un trozo de cita en patrón `ilike` tolerante a espacios.

    Cada racha de espacio en blanco se sustituye por `*`: así el patrón casa
    aunque en la base el salto de línea de una tabla esté donde la cita tiene un
    espacio. Sin esto, el sondeo global daría falsos negativos justo en las citas
    que cruzan celdas — que son las más frecuentes en manuales técnicos.
    """
    t = texto.replace("%", r"\%").replace("_", r"\_").replace("*", " ")
    return "*" + re.sub(r"\s+", "*", t.strip()) + "*"


def _busca_cita_en_corpus(cliente, cita_norm: str) -> dict | None:
    """¿Existe la cita en ALGÚN sitio del corpus? Distingue invención de
    mala atribución, que es la diferencia entre «fraude» y «traza floja»."""
    trozo = cita_norm[:110]
    if len(trozo) < CITA_MIN:
        return None
    r = cliente.get(f"{SUPABASE_URL}/rest/v1/chunks_v2", headers=H, params={
        "select": "id,document_id,source_file", "content": f"ilike.{_patron_ilike(trozo)}",
        "limit": "3"})
    if r.status_code in (200, 206) and r.json():
        x = r.json()[0]
        return {"document_id": x["document_id"], "source_file": x.get("source_file")}
    return None


def _docs_por_nombre(cliente, nombre: str) -> list[str]:
    """Resuelve nombre de fichero -> document_id(s). El recibo E1b-QA solo guarda
    el NOMBRE del manual de procedencia, así que hay que ir a `documents`."""
    nombre = _limpia_nombre_doc(nombre)
    if not nombre:
        return []
    with _LOCK:
        if nombre in _CACHE_NOMBRE:
            return _CACHE_NOMBRE[nombre]
    ids = []
    for patron in (f"ilike.{nombre}*", f"ilike.*{nombre}*"):
        r = cliente.get(f"{SUPABASE_URL}/rest/v1/documents", headers=H, params={
            "select": "id,source_pdf_filename,status",
            "source_pdf_filename": patron, "limit": "20"})
        if r.status_code in (200, 206) and r.json():
            ids = [x["id"] for x in r.json()]
            break
    with _LOCK:
        _CACHE_NOMBRE[nombre] = ids
    return ids


def _censo_chunks_del_modelo(cliente, modelo: str, limite: int = 60) -> str:
    """Universo ANCHO para el recibo E1b-QA: los chunks del corpus que mencionan
    el modelo. Es lo que el agente le enseñó al juez; verificar solo contra el doc
    de procedencia produciría fallos que no son invenciones sino atribuciones."""
    if not modelo:
        return ""
    seguro = modelo.replace("*", "").replace("%", "").replace(",", " ")
    r = cliente.get(f"{SUPABASE_URL}/rest/v1/chunks_v2", headers=H, params={
        "select": "content", "content": f"ilike.*{seguro}*", "limit": str(limite)})
    if r.status_code not in (200, 206):
        return ""
    return _norm(" ".join((x.get("content") or "") for x in r.json()))


def _verificar(cliente, f: dict) -> dict:
    """Reejecuta la verificación de UNA cita, desde cero, contra `chunks_v2`.

    Devuelve un veredicto de TRES estados, y los tres estados son el hallazgo:
      VERIFICA_EN_DOC_ATRIBUIDO — la cita está en el documento que la fila nombra.
      VERIFICA_SOLO_EN_OTRO_DOC — la cita existe en el corpus pero NO en ese doc.
      NO_VERIFICA — la cita no está en ninguna parte del material. Invención.
    El segundo estado no es fraude, pero un packet que enseña cita + documento
    juntos está afirmando el primero.
    """
    bruta = _sin_puntos_suspensivos(f.get("cita") or "")
    # DOS variantes, y la razón es un fallo que ya cometí en la pasada anterior:
    # quitar «» de la cita (porque el modelo las usa como comillas) rompe las
    # citas donde las guillemets ESTÁN en el corpus — el manual de Securiton
    # escribe literalmente «Basic Control Board». Se prueban las dos formas y
    # basta que una case: exigir la variante equivocada fabrica invenciones.
    variantes = [_norm(bruta[:MAX_CITA]),
                 _norm(bruta.replace("«", "").replace("»", "")[:MAX_CITA])]
    variantes = [v for v in dict.fromkeys(variantes) if len(v) >= CITA_MIN]
    if not variantes:
        return {"estado": "CITA_INUTIL", "detalle": f"cita de {len(_norm(bruta))} chars"}

    def _en(txt: str) -> bool:
        return bool(txt) and any(v in txt for v in variantes)

    # Procedencia EXACTA cuando la fila la declara: el chunk concreto.
    if f.get("chunk_id") and _en(_chunk_texto(cliente, f["chunk_id"])):
        return {"estado": "VERIFICA_EN_DOC_ATRIBUIDO",
                "nivel": "chunk_exacto_declarado", "chunk": f["chunk_id"]}

    doc_id = f.get("doc_atribuido_id")
    if doc_id and _en(_doc_texto(cliente, doc_id)):
        return {"estado": "VERIFICA_EN_DOC_ATRIBUIDO", "nivel": "documento", "doc": doc_id}

    # Atribución POR NOMBRE (recibo E1b-QA). Dos trampas que hay que sortear
    # antes de acusar a nadie de mala atribución:
    #  1. un mismo nombre de fichero puede tener VARIAS filas en `documents`
    #     (revisiones, duplicados-fantasma): hay que probarlas TODAS, no la 1ª;
    #  2. hay ficheros que existen como `chunks_v2.source_file` pero NO tienen
    #     fila resoluble en `documents` — mirar solo `documents` los declaraba
    #     mal atribuidos (me pasó con las 6 filas de Xtralis 9-109xx).
    if not doc_id and f.get("doc_atribuido_nombre"):
        nombre = _limpia_nombre_doc(f["doc_atribuido_nombre"])
        for cand in _docs_por_nombre(cliente, nombre):
            if _en(_doc_texto(cliente, cand)):
                return {"estado": "VERIFICA_EN_DOC_ATRIBUIDO", "nivel": "documento",
                        "doc": cand, "por_nombre": nombre}
        if _en(_texto_por_source_file(cliente, nombre)):
            return {"estado": "VERIFICA_EN_DOC_ATRIBUIDO", "nivel": "source_file",
                    "doc": nombre}

    # Universo ancho: los OTROS documentos que el agente puso delante del juez.
    for otro in f.get("docs_universo") or []:
        if otro and otro != doc_id and _en(_doc_texto(cliente, otro)):
            return {"estado": "VERIFICA_SOLO_EN_OTRO_DOC", "doc": otro,
                    "doc_atribuido": doc_id}
    # Pasajes que el propio recibo guarda (triage): son texto del corpus tal cual.
    for p in f.get("pasajes") or []:
        if _en(_norm(p or "")):
            return {"estado": "VERIFICA_SOLO_EN_OTRO_DOC", "doc": "pasaje_del_recibo",
                    "doc_atribuido": doc_id}
    # Sondeo GLOBAL: ¿está en cualquier punto del corpus? Es la pregunta que
    # separa una invención (no está en ningún sitio) de una atribución floja.
    hallado = _busca_cita_en_corpus(cliente, variantes[0])
    if hallado:
        return {"estado": "VERIFICA_SOLO_EN_OTRO_DOC", "doc": hallado["document_id"],
                "source_file": hallado["source_file"], "doc_atribuido": doc_id}
    ancho = _censo_chunks_del_modelo(cliente, f.get("modelo") or "")
    if _en(ancho):
        return {"estado": "VERIFICA_SOLO_EN_OTRO_DOC", "doc": "censo_por_modelo",
                "doc_atribuido": doc_id}
    return {"estado": "NO_VERIFICA", "doc_atribuido": doc_id,
            "cita_normalizada": variantes[0][:180]}


def bloque_d(cosecha: dict, semilla: int, hilos: int) -> dict:
    """D1 = la muestra de 12 que manda el encargo. D2 = el censo completo."""
    con_cita = []
    for clave, filas in cosecha.items():
        for f in filas:
            if f["origen_cita"] != "sin_cita_por_diseno" and (f.get("cita") or ""):
                g = dict(f)
                g["bolsa"] = clave
                con_cita.append(g)

    # --- D1: muestra ALEATORIA de 12, REPARTIDA entre recibos ----------------
    # Estratificada por bolsa: 12 filas al azar de la bolsa más grande no
    # comprobarían «repartidas entre los recibos», que es lo que pide el encargo.
    rng = random.Random(semilla)
    por_bolsa: dict[str, list] = {}
    for f in con_cita:
        por_bolsa.setdefault(f["bolsa"], []).append(f)
    bolsas = sorted(por_bolsa)
    muestra, i = [], 0
    while len(muestra) < 12 and any(por_bolsa.values()):
        b = bolsas[i % len(bolsas)]
        i += 1
        if por_bolsa[b]:
            # `por_bolsa` son listas nuevas de COPIAS: el pop no toca la cosecha,
            # así que el censo posterior sigue viendo las 570 filas completas.
            muestra.append(por_bolsa[b].pop(rng.randrange(len(por_bolsa[b]))))

    res_muestra, res_censo = [], []
    with abierto(timeout=60.0) as cliente:
        def _run(f):
            v = _verificar(cliente, f)
            return {"bolsa": f["bolsa"], "idx": f["idx"], "sujeto": f["sujeto"],
                    "modelo": f["modelo"], "confianza": f["confianza"],
                    "veredicto": f["veredicto"],
                    "verificada_por_agente": f["verificada_por_agente"],
                    "cita": (f.get("cita") or "")[:MAX_CITA],
                    "doc_atribuido": f.get("doc_atribuido_id")
                                     or f.get("doc_atribuido_nombre"),
                    "mi_verificacion": v}
        res_muestra = [_run(f) for f in muestra]
        with ThreadPoolExecutor(max_workers=hilos) as ex:
            res_censo = list(ex.map(_run, con_cita))

    def _tally(rs):
        t = {}
        for r in rs:
            t[r["mi_verificacion"]["estado"]] = t.get(r["mi_verificacion"]["estado"], 0) + 1
        return t

    por_bolsa_censo = {}
    for r in res_censo:
        d = por_bolsa_censo.setdefault(r["bolsa"], {})
        e = r["mi_verificacion"]["estado"]
        d[e] = d.get(e, 0) + 1

    return {
        "d1_muestra_mandada": {
            "semilla": semilla, "n": len(res_muestra),
            "tally": _tally(res_muestra), "filas": res_muestra,
        },
        "d2_censo_completo": {
            "n": len(res_censo), "tally": _tally(res_censo),
            "por_bolsa": por_bolsa_censo,
            "no_verifican": [r for r in res_censo
                             if r["mi_verificacion"]["estado"] == "NO_VERIFICA"],
            "verifican_solo_en_otro_doc": [
                {k: r[k] for k in ("bolsa", "sujeto", "modelo", "cita",
                                   "doc_atribuido", "mi_verificacion")}
                for r in res_censo
                if r["mi_verificacion"]["estado"] == "VERIFICA_SOLO_EN_OTRO_DOC"],
        },
    }


# ═══════════════════════ D-bis. El bloque SIN cita ═══════════════════════

def _paginado(cliente, tabla: str, params: dict) -> list[dict]:
    filas, off = [], 0
    while True:
        r = cliente.get(f"{SUPABASE_URL}/rest/v1/{tabla}", headers=H,
                        params={**params, "limit": "1000", "offset": str(off)})
        r.raise_for_status()
        lote = r.json()
        filas += lote
        if len(lote) < 1000:
            return filas
        off += 1000


def bloque_d_bis() -> dict:
    """El bloque de E2 (562 altas) no lleva cita: su aval es `chunk_count_hoy`.

    Una afirmación numérica es igual de falsable que una cita, así que se REMIDE
    — las 562, no una muestra. Y se remide con la MISMA definición que usó el
    agente, que hubo que leer en su código para no comparar peras con manzanas:
    `chunk_count_hoy` NO es «veces que el término aparece en el texto», es
    «chunks de documentos ACTIVOS cuyo product_model normaliza al término».
    (Mi primera pasada lo midió como menciones en `content` y produjo 18/20
    «discrepancias» que eran todas mías. Se deja escrito para que nadie repita
    el error de auditar una cifra sin leer su definición.)
    """
    from src.rag.catalog import normkey  # noqa: PLC0415  (misma normalización que el agente)

    a = _cargar("e2_altas")
    with abierto(timeout=120.0) as cliente:
        docs_all = _paginado(cliente, "documents",
                             {"select": "id,source_pdf_filename,status", "order": "id.asc"})
        chunks = _paginado(cliente, "chunks_v2",
                           {"select": "product_model,source_file", "order": "id.asc"})
    activos = {d["id"] for d in docs_all if d.get("status") == "active"}
    sf_activos = {re.sub(r"\.pdf$", "", (d.get("source_pdf_filename") or "").strip().lower())
                  for d in docs_all if d["id"] in activos}
    pm: dict[str, int] = {}
    for ch in chunks:
        if (ch.get("source_file") or "").strip().lower() in sf_activos:
            nk = normkey(ch.get("product_model") or "")
            if nk:
                pm[nk] = pm.get(nk, 0) + 1

    disc = []
    for r in a["seccion_0_bloque"]:
        esperado = pm.get(normkey(r["model"] or ""), 0)
        if esperado != (r.get("chunk_count_hoy") or 0):
            disc.append({"model": r["model"], "declarado": r.get("chunk_count_hoy"),
                         "remedido": esperado})
    return {
        "definicion_verificada": ("chunks de documentos ACTIVOS cuyo product_model "
                                  "normaliza (normkey) al término del alta"),
        "docs_activos": len(activos), "chunks_leidos": len(chunks),
        "n_filas_bloque": len(a["seccion_0_bloque"]),
        "discrepancias": disc,
        "nota_metodo": ("la colisión de nombres entre marcas es posible: normkey "
                        "no distingue fabricante, igual que en el original"),
    }


# ═══════════════════════ E. PACKETS ═══════════════════════

RE_SEC = re.compile(r"^#{2,3}\s*(?:SECCIÓN|§)\s*(.+?)\s*$", re.M)
RE_CASILLA = re.compile(r"^\s*-\s*\[\s*\]", re.M)
RE_N = re.compile(r"\((\d+)\)")


def bloque_e() -> dict:
    """Cabeceras declaradas vs lo realmente escrito + cobertura de términos."""
    rec = _cargar("packets")
    out = {}
    for clave, ruta in PACKETS_MD.items():
        txt = ruta.read_text(encoding="utf-8")
        lineas = txt.splitlines()
        cabeceras = []
        for m in RE_SEC.finditer(txt):
            titulo = m.group(1)
            n = RE_N.findall(titulo)
            cabeceras.append({"titulo": titulo.strip()[:120],
                              "n_declarado": int(n[-1]) if n else None,
                              "linea": txt[:m.start()].count("\n") + 1})
        # contar casillas por sección: entre una cabecera y la siguiente
        marcas = [c["linea"] for c in cabeceras] + [len(lineas) + 1]
        for i, c in enumerate(cabeceras):
            trozo = "\n".join(lineas[marcas[i]:marcas[i + 1] - 1])
            c["casillas"] = len(RE_CASILLA.findall(trozo))
        # TITULAR vs CONTROLES. El packet se vende con «De N casillas → M
        # decisiones». M es la promesa de encogido que Alberto va a creer. Se
        # contrasta contra las casillas `- [ ]` REALMENTE escritas en el fichero:
        # si el documento ofrece 241 casillas y el titular dice 98 decisiones, el
        # encogido que Alberto lee no es el que el fichero le pone delante.
        m = re.search(r"De \*\*([\d.]+) casillas\*\* → \*\*(\d+) decisiones\*\*", txt)
        titular = {"casillas_v1": m.group(1), "decisiones_prometidas": int(m.group(2))} if m else None
        casillas_0 = sum(c["casillas"] for c in cabeceras
                         if re.match(r"^0(\.|\b)", c["titulo"]) or c["titulo"].startswith("0 "))
        out[clave] = {
            "fichero": str(ruta), "lineas_reales": len(lineas),
            "lineas_declaradas": rec["packets"][clave.lower()]["lineas"],
            "cuadra_lineas": len(lineas) == rec["packets"][clave.lower()]["lineas"],
            "cabeceras": cabeceras,
            "casillas_totales": len(RE_CASILLA.findall(txt)),
            "casillas_declaradas": sum(rec["packets"][clave.lower()]["casillas_por_seccion"].values()),
            "titular": titular,
            "casillas_en_seccion_0": casillas_0,
            "titular_vs_casillas": (
                None if not titular else {
                    "decisiones_prometidas": titular["decisiones_prometidas"],
                    "casillas_reales_en_el_fichero": len(RE_CASILLA.findall(txt)),
                    "casillas_en_el_bloque_que_dice_ser_1_si": casillas_0,
                    "coincide": titular["decisiones_prometidas"] == len(RE_CASILLA.findall(txt)),
                }),
        }

    # Cobertura: ¿está LISTADO cada término del bloque de E2, o solo contado?
    a = _cargar("e2_altas")
    txt_e2 = PACKETS_MD["E2"].read_text(encoding="utf-8")
    faltan_b = [r["model"] for r in a["seccion_0_bloque"] if r["model"] not in txt_e2]
    faltan_i = [r["model"] for r in a["seccion_1_individual"] if r["model"] not in txt_e2]
    out["cobertura_e2"] = {
        "bloque_total": len(a["seccion_0_bloque"]),
        "bloque_no_listados": len(faltan_b), "ejemplos_bloque": faltan_b[:15],
        "individual_total": len(a["seccion_1_individual"]),
        "individual_no_listados": len(faltan_i), "ejemplos_individual": faltan_i[:15],
    }
    # Cobertura E1b. OJO con el criterio de búsqueda: el packet lista el §0.A
    # determinista por MODELO con su medida —`CAD-250-BLED`(6·4)— agrupado por
    # marca, no por id `detnov:cad-250-bled`. Buscar el id daba 168 «ausentes»
    # que sí estaban: se busca el id O el modelo, que es lo que Alberto ve.
    e = _cargar("e1b_encoger")
    q = _cargar("e1b_qa")
    txt_e1b = PACKETS_MD["E1b"].read_text(encoding="utf-8")

    def _ausente(fila: dict) -> bool:
        return (fila.get("id") not in txt_e1b
                and (fila.get("modelo") or "\0") not in txt_e1b)

    f1 = [r["id"] for r in e["detalle"]["bloque"] if _ausente(r)]
    f2 = [r["id"] for r in q["secciones"]["0_bloque_confirmar"] if _ausente(r)]
    f3 = [r["id"] for r in e["detalle"]["individual"] if _ausente(r)]
    f4 = [r["id"] for r in q["secciones"]["1_individual"] if _ausente(r)]
    out["cobertura_e1b"] = {
        "criterio": "la fila cuenta como listada si aparece su id O su modelo",
        "encoger_bloque_no_listados": len(f1), "ejemplos": f1[:15],
        "qa_bloque_no_listados": len(f2), "ejemplos_qa": f2[:15],
        "encoger_individual_no_listados": len(f3), "ejemplos_ind": f3[:15],
        "qa_individual_no_listados": len(f4), "ejemplos_ind_qa": f4[:15],
    }
    out["recibo_packets"] = rec["packets"]
    return out


# ═══════════════════════ F. FRAMING ═══════════════════════

def bloque_f(cosecha: dict, d: dict) -> dict:
    """Afirmaciones narrativas contra los números del propio recibo."""
    e = _cargar("e1b_encoger")
    g = _cargar("g1_triage")
    a = _cargar("e2_altas")
    q = _cargar("e1b_qa")
    t = _cargar("e1s2_tierb")
    checks = []

    # 1) e1b: dice «el LLM solo interviene en el residuo». ¿Cuánto es el residuo?
    checks.append({
        "recibo": "e1b_encoger",
        "afirma": "el LLM solo interviene en el residuo que el determinismo no cierra",
        "numeros": {"bloque_determinista": e["desglose_bloque"]["determinista"],
                    "bloque_via_llm": e["desglose_bloque"]["llm_alta_verificada"],
                    "pct_bloque_que_depende_del_llm":
                        round(100 * e["desglose_bloque"]["llm_alta_verificada"]
                              / max(1, e["bloque"]), 1)},
    })
    # 2) e1b: llamadas al LLM HOY vs veredictos reutilizados de una pasada previa
    checks.append({
        "recibo": "e1b_encoger",
        "afirma": "recibo fechado hoy con 130 filas de bloque avaladas por el juez",
        "numeros": {"llamadas_llm_hoy": e["coste_llm"]["llamadas"],
                    "veredictos_reutilizados": e["coste_llm"]["reutilizadas_de_pasada_previa"],
                    "filas_remedidas_en_este_reintento": e["filas_remedidas_en_este_reintento"],
                    "deriva_de_conteo": e["deriva_conteo"]},
    })
    # 3) e1b: avisos DENTRO del bloque (fabricante distinto, colisiones de nombre)
    checks.append({
        "recibo": "e1b_encoger",
        "afirma": "bloque = un solo sí, sin residuo que mirar",
        "numeros": {"avisos_fabricante_distinto_en_bloque":
                        e["avisos_bloque"]["fabricante_del_manual_distinto_al_id"],
                    "colisiones_de_nombre_en_bloque": len(e["avisos_bloque"]["colisiones_de_nombre"]),
                    "evidencia_minima_en_bloque": len(e["avisos_bloque"]["evidencia_minima"])},
    })
    # 4) qa: veredictos reusados
    checks.append({
        "recibo": "e1b_qa",
        "afirma": "261 filas medidas hoy",
        "numeros": {"total": q["total"], "veredictos_reusados": q["veredictos_reusados"],
                    "filas_medidas_hoy_declaradas": q["recuento"]["filas_medidas_hoy"]},
    })
    # 5) triage: «artefactos detectados» vs cuántos van en bloque
    n_art_bloque = sum(1 for r in g["seccion_0b_retirar_en_bloque"])
    n_art_indiv = sum(1 for r in g["seccion_1_individual"]
                      if (r.get("llm") or {}).get("veredicto") == "ARTEFACTO_EXTRACCION")
    checks.append({
        "recibo": "g1_triage",
        "afirma": f"artefactos_detectados={g['hallazgos']['artefactos_detectados']}, "
                  f"chunks_etiquetados_por_terminos_artefacto="
                  f"{g['hallazgos']['chunks_etiquetados_por_terminos_artefacto']}",
        "numeros": {"artefactos_en_bloque_retirar": n_art_bloque,
                    "artefactos_en_individual": n_art_indiv,
                    "hallazgos_listados": sum(len(v) for v in g["hallazgos"]["por_clase"].values())},
    })
    # 6) e2: la nota whisper contra el reparto real del bloque
    sin_chunks = sum(1 for r in a["seccion_0_bloque"] if not r.get("chunk_count_hoy"))
    checks.append({
        "recibo": "e2_altas",
        "afirma": a["nota_whisper"][:120],
        "numeros": {"bloque_total": len(a["seccion_0_bloque"]),
                    "bloque_con_chunk_count_0": sin_chunks,
                    "pct": round(100 * sin_chunks / max(1, len(a["seccion_0_bloque"])), 1)},
    })
    # 7) tierb: bloque con cita que NO nombra al sujeto
    no_nombra = [r["document_id"] for r in t["seccion_0_bloque"]
                 if (r.get("llm") or {}).get("cita_nombra_al_sujeto") is False]
    cero_menciones = [r["document_id"] for r in t["seccion_0_bloque"]
                      if not r.get("menciones_maximas_en_el_documento")]
    checks.append({
        "recibo": "e1s2_tierb",
        "afirma": "42 entradas de doc_map aplicables en bloque",
        "numeros": {"bloque": len(t["seccion_0_bloque"]),
                    "con_cita_que_no_nombra_al_sujeto": len(no_nombra),
                    "con_0_menciones_del_sujeto_en_el_documento": len(cero_menciones),
                    "ejemplos_0_menciones": cero_menciones[:8]},
    })
    return {"contrastes": checks}


# ═══════════════════════ main ═══════════════════════

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--semilla", type=int, default=322815,
                    help="semilla del sorteo de la muestra de 12 (reproducible)")
    ap.add_argument("--hilos", type=int, default=8)
    ap.add_argument("--salida", default=str(DESTINO))
    args = ap.parse_args()

    cosecha = cosechar()
    print("A. integridad…", flush=True)
    a = bloque_a()
    print("B. conteos…", flush=True)
    b = bloque_b()
    print("C. criterio del bloque…", flush=True)
    c = bloque_c(cosecha)
    print("D. citas (muestra + censo)…", flush=True)
    d = bloque_d(cosecha, args.semilla, args.hilos)
    print("D-bis. bloque sin cita (E2)…", flush=True)
    dbis = bloque_d_bis()
    print("E. packets…", flush=True)
    e = bloque_e()
    print("F. framing…", flush=True)
    f = bloque_f(cosecha, d)

    recibo = {
        "que_es": ("s322h — verificación ADVERSARIAL del encogido de packets de "
                   "s322f/s322g. Reejecuta las citas contra chunks_v2 desde cero. "
                   "NO aplica nada: 0 escrituras en catálogo, Supabase y snapshot."),
        "no_se_aplico_nada": True,
        "solo_lectura_sobre": sorted(RECIBOS.values()) + [p.name for p in PACKETS_MD.values()],
        "a_integridad": a,
        "b_cuadre_de_conteos": b,
        "c_criterio_del_bloque": c,
        "d_citas_reejecutadas": d,
        "d_bis_bloque_sin_cita_e2": dbis,
        "e_packets": e,
        "f_framing": f,
    }
    destino = pathlib.Path(args.salida)
    if not destino.is_absolute():
        destino = ROOT / destino
    destino.write_text(json.dumps(recibo, ensure_ascii=False, indent=1),
                       encoding="utf-8")
    print("\nRECIBO:", destino)
    print("D1 muestra:", d["d1_muestra_mandada"]["tally"])
    print("D2 censo:", d["d2_censo_completo"]["tally"])
    print("C fallos de criterio:", len(c["filas_que_fallan_el_criterio"]))


if __name__ == "__main__":
    main()
