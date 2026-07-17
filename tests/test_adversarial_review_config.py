import json
import sys
from types import SimpleNamespace

import pytest

from scripts import adversarial_review as review


class _FakeResponses:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            status="completed",
            usage=SimpleNamespace(total_tokens=7),
            output=[],
            output_text="SÓLIDO",
        )


def test_primary_adversarial_defaults_are_sol_xhigh(monkeypatch) -> None:
    assert review.DEFAULT_MODEL == "gpt-5.6-sol"
    assert review.DEFAULT_REASONING_EFFORT == "xhigh"
    monkeypatch.setattr(review, "MODEL", review.DEFAULT_MODEL)
    monkeypatch.setattr(review, "REASONING_EFFORT", review.DEFAULT_REASONING_EFFORT)
    assert review.primary_contract_satisfied() is True


def test_review_sends_xhigh_on_every_primary_request(monkeypatch) -> None:
    responses = _FakeResponses()
    client = SimpleNamespace(responses=responses)
    monkeypatch.setattr(review, "MODEL", review.DEFAULT_MODEL)
    monkeypatch.setattr(review, "REASONING_EFFORT", review.DEFAULT_REASONING_EFFORT)

    output, tokens, tool_calls, files_read, tool_trace = review.run_review(
        client, "system", "proposal", use_tools=False
    )

    assert output == "SÓLIDO"
    assert tokens == 7
    assert tool_calls == 0
    assert files_read == []
    assert tool_trace == []
    assert responses.calls == [
        {
            "model": "gpt-5.6-sol",
            "instructions": "system",
            "input": [{"role": "user", "content": "proposal"}],
            "reasoning": {"effort": "xhigh"},
            "store": False,
        }
    ]


def test_review_keeps_xhigh_during_responses_tool_loop(monkeypatch) -> None:
    tool_call = SimpleNamespace(
        type="function_call",
        name="read_file",
        arguments='{"path":"CLAUDE.md"}',
        call_id="call_1",
    )

    class _ToolLoopResponses:
        def __init__(self) -> None:
            self.calls: list[dict] = []

        def create(self, **kwargs):
            self.calls.append(kwargs)
            if len(self.calls) == 1:
                return SimpleNamespace(
                    status="completed",
                    usage=SimpleNamespace(total_tokens=5),
                    output=[tool_call],
                    output_text="",
                )
            return SimpleNamespace(
                status="completed",
                usage=SimpleNamespace(total_tokens=8),
                output=[],
                output_text="HALLAZGO",
            )

    responses = _ToolLoopResponses()
    client = SimpleNamespace(responses=responses)
    monkeypatch.setattr(review, "MODEL", review.DEFAULT_MODEL)
    monkeypatch.setattr(review, "REASONING_EFFORT", review.DEFAULT_REASONING_EFFORT)
    monkeypatch.setitem(review.TOOL_IMPL, "read_file", lambda **_: "contenido")

    output, tokens, tool_calls, files_read, tool_trace = review.run_review(
        client, "system", "proposal", use_tools=True
    )

    assert output == "HALLAZGO"
    assert tokens == 13
    assert tool_calls == 1
    assert files_read == ["CLAUDE.md"]
    assert tool_trace == [
        {"name": "read_file", "arguments": {"path": "CLAUDE.md"}, "status": "ok"}
    ]
    assert len(responses.calls) == 2
    assert all(call["reasoning"] == {"effort": "xhigh"} for call in responses.calls)
    assert all("tools" in call for call in responses.calls)
    assert all("function" not in tool for tool in responses.calls[0]["tools"])
    assert responses.calls[1]["input"][-1] == {
        "type": "function_call_output",
        "call_id": "call_1",
        "output": "contenido",
    }


def test_review_fails_closed_on_incomplete_response() -> None:
    response = SimpleNamespace(
        status="incomplete",
        incomplete_details={"reason": "max_output_tokens"},
        usage=SimpleNamespace(total_tokens=2),
        output=[],
        output_text="texto truncado",
    )
    client = SimpleNamespace(
        responses=SimpleNamespace(create=lambda **_: response)
    )

    with pytest.raises(review.ReviewRunError, match="no completó") as caught:
        review.run_review(client, "system", "proposal", use_tools=False)
    assert caught.value.total_tokens == 2


def test_review_fails_closed_on_completed_empty_response() -> None:
    response = SimpleNamespace(
        status="completed",
        usage=SimpleNamespace(total_tokens=3),
        output=[],
        output_text="  ",
    )
    client = SimpleNamespace(responses=SimpleNamespace(create=lambda **_: response))

    with pytest.raises(review.ReviewRunError, match="sin texto") as caught:
        review.run_review(client, "system", "proposal", use_tools=False)
    assert caught.value.total_tokens == 3


def test_parallel_calls_cannot_exceed_hard_tool_cap(monkeypatch) -> None:
    calls = [
        SimpleNamespace(
            type="function_call", name="list_dir", arguments="{}", call_id=f"call_{i}"
        )
        for i in range(2)
    ]

    class _ParallelResponses:
        def __init__(self) -> None:
            self.requests: list[dict] = []

        def create(self, **kwargs):
            self.requests.append(kwargs)
            if len(self.requests) == 1:
                return SimpleNamespace(
                    status="completed",
                    usage=SimpleNamespace(total_tokens=3),
                    output=calls,
                    output_text="",
                )
            return SimpleNamespace(
                status="completed",
                usage=SimpleNamespace(total_tokens=4),
                output=[],
                output_text="FINAL",
            )

    executed: list[dict] = []
    responses = _ParallelResponses()
    monkeypatch.setattr(review, "MAX_TOOL_CALLS", 1)
    monkeypatch.setitem(
        review.TOOL_IMPL, "list_dir", lambda **kwargs: executed.append(kwargs) or "lista"
    )

    output, tokens, tool_calls, _, tool_trace = review.run_review(
        SimpleNamespace(responses=responses), "system", "proposal", use_tools=True
    )

    assert output == "FINAL"
    assert tokens == 7
    assert tool_calls == 1
    assert executed == [{}]
    assert tool_trace == [{"name": "list_dir", "arguments": {}, "status": "ok"}]
    assert "tools" not in responses.requests[1]
    assert "presupuesto agotado" in responses.requests[1]["input"][-2]["output"]


def test_override_does_not_satisfy_primary_contract(monkeypatch) -> None:
    monkeypatch.setattr(review, "MODEL", "another-model")
    assert review.primary_contract_satisfied() is False


def test_invalid_tool_arguments_return_error_instead_of_aborting() -> None:
    bad_call = SimpleNamespace(
        type="function_call",
        name="read_file",
        arguments="not-json",
        call_id="call_bad",
    )

    class _BadArgumentsResponses:
        def __init__(self) -> None:
            self.requests: list[dict] = []

        def create(self, **kwargs):
            self.requests.append(kwargs)
            if len(self.requests) == 1:
                return SimpleNamespace(
                    status="completed",
                    usage=SimpleNamespace(total_tokens=2),
                    output=[bad_call],
                    output_text="",
                )
            return SimpleNamespace(
                status="completed",
                usage=SimpleNamespace(total_tokens=3),
                output=[],
                output_text="RECUPERADO",
            )

    responses = _BadArgumentsResponses()
    output, tokens, tool_calls, files_read, tool_trace = review.run_review(
        SimpleNamespace(responses=responses), "system", "proposal", use_tools=True
    )

    assert output == "RECUPERADO"
    assert tokens == 5
    assert tool_calls == 1
    assert files_read == []
    assert tool_trace == [
        {"name": "read_file", "arguments": None, "status": "invalid_arguments"}
    ]
    assert "argumentos inválidos" in responses.requests[1]["input"][-1]["output"]


def test_main_records_failed_run_in_tally(monkeypatch, tmp_path) -> None:
    briefing = tmp_path / "briefing.md"
    proposal = tmp_path / "proposal.md"
    tally = tmp_path / "tally.jsonl"
    briefing.write_text("system", encoding="utf-8")
    proposal.write_text("proposal", encoding="utf-8")

    monkeypatch.setattr(review, "BRIEFING", briefing)
    monkeypatch.setattr(review, "LOG", tally)
    monkeypatch.setattr(review, "OpenAI", lambda **_: object())
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(sys, "argv", ["adversarial_review.py", str(proposal), "--no-tools"])

    def fail_run(*_args, **_kwargs):
        raise review.ReviewRunError(
            "fallo controlado", total_tokens=11, n_calls=2,
            files_read=["CLAUDE.md"],
            tool_trace=[{"name": "read_file", "arguments": {"path": "CLAUDE.md"},
                         "status": "ok"}],
        )

    monkeypatch.setattr(review, "run_review", fail_run)

    assert review.main() == 1
    entry = json.loads(tally.read_text(encoding="utf-8"))
    assert entry["run_status"] == "failed"
    assert entry["duo_status"] == "sol_failed"
    assert entry["fable_review"]["status"] == "pending"
    assert entry["fable_review"]["model"] == "fable"
    assert entry["tokens"] == 11
    assert entry["tool_calls"] == 2
    assert entry["verdict_notes"] == "RUN_FAILED: fallo controlado"


def test_main_records_missing_key_as_sol_omission(monkeypatch, tmp_path) -> None:
    briefing = tmp_path / "briefing.md"
    proposal = tmp_path / "proposal.md"
    tally = tmp_path / "tally.jsonl"
    briefing.write_text("system", encoding="utf-8")
    proposal.write_text("proposal", encoding="utf-8")

    monkeypatch.setattr(review, "BRIEFING", briefing)
    monkeypatch.setattr(review, "LOG", tally)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(sys, "argv", ["adversarial_review.py", str(proposal), "--no-tools"])

    assert review.main() == 1
    entry = json.loads(tally.read_text(encoding="utf-8"))
    assert entry["run_status"] == "failed_preflight"
    assert entry["duo_status"] == "sol_omitted"
    assert entry["fable_review"]["status"] == "pending"
    assert "OPENAI_API_KEY ausente" in entry["verdict_notes"]
