# -*- coding: utf-8 -*-
"""s320 E2 — GATES de equivalencia del snapshot derivado (freeze r23).

Compara el snapshot VIVO contra un candidato SIN tocar data/model_catalog.json:
parchea `catalog._SNAPSHOT_PATH` + resetea el cache y ejecuta:
  G1 detector : extract_models sobre las 39 queries gold congeladas (STOP si
                un gold PIERDE detección; las altas se listan).
  G2 voz      : all_models COMPLETO ordenado (Whisper trunca: el orden es
                conducta) + mapa model→manufacturer + prompt final byte-a-byte
                + known_manufacturers (las 4 funciones de la API de datos).
Recibo → evals/s320_e2_gates_<candidato>.json
"""
from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=False)

import yaml  # noqa: E402


def _api_con(path: Path) -> dict:
    import src.rag.catalog as cat
    importlib.reload(cat)
    cat._SNAPSHOT_PATH = path
    cat._load()
    import src.bot.whisper_vocabulary as wv
    importlib.reload(wv)
    queries = [g["question"] for g in yaml.safe_load(
        (ROOT / "evals" / "gold_answers_v1.yaml").read_text(encoding="utf-8"))]
    return {
        "detector": {q: sorted(cat.extract_models(q)) for q in queries},
        "all_models": list(cat.all_models()),
        "mfr_map": {m: cat.model_manufacturer(m) for m in cat.all_models()},
        "known_manufacturers": sorted(cat.known_manufacturers()),
        "whisper_prompt": wv.get_whisper_prompt(),
    }


def main() -> int:
    candidato = Path(sys.argv[1])
    vivo = _api_con(ROOT / "data" / "model_catalog.json")
    nuevo = _api_con(candidato)

    from src.rag.catalog import normkey as _nk
    perdidas, cambios_forma, altas_detector = [], [], []
    for q in vivo["detector"]:
        antes = set(vivo["detector"][q])
        despues = set(nuevo["detector"][q])
        antes_nk = {_nk(m) for m in antes}
        despues_nk = {_nk(m) for m in despues}
        # STOP solo en pérdida REAL (normkey); la forma se lista aparte
        reales = sorted(m for m in antes - despues
                        if _nk(m) not in despues_nk)
        forma = sorted(m for m in antes - despues
                       if _nk(m) in despues_nk)
        if reales:
            perdidas.append({"query": q[:80], "pierde": reales})
        if forma:
            cambios_forma.append({"query": q[:80], "forma": forma})
        if despues_nk - antes_nk:
            altas_detector.append({"query": q[:80],
                                   "gana": sorted(despues - antes)})

    recibo = {
        "candidato": candidato.name,
        "g1_detector": {"queries": len(vivo["detector"]),
                        "PERDIDAS_STOP": perdidas,
                        "cambios_forma": cambios_forma,
                        "altas_informativas": altas_detector},
        "g2_voz": {
            "all_models_igual_ordenado":
                vivo["all_models"] == nuevo["all_models"],
            "delta_lista": {
                "solo_vivo": sorted(set(vivo["all_models"])
                                    - set(nuevo["all_models"])),
                "solo_nuevo": sorted(set(nuevo["all_models"])
                                     - set(vivo["all_models"]))},
            "mfr_map_diffs": sorted(
                m for m in set(vivo["mfr_map"]) & set(nuevo["mfr_map"])
                if vivo["mfr_map"][m] != nuevo["mfr_map"][m]),
            "known_manufacturers_igual":
                vivo["known_manufacturers"] == nuevo["known_manufacturers"],
            "known_manufacturers_delta": {
                "solo_vivo": sorted(set(vivo["known_manufacturers"])
                                    - set(nuevo["known_manufacturers"])),
                "solo_nuevo": sorted(set(nuevo["known_manufacturers"])
                                     - set(vivo["known_manufacturers"]))},
            "whisper_prompt_igual":
                vivo["whisper_prompt"] == nuevo["whisper_prompt"],
        },
        "veredicto": "STOP" if perdidas else "PASS",
    }
    destino = ROOT / "evals" / f"s320_e2_gates_{candidato.stem}.json"
    destino.write_text(json.dumps(recibo, ensure_ascii=False, indent=1),
                       encoding="utf-8")
    print(f"G1 detector: {len(perdidas)} PÉRDIDAS · "
          f"{len(altas_detector)} altas · G2 voz lista-igual="
          f"{recibo['g2_voz']['all_models_igual_ordenado']} prompt-igual="
          f"{recibo['g2_voz']['whisper_prompt_igual']} · "
          f"VEREDICTO {recibo['veredicto']}")
    print(f"recibo -> {destino}")
    return 0 if not perdidas else 1


if __name__ == "__main__":
    raise SystemExit(main())
