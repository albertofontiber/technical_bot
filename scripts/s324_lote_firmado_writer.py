# -*- coding: utf-8 -*-
"""s324 — WRITER del lote firmado + CENSO del radio de explosión (mecánica T3).

Consume `evals/s324_lote_firmado_plan_v1.json` (generado por s324_lote_firmado_plan.py, cada
fila verificada full-text) y:

  dry-run (por defecto): aplica el plan sobre una COPIA del catálogo en un directorio temporal
      (misma puerta `catalog_store.write_jsonl` → el validador corre sobre el conjunto entero) y
      mide el RADIO DE EXPLOSIÓN: términos que entran/salen del detector del resolver
      (`catalog_resolver._resolvable_terms`), banderas de riesgo léxico por término, y un gate
      de disparo: el patrón NUEVO no debe detectar nada en el conjunto de NEGATIVOS (frases
      genéricas de técnico) ni perder detecciones en las 51 preguntas gold. NO toca
      data/catalog ni Supabase.
  --aplicar: exige que el dry-run del MISMO plan haya pasado el gate (fichero de censo con
      veredicto PASS y el mismo sha del plan); backup de los 4 .jsonl; escritura por la puerta;
      retags en Supabase (documents.product_model + chunks_v2.product_model con CAS por chunk);
      censo posterior sobre el catálogo real; recibo. Reversible con el backup + recibo.

Uso:  python scripts/s324_lote_firmado_writer.py [--aplicar]
"""
from __future__ import annotations
import argparse, copy, hashlib, json, os, re, shutil, sys, tempfile
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

PLAN = ROOT / "evals" / "s324_lote_firmado_plan_v1.json"
CENSO = ROOT / "evals" / "s324_radio_explosion_v1.json"
SB = os.environ.get("SUPABASE_URL", "").rstrip("/")
HS = {"apikey": os.environ.get("SUPABASE_SERVICE_KEY", ""),
      "Authorization": f"Bearer {os.environ.get('SUPABASE_SERVICE_KEY', '')}"}

# Frases de técnico SIN ninguno de los productos del lote: el patrón nuevo NO debe disparar aquí.
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


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def aplicar_plan(plan: dict, destino: Path, origen: Path) -> dict:
    """Aplica el plan sobre los .jsonl de `origen` escribiendo en `destino` (misma puerta)."""
    prods = _read_jsonl(origen / FILES["products"])
    aliases = _read_jsonl(origen / FILES["aliases"])
    umbrellas = _read_jsonl(origen / FILES["umbrellas"])
    doc_map = _read_jsonl(origen / FILES["doc_map"])
    for name in ("homonyms", "relations", "docrel"):
        if (origen / FILES[name]).exists() and origen != destino:
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
            stats["confirmadas"] += 1
    for rt in plan["products_retirar"]:
        p = by_id[rt["id"]]
        if p["estado"] == "activo":
            p["estado"] = "retirado"
            p["provenance"] = (p.get("provenance") or "") + f" | s324 retirado: {rt['motivo']}"
            stats["retiradas"] += 1
    quitar = {(a["alias"], a["id"]) for a in plan["aliases_quitar"]}
    n0 = len(aliases)
    aliases = [a for a in aliases if (a.get("alias"), a.get("id")) not in quitar]
    stats["aliases_quitados"] = n0 - len(aliases)
    terms = {norm_token(u["termino"]) for u in umbrellas}
    for u in plan["umbrellas_altas"]:
        if norm_token(u["termino"]) in terms or u.get("diferido"):
            continue
        fila = {k: v for k, v in u.items() if k != "diferido"}
        umbrellas.append(fila); terms.add(norm_token(u["termino"])); stats["umbrellas"] += 1
    dm_by_id = {r["document_id"]: r for r in doc_map}
    for m in plan["doc_map_modificaciones"]:
        r = dm_by_id.get(m["document_id"])
        if not r:
            continue
        prev = {e["id"]: e for e in r["entries"]}
        nuevas = []
        for pid in m["entries_nuevas"]:
            e = prev.get(pid) or {"id": pid, "role": "primary", "scope": "doc",
                                  "provenance": f"s324 {m['regla']}: {m['detalle']}"}
            nuevas.append(e)
        r["entries"] = nuevas; stats["doc_map_modificadas"] += 1
    for alta in plan["doc_map_altas"]:
        if alta["document_id"] in dm_by_id:
            r = dm_by_id[alta["document_id"]]
            vistos = {e["id"] for e in r["entries"]}
            r["entries"] += [e for e in alta["entries"] if e["id"] not in vistos]
        else:
            row = {"document_id": alta["document_id"], "source_file": alta["source_file"], "entries": alta["entries"]}
            doc_map.append(row); dm_by_id[row["document_id"]] = row
        stats["doc_map_altas"] += 1
    # orden de dependencia; validación al final (write_jsonl valida el conjunto)
    write_jsonl("products", prods, catalog_dir=destino, validate_after=False)
    write_jsonl("aliases", aliases, catalog_dir=destino, validate_after=False)
    write_jsonl("umbrellas", umbrellas, catalog_dir=destino, validate_after=False)
    write_jsonl("doc_map", doc_map, catalog_dir=destino, validate_after=True)
    return stats


def patron(cat) -> "re.Pattern | None":
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


def censo(antes, despues, plan: dict) -> dict:
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
    for nk, term in sorted(entran.items()):
        # ¿de dónde viene el término? (alta / confirmación / paraguas / alias)
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
        por_termino.append({"termino": term, "normkey": nk, "core": C._core(term), "origen": origen, "riesgo": riesgo(term)})
    # colisiones: el core nuevo ¿es prefijo/sufijo de un core existente o viceversa? (sombra)
    cores0 = {C._core(v) for v in t0.values() if C._core(v)}
    for row in por_termino:
        c = row["core"]
        row["sombra_de_existentes"] = sorted(x for x in cores0 if c and x != c and (x.startswith(c) or c.startswith(x)))[:6]
    # alias que se ACTIVAN al confirmar (r30: confirmar enciende los alias existentes del producto)
    conf_ids = {cf["id"] for cf in plan["products_confirmar"]}
    alias_activados = [{"alias": a["alias"], "id": a["id"], "tipo": a.get("tipo"),
                        "entra_en_detector": C.normkey(a["alias"]) in entran}
                       for a in despues.aliases if a["id"] in conf_ids]
    # Regla del veredicto (mecánica): STOP si se pierde una detección gold, si un término nuevo
    # DISPARA en un negativo, o si es palabra común. `muy_corto`/`sin_digitos` = AVISO (hoy ya hay
    # 43 términos con normkey ≤3 en el detector: DX1, DX4, DXc, E10…): un término corto solo para si dispara.
    stop_terminos = sorted({x for v in disparos_negativos.values() for x in v["nuevos"]})
    veredicto = "PASS" if not perdidas and not disparos_negativos and not any(
        "palabra_comun" in r["riesgo"] for r in por_termino) else "STOP"
    return {"terminos_antes": len(t0), "terminos_despues": len(t1), "entran": len(entran), "salen": len(salen),
            "salen_lista": sorted(salen.values()), "por_termino": por_termino, "alias_activados": alias_activados,
            "gold_perdidas": perdidas, "gold_nuevas_detecciones": nuevas_en_gold,
            "negativos_probados": len(NEGATIVOS), "disparos_en_negativos": disparos_negativos,
            "terminos_que_disparan_negativos": stop_terminos,
            "avisos_muy_corto": [r["termino"] for r in por_termino if "muy_corto" in r["riesgo"]],
            "veredicto": veredicto}


def retags(c, plan: dict, aplicar: bool) -> dict:
    """documents.product_model + chunks_v2.product_model (CAS por chunk); backup por chunk."""
    out = {"planeados": [], "aplicados": [], "backup": [], "aborts": []}
    for rt in plan["retags_db"]:
        r = c.get(f"{SB}/rest/v1/chunks_v2", headers=HS,
                  params={"select": "id,product_model", "document_id": f"eq.{rt['document_id']}"})
        r.raise_for_status()
        rows = r.json()
        objetivo = [x for x in rows if x["product_model"] == rt["pm_prev"]]
        out["planeados"].append({**rt, "chunks_doc": len(rows), "chunks_pm_prev": len(objetivo)})
        if not objetivo or len(objetivo) != len(rows):
            out["aborts"].append({"doc": rt["source_file"], "motivo": f"esperaba TODOS los chunks con pm_prev; {len(objetivo)}/{len(rows)}"})
            continue
        out["backup"] += [{"id": x["id"], "document_id": rt["document_id"], "product_model_prev": x["product_model"]} for x in objetivo]
        if not aplicar:
            continue
        n = 0
        for x in objetivo:
            rr = c.patch(f"{SB}/rest/v1/chunks_v2", headers={**HS, "Prefer": "return=representation"},
                         params={"id": f"eq.{x['id']}", "product_model": f"eq.{rt['pm_prev']}"},
                         json={"product_model": rt["pm_nuevo"]})
            rr.raise_for_status(); n += len(rr.json())
        rd = c.patch(f"{SB}/rest/v1/documents", headers={**HS, "Prefer": "return=representation"},
                     params={"id": f"eq.{rt['document_id']}"}, json={"product_model": rt["pm_nuevo"]})
        rd.raise_for_status()
        out["aplicados"].append({"doc": rt["source_file"], "chunks": n, "documents": len(rd.json()), "esperado": len(objetivo)})
        if n != len(objetivo):
            out["aborts"].append({"doc": rt["source_file"], "motivo": f"CAS afectó {n} != {len(objetivo)}"})
    return out


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--aplicar", action="store_true")
    args = ap.parse_args(); modo = "aplicar" if args.aplicar else "dry-run"
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    plan_sha = sha(PLAN)
    utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    antes = cs.load(CATALOG_DIR)

    if not args.aplicar:
        tmp = Path(tempfile.mkdtemp(prefix="s324_catalog_"))
        stats = aplicar_plan(plan, tmp, CATALOG_DIR)
        despues = cs.load(tmp)
        cz = censo(antes, despues, plan)
        with abierto(timeout=60.0) as c:
            rt = retags(c, plan, aplicar=False)
        recibo = {"que_es": "s324 dry-run del lote firmado + censo del radio de explosión", "modo": modo, "utc": utc,
                  "plan_sha": plan_sha, "stats": stats, "censo": cz, "retags": rt, "tmp": str(tmp)}
        CENSO.write_text(json.dumps(recibo, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"dry-run OK (validador PASS en copia) · {stats}")
        print(f"detector: {cz['terminos_antes']} → {cz['terminos_despues']} (+{cz['entran']}/−{cz['salen']}) · gold perdidas {len(cz['gold_perdidas'])} · disparos en negativos {len(cz['disparos_en_negativos'])} · VEREDICTO {cz['veredicto']}")
        for t in cz["por_termino"]:
            print(f"   + {t['termino']!r:28} core={t['core']!r:22} {t['origen'][:40]:42} riesgo={t['riesgo']} sombra={t['sombra_de_existentes'][:3]}")
        for q, v in cz["disparos_en_negativos"].items():
            print("   NEG DISPARA:", q, v)
        for q, v in cz["gold_perdidas"].items():
            print("   GOLD PIERDE:", q, v)
        print("retags planeados:", [(x["source_file"], x["chunks_pm_prev"], "/", x["chunks_doc"]) for x in rt["planeados"]], "aborts:", rt["aborts"])
        print("censo:", CENSO.relative_to(ROOT))
        shutil.rmtree(tmp, ignore_errors=True)
        return 0 if cz["veredicto"] == "PASS" and not rt["aborts"] else 1

    # ── aplicar ──
    prev = json.loads(CENSO.read_text(encoding="utf-8")) if CENSO.exists() else None
    if not prev or prev.get("plan_sha") != plan_sha or prev["censo"]["veredicto"] != "PASS":
        print("ABORT: falta un dry-run PASS del MISMO plan (sha)"); return 2
    backup_dir = ROOT / "evals" / f"s324_lote_backup_{utc}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    for name in ("products", "aliases", "umbrellas", "doc_map"):
        shutil.copy(CATALOG_DIR / FILES[name], backup_dir / FILES[name])
    stats = aplicar_plan(plan, CATALOG_DIR, CATALOG_DIR)
    despues = cs.load(CATALOG_DIR)
    cz = censo(antes, despues, plan)
    with abierto(timeout=60.0) as c:
        rt = retags(c, plan, aplicar=True)
    recibo = {"que_es": "s324 APLICACIÓN del lote firmado (catálogo por la puerta + retags DB con CAS)", "modo": modo,
              "utc": utc, "plan_sha": plan_sha, "stats": stats, "censo_post": cz, "retags": rt,
              "backup_dir": str(backup_dir.relative_to(ROOT)),
              "reversion": "restaurar los 4 .jsonl del backup_dir; chunks: PATCH product_model=product_model_prev por id (retags.backup); documents.product_model: ver retags.planeados.documents_pm_actual"}
    out = ROOT / "evals" / f"s324_lote_firmado_aplicar_{utc}.json"
    out.write_text(json.dumps(recibo, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"APLICADO · {stats} · censo post {cz['veredicto']} · retags {[(x['doc'], x['chunks']) for x in rt['aplicados']]} aborts {rt['aborts']}")
    print("recibo:", out.relative_to(ROOT))
    return 0 if cz["veredicto"] == "PASS" and not rt["aborts"] else 1


if __name__ == "__main__":
    sys.exit(main())
