import json
import subprocess
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
            id=f"resp_{len(self.calls)}",
            model=review.MODEL,
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

    output, tokens, tool_calls, files_read, tool_trace, provider_trace = review.run_review(
        client, "system", "proposal", use_tools=False
    )

    assert output == "SÓLIDO"
    assert tokens == 7
    assert tool_calls == 0
    assert files_read == []
    assert tool_trace == []
    assert provider_trace[0]["model"] == review.DEFAULT_MODEL
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
                    id="resp_1",
                    model=review.MODEL,
                    status="completed",
                    usage=SimpleNamespace(total_tokens=5),
                    output=[tool_call],
                    output_text="",
                )
            return SimpleNamespace(
                id="resp_2",
                model=review.MODEL,
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

    output, tokens, tool_calls, files_read, tool_trace, provider_trace = review.run_review(
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
    assert [item["id"] for item in provider_trace] == ["resp_1", "resp_2"]
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
        id="resp_incomplete",
        model=review.MODEL,
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
    assert caught.value.provider_trace[0]["id"] == "resp_incomplete"


def test_review_fails_closed_on_completed_empty_response() -> None:
    response = SimpleNamespace(
        id="resp_empty",
        model=review.MODEL,
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
                    id="resp_1",
                    model=review.MODEL,
                    status="completed",
                    usage=SimpleNamespace(total_tokens=3),
                    output=calls,
                    output_text="",
                )
            return SimpleNamespace(
                id="resp_2",
                model=review.MODEL,
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

    output, tokens, tool_calls, _, tool_trace, _provider_trace = review.run_review(
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


def test_positive_env_int_accepts_override_and_rejects_invalid(monkeypatch) -> None:
    monkeypatch.setenv("REVIEW_TEST_BUDGET", "42")
    assert review._positive_env_int("REVIEW_TEST_BUDGET", 60) == 42
    monkeypatch.setenv("REVIEW_TEST_BUDGET", "0")
    with pytest.raises(RuntimeError, match="entero positivo"):
        review._positive_env_int("REVIEW_TEST_BUDGET", 60)


def test_review_subject_identity_binds_order_paths_and_bytes(monkeypatch, tmp_path) -> None:
    first = tmp_path / "first.md"
    second = tmp_path / "second.md"
    authority = tmp_path / "authority.md"
    briefing = tmp_path / "briefing.md"
    first.write_bytes(b"first\n")
    second.write_bytes(b"second\n")
    authority.write_bytes(b"authority\n")
    briefing.write_bytes(b"briefing\n")
    monkeypatch.setattr(review, "ROOT", tmp_path)
    monkeypatch.setattr(review, "BRIEFING", briefing)
    def snapshot():
        return {
            "head": "1" * 40,
            "files": {
                name: (tmp_path / name).read_bytes()
                for name in ("first.md", "second.md", "authority.md", "briefing.md")
            },
            "change_manifest": [{"status": "modified", "path": "authority.md"}],
        }

    initial = review.review_subject_identity([str(first), str(second)], snapshot())
    reversed_order = review.review_subject_identity([str(second), str(first)], snapshot())
    second.write_bytes(b"changed\n")
    changed = review.review_subject_identity([str(first), str(second)], snapshot())
    second.write_bytes(b"second\n")
    authority.write_bytes(b"authority changed\n")
    authority_changed = review.review_subject_identity(
        [str(first), str(second)], snapshot()
    )
    authority.write_bytes(b"authority\n")
    briefing.write_bytes(b"briefing changed\n")
    briefing_changed = review.review_subject_identity(
        [str(first), str(second)], snapshot()
    )

    assert initial["review_subject_files"][0]["path"] == "first.md"
    assert initial["review_seed_delivery"] == "full_bytes"
    assert initial["review_repo_view_file_count"] == 4
    assert initial["review_subject_sha256"] != reversed_order["review_subject_sha256"]
    assert initial["review_subject_sha256"] != changed["review_subject_sha256"]
    assert initial["review_subject_sha256"] != authority_changed["review_subject_sha256"]
    assert initial["review_subject_sha256"] != briefing_changed["review_subject_sha256"]


def test_sol_tools_deny_prior_reviewer_outputs() -> None:
    denied = review._deny(
        review.ROOT / "evals" / "s197_sol56_xhigh_design_review_v1.md"
    )
    assert denied == "denegado: salida previa de revisor (independencia)"
    assert review._is_prior_review_output(
        "evals/s113_canary_adversarial_review_v1.yaml"
    ) is True
    assert review._is_prior_review_output(
        "evals/s276_duo_adjudication_v1.yaml"
    ) is True
    assert review._is_prior_review_output("evals/s276_duo_brief_v1.md") is True
    assert review._is_prior_review_output(
        "evals/s276_corrections_packet_v1.md"
    ) is False


def test_snapshot_is_single_source_for_seed_and_tools(monkeypatch, tmp_path) -> None:
    proposal = tmp_path / "proposal.md"
    proposal.write_bytes(b"frozen\r\nbytes\r\n")
    snapshot = {
        "head": "1" * 40,
        "files": {"proposal.md": proposal.read_bytes()},
        "change_manifest": [],
    }
    monkeypatch.setattr(review, "ROOT", tmp_path)
    monkeypatch.setattr(review, "_ACTIVE_REVIEW_SNAPSHOT", snapshot)
    proposal.write_bytes(b"mutated\n")

    assert review.snapshot_file_text(proposal) == "frozen\r\nbytes\r\n"
    rendered = review.tool_read_file("proposal.md")
    assert "frozen" in rendered
    assert "mutated" not in rendered


def test_capture_snapshot_rejects_visible_symlink(monkeypatch, tmp_path) -> None:
    linked = tmp_path / "linked.txt"
    linked.write_text("content", encoding="utf-8")
    original_is_symlink = review.Path.is_symlink

    monkeypatch.setattr(review, "ROOT", tmp_path)
    monkeypatch.setattr(review, "_git_visible_files", lambda refresh=False: {"linked.txt"})
    monkeypatch.setattr(review, "_git_head_and_changes", lambda: ("1" * 40, []))
    monkeypatch.setattr(
        review.Path,
        "is_symlink",
        lambda path: path.name == "linked.txt" or original_is_symlink(path),
    )

    with pytest.raises(RuntimeError, match="enlace simbólico"):
        review.capture_review_snapshot()


def test_capture_snapshot_rejects_concurrent_file_change(monkeypatch, tmp_path) -> None:
    target = tmp_path / "changing.txt"
    target.write_text("initial", encoding="utf-8")
    original_read_bytes = review.Path.read_bytes
    reads = 0

    def changing_read(path):
        nonlocal reads
        if path.name == "changing.txt":
            reads += 1
            return b"first" if reads == 1 else b"second"
        return original_read_bytes(path)

    monkeypatch.setattr(review, "ROOT", tmp_path)
    monkeypatch.setattr(
        review, "_git_visible_files", lambda refresh=False: {"changing.txt"}
    )
    monkeypatch.setattr(review, "_git_head_and_changes", lambda: ("1" * 40, []))
    monkeypatch.setattr(review.Path, "read_bytes", changing_read)

    with pytest.raises(RuntimeError, match="worktree cambió"):
        review.capture_review_snapshot()


def test_capture_snapshot_uses_real_git_visibility_and_change_manifest(
    monkeypatch, tmp_path
) -> None:
    def git(*args: str) -> None:
        subprocess.run(
            ["git", *args], cwd=tmp_path, check=True, capture_output=True
        )

    git("init")
    git("config", "user.email", "snapshot@example.invalid")
    git("config", "user.name", "Snapshot Test")
    (tmp_path / ".gitignore").write_text(".env\nignored.txt\n", encoding="utf-8")
    (tmp_path / "tracked.txt").write_text("initial\n", encoding="utf-8")
    git("add", ".gitignore", "tracked.txt")
    git("commit", "-m", "initial")

    (tmp_path / "tracked.txt").write_text("modified\n", encoding="utf-8")
    (tmp_path / "new.txt").write_text("new\n", encoding="utf-8")
    (tmp_path / ".env").write_text("SECRET=hidden\n", encoding="utf-8")
    (tmp_path / "ignored.txt").write_text("ignored\n", encoding="utf-8")
    prior = tmp_path / "evals" / "s113_canary_adversarial_review_v1.yaml"
    prior.parent.mkdir()
    prior.write_text("prior review\n", encoding="utf-8")

    monkeypatch.setattr(review, "ROOT", tmp_path)
    monkeypatch.setattr(review, "_VISIBLE_FILES_CACHE", None)
    monkeypatch.setattr(review, "_ACTIVE_REVIEW_SNAPSHOT", None)
    snapshot = review.capture_review_snapshot()

    assert set(snapshot["files"]) == {".gitignore", "new.txt", "tracked.txt"}
    assert snapshot["files"]["tracked.txt"] == (tmp_path / "tracked.txt").read_bytes()
    assert {item["path"] for item in snapshot["change_manifest"]} == {
        "new.txt",
        "tracked.txt",
    }


def test_failed_sol_trace_is_persisted_without_normalized_review(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.setattr(review, "ROOT", tmp_path)
    trace = [
        {
            "id": "resp_incomplete",
            "model": review.DEFAULT_MODEL,
            "status": "incomplete",
        }
    ]

    receipt = review.persist_sol_outputs(None, trace, "2026-07-17T18:30:00")

    assert receipt["review_output_path"] is None
    assert receipt["review_output_sha256"] is None
    provider_path = tmp_path / receipt["provider_response_path"]
    payload = json.loads(provider_path.read_text(encoding="utf-8"))
    assert payload["responses"] == trace
    assert receipt["provider_statuses"] == ["incomplete"]


def test_diff_flag_is_rejected_before_review(monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["adversarial_review.py", "proposal.md", "--diff"])
    with pytest.raises(SystemExit, match="no reconocido"):
        review.main()


def test_sol_outputs_are_persisted_with_physical_provider_receipts(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.setattr(review, "ROOT", tmp_path)
    trace = [
        {
            "id": "resp_1",
            "model": "gpt-5.6-sol",
            "status": "completed",
            "output_text": "SÓLIDO",
        }
    ]
    receipt = review.persist_sol_outputs(
        "SÓLIDO", trace, "2026-07-17T18:03:00"
    )

    review_path = tmp_path / receipt["review_output_path"]
    provider_path = tmp_path / receipt["provider_response_path"]
    assert review_path.read_text(encoding="utf-8") == "SÓLIDO"
    assert review.hashlib.sha256(review_path.read_bytes()).hexdigest() == receipt[
        "review_output_sha256"
    ]
    assert review.hashlib.sha256(provider_path.read_bytes()).hexdigest() == receipt[
        "provider_response_sha256"
    ]
    assert receipt["provider_response_ids"] == ["resp_1"]


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
                    id="resp_1",
                    model=review.MODEL,
                    status="completed",
                    usage=SimpleNamespace(total_tokens=2),
                    output=[bad_call],
                    output_text="",
                )
            return SimpleNamespace(
                id="resp_2",
                model=review.MODEL,
                status="completed",
                usage=SimpleNamespace(total_tokens=3),
                output=[],
                output_text="RECUPERADO",
            )

    responses = _BadArgumentsResponses()
    output, tokens, tool_calls, files_read, tool_trace, _provider_trace = review.run_review(
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
    monkeypatch.setattr(review, "ROOT", tmp_path)
    frozen = {
        "head": "1" * 40,
        "files": {
            "proposal.md": proposal.read_bytes(),
            "briefing.md": briefing.read_bytes(),
        },
        "change_manifest": [],
    }
    monkeypatch.setattr(review, "capture_review_snapshot", lambda: frozen)
    monkeypatch.setattr(review, "_ACTIVE_REVIEW_SNAPSHOT", None)
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
    monkeypatch.setattr(review, "ROOT", tmp_path)
    frozen = {
        "head": "1" * 40,
        "files": {
            "proposal.md": proposal.read_bytes(),
            "briefing.md": briefing.read_bytes(),
        },
        "change_manifest": [],
    }
    monkeypatch.setattr(review, "capture_review_snapshot", lambda: frozen)
    monkeypatch.setattr(review, "_ACTIVE_REVIEW_SNAPSHOT", None)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(sys, "argv", ["adversarial_review.py", str(proposal), "--no-tools"])

    assert review.main() == 1
    entry = json.loads(tally.read_text(encoding="utf-8"))
    assert entry["run_status"] == "failed_preflight"
    assert entry["duo_status"] == "sol_omitted"
    assert entry["fable_review"]["status"] == "pending"
    assert entry["review_subject_schema"] == "adversarial_duo_subject_v1"
    assert "OPENAI_API_KEY ausente" in entry["verdict_notes"]
