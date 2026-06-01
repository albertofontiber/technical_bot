#!/usr/bin/env python3
"""Revisor adversarial CROSS-MODEL (GPT-5.5) — Protocolo 3.

Da independencia CONCEPTUAL (modelo distinto del autor, que es Claude), rompiendo el
echo-chamber del mismo-modelo (lección validator s13). Complementa al sub-agente Claude
(que lee el repo y ancla en código). Ver docs/ADVERSARIAL_REVIEWER.md.

El system prompt canónico vive en scripts/adversarial_briefing.md (fuente ÚNICA, también
citada por el sub-agente) — no se duplica aquí, para no re-divergir.

Uso:
  python scripts/adversarial_review.py <propuesta.md> [<contexto> ...] [--diff]

  El 1er fichero es la propuesta a atacar; el resto, contexto que GPT no lee del repo.
  --diff  auto-incluye `git diff HEAD` (tracked) + lista de untracked como contexto (mitiga
          el sesgo de SELECCIÓN de qué pegarle al revisor; TECH_DEBT #36). Falla-CERRADO si
          git falla, y excluye el propio log de tally para no contaminar el contexto.

Tras cada revisión escribe una entrada PARCIAL en evals/adversarial_review_log.jsonl
(coste auto-capturado: tokens/tiempo). COMPLETA a mano los campos de JUICIO
(findings/confirmed/false_pos/severity_max) tras verificar sus claims (regla C) — es la
métrica del guardarraíl anti-ritual (docs/ADVERSARIAL_REVIEWER.md §métrica).
"""
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)
MODEL = os.getenv("ADVERSARIAL_MODEL", "gpt-5.5")
BRIEFING = ROOT / "scripts" / "adversarial_briefing.md"
LOG = ROOT / "evals" / "adversarial_review_log.jsonl"
LOG_REL = "evals/adversarial_review_log.jsonl"
KNOWN_FLAGS = {"--diff"}


def _git(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=ROOT,
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )


def git_context() -> str:
    """`git diff HEAD` (tracked, excluyendo el propio log de tally) + lista de untracked (su
    contenido NO se incluye → se avisa). Falla-CERRADO si git falla: para un mecanismo
    anti-sesgo-de-selección, abortar es mejor que revisar a ciegas creyendo que se vio todo."""
    exclude = [f":(exclude){LOG_REL}"]
    diff = _git(["diff", "HEAD", "--", ".", *exclude])
    untr = _git(["ls-files", "--others", "--exclude-standard", "--", ".", *exclude])
    for label, r in (("git diff HEAD", diff), ("git ls-files", untr)):
        if r.returncode != 0:
            sys.exit(f"--diff: `{label}` falló (rc={r.returncode}): {r.stderr.strip()[:200]}")
    blocks = []
    if diff.stdout.strip():
        blocks.append("# git diff HEAD (ficheros tracked modificados)\n" + diff.stdout.strip())
    if untr.stdout.strip():
        blocks.append(
            "# ficheros NUEVOS sin commitear (untracked) — contenido NO incluido; "
            "pásalos como contexto explícito si quieres que se revisen:\n" + untr.stdout.strip()
        )
    return "\n\n".join(blocks)


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    args = sys.argv[1:]
    unknown = [a for a in args if a.startswith("--") and a not in KNOWN_FLAGS]
    if unknown:
        sys.exit(f"flag(s) no reconocido(s): {' '.join(unknown)} "
                 f"(conocidos: {', '.join(sorted(KNOWN_FLAGS))})")
    include_diff = "--diff" in args
    files = [a for a in args if not a.startswith("--")]
    if not files:
        sys.exit("uso: adversarial_review.py <propuesta> [contexto...] [--diff]")
    if not BRIEFING.is_file():
        sys.exit(f"falta el briefing canónico (¿versionado?): {BRIEFING}")
    if "OPENAI_API_KEY" not in os.environ:
        sys.exit("OPENAI_API_KEY ausente — fallback: sub-agente Claude + marcar "
                 "'cross-model omitido' (docs/ADVERSARIAL_REVIEWER.md §cross-model).")

    sys_prompt = BRIEFING.read_text(encoding="utf-8")
    parts = []
    for i, f in enumerate(files):
        p = Path(f)
        rol = "PROPUESTA A ATACAR" if i == 0 else "CONTEXTO"
        parts.append(f"===== [{rol}] {p.name} =====\n{p.read_text(encoding='utf-8')}")
    if include_diff:
        ctx = git_context()
        if ctx:
            parts.append(f"===== [CONTEXTO: cambios git] =====\n{ctx}")
        else:
            print("[--diff] aviso: sin cambios (git diff HEAD vacío y sin untracked).",
                  file=sys.stderr)

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    t0 = time.monotonic()
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": sys_prompt},
                  {"role": "user", "content": "\n\n".join(parts)}],
    )
    elapsed = time.monotonic() - t0
    print(f"--- {MODEL} (revisor adversarial cross-model) ---")
    print(resp.choices[0].message.content)

    usage = getattr(resp, "usage", None)
    entry = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "model": MODEL,
        "files": [Path(f).name for f in files],
        "diff_included": include_diff,
        "tokens": getattr(usage, "total_tokens", None),
        "elapsed_s": round(elapsed, 1),
        # Campos de JUICIO — los completo YO tras verificar sus claims (regla C):
        "findings": None,
        "confirmed": None,
        "false_pos": None,
        "severity_max": None,
        "verdict_notes": "",
    }
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"\n[tally] entrada parcial → {LOG.relative_to(ROOT)} (ts={entry['ts']}).")
    print("[tally] COMPLETA tras verificar (regla C): "
          "findings/confirmed/false_pos/severity_max.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
