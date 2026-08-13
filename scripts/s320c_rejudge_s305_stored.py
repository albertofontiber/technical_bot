#!/usr/bin/env python3
"""s320c — Re-juez de las 9 respuestas GUARDADAS de s305 con el juez canónico.

**Por qué existe.** `s305_techo_modelo_ab.py` (v1, hoy corregido) hacía
`sum(1 for v in judge_conveyed21(...) if v)` sobre el retorno del juez, que es un DICT
`{"yes": int, "n_fail": int}`: iterar un dict recorre sus CLAVES ⇒ la suma valía **siempre 2**.
Las cifras de `evals/s305_techo_modelo_ab_v1.json` (`base_yes = oracle_yes = 2` en las 9 reps de
los 3 brazos) NO proceden del juez, y DEC-186 se apoyó en ellas. Este script pasa las respuestas
que aquel recibo SÍ guardó por el juez de verdad.

**Por qué es irrepetible.** La corrida de s305 es del 7-ago-2026. Desde entonces el catálogo se
movió (PR #248: `doc_map` 861→887 entradas, y `doc_map` lo lee el camino de servicio vía
`catalog_resolver` seam-2 y `must_preserve`). Aquel estado ya no existe: re-correr la sonda mide
el sistema de HOY, no aquella corrida. Este re-juicio es la ÚNICA lectura limpia posible de lo
que s305 realmente produjo — de ahí que el recibo se versione en el repo.

**Qué NO es.** Las respuestas del recibo v1 están TRUNCADAS a 1.500 chars (la v1 guardaba
`oracle_answer[:1500]`), así que esto es un **LOWER BOUND**: truncar solo puede QUITAR texto, así
que un veredicto «transmite» es sólido y un «no transmite» puede ser artefacto del corte. Tampoco
hay brazo `base` (la v1 no guardaba esas respuestas). No sustituye a la re-medición fresca
(`evals/s320c_techo_modelo_ab_v2.json`).

Instrumento: `FA.judge_conveyed21` (GPT-5.5, K=5) y `FA.THRESH_FIRM` — el juez canónico tal cual,
sin reimplementar. Criterio de alcanzabilidad = el de DEC-173: alguna rep con `yes >= THRESH_FIRM`.

Uso:  python scripts/s320c_rejudge_s305_stored.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), "scripts"))

import scripts.factlevel_assessment as FA  # noqa: E402  (fija DEMO_FLAGS en import-time)

FUENTE = "evals/s305_techo_modelo_ab_v1.json"
DESTINO = "evals/s320c_rejudge_s305_stored_v1.json"


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    d = json.load(open(FUENTE, encoding="utf-8"))
    valor, texto = d["valor"], d["texto"]
    firme = FA.THRESH_FIRM

    print(f"hecho:  {d['fact']} · valor «{valor}»")
    print(f"juez:   {FA.JUDGE_MODEL} K={FA.K} · THRESH_FIRM={firme}")
    print(f"fuente: {FUENTE} (respuestas truncadas a 1.500 chars → LOWER BOUND)\n")

    salida = {}
    for brazo, datos in d["brazos"].items():
        filas = []
        print(f"── {brazo} · {datos['modelo']}")
        for r in datos["reps"]:
            ans = r["oracle_answer"]
            v = FA.judge_conveyed21(valor, texto, ans)
            fila = {"rep": r["rep"], "yes": v["yes"], "n_fail": v["n_fail"],
                    "firme": v["yes"] >= firme,
                    "yes_del_recibo_roto": r["oracle_yes"],
                    "len_guardada": len(ans), "contiene_295": "295" in ans}
            filas.append(fila)
            print(f"    rep {r['rep']}: {v['yes']}/5"
                  + ("  FIRME" if fila["firme"] else "")
                  + (f"  [n_fail={v['n_fail']}]" if v["n_fail"] else "")
                  + f"   (el recibo roto decía {r['oracle_yes']})")
        oracle_firme = sum(1 for f in filas if f["firme"])
        maximo = max((f["yes"] for f in filas), default=0)
        salida[brazo] = {"modelo": datos["modelo"], "n": len(filas),
                         "oracle_firme": oracle_firme, "max_oracle": maximo,
                         "alcanzable_lower_bound": oracle_firme > 0, "reps": filas}
        print(f"    → firme {oracle_firme}/{len(filas)} · max {maximo}/5\n")

    todas = [f for b in salida.values() for f in b["reps"]]
    n_fail_total = sum(f["n_fail"] for f in todas)
    # Correlación con la aparición LITERAL del valor: si el juez discriminase mal, habría
    # casos «contiene el dato pero 0/5» o «no lo contiene y 5/5». Se estampa para que el
    # veredicto sobre la calidad del juez sea auditable y no una impresión.
    coherentes = sum(1 for f in todas if f["contiene_295"] == f["firme"])
    print(f"correlación firme↔«295» literal: {coherentes}/{len(todas)}")
    if n_fail_total:
        print(f"⚠️  {n_fail_total} votos FALLIDOS del juez: un 0 puede ser API caída, no un «no».")

    with open(DESTINO, "w", encoding="utf-8") as fh:
        json.dump({"probe": "s320c_rejudge_s305_stored_v1",
                   "ts": datetime.now(timezone.utc).isoformat(),
                   "git_sha": subprocess.run(["git", "rev-parse", "HEAD"],
                                             capture_output=True).stdout.decode().strip(),
                   "que_mide": ("re-juicio de las 9 `oracle_answer` guardadas por s305 con el "
                                "juez canónico; el recibo original nunca leyó al juez (sumaba "
                                "sobre las CLAVES del dict ⇒ constante 2)"),
                   "limitaciones": ("respuestas truncadas a 1.500 chars en el recibo original ⇒ "
                                    "LOWER BOUND (un «transmite» es sólido; un «no transmite» "
                                    "puede ser el corte); sin brazo base; mide la corrida del "
                                    "7-ago, no el estado de hoy"),
                   "fuente": FUENTE, "fact": d["fact"], "valor": valor, "texto": texto,
                   "juez": {"model": FA.JUDGE_MODEL, "K": FA.K, "THRESH_FIRM": firme},
                   "correlacion_firme_vs_valor_literal": f"{coherentes}/{len(todas)}",
                   "n_fail_total": n_fail_total,
                   "brazos": salida}, fh, ensure_ascii=False, indent=2)
    print(f"\nrecibo: {DESTINO}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
