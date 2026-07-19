"""s273 — tests del runner v3 (helpers puros, 0 red, 0 modelo, 0 DB)."""
import importlib.util
import json
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def M():
    spec = importlib.util.spec_from_file_location(
        "s273_v3_arbiter", Path("scripts/s273_v3_arbiter.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_stable_set_majority_2_of_3(M):
    assert M.stable_set([{"a", "b"}, {"a"}, {"a", "c"}]) == {"a"}
    assert M.stable_set([{"a", "b"}, {"a", "b"}, set()]) == {"a", "b"}
    assert M.stable_set([]) == set()


def test_stable_facts_missing_key_counts_as_absent(M):
    runs = [{"f1": True, "f2": True}, {"f1": True}, {"f1": False, "f2": True}]
    st = M.stable_facts(runs)
    assert st["f1"] is True and st["f2"] is True
    st2 = M.stable_facts([{"f1": True}, {}, {}])
    assert st2["f1"] is False


def test_paired_stable_diff_losses_and_gains(M):
    off = [{"x", "y", "z"}, {"x", "y"}, {"x", "y", "z"}]     # estable: x,y,z
    on = [{"x", "w"}, {"x", "w"}, {"x"}]                     # estable: x,w
    d = M.paired_stable_diff(off, on)
    assert d["lost_under_on"] == ["y", "z"] and d["gained_under_on"] == ["w"]


def test_v3b_gate_stop_on_simulated_drop_and_pass_otherwise(M):
    off = {"hp005#0": True, "hp005#2": True}
    on_drop = {"hp005#0": True, "hp005#2": False}
    g = M.v3b_gate(off, on_drop)
    assert g["verdict"] == "STOP" and g["lost_stable_facts"] == ["hp005#2"]
    on_ok = {"hp005#0": True, "hp005#2": True, "hp005#3": True}
    g2 = M.v3b_gate(off, on_ok)
    assert g2["verdict"] == "PASS" and g2["gained_stable_facts"] == ["hp005#3"]


def test_hp010_matcher_requires_all_three_groups(M):
    full = ("Acceda al Nivel 3 con la clave, desbloquee la memoria (Memoria Bloqueada) "
            "y en el menú de Lazos pulse la tecla '2' para Autobúsqueda.")
    r = M.hp010_converted(full)
    assert r["converted"] is True and all(r["groups"].values())
    sin_nivel = "Desbloquee la memoria y use Autobúsqueda con la tecla '2'."
    r2 = M.hp010_converted(sin_nivel)
    assert r2["converted"] is False and r2["groups"]["nivel_3"] is False
    # acentos/mayúsculas no importan (NFKD-fold)
    r3 = M.hp010_converted("NIVEL 3 ... DESBLOQUEAR MEMORIA ... AUTOBUSQUEDA")
    assert r3["converted"] is True


def test_ship_gate_composite(M):
    assert M.ship_gate("PASS", "PASS", 2)["verdict"] == "SHIP_CANDIDATE"
    assert M.ship_gate("PASS", "PASS", 3)["verdict"] == "SHIP_CANDIDATE"
    assert M.ship_gate("PASS", "PASS", 1)["verdict"] == "NO_GO"     # conversión inestable
    assert M.ship_gate("STOP", "PASS", 3)["verdict"] == "NO_GO"
    assert M.ship_gate("PASS", "STOP", 3)["verdict"] == "NO_GO"
    assert M.ship_gate("PASS", "MISSING", 3)["verdict"] == "NO_GO"  # v3b no corrido aún


def test_v3a_artifact_declares_reuse_and_routes_nonhard_losses(M):
    """El artefacto v3a (ya ejecutado en la rama) declara el reuse con stamps y enruta
    las pérdidas no-duras a V3-B en vez de disparar el STOP duro."""
    p = Path("evals/s273_v3a_containment_v1.json")
    assert p.exists(), "v3a debe estar ejecutado y committeado"
    d = json.loads(p.read_text(encoding="utf-8"))
    ru = d["reuse_declared"]
    assert "mismo dia" in ru["why"]
    assert ru["probe_off_stamp"]["k"] == 3 and ru["probe_on_stamp"]["k"] == 3
    assert ru["probe_off_stamp"]["flag_on"] is False and ru["probe_on_stamp"]["flag_on"] is True
    assert ru["negcontrol"]["verdict"] == "PASS" and ru["negcontrol"]["excess_high"] <= 7
    a = d["anchors_paired"]
    assert set(a["stop_hard_union"]) == {"hp005#2:misma zona o subzona", "hp006#2:ISO-X",
                                         "hp006#0:Fallo de Tierra"}
    assert set(a["stop_hits"]) <= set(a["stop_hard_union"])
    # toda pérdida no-dura queda enrutada, no silenciada
    assert set(a["routed_to_v3b"]) == set(a["lost"]) - set(a["stop_hits"])
    assert "RETIRADA" in d["reference_v22"]
    assert d["verdict"] in ("PASS", "STOP")


def test_v3b_scope_and_stop_keys_match_prereg(M):
    import yaml
    prereg = yaml.safe_load(Path("evals/s273_quota_prereg_v3.yaml").read_text(encoding="utf-8"))
    v3b = next(p for p in prereg["phases"] if p["id"] == "V3-B")
    assert M.V3B_SCOPE == v3b["scope_qids"]
    assert M.MAJORITY == 2 and M.K == 3
