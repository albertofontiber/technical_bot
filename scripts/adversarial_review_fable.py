#!/usr/bin/env python3
"""Fable 5 side of the independent adversarial-review duo.

The runner calls the pinned Anthropic model directly, gives it the same
read-only repository tools as the Sol runner, persists the raw output and
atomically attaches its receipt to one exact pending Sol review.

Usage:
  python scripts/adversarial_review_fable.py <proposal> [context ...] \
      --sol-ts <pending-sol-timestamp> [--no-tools]
  python scripts/adversarial_review_fable.py <proposal> [context ...] \
      --standalone [--no-tools]

In paired/fallback mode the seed files and their order must be byte-identical to Sol.
Standalone mode covers the protocol's Fable-only tier without pretending Sol ran.
Prior Sol/Fable outputs are denied to the tools so the second execution remains
independent rather than anchoring on the principal review.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import anthropic

ROOT_HINT = Path(__file__).resolve().parents[1]
if str(ROOT_HINT) not in sys.path:
    sys.path.insert(0, str(ROOT_HINT))

from scripts import adversarial_review as shared

ROOT = shared.ROOT
DEFAULT_MODEL = "claude-fable-5"
MODEL = os.getenv("FABLE_REVIEW_MODEL", DEFAULT_MODEL)


def _positive_env_int(name: str, default: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError as exc:
        raise RuntimeError(f"{name} debe ser un entero positivo") from exc
    if value <= 0:
        raise RuntimeError(f"{name} debe ser un entero positivo")
    return value


MAX_TOOL_CALLS = _positive_env_int("FABLE_REVIEW_MAX_TOOL_CALLS", 12)
MAX_TOTAL_TOKENS = _positive_env_int("FABLE_REVIEW_MAX_TOTAL_TOKENS", 300_000)
FINAL_HEADROOM = _positive_env_int("FABLE_REVIEW_FINAL_HEADROOM", 80_000)
MAX_OUTPUT_TOKENS = _positive_env_int("FABLE_REVIEW_MAX_OUTPUT_TOKENS", 16_000)
INPUT_OVERHEAD_TOKENS = _positive_env_int(
    "FABLE_REVIEW_INPUT_OVERHEAD_TOKENS", 8_192
)
MIN_CALL_OUTPUT_TOKENS = _positive_env_int(
    "FABLE_REVIEW_MIN_CALL_OUTPUT_TOKENS", 512
)
TOOL_OUTPUT_CHARS = _positive_env_int("FABLE_REVIEW_TOOL_OUTPUT_CHARS", 12_000)

FABLE_SYSTEM_DELTA = """
Eres Fable 5, el segundo revisor frontera. Esta ejecución es independiente de
la revisión principal Sol: no busques, leas ni infieras su salida. Aplica el
briefing canónico directamente, usa las tools read-only para verificar claims
y devuelve únicamente tu revisión cruda en el formato exigido. Una conclusión
SÓLIDO es válida si se gana con evidencia.
""".strip()


class FableRunError(RuntimeError):
    def __init__(
        self,
        message: str,
        usage: dict[str, int],
        tool_calls: int,
        files_read: list[str],
        tool_trace: list[dict[str, Any]],
        provider_trace: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(message)
        self.usage = usage
        self.tool_calls = tool_calls
        self.files_read = sorted(set(files_read))
        self.tool_trace = tool_trace
        self.provider_trace = provider_trace or []


def model_contract_satisfied() -> bool:
    return MODEL == DEFAULT_MODEL


def _relative(path: Path) -> str | None:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return None


def _independence_deny(path: Path) -> str | None:
    """Deny prior model outputs while keeping canonical governance readable."""
    rel = _relative(path)
    if rel is None:
        return "fuera del repo (sandbox)"
    lower = rel.lower()
    name = path.name.lower()
    if (
        lower == shared.LOG_REL
        or lower == "evals/adversarial_reviews"
        or lower.startswith("evals/adversarial_reviews/")
    ):
        return "denegado: salida previa de revisión (independencia)"
    if lower.startswith("evals/") and "review" in name and (
        "sol" in name or "gpt" in name or "fable" in name or "adversarial" in name
    ):
        return "denegado: salida previa de revisor frontera (independencia)"
    return None


def tool_read_file(
    path: str, start_line: int = 1, max_lines: int = shared.READ_MAX_LINES
) -> str:
    denied = _independence_deny(ROOT / path)
    if denied:
        return f"ERROR: {denied}"
    return shared.tool_read_file(path, start_line=start_line, max_lines=max_lines)


def tool_grep_repo(
    pattern: str, glob: str = "**/*", max_hits: int = shared.GREP_MAX_HITS
) -> str:
    return shared.tool_grep_repo(pattern, glob=glob, max_hits=max_hits)


def tool_list_dir(path: str = ".") -> str:
    return shared.tool_list_dir(path)


TOOL_IMPL = {
    "read_file": tool_read_file,
    "grep_repo": tool_grep_repo,
    "list_dir": tool_list_dir,
}


def anthropic_tools() -> list[dict[str, Any]]:
    return [
        {
            "name": item["name"],
            "description": item["description"],
            "input_schema": item["parameters"],
        }
        for item in shared.TOOLS_SPEC
    ]


def _seed_file_text(path: Path) -> str:
    denied = shared._deny(path) or _independence_deny(path)
    if denied:
        raise ValueError(f"no se puede adjuntar {path}: {denied}")
    return shared.snapshot_file_text(path)


def _text_blocks(content: list[Any]) -> str:
    return "\n".join(
        block.text for block in content if getattr(block, "type", "") == "text"
    ).strip()


def _provider_response_record(response: Any) -> dict[str, Any]:
    """Persist the provider response, not only locally normalized review text."""
    if hasattr(response, "model_dump"):
        return response.model_dump(mode="json", exclude_none=False)
    blocks = []
    for block in getattr(response, "content", []) or []:
        blocks.append(
            {
                "type": getattr(block, "type", None),
                "text": getattr(block, "text", None),
                "id": getattr(block, "id", None),
                "name": getattr(block, "name", None),
                "input": getattr(block, "input", None),
            }
        )
    usage = getattr(response, "usage", None)
    return {
        "id": getattr(response, "id", None),
        "model": getattr(response, "model", None),
        "stop_reason": getattr(response, "stop_reason", None),
        "content": blocks,
        "usage": {
            key: int(getattr(usage, key, 0) or 0)
            for key in (
                "input_tokens",
                "output_tokens",
                "cache_creation_input_tokens",
                "cache_read_input_tokens",
            )
        },
    }


def conservative_call_token_bound(system_text: str, messages: list[dict[str, Any]]) -> int:
    """Conservative next-call bound: one UTF-8 byte per input token plus framing."""
    payload = json.dumps(
        messages, ensure_ascii=False, default=str, separators=(",", ":")
    )
    return (
        len(system_text.encode("utf-8"))
        + len(payload.encode("utf-8"))
        + INPUT_OVERHEAD_TOKENS
    )


def run_review(
    client: anthropic.Anthropic, user_prompt: str, use_tools: bool = True
) -> tuple[
    str,
    dict[str, int],
    int,
    list[str],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    if FINAL_HEADROOM >= MAX_TOTAL_TOKENS:
        raise ValueError("FABLE_REVIEW_FINAL_HEADROOM debe ser menor que MAX_TOTAL_TOKENS")
    system_text = (
        shared.snapshot_file_text(shared.BRIEFING)
        + "\n\n"
        + FABLE_SYSTEM_DELTA
    )
    messages: list[dict[str, Any]] = [{"role": "user", "content": user_prompt}]
    usage = {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
        "total_tokens": 0,
    }
    n_calls = 0
    files_read: list[str] = []
    tool_trace: list[dict[str, Any]] = []
    provider_trace: list[dict[str, Any]] = []
    tools = anthropic_tools()

    for _ in range(MAX_TOOL_CALLS + 8):
        remaining = MAX_TOTAL_TOKENS - usage["total_tokens"]
        input_bound = conservative_call_token_bound(system_text, messages)
        available_output = remaining - input_bound
        if available_output < MIN_CALL_OUTPUT_TOKENS:
            raise FableRunError(
                "preflight conservador excede el presupuesto acumulado de Fable",
                usage,
                n_calls,
                files_read,
                tool_trace,
                provider_trace,
            )
        call_output_cap = min(MAX_OUTPUT_TOKENS, available_output)
        exhausted = (
            not use_tools
            or n_calls >= MAX_TOOL_CALLS
            or remaining <= input_bound + FINAL_HEADROOM
        )
        kwargs: dict[str, Any] = {
            "model": MODEL,
            "max_tokens": call_output_cap,
            "system": system_text,
            "messages": messages,
        }
        if not exhausted:
            kwargs["tools"] = tools
        try:
            response = client.messages.create(**kwargs)
        except Exception as exc:
            raise FableRunError(
                f"Anthropic Messages API falló ({type(exc).__name__})",
                usage,
                n_calls,
                files_read,
                tool_trace,
                provider_trace,
            ) from exc
        provider_trace.append(_provider_response_record(response))
        for key in (
            "input_tokens",
            "output_tokens",
            "cache_creation_input_tokens",
            "cache_read_input_tokens",
        ):
            usage[key] += int(getattr(response.usage, key, 0) or 0)
        usage["total_tokens"] = sum(
            usage[key]
            for key in (
                "input_tokens",
                "output_tokens",
                "cache_creation_input_tokens",
                "cache_read_input_tokens",
            )
        )
        response_model = getattr(response, "model", None)
        if response_model != MODEL:
            raise FableRunError(
                f"Anthropic respondió con model={response_model!r}; se esperaba {MODEL!r}",
                usage,
                n_calls,
                files_read,
                tool_trace,
                provider_trace,
            )
        if usage["total_tokens"] > MAX_TOTAL_TOKENS:
            raise FableRunError(
                "el uso reportado por Anthropic excedió el presupuesto congelado",
                usage,
                n_calls,
                files_read,
                tool_trace,
                provider_trace,
            )

        calls = [
            block
            for block in response.content
            if getattr(block, "type", "") == "tool_use"
        ]
        stop_reason = getattr(response, "stop_reason", None)
        expected_stop = "tool_use" if calls else "end_turn"
        if stop_reason != expected_stop:
            raise FableRunError(
                f"Fable terminó con stop_reason={stop_reason!r}; se esperaba {expected_stop!r}",
                usage,
                n_calls,
                files_read,
                tool_trace,
                provider_trace,
            )
        if not calls:
            final_text = _text_blocks(response.content)
            if not final_text:
                raise FableRunError(
                    "Fable devolvió una revisión final vacía",
                    usage,
                    n_calls,
                    files_read,
                    tool_trace,
                    provider_trace,
                )
            return (
                final_text,
                usage,
                n_calls,
                sorted(set(files_read)),
                tool_trace,
                provider_trace,
            )

        messages.append({"role": "assistant", "content": response.content})
        results = []
        for call in calls:
            args = call.input if isinstance(call.input, dict) else {}
            if n_calls >= MAX_TOOL_CALLS:
                output = "ERROR: presupuesto de tools agotado; emite la revisión final"
                status = "budget_exhausted"
            else:
                n_calls += 1
                impl = TOOL_IMPL.get(call.name)
                try:
                    output = impl(**args) if impl else f"ERROR: tool desconocida {call.name}"
                except Exception as exc:
                    output = f"ERROR ejecutando {call.name}: {type(exc).__name__}"
                status = "tool_error" if output.startswith("ERROR") else "ok"
                if call.name == "read_file" and status == "ok":
                    files_read.append(str(args.get("path")))
                print(
                    f"  [fable tool {n_calls}] {call.name}"
                    f"({json.dumps(args, ensure_ascii=False)[:110]})",
                    file=sys.stderr,
                )
            tool_trace.append({"name": call.name, "arguments": args, "status": status})
            results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": call.id,
                    "content": output[:TOOL_OUTPUT_CHARS],
                }
            )
        messages.append({"role": "user", "content": results})
        if n_calls >= MAX_TOOL_CALLS:
            messages.append(
                {"role": "user", "content": "Emite AHORA la revisión final con lo leído."}
            )
    raise FableRunError(
        "Fable agotó el loop sin revisión final",
        usage,
        n_calls,
        files_read,
        tool_trace,
        provider_trace,
    )


def _verified_artifact(relative: str, expected_sha256: str) -> bytes:
    path = (ROOT / relative).resolve()
    try:
        path.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise ValueError("artefacto de recibo fuera de ROOT") from exc
    if not path.is_file():
        raise ValueError(f"artefacto de recibo ausente: {relative}")
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != expected_sha256:
        raise ValueError(f"SHA-256 de artefacto no coincide: {relative}")
    return data


def _validate_completion_receipt(receipt: dict[str, Any]) -> None:
    if receipt.get("model") != DEFAULT_MODEL:
        raise ValueError("el recibo no usa el pin exacto Fable")
    if receipt.get("model_contract_satisfied") is not True:
        raise ValueError("el recibo no satisface el contrato de modelo Fable")
    if receipt.get("status") != "completed_pending_adjudication":
        raise ValueError("estado de recibo Fable inválido para cerrar ejecución")
    if not isinstance(receipt.get("tools"), bool):
        raise ValueError("el recibo Fable no declara modo de tools")
    if not receipt.get("review_id"):
        raise ValueError("el recibo Fable carece de review_id")
    response_ids = receipt.get("provider_response_ids")
    provider_models = receipt.get("provider_models")
    stop_reasons = receipt.get("provider_stop_reasons")
    if not response_ids or not all(isinstance(item, str) and item for item in response_ids):
        raise ValueError("el recibo Fable carece de IDs de respuesta del proveedor")
    if provider_models != [DEFAULT_MODEL] * len(response_ids):
        raise ValueError("la attestación de modelo del proveedor no coincide con Fable")
    if (
        not isinstance(stop_reasons, list)
        or len(stop_reasons) != len(response_ids)
        or stop_reasons[-1] != "end_turn"
        or any(item != "tool_use" for item in stop_reasons[:-1])
    ):
        raise ValueError("la secuencia de stop reasons del proveedor es inválida")
    raw = _verified_artifact(
        receipt.get("provider_response_path", ""),
        receipt.get("provider_response_sha256", ""),
    )
    normalized = _verified_artifact(
        receipt.get("review_output_path", ""),
        receipt.get("review_output_sha256", ""),
    )
    if not normalized.strip():
        raise ValueError("la salida normalizada Fable está vacía")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("la respuesta serializada del proveedor no es JSON válido") from exc
    responses = payload.get("responses") or []
    if payload.get("requested_model") != DEFAULT_MODEL:
        raise ValueError("el trace no declara el modelo Fable solicitado")
    if [item.get("id") for item in responses] != response_ids:
        raise ValueError("los IDs del trace y del recibo Fable divergen")
    if [item.get("model") for item in responses] != provider_models:
        raise ValueError("los modelos del trace y del recibo Fable divergen")
    if [item.get("stop_reason") for item in responses] != stop_reasons:
        raise ValueError("los stop reasons del trace y del recibo Fable divergen")
    final_blocks = responses[-1].get("content") or []
    final_text = "\n".join(
        str(block.get("text", ""))
        for block in final_blocks
        if block.get("type") == "text"
    ).strip()
    try:
        normalized_text = normalized.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("la salida normalizada Fable no es UTF-8") from exc
    if final_text != normalized_text:
        raise ValueError("la salida normalizada no coincide con el texto final del proveedor")

    usage_keys = (
        "input_tokens",
        "output_tokens",
        "cache_creation_input_tokens",
        "cache_read_input_tokens",
    )
    computed_usage = {key: 0 for key in usage_keys}
    provider_tool_calls: list[tuple[str, Any]] = []
    for response in responses:
        response_usage = response.get("usage") or {}
        for key in usage_keys:
            computed_usage[key] += int(response_usage.get(key, 0) or 0)
        for block in response.get("content") or []:
            if block.get("type") == "tool_use":
                provider_tool_calls.append((block.get("name"), block.get("input") or {}))
    computed_usage["total_tokens"] = sum(computed_usage.values())
    if receipt.get("usage") != computed_usage:
        raise ValueError("el uso Fable no coincide con el trace del proveedor")
    if receipt.get("tokens") != computed_usage["total_tokens"]:
        raise ValueError("los tokens Fable no coinciden con el trace del proveedor")
    tool_trace = receipt.get("tool_trace")
    if not isinstance(tool_trace, list) or [
        (item.get("name"), item.get("arguments")) for item in tool_trace
    ] != provider_tool_calls:
        raise ValueError("la traza de tools Fable no coincide con el trace del proveedor")
    executed_calls = sum(
        item.get("status") != "budget_exhausted" for item in tool_trace
    )
    if receipt.get("tool_calls") != executed_calls:
        raise ValueError("el contador de tools Fable no coincide con la traza")
    computed_files = sorted(
        {
            str(item.get("arguments", {}).get("path"))
            for item in tool_trace
            if item.get("name") == "read_file" and item.get("status") == "ok"
        }
    )
    if receipt.get("files_read") != computed_files:
        raise ValueError("los ficheros leídos por Fable no coinciden con la traza")


def _validate_sol_completion_artifacts(entry: dict[str, Any]) -> None:
    """Revalidate the principal's physical evidence before closing the duo."""
    normalized = _verified_artifact(
        entry.get("review_output_path", ""),
        entry.get("review_output_sha256", ""),
    )
    raw = _verified_artifact(
        entry.get("provider_response_path", ""),
        entry.get("provider_response_sha256", ""),
    )
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("el trace Sol serializado no es JSON válido") from exc
    responses = payload.get("responses") or []
    if payload.get("requested_model") != shared.DEFAULT_MODEL:
        raise ValueError("el trace Sol no declara el modelo principal solicitado")
    if payload.get("reasoning_effort") != shared.DEFAULT_REASONING_EFFORT:
        raise ValueError("el trace Sol no declara reasoning=xhigh")
    if [item.get("id") for item in responses] != entry.get("provider_response_ids"):
        raise ValueError("los IDs del trace y del recibo Sol divergen")
    if [item.get("model") for item in responses] != entry.get("provider_models"):
        raise ValueError("los modelos del trace y del recibo Sol divergen")
    if [item.get("status") for item in responses] != entry.get("provider_statuses"):
        raise ValueError("los estados del trace y del recibo Sol divergen")
    if not responses or any(item.get("status") != "completed" for item in responses):
        raise ValueError("el trace Sol no contiene una ejecución completada")
    final_text = "\n".join(
        str(block.get("text", ""))
        for output in responses[-1].get("output") or []
        if output.get("type") == "message"
        for block in output.get("content") or []
        if block.get("type") == "output_text"
    ).strip()
    try:
        normalized_text = normalized.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("la salida normalizada Sol no es UTF-8") from exc
    if final_text != normalized_text:
        raise ValueError("la salida normalizada Sol no coincide con su trace")


def attach_fable_receipt(log_path: Path, sol_ts: str, receipt: dict[str, Any]) -> None:
    """Atomically close one exact pending Sol row without rewriting other bytes."""
    _validate_completion_receipt(receipt)
    raw_lines = log_path.read_bytes().splitlines(keepends=True)
    matches: list[tuple[int, dict[str, Any], bytes]] = []
    for index, raw_line in enumerate(raw_lines):
        ending = b"\r\n" if raw_line.endswith(b"\r\n") else b"\n" if raw_line.endswith(b"\n") else b""
        payload = raw_line[: -len(ending)] if ending else raw_line
        try:
            entry = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        if entry.get("ts") == sol_ts:
            matches.append((index, entry, ending))
    if len(matches) != 1:
        raise ValueError(f"se esperaba una entrada Sol ts={sol_ts!r}; encontradas={len(matches)}")

    index, entry, ending = matches[0]
    if entry.get("model") != shared.DEFAULT_MODEL:
        raise ValueError("la entrada a emparejar no usa el modelo principal Sol")
    if entry.get("primary_contract_satisfied") is not True:
        raise ValueError("la entrada a emparejar no satisface el contrato Sol principal")
    sol_completed = (
        entry.get("run_status") == "completed"
        and entry.get("duo_status") == "pending_fable"
    )
    sol_omitted = (
        entry.get("run_status") == "failed_preflight"
        and entry.get("duo_status") == "sol_omitted"
    )
    if not (sol_completed or sol_omitted):
        raise ValueError("la entrada Sol no está completada/omitida y pendiente de Fable")
    if sol_completed:
        _validate_sol_completion_artifacts(entry)
    pending_fable = entry.get("fable_review") or {}
    if pending_fable.get("status") != "pending":
        raise ValueError("la entrada Sol ya contiene un estado Fable no pendiente")
    if entry.get("diff_included") is not False:
        raise ValueError("un Sol con --diff no puede emparejarse con el runner Fable")
    if entry.get("tools") is not receipt.get("tools"):
        raise ValueError("Sol y Fable deben usar el mismo modo de tools")
    if shared.recompute_review_subject_sha256(entry) != entry.get(
        "review_subject_sha256"
    ):
        raise ValueError("el subject detallado Sol no recomputa su hash canónico")
    if shared.recompute_review_subject_sha256(receipt) != receipt.get(
        "review_subject_sha256"
    ):
        raise ValueError("el subject detallado Fable no recomputa su hash canónico")
    if entry.get("review_subject_sha256") != receipt.get("review_subject_sha256"):
        raise ValueError("Sol y Fable no revisaron exactamente los mismos bytes ordenados")
    for key in shared.REVIEW_SUBJECT_DETAIL_KEYS:
        if entry.get(key) != receipt.get(key):
            raise ValueError(f"el detalle de subject Sol/Fable diverge en {key}")

    receipt["attempts"] = list(pending_fable.get("attempts") or [])
    entry["duo_status"] = (
        "complete_pending_adjudication"
        if sol_completed
        else "sol_omitted_fable_complete_pending_adjudication"
    )
    entry["fable_review"] = receipt
    replacement = json.dumps(entry, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    raw_lines[index] = replacement + ending
    temporary = log_path.with_name(f".{log_path.name}.{os.getpid()}.tmp")
    try:
        temporary.write_bytes(b"".join(raw_lines))
        os.replace(temporary, log_path)
    finally:
        if temporary.exists():
            temporary.unlink()


def record_fable_attempt(
    log_path: Path,
    sol_ts: str,
    subject: dict[str, Any],
    attempt: dict[str, Any],
) -> None:
    """Audit a failed attempt while keeping the duo retryable and pending."""
    raw_lines = log_path.read_bytes().splitlines(keepends=True)
    matches: list[tuple[int, dict[str, Any], bytes]] = []
    for index, raw_line in enumerate(raw_lines):
        ending = b"\r\n" if raw_line.endswith(b"\r\n") else b"\n" if raw_line.endswith(b"\n") else b""
        payload = raw_line[: -len(ending)] if ending else raw_line
        try:
            entry = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        if entry.get("ts") == sol_ts:
            matches.append((index, entry, ending))
    if len(matches) != 1:
        raise ValueError(f"se esperaba una entrada Sol ts={sol_ts!r}; encontradas={len(matches)}")

    index, entry, ending = matches[0]
    pending = entry.get("fable_review") or {}
    retryable_sol_state = (
        entry.get("run_status") == "completed"
        and entry.get("duo_status") == "pending_fable"
    ) or (
        entry.get("run_status") == "failed_preflight"
        and entry.get("duo_status") == "sol_omitted"
    )
    if (
        entry.get("model") != shared.DEFAULT_MODEL
        or entry.get("primary_contract_satisfied") is not True
        or not retryable_sol_state
        or pending.get("status") != "pending"
    ):
        raise ValueError("la entrada Sol no admite un intento Fable pendiente")
    if entry.get("review_subject_sha256") != subject.get("review_subject_sha256"):
        raise ValueError("el intento Fable no corresponde al subject congelado por Sol")
    attempts = list(pending.get("attempts") or [])
    attempts.append(attempt)
    pending["attempts"] = attempts
    pending["last_attempt_status"] = attempt.get("status")
    entry["fable_review"] = pending
    replacement = json.dumps(entry, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    raw_lines[index] = replacement + ending
    temporary = log_path.with_name(f".{log_path.name}.{os.getpid()}.tmp")
    try:
        temporary.write_bytes(b"".join(raw_lines))
        os.replace(temporary, log_path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _parse_args(args: list[str]) -> tuple[list[str], str | None, bool, bool]:
    use_tools = "--no-tools" not in args
    standalone = "--standalone" in args
    unknown = [
        arg
        for arg in args
        if arg.startswith("--")
        and arg not in {"--no-tools", "--sol-ts", "--standalone"}
    ]
    if unknown:
        raise ValueError(f"flags desconocidos: {unknown}")
    if standalone == (args.count("--sol-ts") == 1):
        raise ValueError("elige exactamente uno: --sol-ts <timestamp> o --standalone")
    position = args.index("--sol-ts") if not standalone else -1
    if not standalone and (
        position + 1 >= len(args) or args[position + 1].startswith("--")
    ):
        raise ValueError("--sol-ts requiere un timestamp")
    sol_ts = None if standalone else args[position + 1]
    paired_indices = set() if standalone else {position, position + 1}
    files = [
        arg
        for index, arg in enumerate(args)
        if arg not in {"--no-tools", "--standalone"}
        and index not in paired_indices
    ]
    if not files:
        raise ValueError("se requiere al menos una propuesta")
    return files, sol_ts, use_tools, standalone


def append_standalone_fable_entry(
    log_path: Path,
    files: list[str],
    subject: dict[str, Any],
    tools: bool,
    *,
    receipt: dict[str, Any] | None = None,
    attempt: dict[str, Any] | None = None,
) -> None:
    if (receipt is None) == (attempt is None):
        raise ValueError("standalone requiere exactamente receipt o attempt")
    completed = receipt is not None
    if receipt is not None:
        _validate_completion_receipt(receipt)
    entry = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "run_status": "completed" if completed else "failed",
        "duo_status": (
            "fable_only_complete_pending_adjudication"
            if completed
            else "fable_only_failed"
        ),
        "reviewer_side": "fable_standalone",
        "model": MODEL,
        "model_contract_satisfied": model_contract_satisfied(),
        "files": [Path(item).name for item in files],
        "tools": tools,
        "fable_review": receipt,
        "fable_attempt": attempt,
        "findings": None,
        "confirmed": None,
        "false_pos": None,
        "severity_max": None,
        "verdict_notes": "",
        **subject,
    }
    with log_path.open("a", encoding="utf-8", newline="") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False, separators=(",", ":")) + "\n")


def record_attempt_for_mode(
    *,
    sol_ts: str | None,
    standalone: bool,
    files: list[str],
    subject: dict[str, Any],
    tools: bool,
    attempt: dict[str, Any],
) -> None:
    if standalone:
        append_standalone_fable_entry(
            shared.LOG,
            files,
            subject,
            tools,
            attempt=attempt,
        )
    else:
        if sol_ts is None:
            raise ValueError("sol_ts ausente en modo emparejado")
        record_fable_attempt(shared.LOG, sol_ts, subject, attempt)


def _persist_provider_trace(
    provider_trace: list[dict[str, Any]], timestamp: str, label: str
) -> tuple[str | None, str | None]:
    if not provider_trace:
        return None, None
    output_dir = ROOT / "evals" / "adversarial_reviews"
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "fable_provider_trace_v1",
        "requested_model": MODEL,
        "responses": provider_trace,
    }
    physical = (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")
    digest = hashlib.sha256(physical).hexdigest()
    path = output_dir / (
        f"{timestamp.replace(':', '-')}_{MODEL}_{label}_{digest[:12]}.json"
    )
    path.write_bytes(physical)
    return path.relative_to(ROOT).as_posix(), digest


def _failed_attempt(
    *,
    status: str,
    reason: str,
    usage: dict[str, int] | None = None,
    tool_calls: int = 0,
    files_read: list[str] | None = None,
    tool_trace: list[dict[str, Any]] | None = None,
    provider_trace: list[dict[str, Any]] | None = None,
    tools: bool | None = None,
) -> dict[str, Any]:
    timestamp = datetime.now().isoformat(timespec="seconds")
    raw_path, raw_sha = _persist_provider_trace(
        provider_trace or [], timestamp, "failed_attempt"
    )
    return {
        "ts": timestamp,
        "status": status,
        "requested_model": MODEL,
        "reason": reason,
        "usage": usage,
        "tokens": (usage or {}).get("total_tokens"),
        "tool_calls": tool_calls,
        "tools": tools,
        "files_read": files_read or [],
        "tool_trace": tool_trace or [],
        "provider_response_path": raw_path,
        "provider_response_sha256": raw_sha,
    }


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    try:
        files, sol_ts, use_tools, standalone = _parse_args(sys.argv[1:])
    except ValueError as exc:
        print(f"uso inválido: {exc}", file=sys.stderr)
        return 2
    paths = [Path(filename) for filename in files]
    try:
        snapshot = shared.capture_review_snapshot()
        shared.activate_review_snapshot(snapshot)
        subject = shared.review_subject_identity(files, snapshot)
        parts = [
            "Tienes tools READ-ONLY sobre el repo. No leas outputs de Sol/Fable. "
            f"Presupuesto: {MAX_TOOL_CALLS} tool-calls / {MAX_TOTAL_TOKENS} tokens acumulados."
        ]
        for index, path in enumerate(paths):
            role = "PROPUESTA A ATACAR" if index == 0 else "CONTEXTO"
            parts.append(f"===== [{role}] {path.name} =====\n{_seed_file_text(path)}")
        parts.append(
            "===== [CONTEXTO: manifiesto de cambios del snapshot] =====\n"
            + shared.snapshot_change_context(snapshot)
        )
    except (OSError, ValueError) as exc:
        print(f"preflight Fable falló: {exc}", file=sys.stderr)
        return 2
    if not model_contract_satisfied():
        reason = f"modelo override {MODEL!r}; se requiere el pin exacto {DEFAULT_MODEL!r}"
        attempt = _failed_attempt(status="failed_preflight", reason=reason, tools=use_tools)
        try:
            record_attempt_for_mode(
                sol_ts=sol_ts,
                standalone=standalone,
                files=files,
                subject=subject,
                tools=use_tools,
                attempt=attempt,
            )
        except ValueError as exc:
            print(f"{reason}; fallo registrando intento: {exc}", file=sys.stderr)
        else:
            print(reason, file=sys.stderr)
        return 2
    if "ANTHROPIC_API_KEY" not in os.environ:
        reason = "ANTHROPIC_API_KEY ausente en este proceso"
        attempt = _failed_attempt(status="failed_preflight", reason=reason, tools=use_tools)
        try:
            record_attempt_for_mode(
                sol_ts=sol_ts,
                standalone=standalone,
                files=files,
                subject=subject,
                tools=use_tools,
                attempt=attempt,
            )
        except ValueError as exc:
            print(f"{reason}; fallo registrando intento: {exc}", file=sys.stderr)
        else:
            print(f"{reason}; la entrada Sol permanece pending_fable", file=sys.stderr)
        return 1

    client = anthropic.Anthropic(
        api_key=os.environ["ANTHROPIC_API_KEY"], max_retries=0
    )
    started = time.monotonic()
    try:
        review, usage, n_calls, files_read, tool_trace, provider_trace = run_review(
            client, "\n\n".join(parts), use_tools=use_tools
        )
    except FableRunError as exc:
        attempt = _failed_attempt(
            status="failed_api",
            reason=str(exc),
            usage=exc.usage,
            tool_calls=exc.tool_calls,
            files_read=exc.files_read,
            tool_trace=exc.tool_trace,
            provider_trace=exc.provider_trace,
            tools=use_tools,
        )
        try:
            record_attempt_for_mode(
                sol_ts=sol_ts,
                standalone=standalone,
                files=files,
                subject=subject,
                tools=use_tools,
                attempt=attempt,
            )
        except ValueError as attach_exc:
            print(f"{exc}; fallo registrando intento: {attach_exc}", file=sys.stderr)
        else:
            print(str(exc), file=sys.stderr)
        return 1
    elapsed = round(time.monotonic() - started, 1)
    timestamp = datetime.now().isoformat(timespec="seconds")
    logical_sha = hashlib.sha256(review.encode("utf-8")).hexdigest()
    output_dir = ROOT / "evals" / "adversarial_reviews"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / (
        f"{timestamp.replace(':', '-')}_{MODEL}_{logical_sha[:12]}.md"
    )
    output_path.write_bytes(review.encode("utf-8"))
    physical_sha = hashlib.sha256(output_path.read_bytes()).hexdigest()
    raw_path, raw_sha = _persist_provider_trace(provider_trace, timestamp, "responses")
    receipt = {
        "model": MODEL,
        "display_name": "Fable 5",
        "status": "completed_pending_adjudication",
        "model_contract_satisfied": True,
        "review_id": f"{timestamp}:{physical_sha[:12]}",
        "review_output_path": output_path.relative_to(ROOT).as_posix(),
        "review_output_sha256": physical_sha,
        "provider_response_path": raw_path,
        "provider_response_sha256": raw_sha,
        "provider_response_ids": [item.get("id") for item in provider_trace],
        "provider_models": [item.get("model") for item in provider_trace],
        "provider_stop_reasons": [item.get("stop_reason") for item in provider_trace],
        "budgets": {
            "max_tool_calls": MAX_TOOL_CALLS,
            "max_total_tokens": MAX_TOTAL_TOKENS,
            "final_headroom": FINAL_HEADROOM,
            "max_output_tokens": MAX_OUTPUT_TOKENS,
            "input_overhead_tokens": INPUT_OVERHEAD_TOKENS,
            "tool_output_chars": TOOL_OUTPUT_CHARS,
        },
        "usage": usage,
        "tokens": usage["total_tokens"],
        "elapsed_s": elapsed,
        "tool_calls": n_calls,
        "files_read": files_read,
        "tool_trace": tool_trace,
        "tools": use_tools,
        "findings": None,
        "confirmed": None,
        "false_pos": None,
        "severity_max": None,
        **subject,
    }
    try:
        if standalone:
            append_standalone_fable_entry(
                shared.LOG,
                files,
                subject,
                use_tools,
                receipt=receipt,
            )
        else:
            if sol_ts is None:
                raise ValueError("sol_ts ausente en modo emparejado")
            attach_fable_receipt(shared.LOG, sol_ts, receipt)
    except ValueError as exc:
        print(
            f"review guardada pero NO emparejada ({output_path}): {exc}",
            file=sys.stderr,
        )
        return 1

    print(f"--- {MODEL} (revisor frontera independiente; {n_calls} tool-calls) ---")
    print(review)
    if standalone:
        print("\n[fable] recibo standalone registrado; pendiente adjudicación Rule C")
    else:
        print(
            f"\n[duo] recibo Fable unido a Sol ts={sol_ts}; "
            "duo_status=complete_pending_adjudication"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
