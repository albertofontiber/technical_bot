from __future__ import annotations

from dataclasses import dataclass

from src.rag.frontier_visual_runtime_v2 import FrontierVisualRuntime


@dataclass
class _Response:
    id: str
    status: str
    output_text: str = ""
    model: str = "gpt-5.6-sol"
    usage: object | None = None

    def model_dump(self, **_kwargs):
        return {
            "id": self.id,
            "status": self.status,
            "output_text": self.output_text,
            "model": self.model,
        }


class _Responses:
    def __init__(self, create_values, retrieve_values):
        self.create_values = list(create_values)
        self.retrieve_values = list(retrieve_values)
        self.create_calls = []
        self.retrieve_calls = []

    def create(self, **kwargs):
        self.create_calls.append(kwargs)
        return self.create_values.pop(0)

    def retrieve(self, response_id, **kwargs):
        self.retrieve_calls.append((response_id, kwargs))
        return self.retrieve_values.pop(0)


class _Client:
    def __init__(self, responses):
        self.responses = responses


def _runtime(tmp_path, monkeypatch) -> FrontierVisualRuntime:
    runtime = FrontierVisualRuntime(
        ledger_path=tmp_path / "ledger.json",
        ledger_schema="test_ledger_v1",
        sol_model="gpt-5.6-sol",
        fable_model="claude-fable-5",
        sol_reasoning="xhigh",
        prices={
            "sol": {"input": 5.0, "output": 30.0},
            "fable": {"input": 30.0, "output": 150.0},
        },
        openai_api_key="test",
        anthropic_api_key="test",
        sol_background=True,
        sol_transport_retries=2,
        sol_poll_interval_seconds=0.001,
        sol_state_dir=tmp_path / "states",
    )
    monkeypatch.setattr("src.rag.frontier_visual_runtime_v2.time.sleep", lambda _seconds: None)
    return runtime


def test_sol_background_create_polls_and_checkpoints(tmp_path, monkeypatch) -> None:
    runtime = _runtime(tmp_path, monkeypatch)
    responses = _Responses(
        [_Response("resp_1", "queued")],
        [
            _Response("resp_1", "in_progress"),
            _Response("resp_1", "completed", '{"ok":true}'),
        ],
    )
    runtime.sol_create = _Client(responses)
    runtime.sol = _Client(responses)

    value, receipt = runtime.call_sol(
        [{"type": "input_text", "text": "test"}], "generate:item"
    )

    assert value == {"ok": True}
    assert receipt["background"] is True
    assert receipt["transport_retries_configured"] == 2
    assert receipt["background_create_retries_configured"] == 0
    assert receipt["background_poll_retries_configured"] == 2
    assert responses.create_calls[0]["background"] is True
    header = responses.create_calls[0]["extra_headers"]["X-Client-Request-Id"]
    assert header.startswith("fv-") and header.isascii()
    assert [row[0] for row in responses.retrieve_calls] == ["resp_1", "resp_1"]
    states = list((tmp_path / "states").glob("*.json"))
    assert len(states) == 1
    assert '"status": "completed"' in states[0].read_text(encoding="utf-8")


def test_sol_background_resumes_existing_response_without_new_post(tmp_path, monkeypatch) -> None:
    runtime = _runtime(tmp_path, monkeypatch)
    request = {
        "model": "gpt-5.6-sol",
        "instructions": "Follow the user contract exactly. Return only JSON.",
        "input": [{"role": "user", "content": [{"type": "input_text", "text": "test"}]}],
        "reasoning": {"effort": "xhigh"},
        "max_output_tokens": 12000,
        "store": False,
        "background": True,
    }
    from src.rag.visual_gold import stable_sha

    request_sha = stable_sha(request)
    client_request_id = f"fv-{request_sha[:24]}-{stable_sha('generate:item')[:16]}"
    runtime._write_background_state(
        call_label="generate:item",
        request_sha256=request_sha,
        response_id="resp_existing",
        status="in_progress",
        polls=4,
        client_request_id=client_request_id,
    )
    responses = _Responses(
        [], [_Response("resp_existing", "completed", '{"resumed":true}')]
    )
    runtime.sol_create = _Client(responses)
    runtime.sol = _Client(responses)

    value, _receipt = runtime.call_sol(
        [{"type": "input_text", "text": "test"}], "generate:item"
    )

    assert value == {"resumed": True}
    assert responses.create_calls == []
    assert responses.retrieve_calls[0][0] == "resp_existing"
    states = list((tmp_path / "states").glob("*.json"))
    assert '"status": "completed"' in states[0].read_text(encoding="utf-8")
