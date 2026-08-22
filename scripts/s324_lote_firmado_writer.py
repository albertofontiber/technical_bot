# -*- coding: utf-8 -*-
"""s324 — WRITER del lote firmado + CENSO del radio de explosión (mecánica T3, endurecida tras el dúo r32).

Consume `evals/s324_lote_firmado_plan_v1.json` (cada fila verificada full-text) y:

  dry-run (por defecto): aplica el plan sobre una COPIA temporal del catálogo (misma puerta
      `catalog_store.write_jsonl` → validador sobre el conjunto) y mide el RADIO DE EXPLOSIÓN:
      (1) detector del resolver (`_resolvable_terms`): términos que entran/salen, riesgo léxico,
          0 pérdidas en las 51 gold, 0 disparos en negativos, alias activados;
      (2) resolver completo (`resolve_query`) sobre las 51 gold ANTES/DESPUÉS: ningún gold pierde
          `allowed_sources` ni ids; se listan las ganancias;
      (3) efecto de los doc_map: fuentes que gana cada producto;
      (4) findability de los retags: el pm nuevo casa con ≥1 entry primaria del doc_map del doc.
      Estampa un FREEZE (sha de los 4 .jsonl + fingerprint del corpus + snapshot de los chunks a
      retaguear + pm actual de documents) — el --aplicar exige que NADA haya cambiado.
      NO toca data/catalog ni Supabase.
  --aplicar: (a) exige dry-run PASS del MISMO plan (sha) y del MISMO estado (freeze idéntico
      recalculado ahora); (b) preflight de retags ANTES de tocar el catálogo; (c) construye en tmp,
      valida, backup de los 4 .jsonl y SOLO ENTONCES los sustituye; (d) retags con CAS por chunk y
      CAS en `documents.product_model` (eq.pm_actual), documents solo si TODOS los chunks pasaron;
      (e) ante cualquier fallo: revierte los chunks ya parcheados y restaura el catálogo del backup
      (recibo ROLLED_BACK); (f) censo posterior; recibo con instrucciones de reversión.

Uso:  python scripts/s324_lote_firmado_writer.py [--aplicar]
"""
from __future__ import annotations
import argparse, hashlib, json, os, re, shutil, sys, tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv
load_dotenv(ROOT / ".env", override=False)
import yaml
from src.http_pool import abierto
from src.rag import catalog_store as cs
from src.rag.catalog_store import CATALOG_DIR, FILES, _read_jsonl, write_jsonl, norm_token
from src.rag import catalog_resolver as R
from src.rag import catalog as C
from src.rag.retriever import model_to_imatch_pattern

PLAN = ROOT / "evals" / "s324_lote_firmado_plan_v1.json"
CENSO = ROOT / "evals" / "s324_radio_explosion_v1.json"
SB = os.environ.get("SUPABASE_URL", "").rstrip("/")
HS = {"apikey": os.environ.get("SUPABASE_SERVICE_KEY", ""),
      "Authorization": f"Bearer {os.environ.get('SUPABASE_SERVICE_KEY', '')}"}
JSONL = ("products", "aliases", "umbrellas", "doc_map")

# Frases de técnico SIN ninguno de los productos del lote: el patrón nuevo NO debe disparar aquí.
# (Sintéticos, escritos por el autor: miden disparo léxico, NO cobertura de tráfico real.)
NEGATIVOS = [
    "tengo un fuego en la central y no sé qué hacer", "cuántas zonas tiene la central convencional de 2 zonas",
    "la sirena exterior no suena al activar la zona 3", "cómo mido la resistencia de final de línea de 4k7",
    "qué batería lleva la central, 7Ah o 12Ah", "el detector óptico da avería de sensibilidad",
    "quiero salir del menú de programación y volver al punto de salida", "la caja mediana no cabe en el hueco de la pared",
    "el módulo de 2 entradas y 1 salida no responde en el lazo", "sn del equipo y número de serie para la garantía",
    "cómo se conecta el relé de 4 contactos a la central", "necesito el plus de potencia en la fuente de 24V",
    "el punto de salida de emergencia está señalizado", "detector dual óptico térmico con aislador integrado",
    "cuál es la referencia del adaptador para bases antiguas", "las etiquetas adhesivas de la base se despegan",
    "caja para carril DIN de 1 módulo", "unidad de monitorización de zona inteligente",
    "sensor remoto de gases tóxicos versión ATEX", "central táctil de un lazo con impresora",
    "repetidor con pantalla táctil en caja pequeña", "central de extinción con 4 relés",
    "guía rápida de la serie de centrales direccionables", "hoja de instalación de los detectores serie 3000",
    "el panel de 1 lazo tiene 3 niveles de acceso", "programa de configuración compatible con Windows 10",
    "avería de resistencia de baterías", "no puedo comunicar con la central por el puerto serie",
    "el nx no arranca", "s3 t1 sensor", "2 x a", "dx 1", "vsn 12", "n io", "ke dp", "exit point de la instalación",
]


def sha_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def sha_obj(o) -> str:
    return hashlib.sha256(json.dumps(o, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


# ───────────────────────── freeze ─────────────────────────
def snapshot_retags(c, plan: dict) -> dict:
    """Estado exacto de lo que se va a retaguear: chunks (id, pm) por documento + pm de documents."""
    out = {}
    for rt in plan["retags_db"]:
        r = c.get(f"{SB}/rest/v1/chunks_v2", headers=HS,
                  params={"select": "id,product_model", "document_id": f"eq.{rt['document_id']}", "order": "id.asc"})
        r.raise_for_status()
        d = c.get(f"{SB}/rest/v1/documents", headers=HS,
                  params={"select": "id,product_model,status", "id": f"eq.{rt['document_id']}"})
        d.raise_for_status()
        out[rt["document_id"]] = {"chunks": [(x["id"], x["product_model"]) for x in r.json()],
                                  "documents_pm": (d.json() or [{}])[0].get("product_model"),
                                  "documents_status": (d.json() or [{}])[0].get("status")}
    return out


def freeze(c, plan: dict, catalog_dir: Path) -> dict:
    fp = R._try_corpus_fingerprint()
    return {"catalog_shas": {n: sha_file(catalog_dir / FILES[n]) for n in JSONL},
            "corpus_fingerprint": list(fp) if fp else None,
            "retags_snapshot_sha": sha_obj(snapshot_retags(c, plan))}


# ───────────────────────── plan → catálogo ─────────────────────────
def aplicar_plan(plan: dict, destino: Path, origen: Path) -> dict:
    prods = _read_jsonl(origen / FILES["products"])
    aliases = _read_jsonl(origen / FILES["aliases"])
    umbrellas = _read_jsonl(origen / FILES["umbrellas"])
    doc_map = _read_jsonl(origen / FILES["doc_map"])
    if origen != destino:
        for name in ("homonyms", "relations", "docrel"):
            if (origen / FILES[name]).exists():
                shutil.copy(origen / FILES[name], destino / FILES[name])
    ids = {p["id"] for p in prods}
    stats = {"altas": 0, "confirmadas": 0, "retiradas": 0, "aliases_quitados": 0, "umbrellas": 0,
             "doc_map_altas": 0, "doc_map_modificadas": 0}
    for a in plan["products_altas"]:
        if a["row"]["id"] in ids:
            continue
        prods.append(a["row"]); ids.add(a["row"]["id"]); stats["altas"] += 1
    by_id = {p["id"]: p for p in prods}
    for cf in plan["products_confirmar"]:
        p = by_id[cf["id"]]
        if p.get("candidate"):
            p["candidate"] = False
            p["provenance"] = (p.get("provenance") or "") + " | " + cf["provenance_add"]
            cl = (plan.get("clasificacion_confirmados") or {}).get(cf["id"])
            if cl and "clasificacion" not in p:
                p["clasificacion"] = cl
            stats["confirmadas"] += 1
    for rt in plan["products_retirar"]:
        p = by_id[rt["id"]]
        if p["estado"] == "activo":
            p["estado"] = "retirado"
            p["provenance"] = (p.get("provenance") or "") + f" | s324 retirado: {rt['motivo']}"
            stats["retiradas"] += 1
    stats["redirects"] = 0
    for rd in plan.get("products_redirect", []):          # id → redirect_to (namespace correcto); el id NO se borra ni se recicla
        p = by_id[rd["id"]]
        if p["estado"] != "redirect" and rd["redirect_to"] in ids:
            p["estado"] = "redirect"; p["redirect_to"] = rd["redirect_to"]
            p["candidate"] = False
            p["provenance"] = (p.get("provenance") or "") + f" | s324 redirect → {rd['redirect_to']}: {rd['motivo']}"
            stats["redirects"] += 1
    stats["vendido_bajo"] = 0
    for vb in plan.get("products_vendido_bajo", []):   # R3: el mismo aparato con dos etiquetas comerciales
        p = by_id.get(vb["id"])
        if not p:
            continue
        ya = list(p.get("vendido_bajo") or [])
        nuevas = [m for m in vb["marcas"] if m not in ya]
        if not nuevas:
            continue
        p["vendido_bajo"] = ya + nuevas
        p["provenance"] = (p.get("provenance") or "") + f" | s324 vendido_bajo += {nuevas}: {vb['motivo']}"
        stats["vendido_bajo"] += 1
    quitar = {(a["alias"], a["id"]) for a in plan["aliases_quitar"]}
    n0 = len(aliases)
    aliases = [a for a in aliases if (a.get("alias"), a.get("id")) not in quitar]
    stats["aliases_quitados"] = n0 - len(aliases)
    ya_alias = {norm_token(a["alias"]) for a in aliases}
    stats["aliases_altas"] = 0
    for a in plan.get("aliases_altas", []):
        if norm_token(a["alias"]) in ya_alias:
            continue
        aliases.append(a); ya_alias.add(norm_token(a["alias"])); stats["aliases_altas"] += 1
    terms = {norm_token(u["termino"]) for u in umbrellas}
    for u in plan["umbrellas_altas"]:
        if norm_token(u["termino"]) in terms or u.get("diferido"):
            continue
        umbrellas.append({k: v for k, v in u.items() if k != "diferido"}); terms.add(norm_token(u["termino"])); stats["umbrellas"] += 1
    dm_by_id = {r["document_id"]: r for r in doc_map}
    for m in plan["doc_map_modificaciones"]:
        r = dm_by_id.get(m["document_id"])
        if not r:
            continue
        prev = {e["id"]: e for e in r["entries"]}
        r["entries"] = [prev.get(pid) or {"id": pid, "role": "primary", "scope": "doc",
                                          "provenance": f"s324 {m['regla']}: {m['detalle']}"} for pid in m["entries_nuevas"]]
        stats["doc_map_modificadas"] += 1
    for alta in plan["doc_map_altas"]:
        if alta["document_id"] in dm_by_id:
            r = dm_by_id[alta["document_id"]]
            vistos = {e["id"] for e in r["entries"]}
            r["entries"] += [e for e in alta["entries"] if e["id"] not in vistos]
        else:
            row = {"document_id": alta["document_id"], "source_file": alta["source_file"], "entries": alta["entries"]}
            doc_map.append(row); dm_by_id[row["document_id"]] = row
        stats["doc_map_altas"] += 1
    write_jsonl("products", prods, catalog_dir=destino, validate_after=False)
    write_jsonl("aliases", aliases, catalog_dir=destino, validate_after=False)
    write_jsonl("umbrellas", umbrellas, catalog_dir=destino, validate_after=False)
    write_jsonl("doc_map", doc_map, catalog_dir=destino, validate_after=True)   # valida el conjunto
    return stats


# ───────────────────────── censo ─────────────────────────
def patron(cat):
    cores = []
    for nk, term in R._resolvable_terms(cat).items():
        core = C._core(term)
        if core:
            cores.append(core)
    cores.sort(key=len, reverse=True)
    seen: set[str] = set()
    alts = [c for c in cores if not (c in seen or seen.add(c))]
    return re.compile(r"\b(" + "|".join(alts) + r")(?![a-z0-9])") if alts else None


def detecta(pat, q: str) -> list[str]:
    if pat is None:
        return []
    out, seen = [], set()
    for m in pat.findall(C._fold(q)):
        nk = C.normkey(m)
        if nk and nk not in seen:
            seen.add(nk); out.append(m)
    return out


COMUNES = {"plus", "exit", "point", "max", "mini", "serie", "series", "central", "panel", "zona", "lazo",
           "fuego", "alarma", "sirena", "base", "caja", "kit", "tactil", "táctil", "vision", "visión"}


def riesgo(term: str) -> list[str]:
    t = term.strip(); nk = C.normkey(t); flags = []
    if len(nk) <= 3:
        flags.append("muy_corto")
    if not any(ch.isdigit() for ch in t):
        flags.append("sin_digitos")
    if nk in COMUNES or t.lower() in COMUNES:
        flags.append("palabra_comun")
    if re.fullmatch(r"[a-z]{1,5}", nk):
        flags.append("acronimo_corto")
    return flags


def vista_resolver(catalog_dir: Path, queries: list[str]) -> dict:
    """resolve_query() del resolver REAL con el catálogo de `catalog_dir` (monkeypatch de load)."""
    orig = cs.load
    try:
        cs.load = lambda *a, **k: orig(catalog_dir)          # _build() llama catalog_store.load()
        R._loaded = False; R._pattern = None; R._build()
        out = {}
        for q in queries:
            r = R.resolve_query(q)
            out[q] = {"detected": r["detected"], "ids": sorted({i for rec in r["records"] for i in rec.get("ids", [])}),
                      "add_models": sorted(set(r["add_models"])), "allowed_sources": sorted(r["allowed_sources"])}
        docs_by_id = {k: sorted(v) for k, v in R._docs_by_id.items()}
        return {"gold": out, "docs_by_id": docs_by_id}
    finally:
        cs.load = orig
        R._loaded = False; R._pattern = None


def censo(antes_dir: Path, despues_dir: Path, plan: dict) -> dict:
    antes, despues = cs.load(antes_dir), cs.load(despues_dir)
    t0, t1 = R._resolvable_terms(antes), R._resolvable_terms(despues)
    entran = {k: v for k, v in t1.items() if k not in t0}
    salen = {k: v for k, v in t0.items() if k not in t1}
    p0, p1 = patron(antes), patron(despues)
    golds = [g["question"] for g in yaml.safe_load((ROOT / "evals" / "gold_answers_v1.yaml").read_text(encoding="utf-8"))]
    perdidas, nuevas_en_gold = {}, {}
    for q in golds:
        a, b = detecta(p0, q), detecta(p1, q)
        if set(C.normkey(x) for x in a) - set(C.normkey(x) for x in b):
            perdidas[q] = {"antes": a, "despues": b}
        if set(C.normkey(x) for x in b) - set(C.normkey(x) for x in a):
            nuevas_en_gold[q] = {"antes": a, "despues": b}
    disparos_negativos = {}
    for q in NEGATIVOS:
        a, b = detecta(p0, q), detecta(p1, q)
        nuevos = [x for x in b if C.normkey(x) not in {C.normkey(y) for y in a}]
        if nuevos:
            disparos_negativos[q] = {"antes": a, "nuevos": nuevos}
    por_termino = []
    cores0 = {C._core(v) for v in t0.values() if C._core(v)}
    for nk, term in sorted(entran.items()):
        origen = "?"
        for a in plan["products_altas"]:
            if C.normkey(a["row"]["canonical_model"]) == nk:
                origen = f"alta {a['row']['id']}"
        for cf in plan["products_confirmar"]:
            if C.normkey(cf["canonical_model"]) == nk:
                origen = f"confirmar {cf['id']}"
        for u in plan["umbrellas_altas"]:
            if C.normkey(u["termino"]) == nk:
                origen = f"paraguas {u['termino']} ({len(u['ids'])} ids)"
        c = C._core(term)
        por_termino.append({"termino": term, "normkey": nk, "core": c, "origen": origen, "riesgo": riesgo(term),
                            "sombra_de_existentes": sorted(x for x in cores0 if c and x != c and (x.startswith(c) or c.startswith(x)))[:6]})
    conf_ids = {cf["id"] for cf in plan["products_confirmar"]}
    alias_activados = [{"alias": a["alias"], "id": a["id"], "tipo": a.get("tipo"), "entra_en_detector": C.normkey(a["alias"]) in entran}
                       for a in despues.aliases if a["id"] in conf_ids]
    # (2) resolver completo antes/después sobre las gold
    v0, v1 = vista_resolver(antes_dir, golds), vista_resolver(despues_dir, golds)
    resolver_perdidas, resolver_ganancias = {}, {}
    for q in golds:
        a, b = v0["gold"][q], v1["gold"][q]
        lost_src = sorted(set(a["allowed_sources"]) - set(b["allowed_sources"]))
        lost_ids = sorted(set(a["ids"]) - set(b["ids"]))
        if lost_src or lost_ids:
            resolver_perdidas[q] = {"allowed_sources_perdidas": lost_src, "ids_perdidos": lost_ids}
        gain_src = sorted(set(b["allowed_sources"]) - set(a["allowed_sources"]))
        gain_ids = sorted(set(b["ids"]) - set(a["ids"]))
        if gain_src or gain_ids:
            resolver_ganancias[q] = {"allowed_sources_nuevas": gain_src[:12], "ids_nuevos": gain_ids[:12], "detected": b["detected"]}
    # (3) efecto doc_map: fuentes que gana cada producto tocado por el plan
    ids_plan = sorted({e["id"] for row in plan["doc_map_altas"] for e in row["entries"]} |
                      {i for m in plan["doc_map_modificaciones"] for i in m["entries_nuevas"]})
    efecto_docmap = {pid: {"fuentes_antes": len(v0["docs_by_id"].get(pid, [])), "fuentes_despues": len(v1["docs_by_id"].get(pid, [])),
                           "ganadas": sorted(set(v1["docs_by_id"].get(pid, [])) - set(v0["docs_by_id"].get(pid, [])))[:8]}
                     for pid in ids_plan}
    # (4) findability de los retags: pm_nuevo casa con ≥1 entry primaria del doc_map del doc
    # Modos por fila (OPT-IN vía `findability`; sin la clave = comportamiento histórico):
    #   ausente / "modelo"        → basta que case una entry primaria del catálogo DESPUÉS.
    #   "modelo_independiente"    → si la ÚNICA entry que casa la añade este mismo plan, el gate
    #       sería autosatisfecho (dúo r38, Fable): se exige además que el pm nuevo YA resuelva en
    #       el catálogo ANTES del plan (producto/alias/paraguas preexistente).
    #   "na_unknown"              → solo válido con pm_nuevo == "unknown"; se declara, no se exige.
    dm1 = {r["document_id"]: r for r in despues.doc_map}
    ids_del_plan = {(row["document_id"], e["id"]) for row in plan["doc_map_altas"] for e in row["entries"]}
    terminos_antes = set(t0)                     # normkeys resolubles ANTES del plan
    findability = []
    for rt in plan["retags_db"]:
        modo = rt.get("findability", "modelo")
        row = dm1.get(rt["document_id"])
        pats = []
        for e in (row or {}).get("entries", []):
            if e.get("role") == "primary":
                pid = despues.follow_redirect(e["id"]) if hasattr(despues, "follow_redirect") else e["id"]
                p = despues.products.get(pid)
                if p:
                    pats.append((pid, re.compile(model_to_imatch_pattern(p["canonical_model"]).replace(r"\y", r"\b"), re.I)))
        casa = [pid for pid, rx in pats if rx.search(rt["pm_nuevo"])]
        fila = {"doc": rt["source_file"], "pm_nuevo": rt["pm_nuevo"], "modo": modo,
                "entries_primarias": [pid for pid, _ in pats], "casan": casa}
        if modo == "na_unknown":
            fila["ok"] = rt["pm_nuevo"] == "unknown"
            fila["declarado"] = ("pm 'unknown' a propósito: doc sin producto citable, no lleva doc_map "
                                 "(clase §0.E MANTENER-unknown) → la findability por modelo NO aplica")
            if not fila["ok"]:
                fila["declarado"] = f"MODO INVÁLIDO: na_unknown exige pm_nuevo 'unknown', llegó {rt['pm_nuevo']!r}"
        elif modo == "modelo_independiente":
            aportadas = [pid for pid in casa if (rt["document_id"], pid) in ids_del_plan]
            autosat = bool(casa) and len(aportadas) == len(casa)
            resuelve_antes = C.normkey(rt["pm_nuevo"]) in terminos_antes
            fila.update({"aportadas_por_este_plan": aportadas, "autosatisfecha_por_el_plan": autosat,
                         "pm_resuelve_en_catalogo_previo": resuelve_antes,
                         "ok": bool(casa) and (resuelve_antes if autosat else True)})
            if autosat:
                fila["declarado"] = ("la entry que satisface el gate la añade ESTE plan; el gate se apoya en que "
                                     "el pm nuevo ya resolvía en el catálogo previo (evidencia independiente del plan)")
        else:
            fila["ok"] = bool(casa)
        findability.append(fila)
    stop_terminos = sorted({x for v in disparos_negativos.values() for x in v["nuevos"]})
    # Términos ADJUDICADOS por Alberto explícitamente (plan.adjudicados_por_alberto_para_el_gate):
    # un disparo en un negativo SINTÉTICO (escrito por el autor) se declara como aviso, no como STOP.
    adjudicados = {C.normkey(k) for k in (plan.get("adjudicados_por_alberto_para_el_gate") or {})}
    disparos_no_adjudicados = {q: v for q, v in disparos_negativos.items()
                               if any(C.normkey(x) not in adjudicados for x in v["nuevos"])}
    # Negativos de TRÁFICO REAL (query_logs): detecciones NUEVAS del patrón — se listan (pueden ser
    # verdaderos positivos si la consulta era sobre ese producto); STOP solo si el término es palabra común.
    try:
        from scripts.s324_lib import consultas_reales
        with abierto(timeout=30.0) as c:
            reales = consultas_reales(c)
    except Exception as e:  # sin red: se declara
        reales = []
    disparos_reales = {}
    for q in reales:
        a, b = detecta(p0, q), detecta(p1, q)
        nuevos = [x for x in b if C.normkey(x) not in {C.normkey(y) for y in a}]
        if nuevos:
            disparos_reales[q[:120]] = nuevos
    # Pérdidas de FUENTE adjudicadas (plan.perdidas_de_fuente_adjudicadas): retirar una atestación
    # equivocada ES perder fuentes de gold a propósito, y sin este canal el gate bloquea toda limpieza
    # de contaminación (nace s331: la FAQ de la DXc atestaba 6 productos ZX que no nombra). Simétrico a
    # `adjudicados_por_alberto_para_el_gate` (negativos sintéticos) y con las mismas cautelas:
    #   · exige coincidencia EXACTA de (gold, source_file) — no hay comodines;
    #   · una fuente perdida que NO esté declarada sigue siendo STOP;
    #   · `ids_perdidos` NUNCA se adjudica por aquí: perder un PRODUCTO es otra clase de daño.
    adj_perdidas = {(str(a.get("gold", "")).strip(), str(a.get("source_file", "")).strip())
                    for a in (plan.get("perdidas_de_fuente_adjudicadas") or [])}
    resolver_perdidas_no_adj = {}
    for q, v in resolver_perdidas.items():
        restantes = [s for s in v["allowed_sources_perdidas"] if (q.strip(), s.strip()) not in adj_perdidas]
        if restantes or v["ids_perdidos"]:
            resolver_perdidas_no_adj[q] = {**v, "allowed_sources_perdidas": restantes}
    veredicto = "PASS" if (not perdidas and not disparos_no_adjudicados and not resolver_perdidas_no_adj
                          and all(f["ok"] for f in findability)
                          and not any("palabra_comun" in r["riesgo"] for r in por_termino)) else "STOP"
    return {"terminos_antes": len(t0), "terminos_despues": len(t1), "entran": len(entran), "salen": len(salen),
            "salen_lista": sorted(salen.values()), "por_termino": por_termino, "alias_activados": alias_activados,
            "gold_perdidas": perdidas, "gold_nuevas_detecciones": nuevas_en_gold,
            "negativos_probados": len(NEGATIVOS), "disparos_en_negativos": disparos_negativos,
            "terminos_que_disparan_negativos": stop_terminos,
            "disparos_sinteticos_adjudicados_por_alberto": {q: v for q, v in disparos_negativos.items() if q not in disparos_no_adjudicados},
            "trafico_real_consultas": len(reales), "trafico_real_detecciones_nuevas": disparos_reales,
            "avisos_muy_corto": [r["termino"] for r in por_termino if "muy_corto" in r["riesgo"]],
            "resolver_gold_perdidas": resolver_perdidas, "resolver_gold_ganancias": resolver_ganancias,
            "resolver_gold_perdidas_no_adjudicadas": resolver_perdidas_no_adj,
            "resolver_gold_perdidas_adjudicadas": {q: v for q, v in resolver_perdidas.items()
                                                   if q not in resolver_perdidas_no_adj},
            "efecto_docmap": efecto_docmap, "findability_retags": findability,
            "no_medido": "retrieval/generación end-to-end (el instrumento es el FULL v3.2, no este censo)",
            "veredicto": veredicto}


# ───────────────────────── retags (DB) ─────────────────────────
def preflight_retags(c, plan: dict) -> tuple[list[dict], list[dict]]:
    plan_rows, aborts = [], []
    for rt in plan["retags_db"]:
        r = c.get(f"{SB}/rest/v1/chunks_v2", headers=HS,
                  params={"select": "id,product_model", "document_id": f"eq.{rt['document_id']}"})
        r.raise_for_status()
        rows = r.json()
        d = c.get(f"{SB}/rest/v1/documents", headers=HS, params={"select": "product_model,status", "id": f"eq.{rt['document_id']}"})
        d.raise_for_status()
        doc = (d.json() or [{}])[0]
        objetivo = [x for x in rows if x["product_model"] == rt["pm_prev"]]
        fila = {**rt, "chunks_doc": len(rows), "chunks_pm_prev": len(objetivo), "documents_pm_actual": doc.get("product_model"),
                "documents_status": doc.get("status"), "backup": [{"id": x["id"], "product_model_prev": x["product_model"]} for x in objetivo]}
        if not objetivo or len(objetivo) != len(rows):
            aborts.append({"doc": rt["source_file"], "motivo": f"esperaba TODOS los chunks con pm_prev; {len(objetivo)}/{len(rows)}"})
        if doc.get("product_model") != rt["documents_pm_actual"]:
            aborts.append({"doc": rt["source_file"], "motivo": f"documents.product_model cambió: {doc.get('product_model')!r} != {rt['documents_pm_actual']!r}"})
        if doc.get("status") != "active":
            aborts.append({"doc": rt["source_file"], "motivo": f"documento no active ({doc.get('status')})"})
        plan_rows.append(fila)
    return plan_rows, aborts


def aplicar_retags(c, filas: list[dict]) -> dict:
    """CAS por chunk; documents SOLO si todos los chunks pasaron; revierte lo parcheado si falla."""
    out = {"aplicados": [], "revertidos": [], "aborts": []}
    for f in filas:
        parcheados = []
        for x in f["backup"]:
            rr = c.patch(f"{SB}/rest/v1/chunks_v2", headers={**HS, "Prefer": "return=representation"},
                         params={"id": f"eq.{x['id']}", "product_model": f"eq.{f['pm_prev']}"},
                         json={"product_model": f["pm_nuevo"]})
            if rr.status_code >= 300 or len(rr.json()) != 1:
                out["aborts"].append({"doc": f["source_file"], "motivo": f"CAS falló en chunk {x['id']} (HTTP {rr.status_code}, filas {len(rr.json()) if rr.status_code < 300 else '?'})"})
                break
            parcheados.append(x)
        if len(parcheados) != len(f["backup"]):
            for x in parcheados:   # revertir lo parcheado de este doc
                c.patch(f"{SB}/rest/v1/chunks_v2", headers=HS, params={"id": f"eq.{x['id']}", "product_model": f"eq.{f['pm_nuevo']}"},
                        json={"product_model": x["product_model_prev"]})
            out["revertidos"].append({"doc": f["source_file"], "chunks": len(parcheados)})
            return out
        rd = c.patch(f"{SB}/rest/v1/documents", headers={**HS, "Prefer": "return=representation"},
                     params={"id": f"eq.{f['document_id']}", "product_model": f"eq.{f['documents_pm_actual']}"},
                     json={"product_model": f["pm_nuevo"]})
        if rd.status_code >= 300 or len(rd.json()) != 1:
            out["aborts"].append({"doc": f["source_file"], "motivo": f"CAS de documents falló (HTTP {rd.status_code})"})
            for x in parcheados:
                c.patch(f"{SB}/rest/v1/chunks_v2", headers=HS, params={"id": f"eq.{x['id']}", "product_model": f"eq.{f['pm_nuevo']}"},
                        json={"product_model": x["product_model_prev"]})
            out["revertidos"].append({"doc": f["source_file"], "chunks": len(parcheados)})
            return out
        out["aplicados"].append({"doc": f["source_file"], "chunks": len(parcheados), "documents": 1})
    return out


def revertir_retags(c, aplicados_filas: list[dict]) -> list[dict]:
    rev = []
    for f in aplicados_filas:
        n = 0
        for x in f["backup"]:
            rr = c.patch(f"{SB}/rest/v1/chunks_v2", headers={**HS, "Prefer": "return=representation"},
                         params={"id": f"eq.{x['id']}", "product_model": f"eq.{f['pm_nuevo']}"}, json={"product_model": x["product_model_prev"]})
            n += len(rr.json()) if rr.status_code < 300 else 0
        c.patch(f"{SB}/rest/v1/documents", headers=HS, params={"id": f"eq.{f['document_id']}", "product_model": f"eq.{f['pm_nuevo']}"},
                json={"product_model": f["documents_pm_actual"]})
        rev.append({"doc": f["source_file"], "chunks_revertidos": n})
    return rev


# ───────────────────────── main ─────────────────────────
def main() -> int:
    global PLAN, CENSO
    ap = argparse.ArgumentParser(); ap.add_argument("--aplicar", action="store_true")
    ap.add_argument("--plan", default=str(PLAN), help="plan JSON (por defecto el lote firmado de s324)")
    ap.add_argument("--censo", default=None, help="fichero del censo/dry-run (por defecto evals/<plan>_radio_explosion.json si --plan≠default)")
    args = ap.parse_args(); modo = "aplicar" if args.aplicar else "dry-run"
    PLAN = Path(args.plan) if Path(args.plan).is_absolute() else ROOT / args.plan
    if args.censo:
        CENSO = Path(args.censo) if Path(args.censo).is_absolute() else ROOT / args.censo
    elif PLAN != ROOT / "evals" / "s324_lote_firmado_plan_v1.json":
        CENSO = PLAN.with_name(PLAN.stem.replace("_plan", "") + "_radio_explosion.json")
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    plan_sha = sha_file(PLAN)
    utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    if not args.aplicar:
        with abierto(timeout=60.0) as c:
            frz = freeze(c, plan, CATALOG_DIR)
            pre, aborts = preflight_retags(c, plan)
        tmp = Path(tempfile.mkdtemp(prefix="s324_catalog_"))
        try:
            stats = aplicar_plan(plan, tmp, CATALOG_DIR)
            cz = censo(CATALOG_DIR, tmp, plan)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        veredicto = cz["veredicto"] if not aborts else "STOP"
        recibo = {"que_es": "s324 dry-run del lote firmado + censo del radio de explosión + freeze", "modo": modo, "utc": utc,
                  "plan_sha": plan_sha, "freeze": frz, "stats": stats, "censo": cz,
                  "retags_preflight": [{k: v for k, v in f.items() if k != "backup"} for f in pre], "retags_aborts": aborts,
                  "veredicto": veredicto}
        CENSO.write_text(json.dumps(recibo, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"dry-run · validador PASS en copia · {stats}")
        print(f"detector {cz['terminos_antes']}→{cz['terminos_despues']} (+{cz['entran']}/−{cz['salen']}) · gold perdidas {len(cz['gold_perdidas'])} · negativos sintéticos {len(cz['disparos_en_negativos'])} (adjudicados {len(cz['disparos_sinteticos_adjudicados_por_alberto'])}) · tráfico real {cz['trafico_real_consultas']} consultas / {len(cz['trafico_real_detecciones_nuevas'])} detecciones nuevas · resolver: gold que pierden {len(cz['resolver_gold_perdidas_no_adjudicadas'])} (+{len(cz['resolver_gold_perdidas_adjudicadas'])} adjudicadas), ganan {len(cz['resolver_gold_ganancias'])} · findability retags {[f['ok'] for f in cz['findability_retags']]} · VEREDICTO {veredicto}")
        for q, v in list(cz["trafico_real_detecciones_nuevas"].items())[:8]:
            print("   tráfico real detecta ahora:", q[:70], "→", v)
        for q, v in list(cz["resolver_gold_ganancias"].items())[:6]:
            print("   gold gana:", q[:60], "→ ids", v["ids_nuevos"][:4], "fuentes +", len(v["allowed_sources_nuevas"]))
        for q, v in cz["resolver_gold_perdidas_no_adjudicadas"].items():
            print("   GOLD PIERDE (resolver):", q[:70], v)
        for q, v in cz["disparos_en_negativos"].items():
            print("   NEG DISPARA:", q, v)
        print("retags preflight:", [(f["source_file"][:40], f["chunks_pm_prev"], "/", f["chunks_doc"]) for f in pre], "aborts:", aborts)
        print("censo:", CENSO.relative_to(ROOT))
        return 0 if veredicto == "PASS" else 1

    # ── aplicar ──
    prev = json.loads(CENSO.read_text(encoding="utf-8")) if CENSO.exists() else None
    if not prev or prev.get("plan_sha") != plan_sha or prev.get("veredicto") != "PASS":
        print("ABORT: falta un dry-run PASS del MISMO plan (sha)"); return 2
    with abierto(timeout=60.0) as c:
        frz = freeze(c, plan, CATALOG_DIR)
        if frz != prev["freeze"]:
            print("ABORT: el estado cambió desde el dry-run (freeze distinto):", json.dumps({"dry": prev["freeze"], "ahora": frz}, ensure_ascii=False)[:600]); return 3
        pre, aborts = preflight_retags(c, plan)
        if aborts:
            print("ABORT preflight retags:", aborts); return 4
        tmp = Path(tempfile.mkdtemp(prefix="s324_catalog_"))
        backup_dir = ROOT / "evals" / f"{PLAN.stem.replace('_plan_v1','').replace('_plan','')}_backup_{utc}"
        try:
            stats = aplicar_plan(plan, tmp, CATALOG_DIR)          # construye y VALIDA en tmp
            backup_dir.mkdir(parents=True, exist_ok=True)
            for n in FILES:                                       # backup COMPLETO (también homonyms/relations/docrel:
                if (CATALOG_DIR / FILES[n]).exists():             # el censo post carga el backup como catálogo entero)
                    shutil.copy(CATALOG_DIR / FILES[n], backup_dir / FILES[n])
            for n in JSONL:                                       # swap (tras validar)
                shutil.copy(tmp / FILES[n], CATALOG_DIR / FILES[n])
        except Exception as e:
            print("ABORT construyendo/escribiendo el catálogo:", e)
            if backup_dir.exists():
                for n in JSONL:
                    if (backup_dir / FILES[n]).exists():
                        shutil.copy(backup_dir / FILES[n], CATALOG_DIR / FILES[n])
            shutil.rmtree(tmp, ignore_errors=True); return 5
        shutil.rmtree(tmp, ignore_errors=True)
        rt = aplicar_retags(c, pre)
        estado = "APLICADO"
        if rt["aborts"]:
            # rollback total: chunks ya aplicados de otros docs + catálogo del backup
            hechos = [f for f in pre if any(a["doc"] == f["source_file"] for a in rt["aplicados"])]
            rt["revertidos"] += revertir_retags(c, hechos)
            for n in JSONL:
                shutil.copy(backup_dir / FILES[n], CATALOG_DIR / FILES[n])
            estado = "ROLLED_BACK"
        cz = censo(backup_dir, CATALOG_DIR, plan) if estado == "APLICADO" else None
    recibo = {"que_es": "s324 APLICACIÓN del lote firmado (catálogo por la puerta + retags DB con CAS)", "modo": modo,
              "estado": estado, "utc": utc, "plan_sha": plan_sha, "freeze_verificado": frz, "stats": stats,
              "censo_post": cz, "retags": {**rt, "filas": [{k: v for k, v in f.items() if k != "backup"} for f in pre],
                                            "backup_chunks": [{"doc": f["source_file"], "document_id": f["document_id"], "documents_pm_prev": f["documents_pm_actual"], "chunks": f["backup"]} for f in pre]},
              "backup_dir": str(backup_dir.relative_to(ROOT)),
              "reversion": "restaurar los 4 .jsonl de backup_dir; chunks: PATCH product_model=product_model_prev por id (retags.backup_chunks); documents.product_model=documents_pm_prev"}
    out = ROOT / "evals" / f"{PLAN.stem.replace('_plan_v1','').replace('_plan','')}_aplicar_{utc}.json"
    out.write_text(json.dumps(recibo, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{estado} · {stats} · retags {[(x['doc'][:40], x['chunks']) for x in rt['aplicados']]} aborts {rt['aborts']} · censo post {cz and cz['veredicto']}")
    print("recibo:", out.relative_to(ROOT))
    return 0 if estado == "APLICADO" and cz and cz["veredicto"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
