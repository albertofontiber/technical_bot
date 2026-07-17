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
  python scripts/adversarial_review.py <propuesta.md> [<contexto> ...] [--no-tools]

  El 1er fichero es la propuesta a atacar; el resto, contexto adicional. --no-tools
  restaura el modo legacy (solo ficheros pegados) como escape.
  Un manifiesto de cambios contra HEAD se deriva siempre del mismo snapshot inmutable
  que alimenta prompt y tools; sustituye al antiguo `--diff` sin crear contexto no
  emparejable con Fable.

Tras cada revisión escribe una entrada PARCIAL en evals/adversarial_review_log.jsonl
(coste auto-capturado: tokens/tiempo/tool-calls/ficheros leídos). COMPLETA a mano los
campos de JUICIO (findings/confirmed/false_pos/severity_max) tras verificar sus claims
(regla C) — es la métrica del guardarraíl anti-ritual (docs/ADVERSARIAL_REVIEWER.md §métrica).
"""
import hashlib
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
                 files_read: list[str], tool_trace: list[dict],
                 provider_trace: list[dict] | None = None) -> None:
        super().__init__(message)
        self.total_tokens = total_tokens
        self.n_calls = n_calls
        self.files_read = sorted(set(files_read))
        self.tool_trace = tool_trace
        self.provider_trace = list(provider_trace or [])


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


def review_subject_identity(files: list[str], snapshot: dict | None = None) -> dict:
    """Bind a duo review to the exact, path-addressed input bytes.

    Sol and Fable run independently, but they must review the same frozen seed
    material.  This identity lets the Fable runner fail closed if any input was
    edited, renamed or reordered between the two executions.
    """
    frozen = snapshot or capture_review_snapshot()
    repo_manifest = [
        {"path": relative, "sha256": hashlib.sha256(data).hexdigest()}
        for relative, data in sorted(frozen["files"].items())
    ]
    repo_canonical = json.dumps(
        repo_manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")

    ordered_files = []
    for filename in files:
        path = Path(filename).resolve()
        relative = path.relative_to(ROOT.resolve()).as_posix()
        denied = _static_deny_rel(relative)
        if denied:
            raise ValueError(f"input {relative!r} {denied}")
        if relative not in frozen["files"]:
            raise ValueError(f"input {relative!r} ausente del snapshot")
        data = frozen["files"][relative]
        model_text = data.decode("utf-8")
        ordered_files.append(
            {
                "path": relative,
                "sha256": hashlib.sha256(data).hexdigest(),
                "model_text_sha256": hashlib.sha256(
                    model_text.encode("utf-8")
                ).hexdigest(),
                "encoding": "utf-8-strict",
            }
        )
    briefing_relative = BRIEFING.relative_to(ROOT).as_posix()
    briefing_bytes = frozen["files"].get(briefing_relative)
    if briefing_bytes is None:
        raise ValueError("briefing canónico ausente del snapshot")
    change_canonical = json.dumps(
        frozen["change_manifest"],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    subject = {
        "schema": "adversarial_duo_subject_v1",
        "ordered_files": ordered_files,
        "seed_delivery": "full_bytes",
        "repo_visibility": "immutable_git_visible_snapshot",
        "repo_head": frozen["head"],
        "repo_view_sha256": hashlib.sha256(repo_canonical).hexdigest(),
        "repo_view_file_count": len(repo_manifest),
        "change_manifest_sha256": hashlib.sha256(change_canonical).hexdigest(),
        "change_manifest_count": len(frozen["change_manifest"]),
        "briefing_sha256": hashlib.sha256(briefing_bytes).hexdigest(),
    }
    canonical = json.dumps(
        subject, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return {
        "review_subject_schema": subject["schema"],
        "review_subject_sha256": hashlib.sha256(canonical).hexdigest(),
        "review_subject_files": ordered_files,
        "review_seed_delivery": subject["seed_delivery"],
        "review_repo_visibility": subject["repo_visibility"],
        "review_repo_head": subject["repo_head"],
        "review_repo_view_sha256": subject["repo_view_sha256"],
        "review_repo_view_file_count": subject["repo_view_file_count"],
        "review_change_manifest_sha256": subject["change_manifest_sha256"],
        "review_change_manifest_count": subject["change_manifest_count"],
        "review_change_manifest": frozen["change_manifest"],
        "review_briefing_sha256": subject["briefing_sha256"],
    }


REVIEW_SUBJECT_DETAIL_KEYS = (
    "review_subject_schema",
    "review_subject_files",
    "review_seed_delivery",
    "review_repo_visibility",
    "review_repo_head",
    "review_repo_view_sha256",
    "review_repo_view_file_count",
    "review_change_manifest_sha256",
    "review_change_manifest_count",
    "review_change_manifest",
    "review_briefing_sha256",
)


def recompute_review_subject_sha256(record: dict) -> str:
    change_manifest = record.get("review_change_manifest")
    change_canonical = json.dumps(
        change_manifest,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    if hashlib.sha256(change_canonical).hexdigest() != record.get(
        "review_change_manifest_sha256"
    ):
        raise ValueError("review_change_manifest_sha256 no coincide con sus detalles")
    if len(change_manifest or []) != record.get("review_change_manifest_count"):
        raise ValueError("review_change_manifest_count no coincide con sus detalles")
    subject = {
        "schema": record.get("review_subject_schema"),
        "ordered_files": record.get("review_subject_files"),
        "seed_delivery": record.get("review_seed_delivery"),
        "repo_visibility": record.get("review_repo_visibility"),
        "repo_head": record.get("review_repo_head"),
        "repo_view_sha256": record.get("review_repo_view_sha256"),
        "repo_view_file_count": record.get("review_repo_view_file_count"),
        "change_manifest_sha256": record.get("review_change_manifest_sha256"),
        "change_manifest_count": record.get("review_change_manifest_count"),
        "briefing_sha256": record.get("review_briefing_sha256"),
    }
    canonical = json.dumps(
        subject, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


BRIEFING = ROOT / "scripts" / "adversarial_briefing.md"
LOG = ROOT / "evals" / "adversarial_review_log.jsonl"
LOG_REL = "evals/adversarial_review_log.jsonl"
KNOWN_FLAGS = {"--no-tools"}

# ─────────────────────────── tools read-only (paridad con el sub-agente, s88) ───────────────────────────
MAX_TOOL_CALLS = 30          # cap total (disciplina de coste); al agotar → review con lo leído
READ_MAX_LINES = 250         # por llamada (paginable con start_line)
GREP_MAX_HITS = 50
FILE_SIZE_CAP = 2_000_000    # skip binarios/monstruos en grep
DENY_BASENAMES = {".env", ".env.local", ".env.production"}
SKIP_DIRS = {".git", "__pycache__", "node_modules", ".claude", ".venv", "venv"}
BINARY_EXT = {".pdf", ".png", ".jpg", ".jpeg", ".xlsx", ".pyc", ".zip", ".gz", ".db", ".sqlite"}
_VISIBLE_FILES_CACHE: set[str] | None = None
_ACTIVE_REVIEW_SNAPSHOT: dict | None = None


def _is_prior_review_output(rel: str) -> bool:
    lower = rel.lower()
    name = Path(lower).name
    return (
        lower == "evals/adversarial_reviews"
        or lower.startswith("evals/adversarial_reviews/")
        or (
            lower.startswith("evals/")
            and "review" in name
            and (
                "sol" in name
                or "gpt" in name
                or "fable" in name
                or "adversarial" in name
            )
        )
    )


def _static_deny_rel(rel: str) -> str | None:
    path = Path(rel)
    if path.name in DENY_BASENAMES or path.name.startswith(".env"):
        return "denegado: secretos (.env*)"
    if rel == LOG_REL:
        return "denegado: el log de tally (anti-contaminación)"
    if _is_prior_review_output(rel):
        return "denegado: salida previa de revisor (independencia)"
    if any(part in SKIP_DIRS for part in path.parts[:-1]):
        return "denegado: directorio interno"
    return None


def _git_visible_files(*, refresh: bool = False) -> set[str]:
    """Files exposed to model tools: tracked plus unignored untracked files."""
    global _VISIBLE_FILES_CACHE
    if _VISIBLE_FILES_CACHE is not None and not refresh:
        return set(_VISIBLE_FILES_CACHE)
    result = subprocess.run(
        ["git", "ls-files", "-co", "--exclude-standard", "-z"],
        cwd=ROOT,
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError("git ls-files falló al congelar la vista del revisor")
    _VISIBLE_FILES_CACHE = {
        item.decode("utf-8", errors="surrogateescape").replace("\\", "/")
        for item in result.stdout.split(b"\0")
        if item
    }
    return set(_VISIBLE_FILES_CACHE)


def _git_head_and_changes() -> tuple[str, list[dict[str, str]]]:
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    diff = subprocess.run(
        ["git", "diff", "--name-status", "-z", "HEAD"],
        cwd=ROOT,
        capture_output=True,
    )
    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard", "-z"],
        cwd=ROOT,
        capture_output=True,
    )
    if head.returncode != 0 or diff.returncode != 0 or untracked.returncode != 0:
        raise RuntimeError("Git falló al capturar HEAD/cambios para el snapshot")

    def decode(raw: bytes) -> str:
        return raw.decode("utf-8", errors="surrogateescape").replace("\\", "/")

    fields = [item for item in diff.stdout.split(b"\0") if item]
    changes: list[dict[str, str]] = []
    index = 0
    while index < len(fields):
        status_code = decode(fields[index])
        index += 1
        old_path = decode(fields[index])
        index += 1
        if status_code.startswith(("R", "C")):
            new_path = decode(fields[index])
            index += 1
            if not _static_deny_rel(old_path) and not _static_deny_rel(new_path):
                changes.append(
                    {"status": status_code, "path": new_path, "from_path": old_path}
                )
        elif not _static_deny_rel(old_path):
            changes.append({"status": status_code, "path": old_path})
    for raw_path in untracked.stdout.split(b"\0"):
        if not raw_path:
            continue
        path = decode(raw_path)
        if not _static_deny_rel(path):
            changes.append({"status": "untracked", "path": path})
    return head.stdout.strip(), sorted(changes, key=lambda item: (item["path"], item["status"]))


def capture_review_snapshot() -> dict:
    """Capture the sole byte source for subject, prompts and model tools."""
    def read_visible(visible: set[str]) -> dict[str, bytes]:
        captured: dict[str, bytes] = {}
        for relative in sorted(visible):
            if _static_deny_rel(relative):
                continue
            path = ROOT / relative
            if path.is_symlink():
                raise RuntimeError(
                    "Git expone un enlace simbólico no admitido por el snapshot: "
                    f"{relative}"
                )
            try:
                path.resolve().relative_to(ROOT.resolve())
            except ValueError as exc:
                raise RuntimeError(
                    f"Git expone un path fuera de ROOT: {relative}"
                ) from exc
            if path.is_file():
                captured[relative] = path.read_bytes()
        return captured

    visible_before = _git_visible_files(refresh=True)
    head_before, changes_before = _git_head_and_changes()
    files = read_visible(visible_before)
    verification_files = read_visible(visible_before)
    head_after, changes_after = _git_head_and_changes()
    visible_after = _git_visible_files(refresh=True)
    if (
        visible_before != visible_after
        or head_before != head_after
        or changes_before != changes_after
        or files != verification_files
    ):
        raise RuntimeError(
            "el worktree cambió durante la captura; reintenta con una vista estable"
        )
    return {
        "schema": "adversarial_repo_snapshot_v1",
        "head": head_before,
        "files": files,
        "change_manifest": changes_before,
    }


def activate_review_snapshot(snapshot: dict | None) -> None:
    global _ACTIVE_REVIEW_SNAPSHOT
    _ACTIVE_REVIEW_SNAPSHOT = snapshot


def snapshot_file_text(path: Path, snapshot: dict | None = None) -> str:
    active = snapshot or _ACTIVE_REVIEW_SNAPSHOT
    if active is None:
        return path.read_bytes().decode("utf-8")
    relative = path.resolve().relative_to(ROOT.resolve()).as_posix()
    try:
        data = active["files"][relative]
    except KeyError as exc:
        raise ValueError(f"{relative!r} no pertenece al snapshot del revisor") from exc
    return data.decode("utf-8")


def snapshot_change_context(snapshot: dict) -> str:
    rows = snapshot["change_manifest"]
    if not rows:
        return "# snapshot change manifest\n(clean against HEAD)"
    body = "\n".join(f"{item['status']}\t{item['path']}" for item in rows)
    return "# snapshot change manifest (content available through read_file)\n" + body


def _deny(p: Path) -> str | None:
    """None si permitido; si no, el motivo. Sandbox bajo ROOT + secretos + tally."""
    try:
        rp = p.resolve()
        rp.relative_to(ROOT)
    except Exception:
        return "fuera del repo (sandbox)"
    rel = rp.relative_to(ROOT).as_posix()
    static_reason = _static_deny_rel(rel)
    if static_reason:
        return static_reason
    if _ACTIVE_REVIEW_SNAPSHOT is not None:
        files = _ACTIVE_REVIEW_SNAPSHOT["files"]
        if rel == "." or rel in files:
            return None
        prefix = rel.rstrip("/") + "/"
        if any(item.startswith(prefix) for item in files):
            return None
        return "denegado: path ausente del snapshot congelado"
    if rp.is_file():
        try:
            visible = _git_visible_files()
        except RuntimeError as exc:
            return f"denegado: {exc}"
        if rel not in visible:
            return "denegado: fichero ignorado/no visible por Git"
    elif rp.is_dir() and rel != ".":
        try:
            visible = _git_visible_files()
        except RuntimeError as exc:
            return f"denegado: {exc}"
        prefix = rel.rstrip("/") + "/"
        if not any(item.startswith(prefix) for item in visible):
            return "denegado: directorio sin ficheros visibles por Git"
    return None


def tool_read_file(path: str, start_line: int = 1, max_lines: int = READ_MAX_LINES) -> str:
    p = ROOT / path
    why = _deny(p)
    if why:
        return f"ERROR: {why}"
    try:
        if _ACTIVE_REVIEW_SNAPSHOT is not None:
            rel = p.resolve().relative_to(ROOT.resolve()).as_posix()
            data = _ACTIVE_REVIEW_SNAPSHOT["files"].get(rel)
            if data is None:
                return f"ERROR: no existe en snapshot: {path}"
            lines = data.decode("utf-8", errors="replace").splitlines()
        else:
            if not p.is_file():
                return f"ERROR: no existe: {path}"
            lines = p.read_bytes().decode("utf-8", errors="replace").splitlines()
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
    if _ACTIVE_REVIEW_SNAPSHOT is not None:
        candidates = [
            (ROOT / rel, data)
            for rel, data in sorted(_ACTIVE_REVIEW_SNAPSHOT["files"].items())
            if glob == "**/*" or Path(rel).match(glob)
        ]
    else:
        candidates = [(p, None) for p in sorted(ROOT.glob(glob))]
    for p, snapshot_data in candidates:
        if _deny(p) or p.suffix.lower() in BINARY_EXT:
            continue
        try:
            if snapshot_data is None:
                if not p.is_file() or p.stat().st_size > FILE_SIZE_CAP:
                    continue
                data = p.read_bytes()
            else:
                data = snapshot_data
                if len(data) > FILE_SIZE_CAP:
                    continue
            text = data.decode("utf-8", errors="replace")
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
    if _ACTIVE_REVIEW_SNAPSHOT is not None:
        rel_dir = p.resolve().relative_to(ROOT.resolve()).as_posix()
        prefix = "" if rel_dir == "." else rel_dir.rstrip("/") + "/"
        children: dict[str, tuple[bool, int]] = {}
        for relative, data in _ACTIVE_REVIEW_SNAPSHOT["files"].items():
            if not relative.startswith(prefix):
                continue
            remainder = relative[len(prefix):]
            if not remainder:
                continue
            name, separator, _tail = remainder.partition("/")
            is_dir = bool(separator)
            previous = children.get(name)
            children[name] = (is_dir or bool(previous and previous[0]), len(data))
        if not children and rel_dir != ".":
            return f"ERROR: no es directorio en snapshot: {path}"
        rows = [
            f"  {name}{'/' if is_dir else f' ({size:,}B)'}"
            for name, (is_dir, size) in sorted(children.items())
        ]
        return f"[{path}]\n" + "\n".join(rows[:200])
    if not p.is_dir():
        return f"ERROR: no es directorio: {path}"
    rows = []
    for child in sorted(p.iterdir()):
        if child.name in SKIP_DIRS or child.name.startswith(".env") or _deny(child):
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


def _log_display_path() -> str:
    try:
        return str(LOG.relative_to(ROOT))
    except ValueError:
        return str(LOG)


def _write_preflight_failure(files: list[str], include_diff: bool, use_tools: bool,
                             reason: str, subject: dict | None = None) -> None:
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
        **(subject or {}),
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
    provider_trace: list[dict] = []
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
                total_tokens, n_calls, files_read, tool_trace, provider_trace,
            ) from exc
        if hasattr(resp, "model_dump"):
            provider_trace.append(resp.model_dump(mode="json", exclude_none=False))
        else:
            provider_trace.append(
                {
                    "id": getattr(resp, "id", None),
                    "model": getattr(resp, "model", None),
                    "status": getattr(resp, "status", None),
                    "output_text": getattr(resp, "output_text", None),
                }
            )
        response_model = getattr(resp, "model", None)
        if response_model != MODEL:
            raise ReviewRunError(
                f"Responses API devolvió model={response_model!r}; se esperaba {MODEL!r}",
                total_tokens, n_calls, files_read, tool_trace, provider_trace,
            )
        usage = getattr(resp, "usage", None)
        total_tokens += getattr(usage, "total_tokens", 0) or 0
        status = getattr(resp, "status", None)
        if status != "completed":
            incomplete = getattr(resp, "incomplete_details", None)
            raise ReviewRunError(
                f"Responses API no completó la revisión (status={status!r}, "
                f"incomplete_details={incomplete!r})",
                total_tokens, n_calls, files_read, tool_trace, provider_trace,
            )
        output_items = list(getattr(resp, "output", None) or [])
        tcs = [item for item in output_items
               if getattr(item, "type", None) == "function_call"]
        if not tcs:
            review_text = (getattr(resp, "output_text", "") or "").strip()
            if not review_text:
                raise ReviewRunError(
                    "Responses API completó sin texto de revisión",
                    total_tokens, n_calls, files_read, tool_trace, provider_trace,
                )
            return (
                review_text,
                total_tokens,
                n_calls,
                sorted(set(files_read)),
                tool_trace,
                provider_trace,
            )
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


def persist_sol_outputs(
    review: str | None, provider_trace: list[dict], timestamp: str
) -> dict:
    output_dir = ROOT / "evals" / "adversarial_reviews"
    output_dir.mkdir(parents=True, exist_ok=True)
    review_receipt = {
        "review_output_path": None,
        "review_output_sha256": None,
    }
    if review is not None:
        review_bytes = review.encode("utf-8")
        review_sha = hashlib.sha256(review_bytes).hexdigest()
        review_path = output_dir / (
            f"{timestamp.replace(':', '-')}_{MODEL}_{review_sha[:12]}.md"
        )
        review_path.write_bytes(review_bytes)
        review_receipt = {
            "review_output_path": review_path.relative_to(ROOT).as_posix(),
            "review_output_sha256": review_sha,
        }
    provider_payload = {
        "schema": "sol_provider_trace_v1",
        "requested_model": MODEL,
        "reasoning_effort": REASONING_EFFORT,
        "responses": provider_trace,
    }
    provider_bytes = (
        json.dumps(
            provider_payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")
    provider_sha = hashlib.sha256(provider_bytes).hexdigest()
    provider_path = output_dir / (
        f"{timestamp.replace(':', '-')}_{MODEL}_responses_{provider_sha[:12]}.json"
    )
    provider_path.write_bytes(provider_bytes)
    return {
        **review_receipt,
        "provider_response_path": provider_path.relative_to(ROOT).as_posix(),
        "provider_response_sha256": provider_sha,
        "provider_response_ids": [item.get("id") for item in provider_trace],
        "provider_models": [item.get("model") for item in provider_trace],
        "provider_statuses": [item.get("status") for item in provider_trace],
    }


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
    include_diff = False
    use_tools = "--no-tools" not in args
    files = [a for a in args if not a.startswith("--")]
    if not files:
        sys.exit("uso: adversarial_review.py <propuesta> [contexto...] [--no-tools]")
    if not BRIEFING.is_file():
        sys.exit(f"falta el briefing canónico (¿versionado?): {BRIEFING}")
    if REASONING_EFFORT not in VALID_REASONING_EFFORTS:
        reason = ("ADVERSARIAL_REASONING_EFFORT inválido: "
                  f"{REASONING_EFFORT!r}; usa {sorted(VALID_REASONING_EFFORTS)}")
        _write_preflight_failure(files, include_diff, use_tools, reason)
        print(reason, file=sys.stderr)
        return 2
    try:
        snapshot = capture_review_snapshot()
        activate_review_snapshot(snapshot)
        subject = review_subject_identity(files, snapshot)
    except (OSError, RuntimeError, ValueError) as exc:
        reason = f"inputs de revisión no congelables bajo ROOT: {exc}"
        _write_preflight_failure(files, include_diff, use_tools, reason)
        print(reason, file=sys.stderr)
        return 2
    if "OPENAI_API_KEY" not in os.environ:
        reason = ("OPENAI_API_KEY ausente — fallback: Fable 5 + marcar "
                  "'revisor principal Sol omitido'")
        _write_preflight_failure(files, include_diff, use_tools, reason, subject)
        print(reason, file=sys.stderr)
        return 1

    sys_prompt = snapshot_file_text(BRIEFING, snapshot)
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
        parts.append(
            f"===== [{rol}] {p.name} =====\n{snapshot_file_text(p, snapshot)}"
        )
    parts.append(
        "===== [CONTEXTO: manifiesto de cambios del snapshot] =====\n"
        + snapshot_change_context(snapshot)
    )

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    t0 = time.monotonic()
    is_primary = primary_contract_satisfied()
    try:
        review, total_tokens, n_calls, files_read, tool_trace, provider_trace = run_review(
            client, sys_prompt, "\n\n".join(parts), use_tools)
    except ReviewRunError as exc:
        elapsed = time.monotonic() - t0
        timestamp = datetime.now().isoformat(timespec="seconds")
        output_receipt = persist_sol_outputs(None, exc.provider_trace, timestamp)
        entry = {
            "ts": timestamp,
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
            **subject,
            **output_receipt,
        }
        with LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        print(f"[tally] ejecución fallida registrada → {_log_display_path()} "
              f"(ts={entry['ts']}).", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1
    elapsed = time.monotonic() - t0
    timestamp = datetime.now().isoformat(timespec="seconds")
    output_receipt = persist_sol_outputs(review, provider_trace, timestamp)
    role = "revisor adversarial principal" if is_primary else "override no-principal"
    print(f"--- {MODEL} · reasoning={REASONING_EFFORT} "
          f"({role}; tools={'ON' if use_tools else 'off'}, "
          f"{n_calls} tool-calls) ---")
    print(review)

    entry = {
        "ts": timestamp,
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
        **subject,
        **output_receipt,
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
