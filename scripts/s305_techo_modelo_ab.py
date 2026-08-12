#!/usr/bin/env python3
"""s305 — ¿El techo de la clase «elemento vecino» es del SISTEMA o del MODELO?

La pregunta. Dos instancias de la misma clase están medidas como NO ALCANZABLES:
`hp011#2` (DEC-173: oráculo de evidencia perfecta, 0/5 en 3/3 — el modelo tiene el dato
delante y contesta con OTRO parámetro) y el fallo ORGÁNICO de la CAD-171 (s303/s304: tenía
el §5.4 servido en rango 1 y encabezó con la ruta del §5.1). En ambos casos el veredicto
fue «techo». **Pero todas esas mediciones comparten generador**: `claude-sonnet-4-6`.
Nadie ha preguntado si el techo se mueve con un modelo más fuerte.

El diseño. Se reutiliza el oráculo de DEC-173 TAL CUAL (`s293_reachability_probe`), con sus
mismos parámetros, su mismo juez canónico (`judge_conveyed21`, K=5, THRESH_FIRM=4) y la
misma evidencia inyectada. **La ÚNICA variable es el modelo del generador** — freeze-contract
de manual: corpus, índice, embeddings, juez, flags y semillas quedan fijos.

Los brazos (dos ejes, no uno):
  A `claude-sonnet-4-6`  CONTROL — el de producción. **Debe reproducir 0/5**; si no lo hace,
                          el montaje no es comparable y el resto no se interpreta.
  B `claude-sonnet-5`     mismo tier, generación nueva → ¿lo arregla un swap barato?
  C `claude-opus-5`       tier superior → ¿es techo de MODELO o de esta familia de modelos?

Lo que decide. Si A=0/5 y C=5/5, el «techo» no era del sistema: era del modelo, y la clase
pasa de cerrada a abierta con un lever que no habíamos considerado (el más caro de servir,
pero el único que ninguna lane de retrieval podía tocar). Si los tres dan 0/5, el techo
queda CONFIRMADO con evidencia mucho más fuerte que antes, y la clase se cierra de verdad.

Lo que NO mide: PASS ni el resto del eval. Es la sonda de alcanzabilidad, una clase, un
hecho. Un «alcanzable con Opus» NO es un GO de despliegue — es el permiso para diseñar.

⚠️ **BUG DE LECTURA DEL JUEZ, corregido el 12-ago-2026 (s320c).** La v1 de este script hacía
`sum(1 for v in judge_conveyed21(...) if v)` sobre el retorno del juez, que es un DICT
(`{"yes": int, "n_fail": int}`): iterar un dict recorre sus CLAVES, dos strings no vacías ⇒ la
suma valía **siempre 2**, sin consultar al juez. Por eso `evals/s305_techo_modelo_ab_v1.json`
tiene `base_yes = oracle_yes = 2` en las 9 reps de los 3 brazos, `oracle_firme` (≥4) salía 0 por
construcción y el veredicto «TECHO CONFIRMADO» era INFALSABLE — la guarda del control no podía
dispararse nunca. `s293_reachability_probe.py:183` usaba el mismo juez BIEN (`votes["yes"]`): el
fallo era de este único llamador. **DEC-186 se apoyó en esa cifra.** El recibo v1 se CONSERVA
como prueba (por eso esta versión escribe a fichero nuevo). Añadido además el detector de
aguja-atascada: si todos los brazos devuelven la misma pareja de cifras, el veredicto no se lee.

Uso:  python scripts/s305_techo_modelo_ab.py [reps]     (default 3, como DEC-173)
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), "scripts"))

import yaml  # noqa: E402

import scripts.factlevel_assessment as FA  # noqa: E402  (fija DEMO_FLAGS en import-time)
import scripts.s293_reachability_probe as PROBE  # noqa: E402
from src.rag import generator as GEN  # noqa: E402

# Los parámetros EXACTOS con los que DEC-173 midió hp011#2 (leídos de su recibo
# `evals/s293_reachability_hp011_hp011_2.json`): mismas dos mitades inyectadas, mismo
# hecho, mismo modo. Cambiar cualquiera rompería la comparabilidad con el 0/5 histórico.
QID = "hp011"
# El prefijo es el del RECIBO (`hp011#2:...`), no el del nombre de fichero (`hp011_2`) —
# el probe original sustituye `#`→`_` solo al escribir la ruta de salida.
FACT_PREFIX = "hp011#2"
INJECT = ["f18362c6-26d2-4bb2-8c97-f1a4fb81729e",
          "2d45a70a-5202-442e-af84-c3a176c2178d"]

BRAZOS = [
    ("A_control_prod", "claude-sonnet-4-6"),
    ("B_sonnet_5", "claude-sonnet-5"),
    ("C_opus_5", "claude-opus-5"),
]


# El recibo v1 (roto) se CONSERVA como prueba de sobre qué se apoyó DEC-186 ⇒ fichero NUEVO.
DESTINO = "evals/s320c_techo_modelo_ab_v2.json"


def _volcar(hecho: str, valor: str, texto: str, reps: int,
            resumen: dict, resultados: dict, parcial: bool) -> None:
    """Vuelca el recibo. Se llama tras CADA brazo: una corrida larga que muera en el último
    brazo no puede llevarse por delante los brazos ya medidos."""
    with open(DESTINO, "w", encoding="utf-8") as fh:
        json.dump({"probe": "s320c_techo_modelo_ab_v2",
                   "corrige": ("evals/s305_techo_modelo_ab_v1.json — bug de lectura del juez "
                               "(sum sobre las CLAVES del dict ⇒ constante 2). DEC-186 se apoyó "
                               "en esa cifra."),
                   "parcial": parcial,
                   "ts": datetime.now(timezone.utc).isoformat(),
                   "git_sha": subprocess.run(["git", "rev-parse", "HEAD"],
                                             capture_output=True).stdout.decode().strip(),
                   "qid": QID, "fact": hecho, "valor": valor, "texto": texto,
                   "inject": INJECT, "reps_por_brazo": reps,
                   "THRESH_FIRM": FA.THRESH_FIRM, "juez": "judge_conveyed21 K=5",
                   "resumen": resumen, "brazos": resultados}, fh,
                  ensure_ascii=False, indent=2)


_MODELOS_ENVIADOS: list[str] = []


def _parchear_cliente():
    """Los modelos de la generación 5 RECHAZAN `temperature` (400: «deprecated for this
    model»), y el envelope de producción la fija a 0 para reproducibilidad. Se envuelve la
    CLASE del cliente (`generator` lo instancia dentro de la función, no a nivel de módulo)
    para retirarla SOLO en esos modelos.

    Consecuencia declarada, no escondida: los brazos 5 corren SIN `temperature=0`, así que
    su determinismo no está garantizado como en el control. Por eso el veredicto exige el
    juez K=5 y varias reps, no una pasada."""
    import anthropic

    original = anthropic.resources.messages.Messages.create

    def create(self, **kw):
        # TESTIGO DEL EFECTO, no de la intención (lección transversal del proyecto): se
        # registra el modelo REALMENTE enviado al proveedor. Si el conmutador no surtiera
        # efecto, los tres brazos mandarían el mismo y la medición sería una ilusión —
        # y con tres brazos dando cifras idénticas, esa es la primera sospecha.
        # Un turno hace VARIAS llamadas a Anthropic: el RERANKER usa su propio modelo
        # (`reranker.RERANK_MODEL`, hoy sonnet-4-6) y DEBE seguir usándolo — el
        # freeze-contract exige que la única variable sea el GENERADOR. Así que el
        # testigo solo mira la llamada de GENERACIÓN, identificable por su `system`
        # prompt (el reranker no manda uno).
        if kw.get("system"):
            _MODELOS_ENVIADOS.append(str(kw.get("model", "?")))
        es_gen5 = str(kw.get("model", "")).startswith(
            ("claude-sonnet-5", "claude-opus-5", "claude-fable-5"))
        if es_gen5:
            kw.pop("temperature", None)
        resp = original(self, **kw)
        if es_gen5:
            # 2ª incompatibilidad real: los modelos con razonamiento devuelven un
            # `ThinkingBlock` en `content[0]`, y `generator.py:851` hace
            # `response.content[0].text` → AttributeError. Aquí se reordena para que el
            # primer bloque sea el de TEXTO. **Esto no es solo un apaño del probe: es un
            # bloqueador REAL para cambiar el modelo de producción** — anotado en el
            # recibo como hallazgo, no escondido en el instrumento.
            try:
                texto_i = next(i for i, b in enumerate(resp.content)
                               if getattr(b, "type", None) == "text")
                if texto_i:
                    resp.content = ([resp.content[texto_i]]
                                    + [b for i, b in enumerate(resp.content) if i != texto_i])
            except StopIteration:
                pass
        return resp

    anthropic.resources.messages.Messages.create = create
    return lambda: setattr(anthropic.resources.messages.Messages, "create", original)


def _medir(modelo: str, question: str, valor: str, texto: str,
           inject_rows: list[dict], reps: int) -> list[dict]:
    """Un brazo completo. El modelo se conmuta EN `generator`, no en `config`:
    `generator.py` hace `from ..config import LLM_MODEL` en import-time, así que parchear
    `config` después no tendría efecto — el clásico no-op silencioso."""
    anterior = GEN.LLM_MODEL
    GEN.LLM_MODEL = modelo
    restaurar = _parchear_cliente()
    _MODELOS_ENVIADOS.clear()
    try:
        salida = []
        for i in range(reps):
            base = PROBE.run_turn(question, [])
            oraculo = PROBE.run_turn(question, inject_rows)
            base_votos = FA.judge_conveyed21(valor, texto, base["answer"])
            oraculo_votos = FA.judge_conveyed21(valor, texto, oraculo["answer"])
            # `judge_conveyed21` devuelve {"yes": int, "n_fail": int} — se LEE POR CLAVE.
            # (v1 sumaba sobre el dict ⇒ constante 2; ver la nota del docstring.)
            fila = {"rep": i,
                    "base_yes": base_votos["yes"],
                    "oracle_yes": oraculo_votos["yes"],
                    "base_n_fail": base_votos["n_fail"],
                    "oracle_n_fail": oraculo_votos["n_fail"],
                    # ENTERAS, no truncadas: el truncado a 1.500 de la v1 dejó el recibo
                    # inservible para re-juzgar (el dato podía caer más allá del corte).
                    "base_answer": base["answer"],
                    "oracle_answer": oraculo["answer"]}
            salida.append(fila)
            fallos = fila["base_n_fail"] + fila["oracle_n_fail"]
            print(f"    rep {i}: base={fila['base_yes']}/5 · oráculo={fila['oracle_yes']}/5"
                  + (f"  ⚠️ {fallos} votos fallidos" if fallos else ""),
                  flush=True)
        enviados = set(_MODELOS_ENVIADOS)
        # El testigo manda sobre la intención: si el proveedor no recibió ESTE modelo, el
        # brazo NO es lo que dice ser y su cifra no puede leerse como del modelo.
        if enviados != {modelo}:
            raise RuntimeError(
                f"CONMUTADOR SIN EFECTO: la GENERACIÓN se pidió con {modelo!r} pero el "
                f"proveedor recibió {sorted(enviados)!r}. La medición NO es interpretable."
            )
        print(f"    [testigo] generación enviada con: {sorted(enviados)}"
              f"  ({len(_MODELOS_ENVIADOS)} llamadas de generación)")
        return salida
    finally:
        GEN.LLM_MODEL = anterior          # el brazo no contamina al siguiente
        restaurar()


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    reps = int(sys.argv[1]) if len(sys.argv) > 1 else 3

    recibo = yaml.safe_load(open(PROBE.RECEIPT, encoding="utf-8"))
    gold = [r for r in recibo["per_gold"] if r["qid"] == QID][0]
    hecho = [f for f in gold["facts"] if f["key"].startswith(FACT_PREFIX)][0]
    valor, texto, question = hecho["valor"], hecho["texto"], gold["question"]

    print("s305 — ¿techo del SISTEMA o del MODELO?")
    print(f"hecho:   {hecho['key']} · valor «{valor}»")
    print(f"oráculo: serve, inyectando {len(INJECT)} portadores (idénticos a DEC-173)")
    print(f"juez:    judge_conveyed21 K=5 · THRESH_FIRM={FA.THRESH_FIRM} · reps={reps}\n")

    inject_rows = PROBE.fetch_by_prefix(INJECT, list(gold["pool_ids"]))
    if len(inject_rows) != len(INJECT):
        raise SystemExit(
            f"portadores incompletos: {len(inject_rows)}/{len(INJECT)}. El oráculo de "
            f"DEC-173 exige AMBAS mitades del label; con una sola la medición NO es "
            f"comparable (fue uno de los 3 fallos que la regla-C cazó en s293)."
        )

    resultados = {}
    for nombre, modelo in BRAZOS:
        print(f"── brazo {nombre} · {modelo}")
        try:
            resultados[nombre] = {"modelo": modelo,
                                  "reps": _medir(modelo, question, valor, texto,
                                                 inject_rows, reps)}
        except Exception as e:                                    # noqa: BLE001
            print(f"    ABORTADO: {type(e).__name__}: {str(e)[:200]}")
            resultados[nombre] = {"modelo": modelo, "error":
                                  f"{type(e).__name__}: {str(e)[:300]}", "reps": []}
        _volcar(hecho["key"], valor, texto, reps, {}, resultados, parcial=True)

    firme = FA.THRESH_FIRM
    print("\n--- veredicto ---")
    resumen = {}
    for nombre, datos in resultados.items():
        rs = datos.get("reps") or []
        oraculo_firme = sum(1 for r in rs if r["oracle_yes"] >= firme)
        maximo = max((r["oracle_yes"] for r in rs), default=0)
        resumen[nombre] = {"modelo": datos["modelo"], "n": len(rs),
                           "oracle_firme": oraculo_firme, "max_oracle": maximo,
                           "alcanzable": oraculo_firme > 0}
        estado = "ALCANZABLE" if oraculo_firme else "no alcanzable"
        print(f"  {nombre:16s} {datos['modelo']:20s} oráculo firme {oraculo_firme}/{len(rs)}"
              f" · max {maximo}/5 → {estado}"
              + (f"  [{datos['error'][:60]}]" if datos.get("error") else ""))

    # ── DETECTOR DE AGUJA ATASCADA (nace del bug de la v1, s320c) ──────────────────────────
    # Un instrumento que no mide se delata dando la MISMA cifra en todas las observaciones.
    # La v1 dio (2,2) en las 9 reps de los 3 brazos y nadie lo leyó como síntoma: se leyó como
    # «consistencia». Ahora el propio script se niega a emitir veredicto en ese caso.
    parejas = {(r["base_yes"], r["oracle_yes"])
               for d in resultados.values() for r in (d.get("reps") or [])}
    n_obs = sum(len(d.get("reps") or []) for d in resultados.values())
    fallos = sum(r.get("base_n_fail", 0) + r.get("oracle_n_fail", 0)
                 for d in resultados.values() for r in (d.get("reps") or []))
    atascada = n_obs >= 4 and len(parejas) == 1
    if fallos:
        print(f"\n⚠️  {fallos} votos del juez FALLIDOS: un 0 puede ser API caída, no un «no».")
    if atascada:
        print(f"\n=> INSTRUMENTO SOSPECHOSO: las {n_obs} observaciones de los "
              f"{len(resultados)} brazos dan la MISMA pareja {parejas.pop()}. Con modelos "
              "distintos y brazos base/oráculo distintos, eso no es consistencia: es una "
              "aguja atascada. NO leas el veredicto — audita el instrumento primero.")
        _volcar(hecho["key"], valor, texto, reps, resumen, resultados, parcial=False)
        print(f"\nrecibo: {DESTINO}")
        return 1

    control = resumen.get("A_control_prod", {})
    fuertes = [v for k, v in resumen.items() if k != "A_control_prod"]
    abortados = [k for k, v in resultados.items() if v.get("error") or not v.get("reps")]
    print()
    if abortados:
        # LA GUARDA QUE FALTABA (cazada en el smoke): sin esto, un brazo que ABORTA cuenta
        # como «no alcanzable» y el veredicto proclamaba «techo confirmado» sobre brazos
        # que jamás corrieron. Un brazo caído es AUSENCIA DE DATO, no un cero.
        print(f"=> INCONCLUYENTE: brazos abortados → {', '.join(abortados)}.")
        print("   Un brazo que no corre NO es un 0/5: es un dato que falta. Arregla la")
        print("   causa y re-mide antes de leer ningún veredicto.")
    elif control.get("n", 0) == 0:
        print("=> INCONCLUYENTE: el brazo de control no corrió. Sin reproducir el 0/5")
        print("   histórico, los otros brazos no son interpretables.")
    elif control.get("alcanzable"):
        print("=> MONTAJE NO COMPARABLE: el control (modelo de producción) SÍ transmite,")
        print("   contradiciendo el 0/5 de DEC-173. Antes de leer nada más hay que")
        print("   explicar la divergencia (¿corpus? ¿flags? ¿portadores?).")
    elif any(v["alcanzable"] for v in fuertes):
        ganan = [v["modelo"] for v in fuertes if v["alcanzable"]]
        print(f"=> EL TECHO ERA DEL MODELO: {', '.join(ganan)} transmite(n) el hecho con la")
        print("   MISMA evidencia con la que el modelo de producción falla. La clase deja")
        print("   de estar cerrada: el lever es el generador, no el serving.")
    else:
        print("=> TECHO CONFIRMADO, y ahora con evidencia mucho más fuerte: ni un tier")
        print("   superior transmite el hecho con la evidencia ideal delante. La clase se")
        print("   cierra de verdad; no hay lever de serving NI de modelo que la pague.")

    _volcar(hecho["key"], valor, texto, reps, resumen, resultados, parcial=False)
    print(f"\nrecibo: {DESTINO}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
