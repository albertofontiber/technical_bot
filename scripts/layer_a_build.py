#!/usr/bin/env python3
"""Capa A — gold answers con Opus 4.7 sobre PDFs (PLAN_RAG_2026 §5 Capa A).

Para cada pregunta hp* genera la respuesta CANÓNICA (gold standard) que un
técnico experto daría, basándose EXCLUSIVAMENTE en las páginas relevantes del/
los manual(es) oficial(es). Opus 4.7 lee los PDFs de forma nativa (multimodal:
texto + tablas + diagramas), evitando el sesgo de "citar de memoria" (lección
Fase 0) y los posibles fallos del chunker (lee el PDF, no los chunks).

Diseño:
  - Páginas relevantes desde evals/gold_layer_a_mapping.json (relevant_chunks),
    con margen ±MARGIN para absorber el off-by-2 del chunker (bug conocido B3).
  - Docs sin relevant_chunks (admit_no_info de facto): se pasa el PDF completo
    del producto y Opus decide conducta (answer / ask_clarification /
    admit_no_info).
  - Output estructurado por pregunta → evals/gold_answers_v1.yaml.

Uso:
    python scripts/layer_a_build.py hp001        # una pregunta (mini-test)
    python scripts/layer_a_build.py all           # las 19
"""
from __future__ import annotations

import base64
import json
import os
import sys
from pathlib import Path

import fitz  # pymupdf
import yaml
from anthropic import Anthropic
from dotenv import load_dotenv

# Path absoluto al .env del proyecto + override=True: el shell/sandbox puede
# tener ANTHROPIC_API_KEY="" (vacía), y load_dotenv con override=False (default)
# no la pisaría. override=True fuerza el valor real del .env.
load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

MODEL_CANDIDATES = ["claude-opus-4-7", "claude-opus-4-6"]
MAPPING = "evals/gold_layer_a_mapping.json"
OUTPUT = "evals/gold_answers_v1.yaml"
# Pasamos TEXTO COMPLETO del PDF (fitz), no páginas-imagen recortadas: recortar
# producía admit_no_info falsos (la respuesta estaba en una página no incluida —
# caso hp020 pág 49, hp006 pág 215). Cobertura total > fidelidad visual parcial.
#
# NO truncar documentos (decisión sesión 27): el truncado por doc perdía la
# sección de datos técnicos (suele ir al final del manual) — caso hp019 ASD535.
# El único límite es físico: la ventana de contexto de Opus (~200K tokens input
# ≈ 800K chars). Dejamos margen para prompt+respuesta. Si los docs de una
# pregunta exceden el tope, se priorizan los primeros (más relevantes) — no se
# trunca el texto de un doc a media sección.
MAX_CHARS_PER_DOC = 700000   # un doc entero cabe (el mayor del corpus ~500K)
MAX_CHARS_TOTAL = 700000     # ~175K tokens; margen para prompt+output en 200K

_INSTRUCTION = (
    "Eres un técnico experto en sistemas PCI (detección y extinción de "
    "incendios). Arriba tienes el TEXTO COMPLETO del/los manual(es) oficial(es) "
    "de un producto (todas las páginas, marcadas con [página N]) y abajo la "
    "pregunta de un técnico de campo.\n\n"
    "IMPORTANTE: busca en TODO el texto antes de concluir que algo no está. "
    "Si el índice menciona una sección, búscala por su número de página.\n\n"
    "Genera la RESPUESTA CANÓNICA (gold standard) basándote EXCLUSIVAMENTE en "
    "los documentos adjuntos. Esta respuesta será la referencia para evaluar al "
    "bot, así que debe ser precisa, completa y citable.\n\n"
    "Reglas:\n"
    "- Si la respuesta está en los documentos: respóndela con precisión técnica "
    "(valores, pasos, condiciones), citando manual y página.\n"
    "- Si la información NO aparece en los documentos: conducta_esperada = "
    "admit_no_info (no inventes).\n"
    "- Si la pregunta es ambigua (varios productos/variantes posibles): "
    "conducta_esperada = ask_clarification, indicando qué hay que aclarar.\n"
    "- NO uses conocimiento externo. Solo los documentos adjuntos.\n\n"
    "Pregunta del técnico:\n{question}\n\n"
    "Responde SOLO con un objeto JSON válido (sin markdown, sin ```):\n"
    "{{\n"
    '  "conducta_esperada": "answer" | "ask_clarification" | "admit_no_info",\n'
    '  "gold_answer": "respuesta canónica completa en español",\n'
    '  "citations": [{{"manual": "nombre", "page": N, "quote": "frase textual breve"}}],\n'
    '  "confidence": "alta" | "media" | "baja",\n'
    '  "notes": "observaciones para el validador humano (ambigüedades, '
    'info parcial, etc.)"\n'
    "}}"
)


def pick_model(client: Anthropic) -> str:
    for m in MODEL_CANDIDATES:
        try:
            client.messages.create(model=m, max_tokens=5,
                                    messages=[{"role": "user", "content": "ok"}])
            return m
        except Exception as e:
            print(f"  {m}: {str(e)[:140]}")
            continue
    raise RuntimeError(f"Ningún modelo Opus disponible: {MODEL_CANDIDATES}")


def pdf_full_text(pdf_path: str, max_chars: int = MAX_CHARS_PER_DOC) -> str | None:
    """Texto completo del PDF (todas las páginas, marcadas), truncado a max_chars."""
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        print(f"    no se pudo abrir {pdf_path}: {e}")
        return None
    parts = []
    for page in doc:
        txt = page.get_text().strip()
        if txt:
            parts.append(f"[página {page.number + 1}]\n{txt}")
    doc.close()
    text = "\n\n".join(parts)
    return text[:max_chars]


def collect_pdf_paths(entry: dict) -> list[str]:
    """PDFs relevantes a la pregunta (de relevant_chunks o del re-mapeo)."""
    paths: list[str] = []
    seen: set[str] = set()
    if entry["has_relevant_chunks"]:
        for s in entry["sources"]:
            for p in s["pdf_paths_found"][:1]:  # un PDF por source_file
                if p not in seen:
                    seen.add(p); paths.append(p)
    else:
        for _k, plist in entry.get("pdf_candidates", {}).items():
            for p in plist[:1]:
                if p not in seen:
                    seen.add(p); paths.append(p)
    return paths


def build_text_blocks(entry: dict) -> tuple[str, list[str]]:
    """Texto COMPLETO de los PDFs relevantes. No trunca un doc a media sección:
    incluye cada doc entero o lo salta si no cabe en el contexto restante. El
    primer doc (el más relevante) siempre entra."""
    chunks_txt: list[str] = []
    used: list[str] = []
    skipped: list[str] = []
    budget = MAX_CHARS_TOTAL
    for path in collect_pdf_paths(entry):
        txt = pdf_full_text(path, max_chars=MAX_CHARS_PER_DOC)
        if not txt:
            continue
        name = os.path.basename(path)
        if used and len(txt) > budget:   # ya hay docs y este no cabe entero
            skipped.append(name)
            continue
        chunks_txt.append(f"===== MANUAL: {name} =====\n{txt}")
        used.append(name)
        budget -= len(txt)
    if skipped:
        print(f"    (saltados por contexto, no truncados: {skipped})")
    return "\n\n".join(chunks_txt), used


def gen_gold(client: Anthropic, model: str, qid: str, entry: dict) -> dict:
    docs_text, used = build_text_blocks(entry)
    if not docs_text.strip():
        return {"qid": qid, "error": "sin PDFs utilizables", "pdfs_used": []}
    content = [
        {"type": "text",
         "text": f"<documentos>\n{docs_text}\n</documentos>"},
        {"type": "text", "text": _INSTRUCTION.format(question=entry["question"])},
    ]
    resp = client.messages.create(
        model=model, max_tokens=4000,
        messages=[{"role": "user", "content": content}],
    )
    text = resp.content[0].text.strip()
    # Parsear JSON (tolerante a fences)
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    try:
        parsed = json.loads(text)
    except Exception as e:
        parsed = {"parse_error": str(e), "raw": text[:1000]}
    parsed["qid"] = qid
    parsed["question"] = entry["question"]
    parsed["pdfs_used"] = used
    parsed["_usage"] = {"in": resp.usage.input_tokens, "out": resp.usage.output_tokens}
    return parsed


def main() -> int:
    # Windows console = cp1252; las gold answers pueden traer emojis/símbolos.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    if len(sys.argv) < 2:
        print("uso: python scripts/layer_a_build.py <hp001|all>")
        return 1
    target = sys.argv[1]

    mapping = json.loads(open(MAPPING, encoding="utf-8").read())
    if target == "all":
        ids = sorted(mapping)
    else:
        ids = [t.strip() for t in target.split(",") if t.strip()]
    # merge_mode: re-correr IDs concretos y fusionarlos al YAML existente
    merge_mode = target != "all" and len(ids) >= 1 and all(
        i in mapping for i in ids) and os.path.exists(OUTPUT)

    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    model = pick_model(client)
    print(f"Modelo: {model}\n")

    results = []
    for qid in ids:
        if qid not in mapping:
            print(f"{qid}: no está en el mapeo")
            continue
        print(f"=== {qid} ===")
        out = gen_gold(client, model, qid, mapping[qid])
        results.append(out)
        if "error" in out:
            print(f"  ERROR: {out['error']}")
            continue
        print(f"  conducta: {out.get('conducta_esperada')}  "
              f"confidence: {out.get('confidence')}")
        print(f"  PDFs: {out.get('pdfs_used')}")
        print(f"  gold_answer: {str(out.get('gold_answer'))[:400]}")
        if out.get("citations"):
            for cit in out["citations"][:4]:
                print(f"    cita: {cit.get('manual')} p{cit.get('page')} — "
                      f"\"{str(cit.get('quote'))[:80]}\"")
        if out.get("notes"):
            print(f"  notes: {out['notes'][:200]}")
        u = out.get("_usage", {})
        print(f"  tokens: {u.get('in')} in / {u.get('out')} out\n")

    # Guardar
    if target == "all":
        with open(OUTPUT, "w", encoding="utf-8") as f:
            yaml.safe_dump(results, f, allow_unicode=True, sort_keys=False)
        print(f"Guardado en {OUTPUT}")
    elif merge_mode:
        existing = yaml.safe_load(open(OUTPUT, encoding="utf-8"))
        by_id = {r["qid"]: r for r in existing}
        for r in results:
            by_id[r["qid"]] = r   # reemplaza los re-corridos
        merged = [by_id[q] for q in sorted(by_id)]
        with open(OUTPUT, "w", encoding="utf-8") as f:
            yaml.safe_dump(merged, f, allow_unicode=True, sort_keys=False)
        print(f"Merge de {[r['qid'] for r in results]} en {OUTPUT} "
              f"({len(merged)} total)")
    else:
        with open(f"evals/_layer_a_{target}.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"Mini-test guardado en evals/_layer_a_{target}.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
