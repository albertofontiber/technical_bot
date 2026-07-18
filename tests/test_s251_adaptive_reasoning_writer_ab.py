from scripts.s251_run_adaptive_reasoning_writer_ab import (
    MAX_TOKENS,
    MODEL,
    build_arm_requests,
)


def test_s251_arms_change_only_inference_envelope() -> None:
    control, treatment = build_arm_requests("system bytes", "user bytes")
    assert control["model"] == treatment["model"] == MODEL
    assert control["max_tokens"] == treatment["max_tokens"] == MAX_TOKENS
    assert control["system"] == treatment["system"] == "system bytes"
    assert control["messages"] == treatment["messages"] == [
        {"role": "user", "content": "user bytes"}
    ]
    assert control["temperature"] == 0
    assert "temperature" not in treatment
    assert treatment["thinking"] == {"type": "adaptive"}
    assert treatment["output_config"] == {"effort": "high"}

