#!/usr/bin/env python3
"""Revisor adversarial principal (GPT-5.6 Sol xhigh) — Protocolo 3.

Da una lente CONCEPTUAL cross-family y complementa a Fable 5, el segundo revisor
frontera, que se ejecuta de forma independiente (lee el repo y ancla en código). Ver
docs/ADVERSARIAL_REVIEWER.md.

s88 (pedido de Alberto): ACCESO AUTÓNOMO AL REPO VERSIONADO — el cross-model ya no depende
de lo que el autor le pegue (sesgo de SELECCIÓN, TECH_DEBT #36): corre un LOOP AGÉNTICO con tools
READ-ONLY (`read_file` / `grep_repo` / `list_dir`) sandboxeadas al repo versionado.
La memoria externa que vea Fable 5 solo entra mediante snapshot/contexto autorizado.
Deny-list: `.env*` (secretos),
`.git/` interno y el propio log de tally (anti-contaminación). Cap de tool-calls
(disciplina de coste); al agotarlo se fuerza la review con lo leído.

El system prompt canónico vive en scripts/adversarial_briefing.md (fuente ÚNICA, también
citado por Fable 5) — no se duplica aquí, para no re-divergir.

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
DEFAULT_MODEL = "gpt-5.6-sol"
DEFAULT_REASONING_EFFORT = "xhigh"
MODEL = os.getenv("ADVERSARIAL_MODEL", DEFAULT_MODEL)
REASONING_EFFORT = os.getenv(
    "ADVERSARIAL_REASONING_EFFORT", DEFAULT_REASONING_EFFORT
).strip().lower()
VALID_REASONING_EFFORTS = {"none", "minimal", "low", "medium", "high", "xhigh", "max"}


def primary_contract_satisfied() -> bool:
    """El rol principal exige exactamente el modelo y esfuerzo aprobados."""
    return MODEL == DEFAULT_MODEL and REASONING_EFFORT == DEFAULT_REASONING_EFFORT


class ReviewRunError(RuntimeError):
    """Fallo auditable con el coste/traza acumulados antes de abortar."""

    def __init__(self, message: str, total_tokens: int, n_calls: int,
                 files_read: list[str], tool_trace: list[dict]) -> None:
        super().__init__(message)
        self.total_tokens = total_tokens
        self.n_calls = n_calls
        self.files_read = sorted(set(files_read))
        self.tool_trace = tool_trace


def _pending_fable_review() -> dict:
    return {
        "model": "fable",
        "display_name": "Fable 5",
        "status": "pending",
        "review_id": None,
        "tokens": None,
        "elapsed_s": None,
        "findings": None,
        "confirmed": None,
        "false_pos": None,
        "severity_max": None,
    }


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
    {"type": "function",
     "name": "read_file",
     "description": "Lee un fichero del repo (relativo a la raíz), con números de línea para anclar "
                    "fichero:línea. Pagina con start_line si es largo.",
     "parameters": {"type": "object", "properties": {
         "path": {"type": "string"},
         "start_line": {"type": "integer", "default": 1},
         "max_lines": {"type": "integer", "default": READ_MAX_LINES}},
         "required": ["path"]}},
    {"type": "function",
     "name": "grep_repo",
     "description": "Busca una regex en los ficheros del repo. Devuelve fichero:línea:texto.",
     "parameters": {"type": "object", "properties": {
         "pattern": {"type": "string"},
         "glob": {"type": "string", "default": "**/*", "description": "p.ej. src/**/*.py, docs/*.md"},
         "max_hits": {"type": "integer", "default": GREP_MAX_HITS}},
         "required": ["pattern"]}},
    {"type": "function",
     "name": "list_dir",
     "description": "Lista un directorio del repo.",
     "parameters": {"type": "object", "properties": {
         "path": {"type": "string", "default": "."}}, "required": []}},
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


def _log_display_path() -> str:
    try:
        return str(LOG.relative_to(ROOT))
    except ValueError:
        return str(LOG)


def _write_preflight_failure(files: list[str], include_diff: bool, use_tools: bool,
                             reason: str) -> None:
    entry = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "run_status": "failed_preflight",
        "duo_status": "sol_omitted",
        "model": MODEL,
        "reasoning_effort": REASONING_EFFORT,
        "primary_contract_satisfied": primary_contract_satisfied(),
        "files": [Path(f).name for f in files],
        "diff_included": include_diff,
        "tools": use_tools,
        "tool_calls": 0,
        "files_read": [],
        "tool_trace": [],
        "tokens": None,
        "elapsed_s": 0.0,
        "findings": None,
        "confirmed": None,
        "false_pos": None,
        "severity_max": None,
        "verdict_notes": f"RUN_FAILED_PREFLIGHT: {reason}",
        "fable_review": _pending_fable_review(),
    }
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"[tally] omisión Sol registrada → {_log_display_path()} "
          f"(ts={entry['ts']}).", file=sys.stderr)


def run_review(client: OpenAI, sys_prompt: str, user_prompt: str, use_tools: bool):
    """Loop agéntico. Devuelve texto, tokens, calls, files_read y traza de tools."""
    input_items: list = [{"role": "user", "content": user_prompt}]
    total_tokens = 0
    n_calls = 0
    files_read: list[str] = []
    tool_trace: list[dict] = []
    while True:
        kwargs = {
            "model": MODEL,
            "instructions": sys_prompt,
            "input": input_items,
            "reasoning": {"effort": REASONING_EFFORT},
            "store": False,
        }
        if use_tools and n_calls < MAX_TOOL_CALLS:
            kwargs["tools"] = TOOLS_SPEC
        try:
            resp = client.responses.create(**kwargs)
        except Exception as exc:
            raise ReviewRunError(
                f"Responses API falló ({type(exc).__name__})",
                total_tokens, n_calls, files_read, tool_trace,
            ) from exc
        usage = getattr(resp, "usage", None)
        total_tokens += getattr(usage, "total_tokens", 0) or 0
        status = getattr(resp, "status", None)
        if status != "completed":
            incomplete = getattr(resp, "incomplete_details", None)
            raise ReviewRunError(
                f"Responses API no completó la revisión (status={status!r}, "
                f"incomplete_details={incomplete!r})",
                total_tokens, n_calls, files_read, tool_trace,
            )
        output_items = list(getattr(resp, "output", None) or [])
        tcs = [item for item in output_items
               if getattr(item, "type", None) == "function_call"]
        if not tcs:
            review_text = (getattr(resp, "output_text", "") or "").strip()
            if not review_text:
                raise ReviewRunError(
                    "Responses API completó sin texto de revisión",
                    total_tokens, n_calls, files_read, tool_trace,
                )
            return review_text, total_tokens, n_calls, sorted(set(files_read)), tool_trace
        # Responses conserva los function_call previos en el siguiente input; es necesario
        # para enlazarlos con sus function_call_output mediante call_id.
        input_items.extend(output_items)
        for tc in tcs:
            name = tc.name
            if n_calls >= MAX_TOOL_CALLS:
                out = (f"ERROR: presupuesto agotado; no se ejecutan más de "
                       f"{MAX_TOOL_CALLS} tool-calls")
                print(f"  [tool bloqueada por cap] {name}", file=sys.stderr)
            else:
                n_calls += 1
                try:
                    args = json.loads(tc.arguments or "{}")
                    if not isinstance(args, dict):
                        raise TypeError("los argumentos deben ser un objeto JSON")
                except (json.JSONDecodeError, TypeError) as exc:
                    args = None
                    out = f"ERROR: argumentos inválidos ({type(exc).__name__})"
                    tool_status = "invalid_arguments"
                else:
                    impl = TOOL_IMPL.get(name)
                    if impl is None:
                        out = f"ERROR: tool desconocida {name}"
                        tool_status = "unknown_tool"
                    else:
                        try:
                            out = impl(**args)
                            tool_status = "tool_error" if out.startswith("ERROR") else "ok"
                        except Exception as exc:
                            out = f"ERROR ejecutando {name}: {type(exc).__name__}"
                            tool_status = "execution_error"
                tool_trace.append({"name": name, "arguments": args, "status": tool_status})
                if name == "read_file" and not out.startswith("ERROR"):
                    files_read.append(str(args.get("path")))
                print(f"  [tool {n_calls}] {name}({json.dumps(args, ensure_ascii=False)[:110]})",
                      file=sys.stderr)
            input_items.append({"type": "function_call_output",
                                "call_id": tc.call_id, "output": out[:12000]})
        if n_calls >= MAX_TOOL_CALLS:
            input_items.append({"role": "user", "content":
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
    if REASONING_EFFORT not in VALID_REASONING_EFFORTS:
        reason = ("ADVERSARIAL_REASONING_EFFORT inválido: "
                  f"{REASONING_EFFORT!r}; usa {sorted(VALID_REASONING_EFFORTS)}")
        _write_preflight_failure(files, include_diff, use_tools, reason)
        print(reason, file=sys.stderr)
        return 2
    if "OPENAI_API_KEY" not in os.environ:
        reason = ("OPENAI_API_KEY ausente — fallback: Fable 5 + marcar "
                  "'revisor principal Sol omitido'")
        _write_preflight_failure(files, include_diff, use_tools, reason)
        print(reason, file=sys.stderr)
        return 1

    sys_prompt = BRIEFING.read_text(encoding="utf-8")
    parts = []
    if use_tools:
        parts.append(
            "Tienes tools READ-ONLY sobre el repo versionado (read_file / grep_repo / list_dir). "
            "La memoria externa solo está disponible si se adjunta como contexto autorizado. "
            "ÚSALAS: verifica cada claim contra el código "
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
    is_primary = primary_contract_satisfied()
    try:
        review, total_tokens, n_calls, files_read, tool_trace = run_review(
            client, sys_prompt, "\n\n".join(parts), use_tools)
    except ReviewRunError as exc:
        elapsed = time.monotonic() - t0
        entry = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "run_status": "failed",
            "duo_status": "sol_failed",
            "model": MODEL,
            "reasoning_effort": REASONING_EFFORT,
            "primary_contract_satisfied": is_primary,
            "files": [Path(f).name for f in files],
            "diff_included": include_diff,
            "tools": use_tools,
            "tool_calls": exc.n_calls,
            "files_read": exc.files_read,
            "tool_trace": exc.tool_trace,
            "tokens": exc.total_tokens or None,
            "elapsed_s": round(elapsed, 1),
            "findings": None,
            "confirmed": None,
            "false_pos": None,
            "severity_max": None,
            "verdict_notes": f"RUN_FAILED: {exc}",
            "fable_review": _pending_fable_review(),
        }
        with LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        print(f"[tally] ejecución fallida registrada → {_log_display_path()} "
              f"(ts={entry['ts']}).", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1
    elapsed = time.monotonic() - t0
    role = "revisor adversarial principal" if is_primary else "override no-principal"
    print(f"--- {MODEL} · reasoning={REASONING_EFFORT} "
          f"({role}; tools={'ON' if use_tools else 'off'}, "
          f"{n_calls} tool-calls) ---")
    print(review)

    entry = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "run_status": "completed",
        "duo_status": "pending_fable",
        "model": MODEL,
        "reasoning_effort": REASONING_EFFORT,
        "primary_contract_satisfied": is_primary,
        "files": [Path(f).name for f in files],
        "diff_included": include_diff,
        "tools": use_tools,
        "tool_calls": n_calls,
        "files_read": files_read,
        "tool_trace": tool_trace,
        "tokens": total_tokens or None,
        "elapsed_s": round(elapsed, 1),
        # Campos de JUICIO — los completo YO tras verificar sus claims (regla C):
        "findings": None,
        "confirmed": None,
        "false_pos": None,
        "severity_max": None,
        "verdict_notes": "",
        "fable_review": _pending_fable_review(),
    }
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"\n[tally] entrada parcial → {_log_display_path()} (ts={entry['ts']}).")
    print("[tally] COMPLETA tras verificar (regla C): "
          "findings/confirmed/false_pos/severity_max + recibo Fable 5; "
          "hasta entonces duo_status=pending_fable.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
