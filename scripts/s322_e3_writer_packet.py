# -*- coding: utf-8 -*-
"""s322d — Aplicador de los SÍES de Alberto al packet E3 v2 (14-ago):
«sí al §0 y al §0-bis» + §1 adjudicado en su mensaje (ART 535 multi, MPS-24AE,
FD2705 multi con extensión al addendum que él mismo citó). ZXrA queda FUERA
(pendiente su decisión retag-vs-borrar tras mi verificación).

Mecánica T3 EXACTA del writer E3 (r24/r25): re-verificación fresca por doc +
BACKUP por-chunk antes de tocar + PATCH por-chunk con CAS (id + pm_prev) y
conteo == esperado o ABORT + gate findability POST (el pm nuevo debe matchear
el patrón imatch de ≥1 entry primaria del doc_map del doc). Los veredictos
MANTENER_PREV son no-op y van a recibo. Dry-run por defecto.

Uso:
    python scripts/s322_e3_writer_packet.py             # dry-run
    python scripts/s322_e3_writer_packet.py --aplicar
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=False)

import os  # noqa: E402

from src.http_pool import abierto  # noqa: E402
from src.rag.catalog_store import CATALOG_DIR, _read_jsonl  # noqa: E402
from src.rag.retriever import model_to_imatch_pattern  # noqa: E402

SB = os.environ["SUPABASE_URL"].rstrip("/")
HS = {"apikey": os.environ["SUPABASE_SERVICE_KEY"],
      "Authorization": f"Bearer {os.environ['SUPABASE_SERVICE_KEY']}",
      "Content-Type": "application/json"}

# §1 adjudicado UNA A UNA por Alberto (mensaje 14-ago) — clave (doc, pm_prev):
OVERRIDES = {
    ("TD 003 006c_Technische Dokumentation_Externer Temperatu", "ART 535-x"):
        "ART 535-10/ART 535-30",
    ("50478 RevA - MPS-24AE _Eng", "ECN-96-200"): "MPS-24AE",
    ("22318.18.08_-_aritech_ra_-_fd2705-10r_english_std_refle", "FD2705R"):
        "FD2705R/FD2710R",
}
# extensión adjudicada: Alberto citó el ADDENDUM explícitamente («según se
# puede deducir en el archivo 0044-055-02…») — sus chunks FD2705R → multi.
EXTRA = [{"source_file": "0044-055-02_-_aritech_ra_-_fd2705-10r_addendum_-_en_de",
          "pm_prev": "FD2705R", "pm_nuevo": "FD2705R/FD2710R",
          "nota": "addendum citado por Alberto; cubre ambos modelos"}]
EXCLUIDAS = {("Puesta-en-marcha-repetidor-ZXrA-en-central-CONNEXION", "ZXrA")}


def _patron(canonico: str) -> re.Pattern:
    return re.compile(model_to_imatch_pattern(canonico).replace(r"\y", r"\b"),
                      re.IGNORECASE)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--aplicar", action="store_true")
    args = ap.parse_args()
    modo = "aplicar" if args.aplicar else "dry-run"

    atest = json.loads((ROOT / "evals" / "s321_e3_atestacion_v1.json")
                       .read_text(encoding="utf-8"))
    llm = json.loads((ROOT / "evals" / "s321_e3_llm_recomendaciones_v2.json")
                     .read_text(encoding="utf-8"))
    por_clave = {(f["document_id"], f["pm_prev"]): f for f in llm["detalle"]}

    # canónicos por doc (para el gate findability) desde el doc_map gobernado
    products = {r["id"]: r for r in _read_jsonl(CATALOG_DIR / "products.jsonl")}

    def _resuelto(pid: str) -> dict | None:
        # sigue la cadena de redirects (caso VSN4-PLUS: la entry primaria es
        # notifier:vsn4-plus estado=redirect → morley:vsn-4-plus «VSN 4 PLUS»)
        visto: set[str] = set()
        p = products.get(pid)
        while p and p.get("estado") == "redirect" and p.get("redirect_to"):
            if p["id"] in visto:
                return None
            visto.add(p["id"])
            p = products.get(p["redirect_to"])
        return p

    patrones_doc: dict[str, list[re.Pattern]] = {}
    for dm in _read_jsonl(CATALOG_DIR / "doc_map.jsonl"):
        pats = []
        for e in dm.get("entries") or ():
            if e.get("role") != "primary":
                continue
            for p in (products.get(e["id"]), _resuelto(e["id"])):
                if p and p.get("canonical_model"):
                    pats.append(_patron(p["canonical_model"]))
        if pats:
            patrones_doc[dm["source_file"]] = pats

    # plan: filas §0 + §0-bis (criterio del packet v2) + overrides §1 + EXTRA
    plan, mantener = [], []
    for clase in ("pm_prev_producto_real", "ambigua_hermanas", "no_dominante",
                  "no_atestada"):
        for f in atest["detalle"][clase]:
            clave55 = (f["source_file"][:55], f["pm_prev"])
            if (f["source_file"], f["pm_prev"]) in EXCLUIDAS:
                continue
            rec = por_clave.get((f["document_id"], f["pm_prev"]), {})
            v = rec.get("llm", {})
            alta = v.get("confianza") == "alta" and rec.get("cita_verificada")
            en_bloque = alta and (not f.get("hermanas")
                                  or rec.get("hermanas_resueltas"))
            override = OVERRIDES.get(clave55)
            if not en_bloque and not override:
                continue
            if v.get("veredicto") == "MANTENER_PREV" and not override:
                mantener.append({"source_file": f["source_file"],
                                 "pm_prev": f["pm_prev"],
                                 "motivo": "MANTENER_PREV adjudicado (no-op)"})
                continue
            plan.append({"document_id": f["document_id"],
                         "source_file": f["source_file"],
                         "pm_prev": f["pm_prev"],
                         "pm_nuevo": override or f["canonico"],
                         "origen": ("§1 adjudicado" if override
                                    else "§0/§0-bis en bloque")})
    utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    filas_recibo, backup, saltados = [], [], []
    aplicadas = abortado = 0

    with abierto(timeout=30.0) as c:
        for x in EXTRA:
            r = c.get(f"{SB}/rest/v1/chunks_v2", headers=HS,
                      params={"select": "document_id",
                              "source_file": f"eq.{x['source_file']}",
                              "limit": "1"})
            r.raise_for_status()
            if r.json():
                plan.append({"document_id": r.json()[0]["document_id"], **x,
                             "origen": "extensión adjudicada"})
        for fila in plan:
            did = fila["document_id"]
            r = c.get(f"{SB}/rest/v1/documents", headers=HS,
                      params={"select": "id,status", "id": f"eq.{did}"})
            r.raise_for_status()
            doc = (r.json() or [None])[0]
            if not doc or doc.get("status") != "active":
                saltados.append({**fila, "motivo": "doc no activo (drift)"})
                continue
            r = c.get(f"{SB}/rest/v1/chunks_v2", headers=HS,
                      params={"select": "id,product_model",
                              "document_id": f"eq.{did}",
                              "product_model": f"eq.{fila['pm_prev']}",
                              "order": "id.asc", "limit": "1000"})
            r.raise_for_status()
            objetivo = r.json()
            if not objetivo:
                saltados.append({**fila, "motivo": "0 chunks con pm_prev (drift)"})
                continue
            for ch in objetivo:
                backup.append({"id": ch["id"], "document_id": did,
                               "product_model_prev": ch["product_model"]})
            esperado, afectadas, doc_ok = len(objetivo), 0, True
            if args.aplicar:
                try:
                    for ch in objetivo:
                        rr = c.patch(
                            f"{SB}/rest/v1/chunks_v2",
                            headers={**HS, "Prefer": "return=representation"},
                            params={"id": f"eq.{ch['id']}",
                                    "product_model": f"eq.{fila['pm_prev']}"},
                            json={"product_model": fila["pm_nuevo"]})
                        rr.raise_for_status()
                        afectadas += len(rr.json())
                except Exception as exc:          # noqa: BLE001
                    doc_ok = False
                    abortado += 1
                    fila["ABORT"] = f"HTTP: {type(exc).__name__}"
                if doc_ok and afectadas != esperado:
                    doc_ok = False
                    abortado += 1
                    fila["ABORT"] = f"CAS {afectadas} != {esperado}"
                else:
                    aplicadas += afectadas
            # gate findability: el pm NUEVO matchea ≥1 canónico primario del doc
            pats = patrones_doc.get(fila["source_file"])
            gate = (any(p.search(fila["pm_nuevo"]) for p in pats)
                    if pats else None)
            filas_recibo.append({**fila, "chunks": esperado,
                                 "aplicadas": afectadas if args.aplicar else None,
                                 "findability_pm_nuevo": gate})

    gate_global = all(f["findability_pm_nuevo"] is not False
                      for f in filas_recibo)
    recibo = {
        "que_es": ("Aplicador de los síes de Alberto al packet E3 v2 "
                   "(§0+§0-bis en bloque + §1 adjudicado; ZXrA excluida "
                   "pendiente de su decisión). Mecánica T3: backup por-chunk + "
                   "CAS + gate findability sobre el pm nuevo vs doc_map."),
        "modo": modo, "utc": utc, "plan": len(plan),
        "mantener_noop": mantener, "saltados": saltados,
        "chunks_backup": len(backup), "chunks_aplicados": aplicadas,
        "aborts": abortado, "findability_ok": gate_global,
        "detalle": filas_recibo,
    }
    base = ROOT / "evals" / f"s322_e3_writer_packet_{modo}_{utc}"
    Path(str(base) + ".json").write_text(
        json.dumps(recibo, ensure_ascii=False, indent=1), encoding="utf-8")
    Path(str(base) + "_backup.json").write_text(
        json.dumps(backup, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{modo}: plan {len(plan)} · mantener(no-op) {len(mantener)} · "
          f"saltados {len(saltados)} · backup {len(backup)} · "
          f"aplicadas {aplicadas} · aborts {abortado} · "
          f"findability {gate_global}")
    for f in filas_recibo:
        marca = "" if f["findability_pm_nuevo"] is not False else "  ⚠ GATE"
        print(f"  {f['pm_prev']!r} → {f['pm_nuevo']!r} ({f['chunks']} ch, "
              f"{f['origen']}){marca}")
    print(f"recibo -> {base}.json")
    return 0 if (abortado == 0 and gate_global) else 1


if __name__ == "__main__":
    raise SystemExit(main())
