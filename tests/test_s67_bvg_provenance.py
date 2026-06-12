"""s67 build §4.4 — el assert de provenance del manifest honesto de bvg (dúo s61 F5,
re-aplicado a mano sobre main en s67): el freeze no puede mentir sobre qué backend corrió."""
import os

import pytest

os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")

import bvg_kmajority as bvg  # noqa: E402


def _chunks(*provs):
    return [{"id": i, "rerank_backend_used": p} for i, p in enumerate(provs)]


@pytest.mark.parametrize("backend,provs,ok", [
    ("llm", ("llm",) * 5, True),
    ("llm", ("llm", "llm-padded", "llm"), True),          # padded: legítimo y AVISADO en llm
    ("llm", ("short-circuit",) * 3, True),
    ("llm", ("voyage",) * 5, False),                      # freeze llm sirvió voyage → mentira
    ("voyage", ("voyage",) * 5, True),
    ("voyage", ("short-circuit",) * 3, True),             # pool≤k: ningún backend corre
    ("voyage", ("llm",) * 5, False),                      # freeze voyage sirvió llm → mentira
    ("voyage", ("voyage", "llm-padded", "voyage"), False),  # padded NO existe en voyage
    ("voyage", ("voyage", "fallback-truncate", "voyage"), False),  # fail-open colado
])
def test_assert_rerank_provenance(monkeypatch, backend, provs, ok):
    monkeypatch.setattr(bvg, "RERANKER_BACKEND", backend)
    if ok:
        bvg._assert_rerank_provenance("qX", _chunks(*provs))
    else:
        with pytest.raises(AssertionError, match="provenance del rerank"):
            bvg._assert_rerank_provenance("qX", _chunks(*provs))


def test_manifest_no_miente_sobre_el_backend(monkeypatch):
    """El bloque (d): _ACCEPTED_PROVENANCE cubre exactamente los 2 backends del dispatcher."""
    assert set(bvg._ACCEPTED_PROVENANCE) == {"llm", "voyage"}
    assert "fallback-truncate" not in {p for v in bvg._ACCEPTED_PROVENANCE.values() for p in v}
