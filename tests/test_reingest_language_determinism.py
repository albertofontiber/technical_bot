from __future__ import annotations

import pytest

from src.reingest import language


def _profile(monkeypatch: pytest.MonkeyPatch, detected: list[str]):
    pages = [
        {"page": index, "md": f"page-{index}"}
        for index in range(len(detected))
    ]
    mapping = {f"page-{index}": value for index, value in enumerate(detected)}
    monkeypatch.setattr(language, "detect_language", mapping.__getitem__)
    return language.profile_document({"result": {"pages": pages}})


def test_tied_dominant_uses_first_known_page_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert _profile(monkeypatch, ["en", "es"]).dominant == "en"
    assert _profile(monkeypatch, ["es", "en"]).dominant == "es"


def test_unknown_cover_does_not_define_tie_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The current inheritance policy backfills the cover from the final known
    # language, making the final page counts 2-2. The tie still follows the
    # first genuinely detected language rather than the imputed cover.
    profile = _profile(monkeypatch, ["unknown", "en", "en", "es"])
    assert profile.dominant == "en"
    assert profile.page_language[0] == "es"


def test_unique_maximum_is_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert _profile(monkeypatch, ["es", "en", "es"]).dominant == "es"
