#!/usr/bin/env python3
"""s83_pilot_extract_duo.py - PILOTO de extraccion MULTI-LABEL doc->modelos (duo Opus 4.8 + GPT-5.5).

v4 (esquema FINAL tras dúo del record-schema, s83). Valida que el esquema EXPANDIDO se pueble limpio
ANTES del run completo (~1014 docs, ~$300). Por doc: Opus 4.8 y GPT-5.5 extraen INDEPENDIENTE,
mismo input (CONTENIDO COMPLETO con marcas de pagina), schema ESTRUCTURADO; se reconcilia.
Salida CANDIDATA (confidence), NO autoritativa.

Cambios v4 (dúo Opus + GPT-5.5 sobre el record-schema — los 3 fuerzan re-pago si faltan):
  - relations[] {type, source_model, target_model, evidence}: variant_of|bundles|supersedes|
    superseded_by|requires|compatible_with -> alimenta series_registry (members/shared_docs). doc-13 VCC-1 bundles AMG-1.
  - canonical_model + aliases[] por modelo -> RESOLUCION de identidad (ZXe->ZX2e/ZX5e, 6577->NFXI-ASD11,
    part-numbers, order-codes); construye model_aliases. NO es normalizacion tipografica (esa va downstream).
  - cert[] {norma, clase} EN54-x por modelo -> el tecnico PCI enruta por clase; sale gratis al leer.
  - confidence POR covered_model (no solo doc); evidence {text, page}; source_quality (ok|ocr_poor|scan);
    category FREE-TEXT (el enum se rompio en piloto v3: 'repuesto'); trazabilidad source_sha256/run_id/prompt_hash.

2 capas: este JSONL = el RAW que paga el $300 (re-leer = re-pagar); la tabla normalizada es transform
barato (re-transform gratis). El acuerdo cross-model mide CONVERGENCIA; la PRECISION la da el ground-truth
de Alberto (s83_pilot_groundtruth.yaml). Resumable; error transitorio NO se persiste. Read-only sobre DB.
"""
from __future__ import annotations
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv

os.environ["CHUNKS_TABLE"] = "chunks_v2"
ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)
sys.path.insert(0, str(ROOT))
from src.config import (  # noqa: E402
    SUPABASE_URL, SUPABASE_SERVICE_KEY, ANTHROPIC_API_KEY, OPENAI_API_KEY,
)
from anthropic import Anthropic  # noqa: E402
from openai import OpenAI  # noqa: E402

OPUS_MODEL = os.getenv("EXTRACT_OPUS_MODEL", "claude-opus-4-8")
GPT_MODEL = os.getenv("EXTRACT_GPT_MODEL", "gpt-5.5")
PROMPT_VERSION = "s83-v4"
SCHEMA_VERSION = "s83-v4"
H = {"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"}
CH = f"{SUPABASE_URL}/rest/v1/chunks_v2"
OUT = ROOT / "evals" / "s83_pilot_extraction.jsonl"
SUMMARY = ROOT / "evals" / "s83_pilot_review.md"
MAX_CHARS = 260_000

PILOT = [
    ("36864_00_FAAST_FLEX_Product_Guide_(I56-7020-000_ES)_A4_Spanish_lores",
     "FAAST FLEX Xtralis: FLX-010/020 + cert EN54-20?"),
    ("37430_00_FAAST_FLEX_Bluetooth_User_Guide_(A05-0600-000_ES)_A4_Spanish",
     "familia FAAST FLEX: covered vacio + app=mention"),
    ("A05-7030-000_B_ES_Notifier FAAST FLEX Addressable",
     "OEM Notifier: NFXI-FLX-0xx + aliases/part-numbers + cert"),
    ("A05-7030-100_B_ES_Morley FAAST FLEX Addressable",
     "OEM Morley: MI-FLX-0xx"),
    ("997-671-005-3_Configuration_ES",
     "Pearl config: covered=[Pearl], PRL-COM=mention"),
    ("997-669-005-3_Instal-Comm_ES",
     "Pearl instal: placas con apendice; relations?"),
    ("55315013 Manual Centrales Analogicas CAD-150-8 Instalacion ES FR GB IT",
     "CAD-150-8 prov filename; canonical?"),
    ("55315501 CAD150R Instalacion ES GB 191018",
     "CAD150R distinto, prov filename"),
    ("MFDT280",
     "AM2020 y AFP1010 + CRT-1 (apendice 1)"),
    ("BTDT032",
     "AM2020/AFP1010 composite diminuto"),
    ("997-670-007-3_Operating_PT",
     "Pearl PT diminuto: lang=pt"),
    ("MADT281",
     "AM2020 diminuto"),
    ("MIDT340",
     "MEGAFONIA: relations VCC-1 bundles AMG-1; source_quality"),
    ("MADT283",
     "AM2020/AFP1010 programacion: OCR malo -> source_quality=ocr_poor"),
    ("MADT285",
     "AM2020/AFP1010 mantenimiento"),
]

SYS = """Eres un experto en sistemas de proteccion contra incendios (PCI) y dominios afines (deteccion, rociadores, megafonia, CCTV, control de acceso). Tarea: del CONTENIDO COMPLETO de un documento tecnico, extrae identidad ESTRUCTURADA. Tu salida es CANDIDATA (con confidence), NO verdad absoluta.

JERARQUIA:
- family_scope = familia/linea (FAAST FLEX, Pearl, CAD-150). NO es un modelo. Familia generica SIN SKU concreto -> family_scope + covered_models VACIO.
- covered_models = SKU de PRODUCTO con cobertura sustantiva. NUNCA el nombre de familia/linea. NUNCA software/apps.

CUBIERTO: un producto es CUBIERTO si el doc es FUENTE sustantiva de el (responderias install/config/operacion/specs de X DESDE el doc) -> "una query sobre X se enruta aqui". role 'primary'=sujeto principal; 'secondary'=cobertura sustantiva no-principal (placa opcional CON su propio apendice). MENCIONADO: referencia de paso (tabla de pedido, compatibilidad, cableado, recambio). REGLA REPUESTO: instrucciones de RECAMBIO no hacen covered.

POR CADA covered_model:
- model = forma EXACTA como aparece en el doc.
- canonical_model = la forma CANONICA del SKU. Si el doc usa nombre PARAGUAS ('ZXe') pero nombra/implica variantes (ZX2e, ZX5e), pon el SKU concreto en 'model' y su forma canonica aqui. Si el identificador es un codigo de pedido/part-number, resuelve al modelo comercial.
- aliases[] = OTRAS formas del MISMO producto vistas en el doc: nombre paraguas, part-number, codigo de pedido, alias OEM/relabel. (Construye el mapa de alias; CRITICO, solo sale de leer.)
- category = tipo de producto en TEXTO LIBRE (central, detector optico, sirena, modulo de entrada, aspiracion, repetidor, fuente, rociador, camara, software, accesorio, repuesto...). NO te limites a una lista cerrada.
- provenance = de donde sale el token: body | filename | legacy_tag | feature | external.
- cert[] = certificaciones/normas con clase POR modelo si el doc las da: [{"norma":"EN 54-20","clase":"A"}]. [] si no.
- confidence = high|medium|low de ESTE modelo.
- evidence = {"text": cita/seccion, "page": nº de pagina (texto) o "" si no consta}.

relations[] = relaciones INTER-modelo que el doc establezca: {"type": variant_of|bundles|supersedes|superseded_by|requires|compatible_with, "source_model", "target_model", "evidence"}. Ej.: VCC-1 'bundles' AMG-1 (el VCC-1 EMPAQUETA/incluye el AMG-1); ZX2e 'variant_of' ZXe. [] si no hay.

IDENTITY (reconcilia, NO inventes):
- brand_on_doc = marca de portada (la que el usuario usaria para buscar: Notifier, Morley...).
- oem_manufacturer = fabricante OEM real SOLO si el doc lo EVIDENCIA explicitamente; 'unknown' si no. NUNCA inferir desde conocimiento externo.
- oem_evidence = cita que respalda oem_manufacturer, o ''.
- distributor = canal si el doc lo indica, 'unknown' si no.

DOC-LEVEL:
- source_quality = ok | ocr_poor | scan | partial (HONESTO: tablas/texto ilegibles por OCR -> 'ocr_poor').
- doc_type = instalacion|operacion|configuracion|datasheet|boletin|guia_usuario|mantenimiento|otro.
- languages[] = idiomas presentes (es,en,fr,pt,it). protocol = '' si no. supersession = ciclo de vida doc-level ('EOL','reemplaza a X'); '' si no. confidence = global del doc.

Nullability: 'unknown' cuando MIRASTE pero no determinaste; '' o [] cuando esta AUSENTE. Solo tokens EXPLICITOS; forma EXACTA; lee el CUERPO COMPLETO. Registra con la herramienta/esquema indicado."""

PROMPT_HASH = hashlib.sha256(SYS.encode("utf-8")).hexdigest()[:12]

_EVID = {"type": "object", "additionalProperties": False,
         "properties": {"text": {"type": "string"}, "page": {"type": "string"}},
         "required": ["text", "page"]}
_CERT = {"type": "object", "additionalProperties": False,
         "properties": {"norma": {"type": "string"}, "clase": {"type": "string"}},
         "required": ["norma", "clase"]}
_ITEM_COV = {"type": "object", "additionalProperties": False,
             "properties": {
                 "model": {"type": "string"},
                 "canonical_model": {"type": "string"},
                 "aliases": {"type": "array", "items": {"type": "string"}},
                 "role": {"type": "string", "enum": ["primary", "secondary"]},
                 "category": {"type": "string"},
                 "provenance": {"type": "string",
                                "enum": ["body", "filename", "legacy_tag", "feature", "external"]},
                 "cert": {"type": "array", "items": _CERT},
                 "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                 "evidence": _EVID},
             "required": ["model", "canonical_model", "aliases", "role", "category",
                          "provenance", "cert", "confidence", "evidence"]}
_ITEM_MEN = {"type": "object", "additionalProperties": False,
             "properties": {"model": {"type": "string"}, "category": {"type": "string"},
                            "evidence": _EVID},
             "required": ["model", "category", "evidence"]}
_ITEM_REL = {"type": "object", "additionalProperties": False,
             "properties": {"type": {"type": "string",
                                     "enum": ["variant_of", "bundles", "supersedes",
                                              "superseded_by", "requires", "compatible_with"]},
                            "source_model": {"type": "string"},
                            "target_model": {"type": "string"},
                            "evidence": {"type": "string"}},
             "required": ["type", "source_model", "target_model", "evidence"]}
_IDENT = {"type": "object", "additionalProperties": False,
          "properties": {"brand_on_doc": {"type": "string"},
                         "oem_manufacturer": {"type": "string"},
                         "oem_evidence": {"type": "string"},
                         "distributor": {"type": "string"}},
          "required": ["brand_on_doc", "oem_manufacturer", "oem_evidence", "distributor"]}
SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "source_quality": {"type": "string", "enum": ["ok", "ocr_poor", "scan", "partial"]},
        "identity": _IDENT,
        "family_scope": {"type": "string"},
        "doc_type": {"type": "string"},
        "languages": {"type": "array", "items": {"type": "string"}},
        "protocol": {"type": "string"},
        "covered_models": {"type": "array", "items": _ITEM_COV},
        "mentioned_not_covered": {"type": "array", "items": _ITEM_MEN},
        "relations": {"type": "array", "items": _ITEM_REL},
        "supersession": {"type": "string"},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "notes": {"type": "string"},
    },
    "required": ["source_quality", "identity", "family_scope", "doc_type", "languages", "protocol",
                 "covered_models", "mentioned_not_covered", "relations", "supersession",
                 "confidence", "notes"],
}


def norm_model(m: str) -> str:
    s = (m or "").upper().strip()
    for sym in ("™", "®", "©"):
        s = s.replace(sym, "")
    s = re.sub(r"\s*-\s*", "-", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def fetch_content(sf: str):
    rows: list = []
    off = 0
    while True:
        batch = None
        for a in range(4):
            try:
                r = httpx.get(CH, headers=H, params={
                    "select": "chunk_index,page_number,section_title,content,product_model,manufacturer,extraction_sha256",
                    "source_file": f"eq.{sf}",
                    "order": "chunk_index.asc.nullslast",
                    "limit": "1000", "offset": str(off)}, timeout=120)
                r.raise_for_status()
                batch = r.json()
                break
            except Exception:
                if a == 3:
                    raise
                time.sleep(2 * (a + 1))
        rows.extend(batch)
        if len(batch) < 1000:
            break
        off += 1000
    cur_tag = next((x["product_model"] for x in rows if x.get("product_model")), None)
    cur_mfr = next((x["manufacturer"] for x in rows if x.get("manufacturer")), None)
    sha = next((x["extraction_sha256"] for x in rows if x.get("extraction_sha256")), None)
    parts = []
    for x in rows:
        pg = x.get("page_number")
        st = x.get("section_title")
        head = (f"[pag {pg}] " if pg is not None else "") + (f"## {st}\n" if st else "")
        parts.append(head + (x.get("content") or ""))
    text = "\n\n".join(parts)
    trimmed = len(text) > MAX_CHARS
    return text[:MAX_CHARS], cur_tag, cur_mfr, sha, len(rows), trimmed


def call_opus(client, sf, content):
    user = f"source_file: {sf}\n\n===== CONTENIDO COMPLETO DEL DOCUMENTO =====\n{content}"
    for a in range(3):
        try:
            resp = client.messages.create(
                model=OPUS_MODEL, max_tokens=12000, system=SYS,
                tools=[{"name": "registrar_modelos",
                        "description": "Registra identidad estructurada, modelos cubiertos/mencionados, relaciones y metadatos.",
                        "input_schema": SCHEMA}],
                tool_choice={"type": "tool", "name": "registrar_modelos"},
                messages=[{"role": "user", "content": user}])
            for block in resp.content:
                if block.type == "tool_use":
                    return block.input, (resp.usage.input_tokens, resp.usage.output_tokens)
            return {"_error": "sin tool_use"}, (resp.usage.input_tokens, resp.usage.output_tokens)
        except Exception as e:
            if a == 2:
                return {"_error": str(e)[:240]}, (0, 0)
            time.sleep(4 * (a + 1))


def call_gpt(client, sf, content):
    user = f"source_file: {sf}\n\n===== CONTENIDO COMPLETO DEL DOCUMENTO =====\n{content}"
    for a in range(3):
        try:
            resp = client.chat.completions.create(
                model=GPT_MODEL,
                messages=[{"role": "system", "content": SYS},
                          {"role": "user", "content": user}],
                response_format={"type": "json_schema", "json_schema": {
                    "name": "registrar_modelos", "schema": SCHEMA, "strict": True}})
            u = resp.usage
            return json.loads(resp.choices[0].message.content), (u.prompt_tokens, u.completion_tokens)
        except Exception as e:
            if a == 2:
                return {"_error": str(e)[:240]}, (0, 0)
            time.sleep(4 * (a + 1))


def covered_set(res):
    if not res or res.get("_error"):
        return None
    return {norm_model(m.get("model")) for m in res.get("covered_models", []) if m.get("model")}


def _cov_str(res):
    out = []
    for m in res.get("covered_models", []):
        cert = ",".join(f"{c.get('norma')}:{c.get('clase')}" for c in m.get("cert", []))
        al = ("|al:" + ",".join(m.get("aliases", []))) if m.get("aliases") else ""
        cn = (f"->{m.get('canonical_model')}" if m.get("canonical_model")
              and m.get("canonical_model") != m.get("model") else "")
        out.append(f"{m.get('model')}{cn} ({m.get('role')}/{m.get('category')}/{m.get('confidence')}"
                   f"{'/cert:' + cert if cert else ''}{al})")
    return "; ".join(out) or "-"


def _rel_str(res):
    return "; ".join(f"{r.get('source_model')} -{r.get('type')}-> {r.get('target_model')}"
                     for r in res.get("relations", [])) or "-"


def write_summary(results, n_agree, n_done):
    L = ["# Piloto extraccion v4 (record-schema final: +relations +canonical +cert) -- s83",
         "",
         f"**Acuerdo Opus<->GPT-5.5 (covered_models, ™-norm): {n_agree}/{n_done}** "
         "(convergencia; la PRECISION = ground-truth Alberto)",
         "",
         "| # | source_file | sq | family | Opus cubre | GPT cubre | acuerdo |",
         "|---|---|---|---|---|---|---|"]
    for i, r in enumerate(results, 1):
        oc = ", ".join(r.get("opus_covered") or []) or "(vacio/?)"
        gc = ", ".join(r.get("gpt_covered") or []) or "(vacio/?)"
        of = (r.get("opus") or {}).get("family_scope", "?") if not (r.get("opus") or {}).get("_error") else "ERR"
        sq = (r.get("opus") or {}).get("source_quality", "?") if not (r.get("opus") or {}).get("_error") else "ERR"
        ok = "OK" if r.get("agree") else "**DIVERGE**"
        L.append(f"| {i} | `{r['source_file'][:30]}` | {sq} | {of} | {oc} | {gc} | {ok} |")
    L += ["", "## Detalle por doc (covered[canonical/cert/aliases] + relations + identity)", ""]
    for i, r in enumerate(results, 1):
        L.append(f"### {i}. {r['source_file']}")
        L.append(f"_{r.get('why','')}_  (tag: `{r.get('current_tag')}`; sha: `{(r.get('source_sha256') or '')[:10]}`; "
                 f"{r.get('n_chunks')} chunks)")
        for lbl, res in (("Opus 4.8", r.get("opus")), ("GPT-5.5", r.get("gpt"))):
            if not res or res.get("_error"):
                L.append(f"- **{lbl}**: ERROR {res.get('_error') if res else ''}")
                continue
            idn = res.get("identity", {})
            L.append(f"- **{lbl}** (sq={res.get('source_quality')}, brand={idn.get('brand_on_doc')}, "
                     f"oem={idn.get('oem_manufacturer')}, family={res.get('family_scope')}, "
                     f"doc_type={res.get('doc_type')}, conf={res.get('confidence')})")
            L.append(f"  - CUBRE: {_cov_str(res)}")
            if res.get("relations"):
                L.append(f"  - RELATIONS: {_rel_str(res)}")
            men = "; ".join(f"{m.get('model')}[{m.get('category','')}]"
                            for m in res.get("mentioned_not_covered", []))
            if men:
                L.append(f"  - menciona: {men}")
            if res.get("notes"):
                L.append(f"  - notes: {res['notes'][:200]}")
        L.append("")
    SUMMARY.write_text("\n".join(L), encoding="utf-8")


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    if not ANTHROPIC_API_KEY or not OPENAI_API_KEY:
        sys.exit("Faltan ANTHROPIC_API_KEY / OPENAI_API_KEY en .env")
    run_id = datetime.now().strftime("%Y%m%dT%H%M%S")
    print(f"run_id={run_id} prompt_hash={PROMPT_HASH} schema={SCHEMA_VERSION}", flush=True)
    done = {}
    if OUT.exists():
        for line in OUT.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rec = json.loads(line)
                done[rec["source_file"]] = rec
    a_client = Anthropic(api_key=ANTHROPIC_API_KEY)
    o_client = OpenAI(api_key=OPENAI_API_KEY)
    ti_o = to_o = ti_g = to_g = 0
    results = []
    for i, (sf, why) in enumerate(PILOT, 1):
        if sf in done:
            print(f"[{i}/15] SKIP (ya hecho): {sf[:50]}", flush=True)
            results.append(done[sf])
            continue
        print(f"[{i}/15] {sf[:55]}", flush=True)
        print(f"        ({why})", flush=True)
        try:
            content, cur_tag, cur_mfr, sha, n, trimmed = fetch_content(sf)
        except Exception as e:
            print(f"        !! fetch fallo ({str(e)[:90]}); NO persisto -> reintentable", flush=True)
            continue
        if not content:
            print("        !! sin contenido, salto", flush=True)
            continue
        print(f"        {n} chunks, {len(content)} chars{' (TRIM)' if trimmed else ''} -> Opus + GPT-5.5...",
              flush=True)
        opus_res, (oi, oo) = call_opus(a_client, sf, content)
        gpt_res, (gi, go) = call_gpt(o_client, sf, content)
        ti_o += oi; to_o += oo; ti_g += gi; to_g += go
        oe = opus_res.get("_error") if isinstance(opus_res, dict) else None
        ge = gpt_res.get("_error") if isinstance(gpt_res, dict) else None
        if oe or ge:
            print(f"        !! error de modelo (opus={bool(oe)} gpt={bool(ge)}: "
                  f"{str(oe or ge)[:70]}); NO persisto -> reintentable", flush=True)
            continue
        os_set, gs_set = covered_set(opus_res), covered_set(gpt_res)
        agree = os_set is not None and gs_set is not None and os_set == gs_set
        rec = {
            "source_file": sf, "why": why, "n_chunks": n, "chars": len(content), "trimmed": trimmed,
            "source_sha256": sha, "run_id": run_id, "prompt_hash": PROMPT_HASH,
            "prompt_version": PROMPT_VERSION, "schema_version": SCHEMA_VERSION,
            "current_tag": cur_tag, "current_manufacturer": cur_mfr,
            "opus": opus_res, "gpt": gpt_res, "agree": agree,
            "opus_covered": sorted(os_set) if os_set is not None else None,
            "gpt_covered": sorted(gs_set) if gs_set is not None else None,
        }
        with OUT.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        results.append(rec)
        nrel_o = len(opus_res.get("relations", []))
        nrel_g = len(gpt_res.get("relations", []))
        print(f"        Opus={rec['opus_covered']} (rel:{nrel_o})  GPT={rec['gpt_covered']} (rel:{nrel_g})  "
              f"[{'AGREE' if agree else 'DISAGREE'}]", flush=True)
    n_done = len(results)
    n_agree = sum(1 for r in results if r.get("agree"))
    opus_cost = ti_o / 1e6 * 5 + to_o / 1e6 * 25
    print("\n===== RESUMEN PILOTO v4 =====", flush=True)
    print(f"docs: {n_done}/15 | ACUERDO Opus<->GPT (covered): {n_agree}/{n_done}", flush=True)
    print(f"tokens Opus in/out: {ti_o}/{to_o} (~${opus_cost:.2f} a $5/$25 /M)", flush=True)
    print(f"tokens GPT  in/out: {ti_g}/{to_g}", flush=True)
    write_summary(results, n_agree, n_done)
    print(f"\n-> {OUT}\n-> {SUMMARY}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
