#!/usr/bin/env python3
"""cross_generate.py — C2: co-generador GPT-5.5 de golds (mitiga circularidad).

CATALOG_PLAN §2-C (DEC-008): el autor primario es Claude (= linaje del bot, Sonnet);
GPT-5.5 (linaje distinto) co-genera un candidato INDEPENDIENTE desde la MISMA fuente
confirmada por C4 (locate_fact.py), para no compartir el punto ciego del autor. NO
sustituye el sign-off humano (único corte fuerte); reduce la circularidad Sonnet↔Sonnet.

Lee la FUENTE — texto extraído + RENDER multimodal de las páginas que C4 confirmó — NO
chunks_v2 (no circular con el sustrato Voyage del bot). Las tablas/figuras se leen de la
IMAGEN (el texto extraído de tablas suele venir corrupto). Emite un candidato:
  {question, conducta_esperada, gold_answer, atomic_facts:[{texto,tipo,estado,valor,cita}]}.

Uso:
  python scripts/cross_generate.py --product "Notifier PEARL" \\
     --topic "direccionamiento de detectores en un lazo" \\
     --pages "997-669-005-3_Instal-Comm_ES:21,22 997-671-005-3_Configuration_ES:43"
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
from pathlib import Path

import fitz
from dotenv import load_dotenv
from openai import OpenAI

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)
MODEL = os.getenv("CROSS_GENERATE_MODEL", os.getenv("CROSS_VERIFY_MODEL", "gpt-5.5"))
_PRIV = ("_Privado", "_privado")


def _resolve(sf: str) -> Path | None:
    stem = sf[:-4] if sf.lower().endswith(".pdf") else sf
    m = list(ROOT.rglob(f"{stem}.pdf")) + list(ROOT.rglob(f"{stem}.PDF"))
    if not m:
        return None
    npriv = [p for p in m if not any(x in str(p) for x in _PRIV)]
    return sorted(npriv or m, key=lambda p: len(str(p)))[0]


def _text_and_png(path: Path, page: int, dpi: int = 200) -> tuple[str, Path | None]:
    doc = fitz.open(path)
    if not (1 <= page <= doc.page_count):
        doc.close()
        return "", None
    pg = doc.load_page(page - 1)
    txt = pg.get_text()
    out = ROOT / "logs" / "c4_render"
    out.mkdir(parents=True, exist_ok=True)
    png = out / f"{path.stem[:40]}_p{page}_{dpi}dpi.png"
    pg.get_pixmap(dpi=dpi).save(png)
    doc.close()
    return txt, png


def parse_pages(spec: str) -> list[tuple[str, int]]:
    """'SF:1,2;SF2:3' -> [(SF,1),(SF,2),(SF2,3)]. Manuales separados por ';' (los
    nombres de fichero pueden tener espacios, p.ej. FAAST); fallback a espacios si no hay ';'."""
    out: list[tuple[str, int]] = []
    entries = spec.split(";") if ";" in spec else spec.split()
    for tok in entries:
        tok = tok.strip()
        if not tok:
            continue
        sf, pgs = tok.rsplit(":", 1)
        for p in pgs.split(","):
            out.append((sf.strip(), int(p)))
    return out


PROMPT = """Eres un AUTOR INDEPENDIENTE de golds para un eval de un bot RAG de protección
contra incendios (PCI). Tu linaje es DISTINTO al del bot, así que no compartes su sesgo.

A partir EXCLUSIVAMENTE de los extractos de manual de abajo (texto extraído + imágenes
renderizadas de las páginas), genera UN gold de tipo "answer" sobre el tema:
  «{topic}»   (producto: {product})

Reglas:
- La PREGUNTA debe ser realista (la haría un técnico de PCI instalando/manteniendo el
  equipo), en español, y debe quedar COMPLETAMENTE respondida por los extractos. No
  inventes nada que no esté en ellos.
- Lee las TABLAS y figuras desde las IMÁGENES (el texto extraído de tablas suele venir mal).
- Cada hecho atómico lleva `valor` = el IDENTIFICADOR DISTINTIVO del hecho (número/código/
  unidad concretos), NO una etiqueta compartida. `tipo`: "core" (imprescindible para
  responder) | "supplementary". `estado`: "presente". `cita`: manual + página (p.ej. "MANUAL pX").
- Si la fuente NO basta para una respuesta plena, dilo en un campo "nota" y no rellenes.

Devuelve SOLO un objeto JSON válido con esta forma:
{{"question": "...",
  "conducta_esperada": "answer",
  "gold_answer": "...(prosa para técnico, en español)...",
  "atomic_facts": [{{"texto": "...", "tipo": "core", "estado": "presente", "valor": "...", "cita": "MANUAL pX"}}],
  "nota": ""}}"""


def _parse_json(raw: str) -> dict | None:
    s = raw.strip()
    if s.startswith("```"):
        s = re.sub(r"^```[a-z]*\n?|\n?```$", "", s).strip()
    try:
        return json.loads(s)
    except Exception:
        m = re.search(r"\{.*\}", s, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return None
        return None


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--product", required=True)
    ap.add_argument("--topic", required=True)
    ap.add_argument("--pages", required=True, help='"SF:1,2 SF2:3" (páginas confirmadas por C4)')
    ap.add_argument("--dpi", type=int, default=200)
    ap.add_argument("--out", help="escribe el candidato JSON aquí")
    args = ap.parse_args()

    content: list[dict] = [
        {"type": "text", "text": PROMPT.format(topic=args.topic, product=args.product)},
    ]
    excerpts: list[str] = []
    for sf, pg in parse_pages(args.pages):
        path = _resolve(sf)
        if not path:
            print(f"AVISO: PDF no resuelto: {sf}", file=sys.stderr)
            continue
        txt, png = _text_and_png(path, pg, args.dpi)
        excerpts.append(f"===== {sf} p{pg} (texto extraído) =====\n{txt}")
        if png:
            b64 = base64.b64encode(png.read_bytes()).decode()
            content.append({"type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{b64}"}})
    content.append({"type": "text", "text": "\n\n".join(excerpts)})

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    resp = client.chat.completions.create(
        model=MODEL, messages=[{"role": "user", "content": content}],
    )
    raw = resp.choices[0].message.content or ""
    print(f"--- {MODEL} (co-generador) ---")
    print(raw)
    parsed = _parse_json(raw)
    if args.out and parsed is not None:
        Path(args.out).write_text(json.dumps(parsed, ensure_ascii=False, indent=2),
                                  encoding="utf-8")
        print(f"\n→ {args.out}", file=sys.stderr)
    elif parsed is None:
        print("\n[AVISO] no se pudo parsear JSON del candidato (revisar salida cruda).",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
