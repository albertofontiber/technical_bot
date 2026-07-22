import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import adversarial_review as sol_review
from scripts import adversarial_review_fable as fable_review


@pytest.fixture(autouse=True)
def _reset_snapshot(monkeypatch):
    monkeypatch.setattr(sol_review, "_ACTIVE_REVIEW_SNAPSHOT", None)


def _usage(
    input_tokens: int,
    output_tokens: int,
    cache_creation_input_tokens: int = 0,
    cache_read_input_tokens: int = 0,
) -> SimpleNamespace:
    return SimpleNamespace(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_creation_input_tokens=cache_creation_input_tokens,
        cache_read_input_tokens=cache_read_input_tokens,
    )


def test_fable_defaults_to_exact_pinned_model() -> None:
    assert fable_review.DEFAULT_MODEL == "claude-fable-5"
    assert fable_review.MODEL == fable_review.DEFAULT_MODEL
    assert fable_review.model_contract_satisfied() is True


def test_anthropic_tools_preserve_read_only_schemas() -> None:
    tools = fable_review.anthropic_tools()
    assert [tool["name"] for tool in tools] == ["read_file", "grep_repo", "list_dir"]
    assert tools[0]["input_schema"] == sol_review.TOOLS_SPEC[0]["parameters"]


def test_independence_guard_denies_model_outputs_but_not_governance() -> None:
    assert fable_review._independence_deny(
        fable_review.ROOT / "evals" / "s197_sol56_xhigh_design_review_v1.md"
    )
    assert fable_review._independence_deny(
        fable_review.ROOT / "evals" / "adversarial_reviews" / "prior.md"
    )
    assert fable_review._independence_deny(
        fable_review.ROOT / "evals" / "s113_canary_adversarial_review_v1.yaml"
    )
    assert fable_review._independence_deny(
        fable_review.ROOT / "docs" / "ADVERSARIAL_REVIEWER.md"
    ) is None
    assert fable_review._independence_deny(
        fable_review.ROOT / "evals" / "s276_duo_adjudication_v1.yaml"
    )
    assert fable_review._independence_deny(
        fable_review.ROOT / "evals" / "s276_duo_brief_v1.md"
    )
    assert fable_review._independence_deny(
        fable_review.ROOT / "evals" / "s276_corrections_packet_v1.md"
    ) is None


def test_fable_prompt_is_versioned_and_has_no_claude_file_dependency() -> None:
    source = Path(fable_review.__file__).read_text(encoding="utf-8")
    assert "shared.snapshot_file_text(shared.BRIEFING)" in source
    assert ".claude/agents" not in source
    assert "no busques, leas ni infieras su salida" in fable_review.FABLE_SYSTEM_DELTA


def test_fable_call_preflight_counts_utf8_and_framing(monkeypatch) -> None:
    monkeypatch.setattr(fable_review, "INPUT_OVERHEAD_TOKENS", 7)
    messages = [{"role": "user", "content": "á"}]
    expected = len("sys".encode("utf-8")) + len(
        json.dumps(
            messages, ensure_ascii=False, default=str, separators=(",", ":")
        ).encode("utf-8")
    ) + 7
    assert fable_review.conservative_call_token_bound("sys", messages) == expected


def test_fable_call_preflight_also_counts_tool_schemas(monkeypatch) -> None:
    monkeypatch.setattr(fable_review, "INPUT_OVERHEAD_TOKENS", 7)
    messages = [{"role": "user", "content": "proposal"}]
    tools = [{"name": "leer", "description": "descripción", "input_schema": {}}]
    without_tools = fable_review.conservative_call_token_bound("sys", messages)
    encoded_tools = json.dumps(
        tools, ensure_ascii=False, default=str, separators=(",", ":")
    ).encode("utf-8")

    assert fable_review.conservative_call_token_bound(
        "sys", messages, tools
    ) == without_tools + len(encoded_tools)


def test_fable_drops_tools_before_call_when_schemas_consume_final_headroom(
    monkeypatch, tmp_path
) -> None:
    briefing = tmp_path / "briefing.md"
    briefing.write_text("system", encoding="utf-8")
    monkeypatch.setattr(sol_review, "BRIEFING", briefing)
    monkeypatch.setattr(fable_review, "MAX_TOTAL_TOKENS", 4_000)
    monkeypatch.setattr(fable_review, "FINAL_HEADROOM", 1_000)
    monkeypatch.setattr(fable_review, "INPUT_OVERHEAD_TOKENS", 10)
    monkeypatch.setattr(
        fable_review,
        "anthropic_tools",
        lambda: [{"name": "huge", "description": "x" * 4_000, "input_schema": {}}],
    )
    calls = []

    def create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(
            id="msg_final",
            model="claude-fable-5",
            usage=_usage(3, 2),
            content=[SimpleNamespace(type="text", text="SÓLIDO")],
            stop_reason="end_turn",
        )

    result, *_ = fable_review.run_review(
        SimpleNamespace(messages=SimpleNamespace(create=create)),
        "proposal",
        use_tools=True,
    )

    assert result == "SÓLIDO"
    assert "tools" not in calls[0]


def test_fable_tool_loop_returns_raw_review_and_trace(monkeypatch, tmp_path) -> None:
    briefing = tmp_path / "briefing.md"
    briefing.write_text("system", encoding="utf-8")
    monkeypatch.setattr(sol_review, "BRIEFING", briefing)
    monkeypatch.setattr(fable_review, "MAX_TOOL_CALLS", 2)
    monkeypatch.setattr(fable_review, "MAX_TOTAL_TOKENS", 10_000)
    monkeypatch.setattr(fable_review, "FINAL_HEADROOM", 1_000)
    monkeypatch.setattr(fable_review, "INPUT_OVERHEAD_TOKENS", 10)
    monkeypatch.setitem(fable_review.TOOL_IMPL, "list_dir", lambda **_: "files")

    tool_use = SimpleNamespace(type="tool_use", name="list_dir", input={}, id="tool_1")
    text = SimpleNamespace(type="text", text="SÓLIDO")

    class _Messages:
        def __init__(self) -> None:
            self.calls = []

        def create(self, **kwargs):
            self.calls.append(kwargs)
            if len(self.calls) == 1:
                return SimpleNamespace(
                    id="msg_1",
                    model="claude-fable-5",
                    usage=_usage(3, 2),
                    content=[tool_use],
                    stop_reason="tool_use",
                )
            return SimpleNamespace(
                id="msg_2",
                model="claude-fable-5",
                usage=_usage(4, 2),
                content=[text],
                stop_reason="end_turn",
            )

    messages = _Messages()
    client = SimpleNamespace(messages=messages)
    result, usage, calls, files_read, trace, provider_trace = fable_review.run_review(
        client, "proposal", use_tools=True
    )

    assert result == "SÓLIDO"
    assert usage["total_tokens"] == 11
    assert calls == 1
    assert files_read == []
    assert trace == [{"name": "list_dir", "arguments": {}, "status": "ok"}]
    assert [item["id"] for item in provider_trace] == ["msg_1", "msg_2"]
    assert all(item["model"] == "claude-fable-5" for item in provider_trace)
    assert messages.calls[0]["model"] == "claude-fable-5"
    assert "tools" in messages.calls[0]


def test_fable_recovers_once_from_empty_end_turn_without_more_tools(
    monkeypatch, tmp_path
) -> None:
    briefing = tmp_path / "briefing.md"
    briefing.write_text("system", encoding="utf-8")
    monkeypatch.setattr(sol_review, "BRIEFING", briefing)
    monkeypatch.setattr(fable_review, "MAX_TOTAL_TOKENS", 10_000)
    monkeypatch.setattr(fable_review, "FINAL_HEADROOM", 1_000)
    monkeypatch.setattr(fable_review, "INPUT_OVERHEAD_TOKENS", 10)
    monkeypatch.setattr(fable_review, "MAX_TOOL_CALLS", 2)
    monkeypatch.setitem(fable_review.TOOL_IMPL, "list_dir", lambda **_: "files")

    tool_use = SimpleNamespace(type="tool_use", name="list_dir", input={}, id="tool_1")
    empty = SimpleNamespace(type="text", text="")
    final = SimpleNamespace(type="text", text="SÓLIDO")

    class _Messages:
        def __init__(self) -> None:
            self.calls = []

        def create(self, **kwargs):
            self.calls.append(kwargs)
            if len(self.calls) == 1:
                content = [tool_use]
                stop_reason = "tool_use"
            elif len(self.calls) == 2:
                content = [empty]
                stop_reason = "end_turn"
            else:
                content = [final]
                stop_reason = "end_turn"
            return SimpleNamespace(
                id=f"msg_{len(self.calls)}",
                model="claude-fable-5",
                usage=_usage(3, 2),
                content=content,
                stop_reason=stop_reason,
            )

    messages = _Messages()
    result, usage, calls, _, _, provider_trace = fable_review.run_review(
        SimpleNamespace(messages=messages), "proposal", use_tools=True
    )

    assert result == "SÓLIDO"
    assert usage["total_tokens"] == 15
    assert calls == 1
    assert [item["id"] for item in provider_trace] == ["msg_1", "msg_2", "msg_3"]
    assert "tools" in messages.calls[0]
    assert "tools" in messages.calls[1]
    assert "tools" not in messages.calls[2]
    assert [item["role"] for item in messages.calls[2]["messages"]] == [
        "user",
        "assistant",
        "user",
        "user",
    ]
    assert all(
        item["role"] != "assistant" or item["content"]
        for item in messages.calls[2]["messages"]
    )
    assert messages.calls[2]["messages"][-1]["content"] == (
        fable_review.EMPTY_FINAL_RECOVERY_PROMPT
    )


def test_fable_fails_closed_after_one_empty_final_recovery(monkeypatch, tmp_path) -> None:
    briefing = tmp_path / "briefing.md"
    briefing.write_text("system", encoding="utf-8")
    monkeypatch.setattr(sol_review, "BRIEFING", briefing)
    monkeypatch.setattr(fable_review, "MAX_TOTAL_TOKENS", 10_000)
    monkeypatch.setattr(fable_review, "FINAL_HEADROOM", 1_000)
    monkeypatch.setattr(fable_review, "INPUT_OVERHEAD_TOKENS", 10)
    response_number = 0

    def create(**_):
        nonlocal response_number
        response_number += 1
        return SimpleNamespace(
            id=f"msg_empty_{response_number}",
            model="claude-fable-5",
            usage=_usage(3, 2),
            content=[SimpleNamespace(type="text", text="")],
            stop_reason="end_turn",
        )

    with pytest.raises(fable_review.FableRunError, match="tras el retry de cierre") as caught:
        fable_review.run_review(
            SimpleNamespace(messages=SimpleNamespace(create=create)),
            "proposal",
            use_tools=True,
        )
    assert len(caught.value.provider_trace) == 2


def test_fable_rejects_tool_request_during_empty_final_recovery(
    monkeypatch, tmp_path
) -> None:
    briefing = tmp_path / "briefing.md"
    briefing.write_text("system", encoding="utf-8")
    monkeypatch.setattr(sol_review, "BRIEFING", briefing)
    monkeypatch.setattr(fable_review, "MAX_TOTAL_TOKENS", 10_000)
    monkeypatch.setattr(fable_review, "FINAL_HEADROOM", 1_000)
    monkeypatch.setattr(fable_review, "INPUT_OVERHEAD_TOKENS", 10)
    call_number = 0

    def create(**kwargs):
        nonlocal call_number
        call_number += 1
        if call_number == 1:
            return SimpleNamespace(
                id="msg_empty",
                model="claude-fable-5",
                usage=_usage(3, 2),
                content=[SimpleNamespace(type="text", text="")],
                stop_reason="end_turn",
            )
        assert "tools" not in kwargs
        return SimpleNamespace(
            id="msg_tool_after_empty",
            model="claude-fable-5",
            usage=_usage(3, 2),
            content=[
                SimpleNamespace(type="tool_use", name="list_dir", input={}, id="tool_1")
            ],
            stop_reason="tool_use",
        )

    with pytest.raises(fable_review.FableRunError, match="durante la recuperación final"):
        fable_review.run_review(
            SimpleNamespace(messages=SimpleNamespace(create=create)),
            "proposal",
            use_tools=True,
        )


def test_fable_rejects_non_object_tool_input(monkeypatch, tmp_path) -> None:
    briefing = tmp_path / "briefing.md"
    briefing.write_text("system", encoding="utf-8")
    monkeypatch.setattr(sol_review, "BRIEFING", briefing)
    monkeypatch.setattr(fable_review, "MAX_TOTAL_TOKENS", 10_000)
    monkeypatch.setattr(fable_review, "FINAL_HEADROOM", 1_000)
    monkeypatch.setattr(fable_review, "INPUT_OVERHEAD_TOKENS", 10)
    response = SimpleNamespace(
        id="msg_bad_input",
        model="claude-fable-5",
        usage=_usage(3, 2),
        content=[
            SimpleNamespace(type="tool_use", name="list_dir", input="bad", id="tool_1")
        ],
        stop_reason="tool_use",
    )

    with pytest.raises(fable_review.FableRunError, match="no es un objeto JSON"):
        fable_review.run_review(
            SimpleNamespace(messages=SimpleNamespace(create=lambda **_: response)),
            "proposal",
            use_tools=True,
        )


def test_fable_budget_counts_cache_tokens(monkeypatch, tmp_path) -> None:
    briefing = tmp_path / "briefing.md"
    briefing.write_text("system", encoding="utf-8")
    monkeypatch.setattr(sol_review, "BRIEFING", briefing)
    monkeypatch.setattr(fable_review, "MAX_TOTAL_TOKENS", 10_000)
    monkeypatch.setattr(fable_review, "FINAL_HEADROOM", 1_000)
    monkeypatch.setattr(fable_review, "INPUT_OVERHEAD_TOKENS", 10)
    response = SimpleNamespace(
        id="msg_cache",
        model="claude-fable-5",
        usage=_usage(3, 2, 5, 7),
        content=[SimpleNamespace(type="text", text="SÓLIDO")],
        stop_reason="end_turn",
    )

    _, usage, *_ = fable_review.run_review(
        SimpleNamespace(messages=SimpleNamespace(create=lambda **_: response)),
        "proposal",
        use_tools=False,
    )

    assert usage["total_tokens"] == 17


def test_fable_rejects_truncated_final(monkeypatch, tmp_path) -> None:
    briefing = tmp_path / "briefing.md"
    briefing.write_text("system", encoding="utf-8")
    monkeypatch.setattr(sol_review, "BRIEFING", briefing)
    monkeypatch.setattr(fable_review, "MAX_TOTAL_TOKENS", 10_000)
    monkeypatch.setattr(fable_review, "FINAL_HEADROOM", 1_000)
    monkeypatch.setattr(fable_review, "INPUT_OVERHEAD_TOKENS", 10)
    response = SimpleNamespace(
        id="msg_truncated",
        model="claude-fable-5",
        usage=_usage(3, 2),
        content=[SimpleNamespace(type="text", text="truncated")],
        stop_reason="max_tokens",
    )
    client = SimpleNamespace(messages=SimpleNamespace(create=lambda **_: response))

    with pytest.raises(fable_review.FableRunError, match="se esperaba 'end_turn'"):
        fable_review.run_review(client, "proposal", use_tools=False)


def test_fable_rejects_truncated_tool_response(monkeypatch, tmp_path) -> None:
    briefing = tmp_path / "briefing.md"
    briefing.write_text("system", encoding="utf-8")
    monkeypatch.setattr(sol_review, "BRIEFING", briefing)
    monkeypatch.setattr(fable_review, "MAX_TOTAL_TOKENS", 10_000)
    monkeypatch.setattr(fable_review, "FINAL_HEADROOM", 1_000)
    monkeypatch.setattr(fable_review, "INPUT_OVERHEAD_TOKENS", 10)
    tool_use = SimpleNamespace(type="tool_use", name="list_dir", input={}, id="tool_1")
    response = SimpleNamespace(
        id="msg_truncated_tool",
        model="claude-fable-5",
        usage=_usage(3, 2),
        content=[tool_use],
        stop_reason="max_tokens",
    )
    client = SimpleNamespace(messages=SimpleNamespace(create=lambda **_: response))

    with pytest.raises(fable_review.FableRunError, match="se esperaba 'tool_use'"):
        fable_review.run_review(client, "proposal", use_tools=True)


def test_fable_rejects_provider_model_mismatch(monkeypatch, tmp_path) -> None:
    briefing = tmp_path / "briefing.md"
    briefing.write_text("system", encoding="utf-8")
    monkeypatch.setattr(sol_review, "BRIEFING", briefing)
    monkeypatch.setattr(fable_review, "MAX_TOTAL_TOKENS", 10_000)
    monkeypatch.setattr(fable_review, "FINAL_HEADROOM", 1_000)
    monkeypatch.setattr(fable_review, "INPUT_OVERHEAD_TOKENS", 10)
    response = SimpleNamespace(
        id="msg_wrong_model",
        model="claude-other-model",
        usage=_usage(3, 2),
        content=[SimpleNamespace(type="text", text="SÓLIDO")],
        stop_reason="end_turn",
    )
    client = SimpleNamespace(messages=SimpleNamespace(create=lambda **_: response))

    with pytest.raises(fable_review.FableRunError, match="se esperaba 'claude-fable-5'") as caught:
        fable_review.run_review(client, "proposal", use_tools=False)
    assert caught.value.usage["total_tokens"] == 5
    assert caught.value.provider_trace[0]["id"] == "msg_wrong_model"


def _sol_artifact_bytes() -> tuple[bytes, bytes]:
    review_bytes = b"SOL REVIEW"
    payload = {
        "requested_model": "gpt-5.6-sol",
        "reasoning_effort": "xhigh",
        "responses": [
            {
                "id": "resp_sol",
                "model": "gpt-5.6-sol",
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": "SOL REVIEW"}],
                    }
                ],
            }
        ],
    }
    raw_bytes = (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")
    return review_bytes, raw_bytes


def _pending_sol_entry(subject: dict, ts: str = "2026-07-17T18:00:00") -> dict:
    review_bytes, raw_bytes = _sol_artifact_bytes()
    return {
        "ts": ts,
        "run_status": "completed",
        "duo_status": "pending_fable",
        "model": "gpt-5.6-sol",
        "reasoning_effort": "xhigh",
        "primary_contract_satisfied": True,
        "diff_included": False,
        "tools": True,
        "files": ["proposal.md"],
        "review_output_path": "evals/adversarial_reviews/sol-review.md",
        "review_output_sha256": fable_review.hashlib.sha256(review_bytes).hexdigest(),
        "provider_response_path": "evals/adversarial_reviews/sol-responses.json",
        "provider_response_sha256": fable_review.hashlib.sha256(raw_bytes).hexdigest(),
        "provider_response_ids": ["resp_sol"],
        "provider_models": ["gpt-5.6-sol"],
        "provider_statuses": ["completed"],
        "fable_review": {"model": "fable", "status": "pending"},
        **subject,
    }


def _subject() -> dict:
    record = {
        "review_subject_schema": "adversarial_duo_subject_v1",
        "review_subject_files": [
            {
                "path": "proposal.md",
                "sha256": "b" * 64,
                "model_text_sha256": "b" * 64,
                "encoding": "utf-8-strict",
            }
        ],
        "review_seed_delivery": "full_bytes",
        "review_repo_visibility": "immutable_git_visible_snapshot",
        "review_repo_head": "1" * 40,
        "review_repo_view_sha256": "c" * 64,
        "review_repo_view_file_count": 1,
        "review_change_manifest": [],
        "review_change_manifest_sha256": fable_review.hashlib.sha256(b"[]").hexdigest(),
        "review_change_manifest_count": 0,
        "review_briefing_sha256": "d" * 64,
    }
    record["review_subject_sha256"] = sol_review.recompute_review_subject_sha256(record)
    return record


def _valid_receipt(tmp_path, subject: dict, tools: bool = True) -> dict:
    output_dir = tmp_path / "evals" / "adversarial_reviews"
    output_dir.mkdir(parents=True)
    sol_review_bytes, sol_raw_bytes = _sol_artifact_bytes()
    (output_dir / "sol-review.md").write_bytes(sol_review_bytes)
    (output_dir / "sol-responses.json").write_bytes(sol_raw_bytes)
    normalized = output_dir / "review.md"
    normalized.write_bytes(b"SOLIDO")
    raw = output_dir / "responses.json"
    raw_payload = {
        "requested_model": "claude-fable-5",
        "responses": [
            {
                "id": "msg_1",
                "model": "claude-fable-5",
                "stop_reason": "end_turn",
                "content": [{"type": "text", "text": "SOLIDO"}],
                "usage": {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cache_creation_input_tokens": 0,
                    "cache_read_input_tokens": 0,
                },
            }
        ],
    }
    raw.write_text(json.dumps(raw_payload), encoding="utf-8")
    return {
        "model": "claude-fable-5",
        "model_contract_satisfied": True,
        "status": "completed_pending_adjudication",
        "tools": tools,
        "review_id": "review_1",
        "review_output_path": normalized.relative_to(tmp_path).as_posix(),
        "review_output_sha256": fable_review.hashlib.sha256(
            normalized.read_bytes()
        ).hexdigest(),
        "provider_response_path": raw.relative_to(tmp_path).as_posix(),
        "provider_response_sha256": fable_review.hashlib.sha256(
            raw.read_bytes()
        ).hexdigest(),
        "provider_response_ids": ["msg_1"],
        "provider_models": ["claude-fable-5"],
        "provider_stop_reasons": ["end_turn"],
        "usage": {
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
            "total_tokens": 0,
        },
        "tokens": 0,
        "tool_calls": 0,
        "files_read": [],
        "tool_trace": [],
        **subject,
    }


def test_attach_fable_receipt_closes_exact_sol_row_and_preserves_other_bytes(
    monkeypatch, tmp_path
) -> None:
    subject = _subject()
    target = _pending_sol_entry(subject)
    untouched = b'{"ts":"older","note":"physical bytes stay exact"}\r\n'
    log = tmp_path / "log.jsonl"
    log.write_bytes(untouched + (json.dumps(target) + "\n").encode("utf-8"))
    monkeypatch.setattr(fable_review, "ROOT", tmp_path)
    receipt = _valid_receipt(tmp_path, subject)

    fable_review.attach_fable_receipt(log, target["ts"], receipt)

    assert log.read_bytes().startswith(untouched)
    closed = json.loads(log.read_bytes().splitlines()[-1])
    assert closed["duo_status"] == "complete_pending_adjudication"
    assert closed["fable_review"] == receipt


def test_attachment_accepts_one_audited_empty_final_recovery(monkeypatch, tmp_path) -> None:
    subject = _subject()
    target = _pending_sol_entry(subject)
    log = tmp_path / "log.jsonl"
    log.write_text(json.dumps(target) + "\n", encoding="utf-8")
    monkeypatch.setattr(fable_review, "ROOT", tmp_path)
    receipt = _valid_receipt(tmp_path, subject)
    raw_path = tmp_path / receipt["provider_response_path"]
    raw_payload = json.loads(raw_path.read_text(encoding="utf-8"))
    raw_payload["responses"].insert(
        0,
        {
            "id": "msg_empty",
            "model": "claude-fable-5",
            "stop_reason": "end_turn",
            "content": [{"type": "text", "text": ""}],
            "usage": {
                "input_tokens": 0,
                "output_tokens": 0,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 0,
            },
        },
    )
    raw_path.write_text(json.dumps(raw_payload), encoding="utf-8")
    receipt["provider_response_sha256"] = fable_review.hashlib.sha256(
        raw_path.read_bytes()
    ).hexdigest()
    receipt["provider_response_ids"] = ["msg_empty", "msg_1"]
    receipt["provider_models"] = ["claude-fable-5", "claude-fable-5"]
    receipt["provider_stop_reasons"] = ["end_turn", "end_turn"]

    fable_review.attach_fable_receipt(log, target["ts"], receipt)

    closed = json.loads(log.read_text(encoding="utf-8"))
    assert closed["duo_status"] == "complete_pending_adjudication"


def test_attachment_rejects_empty_final_recovery_out_of_position(
    monkeypatch, tmp_path
) -> None:
    subject = _subject()
    monkeypatch.setattr(fable_review, "ROOT", tmp_path)
    receipt = _valid_receipt(tmp_path, subject)
    raw_path = tmp_path / receipt["provider_response_path"]
    raw_payload = json.loads(raw_path.read_text(encoding="utf-8"))
    raw_payload["responses"] = [
        {
            "id": "msg_empty",
            "model": "claude-fable-5",
            "stop_reason": "end_turn",
            "content": [{"type": "text", "text": ""}],
            "usage": {
                "input_tokens": 0,
                "output_tokens": 0,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 0,
            },
        },
        {
            "id": "msg_tool",
            "model": "claude-fable-5",
            "stop_reason": "tool_use",
            "content": [
                {"type": "tool_use", "id": "tool_1", "name": "list_dir", "input": {}}
            ],
            "usage": {
                "input_tokens": 0,
                "output_tokens": 0,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 0,
            },
        },
        raw_payload["responses"][-1],
    ]
    raw_path.write_text(json.dumps(raw_payload), encoding="utf-8")
    receipt["provider_response_sha256"] = fable_review.hashlib.sha256(
        raw_path.read_bytes()
    ).hexdigest()
    receipt["provider_response_ids"] = ["msg_empty", "msg_tool", "msg_1"]
    receipt["provider_models"] = ["claude-fable-5"] * 3
    receipt["provider_stop_reasons"] = ["end_turn", "tool_use", "end_turn"]
    receipt["tool_trace"] = [{"name": "list_dir", "arguments": {}, "status": "ok"}]
    receipt["tool_calls"] = 1

    with pytest.raises(ValueError, match="no precede inmediatamente"):
        fable_review._validate_completion_receipt(receipt)


def test_attachment_rejects_tool_use_inside_final_end_turn(monkeypatch, tmp_path) -> None:
    subject = _subject()
    monkeypatch.setattr(fable_review, "ROOT", tmp_path)
    receipt = _valid_receipt(tmp_path, subject)
    raw_path = tmp_path / receipt["provider_response_path"]
    raw_payload = json.loads(raw_path.read_text(encoding="utf-8"))
    raw_payload["responses"][-1]["content"].append(
        {"type": "tool_use", "id": "tool_final", "name": "list_dir", "input": {}}
    )
    raw_path.write_text(json.dumps(raw_payload), encoding="utf-8")
    receipt["provider_response_sha256"] = fable_review.hashlib.sha256(
        raw_path.read_bytes()
    ).hexdigest()
    receipt["tool_trace"] = [{"name": "list_dir", "arguments": {}, "status": "ok"}]
    receipt["tool_calls"] = 1

    with pytest.raises(ValueError, match="cierre final end_turn contiene un tool_use"):
        fable_review._validate_completion_receipt(receipt)


@pytest.mark.parametrize(
    ("prior_texts", "message"),
    [
        (["", ""], "excede los retries"),
        (["no es vacío"], "no es una recuperación final vacía"),
    ],
)
def test_attachment_rejects_invalid_empty_final_recovery_sequences(
    monkeypatch, tmp_path, prior_texts, message
) -> None:
    subject = _subject()
    monkeypatch.setattr(fable_review, "ROOT", tmp_path)
    receipt = _valid_receipt(tmp_path, subject)
    raw_path = tmp_path / receipt["provider_response_path"]
    raw_payload = json.loads(raw_path.read_text(encoding="utf-8"))
    prior_responses = []
    for index, prior_text in enumerate(prior_texts):
        prior_responses.append(
            {
                "id": f"msg_prior_{index}",
                "model": "claude-fable-5",
                "stop_reason": "end_turn",
                "content": [{"type": "text", "text": prior_text}],
                "usage": {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cache_creation_input_tokens": 0,
                    "cache_read_input_tokens": 0,
                },
            }
        )
    raw_payload["responses"] = prior_responses + raw_payload["responses"]
    raw_path.write_text(json.dumps(raw_payload), encoding="utf-8")
    receipt["provider_response_sha256"] = fable_review.hashlib.sha256(
        raw_path.read_bytes()
    ).hexdigest()
    receipt["provider_response_ids"] = [
        response["id"] for response in raw_payload["responses"]
    ]
    receipt["provider_models"] = [
        "claude-fable-5" for _ in raw_payload["responses"]
    ]
    receipt["provider_stop_reasons"] = [
        "end_turn" for _ in raw_payload["responses"]
    ]

    with pytest.raises(ValueError, match=message):
        fable_review._validate_completion_receipt(receipt)


def test_attach_fable_receipt_fails_closed_on_subject_drift(monkeypatch, tmp_path) -> None:
    subject = _subject()
    target = _pending_sol_entry(subject)
    log = tmp_path / "log.jsonl"
    log.write_text(json.dumps(target) + "\n", encoding="utf-8")
    monkeypatch.setattr(fable_review, "ROOT", tmp_path)
    drifted_subject = json.loads(json.dumps(subject))
    drifted_subject["review_subject_files"][0]["sha256"] = "e" * 64
    drifted_subject["review_subject_sha256"] = sol_review.recompute_review_subject_sha256(
        drifted_subject
    )
    drifted = _valid_receipt(tmp_path, drifted_subject)

    with pytest.raises(ValueError, match="mismos bytes"):
        fable_review.attach_fable_receipt(log, target["ts"], drifted)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("diff_included", True, "--diff"),
        ("tools", False, "mismo modo de tools"),
    ],
)
def test_attach_fable_receipt_rejects_context_mode_mismatch(
    monkeypatch, tmp_path, field, value, message
) -> None:
    subject = _subject()
    target = _pending_sol_entry(subject)
    target[field] = value
    log = tmp_path / "log.jsonl"
    log.write_text(json.dumps(target) + "\n", encoding="utf-8")
    monkeypatch.setattr(fable_review, "ROOT", tmp_path)
    receipt = _valid_receipt(tmp_path, subject)

    with pytest.raises(ValueError, match=message):
        fable_review.attach_fable_receipt(log, target["ts"], receipt)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("model", "claude-other", "pin exacto"),
        ("model_contract_satisfied", False, "contrato de modelo"),
        ("status", "completed", "estado de recibo"),
        ("provider_models", ["claude-other"], "attestación de modelo"),
    ],
)
def test_attachment_enforces_fable_provider_invariants(
    monkeypatch, tmp_path, field, value, message
) -> None:
    subject = _subject()
    target = _pending_sol_entry(subject)
    log = tmp_path / "log.jsonl"
    log.write_text(json.dumps(target) + "\n", encoding="utf-8")
    monkeypatch.setattr(fable_review, "ROOT", tmp_path)
    receipt = _valid_receipt(tmp_path, subject)
    receipt[field] = value

    with pytest.raises(ValueError, match=message):
        fable_review.attach_fable_receipt(log, target["ts"], receipt)


def test_attachment_rejects_normalized_text_not_present_in_provider_trace(
    monkeypatch, tmp_path
) -> None:
    subject = _subject()
    target = _pending_sol_entry(subject)
    log = tmp_path / "log.jsonl"
    log.write_text(json.dumps(target) + "\n", encoding="utf-8")
    monkeypatch.setattr(fable_review, "ROOT", tmp_path)
    receipt = _valid_receipt(tmp_path, subject)
    raw_path = tmp_path / receipt["provider_response_path"]
    raw_payload = json.loads(raw_path.read_text(encoding="utf-8"))
    raw_payload["responses"][-1]["content"][0]["text"] = "OTRO TEXTO"
    raw_path.write_text(json.dumps(raw_payload), encoding="utf-8")
    receipt["provider_response_sha256"] = fable_review.hashlib.sha256(
        raw_path.read_bytes()
    ).hexdigest()

    with pytest.raises(ValueError, match="texto final del proveedor"):
        fable_review.attach_fable_receipt(log, target["ts"], receipt)


def test_attachment_rejects_fable_usage_not_derived_from_provider_trace(
    monkeypatch, tmp_path
) -> None:
    subject = _subject()
    target = _pending_sol_entry(subject)
    log = tmp_path / "log.jsonl"
    log.write_text(json.dumps(target) + "\n", encoding="utf-8")
    monkeypatch.setattr(fable_review, "ROOT", tmp_path)
    receipt = _valid_receipt(tmp_path, subject)
    receipt["usage"]["input_tokens"] = 99

    with pytest.raises(ValueError, match="uso Fable"):
        fable_review.attach_fable_receipt(log, target["ts"], receipt)


def test_attachment_revalidates_sol_physical_artifacts(monkeypatch, tmp_path) -> None:
    subject = _subject()
    target = _pending_sol_entry(subject)
    log = tmp_path / "log.jsonl"
    log.write_text(json.dumps(target) + "\n", encoding="utf-8")
    monkeypatch.setattr(fable_review, "ROOT", tmp_path)
    receipt = _valid_receipt(tmp_path, subject)
    sol_output = tmp_path / target["review_output_path"]
    sol_output.write_text("TAMPERED", encoding="utf-8")

    with pytest.raises(ValueError, match="SHA-256"):
        fable_review.attach_fable_receipt(log, target["ts"], receipt)


def test_attachment_recomputes_subject_instead_of_trusting_copied_hash(
    monkeypatch, tmp_path
) -> None:
    subject = _subject()
    target = _pending_sol_entry(subject)
    log = tmp_path / "log.jsonl"
    log.write_text(json.dumps(target) + "\n", encoding="utf-8")
    monkeypatch.setattr(fable_review, "ROOT", tmp_path)
    receipt = _valid_receipt(tmp_path, subject)
    receipt["review_repo_head"] = "2" * 40

    with pytest.raises(ValueError, match="no recomputa"):
        fable_review.attach_fable_receipt(log, target["ts"], receipt)


def test_failed_attempt_is_audited_but_keeps_duo_pending(tmp_path) -> None:
    subject = _subject()
    target = _pending_sol_entry(subject)
    log = tmp_path / "log.jsonl"
    log.write_text(json.dumps(target) + "\n", encoding="utf-8")
    attempt = {
        "ts": "2026-07-17T18:01:00",
        "status": "failed_api",
        "tokens": 12,
    }

    fable_review.record_fable_attempt(log, target["ts"], subject, attempt)

    updated = json.loads(log.read_text(encoding="utf-8"))
    assert updated["duo_status"] == "pending_fable"
    assert updated["fable_review"]["status"] == "pending"
    assert updated["fable_review"]["attempts"] == [attempt]
    assert updated["fable_review"]["last_attempt_status"] == "failed_api"


def test_fable_standalone_and_sol_omitted_fallback_are_explicit(
    monkeypatch, tmp_path
) -> None:
    subject = _subject()
    monkeypatch.setattr(fable_review, "ROOT", tmp_path)
    standalone_log = tmp_path / "standalone.jsonl"
    receipt = _valid_receipt(tmp_path, subject)
    fable_review.append_standalone_fable_entry(
        standalone_log,
        ["proposal.md"],
        subject,
        True,
        receipt=receipt,
    )
    standalone = json.loads(standalone_log.read_text(encoding="utf-8"))
    assert standalone["reviewer_side"] == "fable_standalone"
    assert standalone["duo_status"] == "fable_only_complete_pending_adjudication"

    fallback = _pending_sol_entry(subject, ts="2026-07-17T18:02:00")
    fallback["run_status"] = "failed_preflight"
    fallback["duo_status"] = "sol_omitted"
    fallback_log = tmp_path / "fallback.jsonl"
    fallback_log.write_text(json.dumps(fallback) + "\n", encoding="utf-8")
    fable_review.attach_fable_receipt(fallback_log, fallback["ts"], receipt)
    closed = json.loads(fallback_log.read_text(encoding="utf-8"))
    assert closed["duo_status"] == "sol_omitted_fable_complete_pending_adjudication"


def test_parse_args_requires_explicit_sol_pair() -> None:
    files, ts, use_tools, standalone = fable_review._parse_args(
        ["proposal.md", "context.py", "--sol-ts", "2026-07-17T18:00:00"]
    )
    assert files == ["proposal.md", "context.py"]
    assert ts == "2026-07-17T18:00:00"
    assert use_tools is True
    assert standalone is False

    files, ts, use_tools, standalone = fable_review._parse_args(
        ["proposal.md", "--standalone", "--no-tools"]
    )
    assert files == ["proposal.md"]
    assert ts is None
    assert use_tools is False
    assert standalone is True

    with pytest.raises(ValueError, match="exactamente uno"):
        fable_review._parse_args(["proposal.md"])
