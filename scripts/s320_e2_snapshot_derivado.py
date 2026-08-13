# -*- coding: utf-8 -*-
"""s320 E2 — Generador v2 del snapshot del detector: DERIVADO del catálogo
gobernado (DEC-213; sustituye a build_model_catalog.py cuando E2 se adjudique).

FUENTE (dúo r23): `_resolvable_terms(cat)` — la puerta YA adjudicada del
resolver (canonical activos no-candidate + alias model-shaped + paraguas +
homónimos, stopwords/guardas de replays s92) — NUNCA una re-implementación.

ATESTACIÓN (Sol M2 — «entrada doc_map ≠ corpus servible»): un término entra si
alguno de sus productos (via cat.resolve) tiene entrada doc_map cuyo
document_id está ACTIVO con chunks servibles, o si su normkey está atestado en
el pm de chunks de docs ACTIVOS. Las 49 COLISIONES de E1 (id viejo vivo)
quedan EXCLUIDAS de la atestación hasta adjudicación.

CINTURÓN legacy conservado: fechas/normas EN/acrónimos cortos; y la unión con
MODEL_PATTERN (cero regresión sobre lo que el estático ya detecta).

chunk_count derivado = chunks por pm-normkey (misma fuente que hoy — el ORDEN
de all_models importa: Whisper trunca; Sol M3). manufacturer = dominante en
chunks del término; fallback: dominante en documents de sus docs atestados.

NO escribe data/model_catalog.json: emite a evals/s320_e2_snapshot_candidato.json
+ recibo de DIFF (viejo↔derivado por normkey: sin-cambio/forma/altas/bajas con
causa). El swap del fichero vivo va tras los gates y la PR.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=False)

import os  # noqa: E402

from src.http_pool import abierto  # noqa: E402
from src.rag import catalog as C  # noqa: E402
from src.rag import catalog_store  # noqa: E402
from src.rag.catalog_resolver import _resolvable_terms  # noqa: E402
from src.rag.retriever import MODEL_PATTERN  # noqa: E402

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
KEY = os.environ["SUPABASE_SERVICE_KEY"]
H = {"apikey": KEY, "Authorization": f"Bearer {KEY}"}

_MESES = {"ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO", "JULIO",
          "AGOSTO", "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE", "ENE",
          "FEB", "MAR", "ABR", "JUN", "JUL", "AGO", "SEP", "SEPT", "OCT",
          "NOV", "DIC", "JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY",
          "JUNE", "JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER",
          "DECEMBER", "JAN", "APR", "AUG", "DEC"}


def _es_fecha(pm: str) -> bool:
    return re.split(r"[- /]", pm.upper(), maxsplit=1)[0] in _MESES


def _es_norma(pm: str) -> bool:
    return re.match(r"^EN[- ]?\d", pm.upper()) is not None


def _es_acronimo_riesgo(pm: str) -> bool:
    return (" " not in pm and "-" not in pm and "/" not in pm
            and not any(c.isdigit() for c in pm) and len(pm) <= 4)


def _paginado(client, tabla: str, params: dict) -> list[dict]:
    filas, off = [], 0
    while True:
        r = client.get(f"{SUPABASE_URL}/rest/v1/{tabla}", headers=H,
                       params={**params, "offset": str(off), "limit": "1000"})
        r.raise_for_status()
        lote = r.json()
        filas.extend(lote)
        if len(lote) < 1000:
            return filas
        off += 1000


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--conservador", action="store_true",
                    help="candidato v1 SHIP: vocabulario vivo preservado (salvo "
                         "bajas con causa de atestación); las altas del gobernado "
                         "NO entran — van al packet como backlog adjudicable. "
                         "Sin el flag: derivado PLENO (el target E2, informativo)")
    args = ap.parse_args()
    cat = catalog_store.load()
    terms = _resolvable_terms(cat)          # normkey -> término almacenado

    with abierto(timeout=30.0) as client:
        docs = _paginado(client, "documents", {
            "select": "id,source_pdf_filename,manufacturer",
            "status": "eq.active", "order": "id.asc"})
        chunks = _paginado(client, "chunks_v2", {
            "select": "product_model,source_file,manufacturer",
            "order": "id.asc"})

    # 49 colisiones de E1: el id viejo VIVO queda fuera de la atestación
    recon = json.loads((ROOT / "evals" / "s320_e1_reconciliacion_censo_v1.json")
                       .read_text(encoding="utf-8"))
    colision_ids = {c["id_viejo"] for tier in ("a", "b", "c")
                    for c in recon.get("colision", {}).get(tier, [])
                    if c.get("id_viejo")}

    activos = {d["id"] for d in docs} - colision_ids
    sf_norm = {d["id"]: re.sub(r"\.pdf$", "",
                               (d.get("source_pdf_filename") or "")
                               .strip().lower()) for d in docs}
    sf_activos = {sf_norm[i] for i in activos if i in sf_norm}
    chunks_por_sf = defaultdict(int)
    pm_counter: Counter = Counter()
    pm_manufacturers: dict[str, Counter] = defaultdict(Counter)
    for ch in chunks:
        sf = (ch.get("source_file") or "").strip().lower()
        chunks_por_sf[sf] += 1
        if sf in sf_activos:
            nk = C.normkey(ch.get("product_model") or "")
            if nk:
                pm_counter[nk] += 1
                if ch.get("manufacturer"):
                    pm_manufacturers[nk][ch["manufacturer"]] += 1

    # productos atestados vía doc_map (documento ACTIVO no-colisión con chunks)
    productos_atestados: set[str] = set()
    docs_por_producto: dict[str, Counter] = defaultdict(Counter)
    mfr_por_doc = {d["id"]: d.get("manufacturer") or "" for d in docs}
    for dm in cat.doc_map:
        did = dm.get("document_id")
        if did not in activos:
            continue
        if chunks_por_sf.get((dm.get("source_file") or "").strip().lower(), 0) == 0:
            continue
        for e in dm.get("entries", []):
            productos_atestados.add(e.get("id"))
            if mfr_por_doc.get(did):
                docs_por_producto[e.get("id")][mfr_por_doc[did]] += 1

    modelos, excluidos = [], []
    for nk, termino in sorted(terms.items()):
        res = cat.resolve(termino)
        ids = (res or {}).get("ids", []) or []
        via = (res or {}).get("via")
        atestado_docmap = any(i in productos_atestados for i in ids)
        atestado_pm = nk in pm_counter
        estatico = bool(MODEL_PATTERN.search(termino))
        if not (atestado_docmap or atestado_pm):
            excluidos.append({"model": termino, "motivo": "sin-atestacion-activa"})
            continue
        if not estatico and (_es_fecha(termino) or _es_norma(termino)
                             or _es_acronimo_riesgo(termino)):
            excluidos.append({"model": termino, "motivo": "cinturon-anti-ruido"})
            continue
        mfr = ""
        if pm_manufacturers.get(nk):
            mfr = pm_manufacturers[nk].most_common(1)[0][0]
        else:
            for i in ids:
                if docs_por_producto.get(i):
                    mfr = docs_por_producto[i].most_common(1)[0][0]
                    break
        modelos.append({"model": termino, "manufacturer": mfr or "unknown",
                        "chunk_count": pm_counter.get(nk, 0),
                        "source": ("static-pattern" if estatico
                                   else "catalogo-gobernado"),
                        "via": via})
    modelos.sort(key=lambda m: (-m["chunk_count"], m["model"]))

    if args.conservador:
        # v1 SHIP (dúo r23 + diff pleno 1.235/301: el pleno NO es equivalencia):
        # el vocabulario VIVO se preserva salvo pérdida de atestación REAL; las
        # altas del gobernado quedan como backlog adjudicable (packet).
        vivo_now = json.loads((ROOT / "data" / "model_catalog.json")
                              .read_text(encoding="utf-8"))
        derivado_por_nk = {C.normkey(m["model"]): m for m in modelos}
        conservados, bajas_reales, gaps_catalogo = [], [], []
        for m in vivo_now.get("models", []):
            nk = C.normkey(m["model"])
            if nk in derivado_por_nk:
                # PARIDAD TOTAL v1 (gate G2: refrescar chunk_count re-ordena
                # all_models y Whisper trunca — el orden es conducta): no se
                # actualiza NADA; el refresh de counts/mfr viaja con la
                # adjudicación del backlog, no con el swap del mecanismo.
                conservados.append(dict(m))
            elif nk in pm_counter:
                # GAP del catálogo (atestado en corpus, fuera del gobernado):
                # se conserva IDÉNTICO; el marcador vive en el recibo/packet
                conservados.append(dict(m))
                gaps_catalogo.append(m["model"])
            else:
                # v3 (gate G1 con candidato v2: VESDA-E-VEP era baja "real" y
                # una query GOLD lo necesita — el pm re-tagueado rompe la
                # atestación exacta): NINGUNA baja automática. Se CONSERVA
                # idéntico; la adjudicación viaja en el packet.
                conservados.append(dict(m))
                bajas_reales.append({"model": m["model"],
                                     "motivo": "sin-atestacion-activa → "
                                               "ADJUDICAR (conservado)"})
        # SIN re-sort (gate G1 v1: el re-orden cambiaba qué FORMA duplicada
        # ganaba el match del detector — ID3000 vs ID-3000. El orden del vivo
        # ES conducta; solo se actualizan counts/manufacturer in-place).
        modelos = conservados
        excluidos = bajas_reales

    utc = datetime.now(timezone.utc).isoformat()
    candidato = {
        "build": {"table": os.getenv("CHUNKS_TABLE", "chunks_v2"),
                  "generated_at": utc,
                  "fuente": "catalogo-gobernado (data/catalog) via "
                            "_resolvable_terms + atestacion-activa (E2 DEC-213)",
                  "colisiones_excluidas": len(colision_ids),
                  "n_distinct": len(terms),
                  "n_included": len(modelos), "n_excluded": len(excluidos)},
        "models": modelos, "excluded": excluidos,
    }
    sufijo = "_conservador" if args.conservador else ""
    destino = ROOT / "evals" / f"s320_e2_snapshot_candidato{sufijo}.json"
    destino.write_text(json.dumps(candidato, ensure_ascii=False, indent=1),
                       encoding="utf-8")

    # DIFF por normkey contra el snapshot vivo
    vivo = json.loads((ROOT / "data" / "model_catalog.json")
                      .read_text(encoding="utf-8"))
    vivos = {C.normkey(m["model"]): m for m in vivo.get("models", [])}
    nuevos = {C.normkey(m["model"]): m for m in modelos}
    altas = sorted(set(nuevos) - set(vivos))
    bajas = sorted(set(vivos) - set(nuevos))
    comunes = set(vivos) & set(nuevos)
    cambio_forma = sorted(k for k in comunes
                          if vivos[k]["model"] != nuevos[k]["model"])
    diff = {
        "que_es": ("Diff viejo↔derivado por normkey (E2). Las bajas con causa; "
                   "las altas vienen del gobernado atestado."),
        "vivo_n": len(vivos), "derivado_n": len(nuevos),
        "sin_cambio": len(comunes) - len(cambio_forma),
        "cambio_forma": [{"vivo": vivos[k]["model"], "derivado": nuevos[k]["model"]}
                         for k in cambio_forma],
        "altas": [{"model": nuevos[k]["model"], "via": nuevos[k].get("via"),
                   "chunk_count": nuevos[k]["chunk_count"]} for k in altas],
        "bajas": [{"model": vivos[k]["model"],
                   "chunk_count": vivos[k].get("chunk_count"),
                   "causa": next((e["motivo"] for e in excluidos
                                  if C.normkey(e["model"]) == k),
                                 "no-en-terminos-gobernados")}
                  for k in bajas],
    }
    destino_diff = ROOT / "evals" / f"s320_e2_snapshot_diff{sufijo}_v1.json"
    destino_diff.write_text(json.dumps(diff, ensure_ascii=False, indent=1),
                            encoding="utf-8")
    print(f"terminos {len(terms)} · incluidos {len(modelos)} · "
          f"excluidos {len(excluidos)} · vivo {len(vivos)} · "
          f"altas {len(altas)} · bajas {len(bajas)} · forma {len(cambio_forma)}")
    print(f"candidato -> {destino}")
    print(f"diff -> {destino_diff}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
