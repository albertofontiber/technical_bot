"""Lógica de veredicto de la sonda de alcanzabilidad — SIN dependencias pesadas, a propósito.

**Por qué vive aquí y no dentro de `s293_reachability_probe.py`.** Estas funciones son el guard
que impide volver a publicar un «NO alcanzable» sin pruebas (DEC-173(b), corregida en s321). Un
guard solo protege si se ejecuta, y la sonda importa el instrumento completo —pipeline, Supabase,
juez— así que un test sobre ella **se cae en CI por falta de entorno** y queda decorativo.
Lo descubrí en la PR #263: `KeyError: 'SUPABASE_URL'` en CI mientras en local pasaba, porque el
worktree tenía una copia del `.env`. Aquí no hay imports pesados: el test corre siempre.

Los tres verdictos posibles y qué exige cada uno están en `veredicto_de`.
"""
from __future__ import annotations


def prueba_de_entrega(cfg: dict, rep: dict) -> dict:
    """¿Llegó DE VERDAD la evidencia ideal al generador en esta rep?

    Nace del fallo de `hp017#2` (s321): su «NO alcanzable» se publicó desde un recibo que ni
    inyectaba ni registraba admisión — medía otra cosa y se le importó la etiqueta. Sin prueba
    positiva de entrega, un «no transmite» no distingue «el modelo no puede» de «no se lo
    dimos», que son diagnósticos opuestos.

    La prueba es DISTINTA por modo, y esto NO es un detalle: exigir `oracle_ids_admitidos` en
    `appendix` bloquearía todo NO legítimo de esa rama, que no inyecta chunks sino un span
    (cazado por el dúo s321 en mi primera redacción de la regla).
      · `serve`    → TODOS los carriers del `--inject` admitidos. «No vacío» NO basta: con 2
                     requeridos y 1 admitido, el hecho puede estar en el que faltó.
      · `appendix` → span no vacío. La presencia es CIERTA POR CONSTRUCCIÓN (la respuesta se
                     fabrica concatenando ese span), así que se declara TAUTOLÓGICA en vez de
                     fingir medida — el riesgo real de esa rama es la COBERTURA, no la entrega.

    **ENTREGA ≠ COBERTURA.** Esto solo acredita que lo inyectado LLEGÓ, no que CONTENGA el
    hecho: un oráculo incompleto (media etiqueta) entrega perfectamente y produce un NO falso.
    La cobertura la atesta el operador con `--cobertura-verificada` (ver `veredicto_de`).
    """
    if cfg["mode"] == "serve":
        admitidos = rep.get("oracle_ids_admitidos") or []
        faltan = [p for p in cfg["inject"]
                  if not any(str(cid).startswith(p) for cid in admitidos)]
        return {"ok": not faltan,
                "modo": "serve",
                "tipo": "medida",
                "requeridos": len(cfg["inject"]),
                "admitidos_unicos": len({str(c)[:8] for c in admitidos}),
                "faltan": faltan,
                "motivo": "" if not faltan else f"carriers NO admitidos: {faltan}"}
    span = (rep.get("span") or "").strip()
    return {"ok": bool(span),
            "modo": "appendix",
            "tipo": "estructural_tautologica",
            "span_len": len(span),
            "motivo": "" if span else "span vacío",
            "aviso": ("la entrega es cierta por construcción; esta prueba NO acredita que el span "
                      "CUBRA el hecho — eso lo cubre la atestación de cobertura")}


def veredicto_de(reps: list[dict], firm: int, cobertura_ok: bool = False) -> dict:
    """FAIL-CLOSED del NEGATIVO (s321). Un «NO alcanzable» exige TRES cosas; sin cualquiera de
    ellas el veredicto emitible es INCONCLUYENTE:

      1. **reps** — `veredicto_de([])` emitía un negativo con CERO evidencia, y `reps=0` es
         aceptable por CLI. El guard que existe para impedir negativos sin evidencia emitía uno
         sin ninguna (dúo s321).
      2. **entrega probada en TODAS las reps** — si no, «no transmite» no distingue incapacidad
         de ausencia. Es el fallo que cerró la etapa 3 durante meses.
      3. **cobertura atestada** — probar que el carrier LLEGÓ no prueba que CONTENGA el hecho.
         Un oráculo incompleto entrega perfecto y produce un NO falso (regla-C de DEC-173 sobre
         `hp011#2`, donde se inyectó media etiqueta).

    Asimetría DELIBERADA: un ALCANZABLE sí se emite aunque alguna rep no pruebe entrega, porque
    una sola rep firme demuestra la capacidad por sí sola. El fail-closed protege el negativo,
    que es el caro de equivocar — es el que cierra líneas de trabajo.
    """
    oracle_firme = sum(1 for r in reps if r["oracle_yes"] >= firm)
    sin_entrega = [r["rep"] for r in reps if not (r.get("prueba_entrega") or {}).get("ok")]
    alcanzable = oracle_firme > 0
    if not reps:
        txt = "INCONCLUYENTE_SIN_REPS"
    elif alcanzable:
        txt = "ALCANZABLE"
    elif sin_entrega:
        txt = "INCONCLUYENTE_SIN_PRUEBA_DE_ENTREGA"
    elif not cobertura_ok:
        txt = "INCONCLUYENTE_SIN_COBERTURA_ATESTADA"
    else:
        txt = "NO_ALCANZABLE"
    return {"oracle_firme": oracle_firme, "alcanzable": alcanzable,
            "veredicto": txt, "reps_sin_prueba_de_entrega": sin_entrega,
            "cobertura_atestada": bool(cobertura_ok)}
