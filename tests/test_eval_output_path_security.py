from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from scripts import s117_m210_candidate_live_alignment as alignment
from scripts import s117_m29_reconciled_loss_ledger as ledger


def _directory_link(link: Path, target: Path) -> None:
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError:
        created = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(target)],
            capture_output=True,
            check=False,
        )
        if created.returncode != 0:
            pytest.skip("directory links are unavailable on this host")


def _remove_directory_link(path: Path) -> None:
    if path.is_symlink():
        path.unlink()
    else:
        os.rmdir(path)


@pytest.mark.parametrize(
    ("resolver", "failure"),
    [
        (alignment._output_path, alignment.AlignmentFailure),
        (ledger._resolve_output, ledger.LedgerFailure),
    ],
)
def test_evaluation_output_rejects_linked_parent_directory(
    tmp_path: Path, resolver, failure: type[Exception]
) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}_outside"
    outside.mkdir()
    linked_parent = tmp_path / "evals"
    _directory_link(linked_parent, outside)
    try:
        with pytest.raises(failure, match="contract_integrity_failure"):
            resolver(tmp_path, "evals/output.json")
        assert list(outside.iterdir()) == []
    finally:
        _remove_directory_link(linked_parent)
        outside.rmdir()
