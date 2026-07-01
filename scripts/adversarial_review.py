#!/usr/bin/env python3
"""Revisor adversarial CROSS-MODEL (GPT-5.5) — Protocolo 3.

Da independencia CONCEPTUAL (modelo distinto del autor, que es Claude), rompiendo el
echo-chamber del mismo-modelo (lección validator s13). Complementa al sub-agente Claude
(que lee el repo y ancla en código). Ver docs/ADVERSARIAL_REVIEWER.md.

s88 (pedido de Alberto): PARIDAD DE INFORMACIÓN — el cross-model ya no depende de lo que el
autor le pegue (sesgo de SELECCIÓN, TECH_DEBT #36): corre un LOOP AGÉNTICO con tools
READ-ONLY (`read_file` / `grep_repo` / `list_dir`) sandboxeadas al repo, la misma
información que el sub-agente Claude (Read/Grep/Glob). Deny-list: `.env*` (secretos),
`.git/` interno y el propio log de tally (anti-contaminación). Cap de tool-calls
(disciplina de coste); al agotarlo se fuerza la review con lo leído.

El system prompt canónico vive en scripts/adversarial_briefing.md (fuente ÚNICA, también
citada por el sub-agente) — no se duplica aquí, para no re-divergir.

Uso:
  python scripts/adversarial_review.py <propuesta.md> [<contexto> ...] [--diff] [--no-tools]

  El 1er fichero es la propuesta a atacar; el resto, contexto adicional. --no-tools
  restaura el modo legacy (solo ficheros pegados) como escape.
  --diff  auto-incluye `git diff HEAD` (tracked) + lista de untracked como contexto (mitiga
          el sesgo de SELECCIÓN de qué pegarle al revisor; TECH_DEBT #36). Falla-CERRADO si
          git falla, y excluye el propio log de tally para no contaminar el contexto.

Tras cada revisión escribe una entrada PARCIAL en evals/adversarial_review_log.jsonl
(coste auto-capturado: tokens/tiempo/tool-calls/ficheros leídos). COMPLETA a mano los
campos de JUICIO (findings/confirmed/false_pos/severity_max) tras verificar sus claims
(regla C) — es la métrica del guardarraíl anti-ritual (docs/ADVERSARIAL_REVIEWER.md §métrica).
"""
import fnmatch
import json
import os
import re
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
KNOWN_FLAGS = {"--diff", "--no-tools"}

# ─────────────────────────── tools read-only (paridad con el sub-agente, s88) ───────────────────────────
MAX_TOOL_CALLS = 30          # cap total (disciplina de coste); al agotar → review con lo leído
READ_MAX_LINES = 250         # por llamada (paginable con start_line)
GREP_MAX_HITS = 50
FILE_SIZE_CAP = 2_000_000    # skip binarios/monstruos en grep
DENY_BASENAMES = {".env", ".env.local", ".env.production"}
SKIP_DIRS = {".git", "__pycache__", "node_modules", ".claude", ".venv", "venv"}
BINARY_EXT = {".pdf", ".png", ".jpg", ".jpeg", ".xlsx", ".pyc", ".zip", ".gz", ".db", ".sqlite"}


def _deny(p: Path) -> str | None:
    """None si permitido; si no, el motivo. Sandbox bajo ROOT + secretos + tally."""
    try:
        rp = p.resolve()
        rp.relative_to(ROOT)
    except Exception:
        return "fuera del repo (sandbox)"
    if rp.name in DENY_BASENAMES or rp.name.startswith(".env"):
        return "denegado: secretos (.env*)"
    rel = rp.relative_to(ROOT).as_posix()
    if rel == LOG_REL:
        return "denegado: el log de tally (anti-contaminación)"
    if any(part in SKIP_DIRS for part in rp.relative_to(ROOT).parts[:-1]):
        return "denegado: directorio interno"
    return None


def tool_read_file(path: str, start_line: int = 1, max_lines: int = READ_MAX_LINES) -> str:
    p = ROOT / path
    why = _deny(p)
    if why:
        return f"ERROR: {why}"
    if not p.is_file():
        return f"ERROR: no existe: {path}"
    try:
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception as e:
        return f"ERROR leyendo {path}: {type(e).__name__}"
    start = max(1, int(start_line))
    chunk = lines[start - 1:start - 1 + min(int(max_lines), READ_MAX_LINES)]
    body = "\n".join(f"{start + i}\t{l}" for i, l in enumerate(chunk))
    more = f"\n... ({len(lines)} líneas en total; sigue con start_line={start + len(chunk)})" \
        if start - 1 + len(chunk) < len(lines) else ""
    return f"[{path} · líneas {start}-{start + len(chunk) - 1} de {len(lines)}]\n{body}{more}"


def tool_grep_repo(pattern: str, glob: str = "**/*", max_hits: int = GREP_MAX_HITS) -> str:
    try:
        rx = re.compile(pattern)
    except re.error as e:
        return f"ERROR: regex inválida: {e}"
    hits, scanned = [], 0
    for p in sorted(ROOT.glob(glob)):
        if not p.is_file() or _deny(p) or p.suffix.lower() in BINARY_EXT:
            continue
        try:
            if p.stat().st_size > FILE_SIZE_CAP:
                continue
            text = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        scanned += 1
        for n, line in enumerate(text.splitlines(), 1):
            if rx.search(line):
                hits.append(f"{p.relative_to(ROOT).as_posix()}:{n}: {line.strip()[:200]}")
                if len(hits) >= min(int(max_hits), GREP_MAX_HITS):
                    return "\n".join(hits) + f"\n... (cap {max_hits} hits; afina pattern/glob)"
    return "\n".join(hits) if hits else f"0 hits ({scanned} ficheros escaneados; glob={glob})"


def tool_list_dir(path: str = ".") -> str:
    p = ROOT / path
    why = _deny(p)
    if why:
        return f"ERROR: {why}"
    if not p.is_dir():
        return f"ERROR: no es directorio: {path}"
    rows = []
    for child in sorted(p.iterdir()):
        if child.name in SKIP_DIRS or child.name.startswith(".env"):
            continue
        tag = "/" if child.is_dir() else f" ({child.stat().st_size:,}B)"
        rows.append(f"  {child.name}{tag}")
    return f"[{path}]\n" + "\n".join(rows[:200])


TOOLS_SPEC = [
    {"type": "function", "function": {
        "name": "read_file",
        "description": "Lee un fichero del repo (relativo a la raíz), con números de línea para anclar "
                       "fichero:línea. Pagina con start_line si es largo.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"},
            "start_line": {"type": "integer", "default": 1},
            "max_lines": {"type": "integer", "default": READ_MAX_LINES}},
            "required": ["path"]}}},
    {"type": "function", "function": {
        "name": "grep_repo",
        "description": "Busca una regex en los ficheros del repo. Devuelve fichero:línea:texto.",
        "parameters": {"type": "object", "properties": {
            "pattern": {"type": "string"},
            "glob": {"type": "string", "default": "**/*", "description": "p.ej. src/**/*.py, docs/*.md"},
            "max_hits": {"type": "integer", "default": GREP_MAX_HITS}},
            "required": ["pattern"]}}},
    {"type": "function", "function": {
        "name": "list_dir",
        "description": "Lista un directorio del repo.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string", "default": "."}}, "required": []}}},
]
TOOL_IMPL = {"read_file": tool_read_file, "grep_repo": tool_grep_repo, "list_dir": tool_list_dir}


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
            "léelos con read_file si son relevantes:\n" + untr.stdout.strip()
        )
    return "\n\n".join(blocks)


def run_review(client: OpenAI, sys_prompt: str, user_prompt: str, use_tools: bool):
    """Loop agéntico (tools ON) o single-shot (legacy). Devuelve (texto, total_tokens, n_calls, files_read)."""
    messages = [{"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt}]
    total_tokens = 0
    n_calls = 0
    files_read: list[str] = []
    while True:
        kwargs = {"model": MODEL, "messages": messages}
        if use_tools and n_calls < MAX_TOOL_CALLS:
            kwargs["tools"] = TOOLS_SPEC
        resp = client.chat.completions.create(**kwargs)
        usage = getattr(resp, "usage", None)
        total_tokens += getattr(usage, "total_tokens", 0) or 0
        msg = resp.choices[0].message
        tcs = getattr(msg, "tool_calls", None)
        if not tcs:
            return (msg.content or "").strip(), total_tokens, n_calls, sorted(set(files_read))
        messages.append({"role": "assistant", "content": msg.content,
                         "tool_calls": [tc.model_dump() for tc in tcs]})
        for tc in tcs:
            n_calls += 1
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            impl = TOOL_IMPL.get(name)
            out = impl(**args) if impl else f"ERROR: tool desconocida {name}"
            if name == "read_file" and not out.startswith("ERROR"):
                files_read.append(str(args.get("path")))
            print(f"  [tool {n_calls}] {name}({json.dumps(args, ensure_ascii=False)[:110]})",
                  file=sys.stderr)
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": out[:12000]})
        if n_calls >= MAX_TOOL_CALLS:
            messages.append({"role": "user", "content":
                             f"Presupuesto de lectura agotado ({MAX_TOOL_CALLS} tool-calls). "
                             "Emite AHORA tu review final con lo leído, en el formato del briefing."})


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
    use_tools = "--no-tools" not in args
    files = [a for a in args if not a.startswith("--")]
    if not files:
        sys.exit("uso: adversarial_review.py <propuesta> [contexto...] [--diff] [--no-tools]")
    if not BRIEFING.is_file():
        sys.exit(f"falta el briefing canónico (¿versionado?): {BRIEFING}")
    if "OPENAI_API_KEY" not in os.environ:
        sys.exit("OPENAI_API_KEY ausente — fallback: sub-agente Claude + marcar "
                 "'cross-model omitido' (docs/ADVERSARIAL_REVIEWER.md §cross-model).")

    sys_prompt = BRIEFING.read_text(encoding="utf-8")
    parts = []
    if use_tools:
        parts.append(
            "Tienes tools READ-ONLY sobre el repo (read_file / grep_repo / list_dir) — la MISMA "
            "información que el sub-agente Claude. ÚSALAS: verifica cada claim contra el código "
            "ANTES de afirmarla y ancla fichero:línea. Los ficheros de abajo son el punto de "
            f"partida, no el límite. Presupuesto: {MAX_TOOL_CALLS} tool-calls."
        )
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
    review, total_tokens, n_calls, files_read = run_review(
        client, sys_prompt, "\n\n".join(parts), use_tools)
    elapsed = time.monotonic() - t0
    print(f"--- {MODEL} (revisor adversarial cross-model; tools={'ON' if use_tools else 'off'}, "
          f"{n_calls} tool-calls) ---")
    print(review)

    entry = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "model": MODEL,
        "files": [Path(f).name for f in files],
        "diff_included": include_diff,
        "tools": use_tools,
        "tool_calls": n_calls,
        "files_read": files_read,
        "tokens": total_tokens or None,
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
