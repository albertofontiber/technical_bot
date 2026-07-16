from scripts.s113_full_regression_preflight import guided_prompt_contract, stable_sha


class _Plan:
    kind = "demo"

    def to_dict(self):
        return {"kind": self.kind}


def test_guided_prompt_hash_changes_with_obligation_or_context():
    kwargs = {
        "question": "Q",
        "context": [{"content": "A"}],
        "plan": [],
        "system": "S",
        "model": "M",
        "max_tokens": 10,
        "coverage_context_content": lambda row: row["content"],
        "render_answer_plan_guidance": lambda plan: "G" if plan else "",
    }
    base = stable_sha(guided_prompt_contract(**kwargs))
    assert stable_sha(guided_prompt_contract(**{**kwargs, "plan": [_Plan()]})) != base
    assert stable_sha(
        guided_prompt_contract(**{**kwargs, "context": [{"content": "B"}]})
    ) != base
