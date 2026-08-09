#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fase DERIVADOS de la ingesta (s315/#68): enunciados + hyq para un LOTE nuevo.

POR QUÉ. Los dos canales derivados están VIVOS en producción (ENUNCIADOS_MULTIVECTOR
DEC-090, HYQ_TABLE DEC-099) pero `ingest_new.py` no los genera: todo lote nuevo entra
como corpus de segunda clase (lote Casmar s314: 1.091 chunks con 0/0 — TECH_DEBT #68).
Este driver orquesta la fase para UN lote, reusando los generadores/gates canónicos:

  E1 enunciados: `enunciados_pass.py --docs <lote> --to-dump` (QA in-run `qa_statement`,
     ledger+resume, Haiku vintage h1 = el GO de DEC-102, budget duro)
  E2 carga: `s104_a3_load.py --dumps ... --only-source-files ... --rewrite-batch-tag
     enunciados-v1:<tag>:h1 --ledger-check --ids-out` (el camino acotado s273, estrenado aquí)
  H  hyq: `hyq_lote_pipeline.py` (vintage POR LOTE append-seguro; parse/embed pineados)
  V  verificación en DB: cobertura por doc en AMBAS tablas + recibo JSON

DÓNDE. Máquina con claves (.env: ANTHROPIC, VOYAGE, SUPABASE) y con el extraction
store del lote (bajo --data-root de ingest_new, normalmente OneDrive). Dry-run por
defecto: imprime plan + coste estimado y NO llama a ninguna API.

Uso típico (lote Casmar s314):
  python scripts/derive_channels_lote.py --since 2026-08-08 --tag casmar314 \
      --data-root "C:\\...\\Technical Bot"            # dry-run
  ... mismo comando + --aplicar                        # ejecuta E1→E2→H→V
Selección alternativa: --docs-file <fichero con un source_file por línea>.
Reanudable: cada herramienta subyacente ya reanuda; re-lanzar continúa donde iba.
Post-carga: VACUUM (fantasmas HNSW, DEC-088) — el recibo lo recuerda.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

try:  # convención del repo (143 scripts): la consola Windows es cp1252 y los
    # informes llevan → ≈ ─ ✅ ❌ — sin esto, un print revienta el run a media carga
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=False)

import httpx  # noqa: E402

from src.config import SUPABASE_SERVICE_KEY, SUPABASE_URL  # noqa: E402

HEADERS = {"apikey": SUPABASE_SERVICE_KEY,
           "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"}
ENUN_MODEL = "claude-haiku-4-5-20251001"   # GO de G0 (DEC-102): mejor QA y 4× más barato
COSTE_HYQ_POR_CHUNK = 0.004
COSTE_ENUN_POR_DOC = (0.05, 0.15)          # banda observada T2 (DEC-102: $9.7 / 81 docs)


def _source_files_de_doc(client: httpx.Client, doc_id: str) -> tuple[set[str], int]:
    """TODOS los source_file distintos de un documento + su nº de chunks.

    (dúo s316, Sol CRÍTICO) La v1 tomaba `limit=1` SIN `order`: un documento con
    source_file heterogéneo entraba a medias y la fila elegida no era determinista
    entre runs. Aquí se paginan los chunks de verdad (max-rows de Supabase = 1000).
    """
    vistos: set[str] = set()
    total = 0
    offset = 0
    while True:
        r = client.get(f"{SUPABASE_URL}/rest/v1/chunks_v2",
                       headers={**HEADERS, "Range": f"{offset}-{offset + 999}"},
                       params={"select": "source_file", "document_id": f"eq.{doc_id}",
                               "order": "id.asc"})
        r.raise_for_status()
        filas = r.json()
        vistos.update(f["source_file"] for f in filas if f.get("source_file"))
        total += len(filas)
        if len(filas) < 1000:
            break
        offset += 1000
    return vistos, total


def _docs_del_lote(client: httpx.Client, since: str,
                   hasta: str | None = None) -> list[dict]:
    """Docs con ingested_at en [since, hasta) y sus source_file (fuente: DB)."""
    params = {"select": "id,source_pdf_filename,ingested_at",
              "ingested_at": f"gte.{since}", "limit": "2000",
              "order": "ingested_at.asc"}
    if hasta:
        # (dúo s316, Sol MEDIO) sin cota superior, `--aplicar` re-consulta y puede
        # arrastrar documentos ingestados DESPUÉS del dry-run revisado.
        params["and"] = f"(ingested_at.gte.{since},ingested_at.lt.{hasta})"
    r = client.get(f"{SUPABASE_URL}/rest/v1/documents", headers=HEADERS, params=params)
    r.raise_for_status()
    out = []
    for d in r.json():
        src, n = _source_files_de_doc(client, d["id"])
        if n and src:
            out.append({"document_id": d["id"], "source_files": sorted(src),
                        "chunks": n})
    return out


def _verificar_biyeccion(client: httpx.Client, lote: list[dict]) -> list[str]:
    """Ningún source_file del lote puede traer chunks de documentos AJENOS.

    (dúo s316, Sol CRÍTICO) El lote se selecciona por `document_id` pero los
    generadores consultan por `source_file`. El runtime endureció exactamente esta
    fuga en s288 F2 (`doc_scoped_hyq_coverage`: «Scope is document_id, never a file
    name … two documents sharing a source_file can no longer bleed into each
    other»); el driver la reintroducía. Aquí se comprueba, ANTES de gastar: el
    recuento corpus-wide por source_file debe casar con el recuento dentro del lote.
    """
    del_lote = {d["document_id"] for d in lote}
    propios: dict[str, int] = {}
    for d in lote:
        for sf in d["source_files"]:
            propios[sf] = propios.get(sf, 0) + 0  # asegura la clave
    # recuento REAL por source_file dentro del lote (por doc, para no confiar en sumas)
    for d in lote:
        for sf in d["source_files"]:
            rc = client.get(f"{SUPABASE_URL}/rest/v1/chunks_v2",
                            headers={**HEADERS, "Prefer": "count=exact",
                                     "Range": "0-0"},
                            params={"select": "id", "document_id": f"eq.{d['document_id']}",
                                    "source_file": f"eq.{sf}"})
            propios[sf] += int((rc.headers.get("content-range") or "/0").split("/")[-1])
    fugas = []
    for sf, n_propios in sorted(propios.items()):
        rc = client.get(f"{SUPABASE_URL}/rest/v1/chunks_v2",
                        headers={**HEADERS, "Prefer": "count=exact", "Range": "0-0"},
                        params={"select": "id", "source_file": f"eq.{sf}"})
        n_global = int((rc.headers.get("content-range") or "/0").split("/")[-1])
        if n_global != n_propios:
            fugas.append(f"{sf}: {n_global} chunks corpus-wide vs {n_propios} del lote "
                         f"(+{n_global - n_propios} de documentos AJENOS)")
    _ = del_lote
    return fugas


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--since", help="fecha ISO: docs con ingested_at >= fecha")
    g.add_argument("--docs-file", help="fichero con un source_file por línea")
    ap.add_argument("--tag", required=True, help="nombre del lote (p.ej. casmar314)")
    ap.add_argument("--hasta", default=None,
                    help="cota SUPERIOR ISO de ingested_at (congela la ventana del lote)")
    ap.add_argument("--data-root", default=None,
                    help="raíz de datos de ingest_new (para el extraction store)")
    ap.add_argument("--aplicar", action="store_true")
    ap.add_argument("--solo", choices=["enunciados", "hyq"], default=None)
    ap.add_argument("--refrescar-seleccion", action="store_true",
                    help="permite que --aplicar re-congele una selección que ha cambiado "
                         "desde el dry-run (por defecto ABORTA: dúo s316)")
    a = ap.parse_args()

    with httpx.Client(timeout=120.0) as client:
        if a.since:
            lote = _docs_del_lote(client, a.since, a.hasta)
            src_files = sorted({sf for d in lote for sf in d["source_files"]})
            n_chunks = sum(d["chunks"] for d in lote)
            fugas = _verificar_biyeccion(client, lote)
            if fugas:
                print("❌ FUGA source_file: estos nombres traen chunks de documentos "
                      "AJENOS al lote — los generadores derivarían corpus que no has "
                      "revisado (s288 F2 prohíbe esta fuga en runtime):")
                for f in fugas:
                    print(f"    - {f}")
                print("   Usa --docs-file con una selección saneada, o corrige la "
                      "colisión de nombres antes de derivar.")
                return 1
        else:
            src_files = sorted({ln.strip() for ln in open(a.docs_file, encoding="utf-8")
                                if ln.strip()})
            lote, n_chunks = [], 0
            for sf in src_files:
                rc = client.get(f"{SUPABASE_URL}/rest/v1/chunks_v2",
                                headers={**HEADERS, "Prefer": "count=exact",
                                         "Range": "0-0"},
                                params={"select": "id", "source_file": f"eq.{sf}"})
                n_chunks += int((rc.headers.get("content-range") or "/0").split("/")[-1])

        if not src_files:
            print("❌ lote vacío (0 source_files) — nada que derivar")
            return 1

        # (dúo s316, Sol MEDIO) CONGELAR la selección: el dry-run que se revisa y el
        # --aplicar que gasta tienen que ser el MISMO lote. Sin esto, un documento
        # ingestado entre ambos entra sin haber sido mirado por nadie.
        doc_ids = sorted(d["document_id"] for d in lote)
        firma = hashlib.sha256(
            json.dumps({"docs": src_files, "document_ids": doc_ids,
                        "chunks": n_chunks}, ensure_ascii=False,
                       sort_keys=True).encode("utf-8")).hexdigest()[:16]
        sel_path = ROOT / "evals" / f"derive_lote_{a.tag}_seleccion.json"
        previa = json.loads(sel_path.read_text(encoding="utf-8")) if sel_path.exists() else None
        if previa and previa.get("firma") != firma:
            print(f"⚠ la selección del lote '{a.tag}' CAMBIÓ desde el dry-run:")
            print(f"    firma congelada: {previa.get('firma')} "
                  f"({previa.get('docs_n')} docs / {previa.get('chunks')} chunks)")
            print(f"    firma de ahora:  {firma} ({len(src_files)} docs / {n_chunks} chunks)")
            if a.aplicar and not a.refrescar_seleccion:
                print("❌ abortado: revisa el diff y re-lanza con --refrescar-seleccion "
                      "si el lote nuevo es el que quieres derivar.")
                return 1
        # (dúo s316) el congelado NO se re-congela solo: si ya hay una firma revisada,
        # solo se sustituye con gesto explícito (--refrescar-seleccion). Antes, un
        # dry-run posterior pisaba en silencio la selección que se había revisado.
        if previa is None or a.refrescar_seleccion:
            sel_path.write_text(json.dumps(
                {"firma": firma, "docs_n": len(src_files), "chunks": n_chunks,
                 "docs": src_files, "document_ids": doc_ids,
                 "hasta": a.hasta, "since": a.since,
                 "fecha_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")},
                ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"selección congelada: firma {firma} → {sel_path.name}")
        else:
            print(f"selección ya congelada: firma {firma} (coincide con {sel_path.name})")

        docs_txt = ROOT / "evals" / f"derive_lote_{a.tag}_docs.txt"
        docs_txt.write_text("\n".join(src_files) + "\n", encoding="utf-8")
        c_lo = len(src_files) * COSTE_ENUN_POR_DOC[0]
        c_hi = len(src_files) * COSTE_ENUN_POR_DOC[1]
        print(f"lote '{a.tag}': {len(src_files)} docs · {n_chunks} chunks → {docs_txt}")
        print(f"coste estimado: enunciados ${c_lo:.0f}-{c_hi:.0f} (banda T2, Haiku) "
              f"+ hyq ≈ ${n_chunks * COSTE_HYQ_POR_CHUNK:.1f} (sonnet-4-6) + Voyage <$1")
        if not a.aplicar:
            print("(dry-run; --aplicar para ejecutar E1→E2→H→V)")
            return 0

        py = sys.executable
        enun_tag = f"enunciados-v1:{a.tag}:h1"
        ids_out = ROOT / "evals" / f"derive_lote_{a.tag}_enun_ids.json"
        corrio_enunciados = a.solo in (None, "enunciados")
        sin_filas: list[str] = []
        if corrio_enunciados:
            # (dúo s316) un manifiesto de un run ANTERIOR haría que V emitiera un
            # veredicto stale sobre esta pasada — se retira antes de re-generarlo.
            if ids_out.exists():
                ids_out.unlink()
            # (dúo s315 #7) --budget-usd del generador compara contra el LEDGER
            # acumulado de por vida: pasar techo = gastado + margen del lote, o el
            # lote N-ésimo se pararía en el doc 1 devolviendo éxito.
            gastado = 0.0
            ledger = ROOT / "evals" / "enunciados_ledger.json"
            if ledger.exists():
                led = json.loads(ledger.read_text(encoding="utf-8"))
                gastado = sum((d.get("cost_usd") or 0)
                              for d in led.get("docs", {}).values())
            budget = round(gastado + max(10.0, 3 * c_hi), 2)
            e1 = [py, "scripts/enunciados_pass.py", "--tranche", a.tag,
                  "--docs", str(docs_txt), "--to-dump", "--resume",
                  "--model", ENUN_MODEL, "--vintage", "h1",
                  "--budget-usd", str(budget)]
            if a.data_root:
                e1 += ["--store",
                       str(Path(a.data_root) / "data" / "extraction"
                           / "agent_anthropic-sonnet-45")]
            print(f"\n── E1 enunciados (budget ledger {gastado:.2f} + lote → {budget}) …")
            rc = subprocess.call(e1, cwd=str(ROOT))
            if rc:
                print(f"❌ E1 falló (rc={rc}) — corrige y re-lanza (reanuda por ledger)")
                return rc
            # (dúo s315 #2) --only-source-files debe llevar los docs CON FILAS EN EL
            # DUMP: pasar la lista de entrada aborta E2 entero si un doc legítimo no
            # produjo enunciados (sin store, todo-dup, 0 items) — y en un lote real
            # eso es lo esperable, no la excepción.
            dump = ROOT / "evals" / f"enunciados_dump_{a.tag}.jsonl"
            docs_en_dump: set[str] = set()
            if dump.exists():
                for ln in dump.read_text(encoding="utf-8-sig").splitlines():
                    try:
                        docs_en_dump.add(json.loads(ln)["source_file"])
                    except Exception:
                        continue
            sin_filas[:] = sorted(set(src_files) - docs_en_dump)
            if sin_filas:
                print(f"  {len(sin_filas)} doc(s) del lote SIN enunciados en el dump "
                      f"(sin store / todo-dup / 0 items) — se cargan los "
                      f"{len(docs_en_dump)} restantes:")
                for d in sin_filas[:10]:
                    print(f"    - {d}")
            if docs_en_dump:
                e2 = [py, "scripts/s104_a3_load.py", "--dumps", str(dump),
                      "--rewrite-batch-tag", enun_tag, "--ledger-check",
                      "--ids-out", str(ids_out),
                      "--only-source-files", *sorted(docs_en_dump)]
                print("\n── E2 carga enunciados …")
                rc = subprocess.call(e2, cwd=str(ROOT))
                if rc:
                    print(f"❌ E2 falló (rc={rc}) — corrige y re-lanza (resume por ids)")
                    return rc
            else:
                print("  dump vacío — E2 saltada (¿--store correcto?)")
        if a.solo in (None, "hyq"):
            h = [py, "scripts/hyq_lote_pipeline.py", "--docs", str(docs_txt),
                 "--tag", a.tag, "--aplicar"]
            print("\n── H hyq por lote …")
            rc = subprocess.call(h, cwd=str(ROOT))
            if rc:
                print(f"❌ H falló (rc={rc}) — corrige y re-lanza (todo reanuda)")
                return rc

        # V — verificación de COMPLETITUD (dúo s315 #9): el manifest de ids que E2
        # declaró es lo que se comprueba en DB, no un presence-check por doc.
        # (dúo s316, Sol CRÍTICO) V es FAIL-CLOSED: antes imprimía ❌ y devolvía 0,
        # así que un lote a medias salía con recibo de éxito.
        enun_ids_ok = None
        fallos: list[str] = []
        avisos: list[str] = []
        corrio_hyq = a.solo in (None, "hyq")
        if corrio_enunciados and not ids_out.exists():
            fallos.append("E2 no dejó manifiesto de ids (ningún enunciado cargado)")
        if sin_filas:
            # (dúo s316) NO es fallo: el propio driver declara que un doc sin store /
            # todo-dup / 0 items es «lo esperable, no la excepción» en un lote real.
            # Hacerlo fallar garantizaba INCOMPLETO en el caso normal = fatiga de
            # alarma, que degrada el fail-closed en vez de reforzarlo. Queda VISIBLE
            # en el recibo y en consola, que es lo que hacía falta.
            avisos.append(f"{len(sin_filas)} doc(s) del lote sin NINGÚN enunciado "
                          f"en el dump (sin store / todo-dup / 0 items)")
        if corrio_enunciados and ids_out.exists():
            ids = json.loads(ids_out.read_text(encoding="utf-8"))
            if isinstance(ids, dict):
                ids = ids.get("ids") or []
            presentes = 0
            for b in range(0, len(ids), 100):
                sub = ids[b:b + 100]
                r = client.get(f"{SUPABASE_URL}/rest/v1/chunks_v2_enunciados",
                               headers={**HEADERS, "Prefer": "count=exact",
                                        "Range": "0-0"},
                               params={"select": "id",
                                       "id": f"in.({','.join(sub)})"})
                presentes += int((r.headers.get("content-range") or "/0")
                                 .split("/")[-1])
            enun_ids_ok = {"manifest": len(ids), "en_db": presentes,
                           "completo": presentes == len(ids)}
            print(f"V enunciados: {presentes}/{len(ids)} ids del manifest en DB "
                  f"→ {'✅' if enun_ids_ok['completo'] else '❌'}")
            if not ids:
                fallos.append("el manifiesto de E2 está VACÍO (0 ids)")
            elif not enun_ids_ok["completo"]:
                fallos.append(f"enunciados incompletos en DB: {presentes}/{len(ids)}")
        hyq_recibo = {}
        hr = ROOT / "evals" / f"hyq_lote_{a.tag}_recibo.json"
        if hr.exists():
            hyq_recibo = json.loads(hr.read_text(encoding="utf-8"))
        if corrio_hyq:
            if not hyq_recibo:
                fallos.append("la fase hyq no dejó recibo")
            elif hyq_recibo.get("veredicto") == "INCOMPLETO" or \
                    hyq_recibo.get("en_tabla") != hyq_recibo.get("universo"):
                fallos.append(f"hyq incompleto: {hyq_recibo.get('en_tabla')}/"
                              f"{hyq_recibo.get('universo')} del universo del lote")
        # (dúo s316, CRÍTICO) el ALCANCE se estampa y manda sobre el mensaje: con
        # --solo, un canal no se ejecuta ni se verifica, así que declarar «COMPLETO en
        # ambos canales» era éxito silencioso — la misma clase que V venía a cerrar.
        canales = [c for c, corrio in (("enunciados", corrio_enunciados),
                                       ("hyq", corrio_hyq)) if corrio]
        recibo = {
            "motivo": "s315/#68: fase derivados del lote (enunciados + hyq)",
            "lote": a.tag, "docs": len(src_files), "chunks": n_chunks,
            "seleccion_firma": firma,
            "alcance": {"solo": a.solo, "canales_ejecutados": canales},
            "enunciados": ({"ingest_batch": enun_tag, "verificacion_ids": enun_ids_ok,
                            "docs_sin_enunciados": sin_filas,
                            "reversible": ("DELETE FROM chunks_v2_enunciados WHERE "
                                           f"ingest_batch = '{enun_tag}'")}
                           if corrio_enunciados else "NO EJECUTADO (--solo)"),
            "hyq": hyq_recibo if corrio_hyq else "NO EJECUTADO (--solo)",
            "veredicto": "COMPLETO" if not fallos else "INCOMPLETO",
            "avisos": avisos,
            "fallos": fallos,
            "fecha_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "pendiente": "VACUUM de chunks_v2_enunciados y chunks_v2_hyq (DEC-088)",
        }
        out = ROOT / "evals" / f"derive_lote_{a.tag}_recibo.json"
        out.write_text(json.dumps(recibo, ensure_ascii=False, indent=1),
                       encoding="utf-8")
        print(f"\nrecibo → {out}")
        for av in avisos:
            print(f"⚠ {av}")
        if fallos:
            print(f"\n❌ lote '{a.tag}' INCOMPLETO — el recibo NO declara cobertura:")
            for f in fallos:
                print(f"    - {f}")
            print("   (lo cargado es reversible por ingest_batch; re-lanzar reanuda)")
            return 1
        print(f"\n✅ lote '{a.tag}' COMPLETO en: {', '.join(canales)}"
              + ("" if len(canales) == 2 else "  ⚠ el otro canal NO se ejecutó (--solo)"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
