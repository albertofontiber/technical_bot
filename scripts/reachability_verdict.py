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
    # (s324d, Sol r34) `judge_conveyed21` devuelve `n_fail`: un voto caído NO es un «no». Una rep no firme
    # con votos caídos podría haber sido firme ⇒ no puede sostener un NEGATIVO (juez incompleto). Un
    # ALCANZABLE sí se sostiene (los «sí» son votos reales).
    juez_incompleto = [r["rep"] for r in reps
                       if (r.get("oracle_n_fail") or 0) > 0 and r["oracle_yes"] < firm]
    alcanzable = oracle_firme > 0
    if not reps:
        txt = "INCONCLUYENTE_SIN_REPS"
    elif alcanzable:
        txt = "ALCANZABLE"
    elif sin_entrega:
        txt = "INCONCLUYENTE_SIN_PRUEBA_DE_ENTREGA"
    elif juez_incompleto:
        txt = "INCONCLUYENTE_JUEZ_INCOMPLETO"
    elif not cobertura_ok:
        txt = "INCONCLUYENTE_SIN_COBERTURA_ATESTADA"
    else:
        txt = "NO_ALCANZABLE"
    return {"oracle_firme": oracle_firme, "alcanzable": alcanzable,
            "veredicto": txt, "reps_sin_prueba_de_entrega": sin_entrega,
            "reps_juez_incompleto": juez_incompleto,
            "cobertura_atestada": bool(cobertura_ok)}


def veredicto_recibo(reps: list[dict], firm: int, cobertura_ok: bool, estado: str, n_reps_pedidas: int) -> dict:
    """Veredicto que se ESCRIBE en el recibo, según el estado del run (Sol r34: un recibo PARCIAL no puede
    llevar un veredicto literal que un consumidor lea como completo).

      · COMPLETO → el de `veredicto_de`.
      · PARCIAL  → NUNCA un `NO_ALCANZABLE` ni un `ALCANZABLE` a secas: `PARCIAL_<lo que dicen las reps
                   juzgadas>`; y como faltan reps, un negativo no es emitible ⇒ `PARCIAL_INCONCLUYENTE_...`.
                   `veredicto_reps_juzgadas` conserva el literal informativo.
    """
    v = veredicto_de(reps, firm, cobertura_ok=cobertura_ok)
    base = v["veredicto"]
    if estado == "COMPLETO":
        v["veredicto_reps_juzgadas"] = base
        return v
    if base == "NO_ALCANZABLE":
        txt = "PARCIAL_INCONCLUYENTE_SIN_REPS_COMPLETAS"
    else:
        txt = f"PARCIAL_{base}"
    v["veredicto_reps_juzgadas"] = base
    v["veredicto"] = txt
    v["n_reps_pedidas"] = n_reps_pedidas
    return v


# ─────────────────────────── s324d — endurecimiento (TECH_DEBT #89), lógica PURA ───────────────────────────
# Cinco defectos vistos al correr las 8 sondas de etapa 3 (agente de medición, 16-ago). Todo lo que se puede
# probar sin entorno vive aquí; el probe solo lo llama.
import re as _re
import unicodedata as _ud


def _norm(s: str) -> str:
    s = _ud.normalize("NFKD", s or "")
    s = "".join(ch for ch in s if not _ud.combining(ch))
    return _re.sub(r"\s+", " ", s.casefold()).strip()


def _tokens_valor(valor: str) -> list[str]:
    """Tokens «duros» del valor (números, códigos, palabras ≥3): lo que el span DEBE contener para
    poder decir que cubre el hecho. Se ignoran conectores y signos."""
    toks = _re.findall(r"[a-z0-9][a-z0-9./,\-]*", _norm(valor))
    toks = [t.strip(".,/-") for t in toks]
    return [t for t in toks if t and (any(ch.isdigit() for ch in t) or len(t) >= 3)]


_STOP_PRED = {"que", "para", "con", "sin", "por", "una", "uno", "unos", "unas", "los", "las", "del", "las",
              "como", "este", "esta", "esto", "estos", "estas", "ese", "esa", "eso", "sus", "más", "mas", "muy",
              "hay", "son", "ser", "está", "esta", "hasta", "desde", "entre", "sobre", "donde", "cuando", "the",
              "and", "for", "with", "not", "solo", "sólo", "pero", "también", "tambien", "the", "cada", "todo",
              "todos", "toda", "todas", "cual", "cuál", "tiene", "tienen", "puede", "pueden", "debe", "deben",
              "según", "segun", "tras", "ante", "bajo", "sea", "sean", "aún", "aun"}


def _tok_presente(tok: str, texto_norm: str) -> bool:
    """Coincidencia con FRONTERA de palabra: «32» no se acredita dentro de «132» ni «zona» dentro de
    «zonas» (Sol r34: la subcadena acreditaba tokens dentro de otros)."""
    return _re.search(r"(?<![a-z0-9])" + _re.escape(tok) + r"(?![a-z0-9])", texto_norm) is not None


def _tokens_predicado(texto: str, excluir: list[str]) -> list[str]:
    """Tokens de CONTENIDO del enunciado del hecho (`texto`) que no son el valor: el «predicado» —
    palabras ≥4 letras o códigos, sin conectores. Sirven para exigir que el span diga DE QUÉ es el valor,
    no solo que el número aparezca (contrato de #89: «valor Y predicado»)."""
    ex = set(excluir)
    toks = []
    for t in _re.findall(r"[a-z0-9][a-z0-9./,\-]*", _norm(texto)):
        t = t.strip(".,/-")
        if not t or t in ex or t in _STOP_PRED:
            continue
        if any(ch.isdigit() for ch in t) or len(t) >= 4:
            if t not in toks:
                toks.append(t)
    return toks


def span_cubre(span: str, valor: str, texto: str | None = None, min_frac: float = 1.0,
               min_predicado: int = 2) -> dict:
    """Guard de COBERTURA del span (defecto 2): el span debe contener TODOS los tokens duros del valor
    (con frontera de palabra) y, si se pasa el enunciado del hecho (`texto`), al menos `min_predicado`
    tokens de contenido de ese enunciado (o todos si hay menos): valor Y predicado. Devuelve el detalle
    para el recibo, no un bool a secas. Es un guard heurístico contra el «oráculo incompleto» (media
    etiqueta, número sin su relación); NO sustituye a la atestación humana de cobertura."""
    toks = _tokens_valor(valor)
    n = _norm(span)
    presentes = [t for t in toks if _tok_presente(t, n)]
    ausentes = [t for t in toks if not _tok_presente(t, n)]
    ok_valor = bool(toks) and len(presentes) / len(toks) >= min_frac
    out = {"ok": ok_valor, "tokens_valor": toks, "presentes": presentes, "ausentes": ausentes,
           "predicado_exigido": False}
    if texto:
        pred = _tokens_predicado(texto, toks)
        req = min(min_predicado, len(pred))
        p_pres = [t for t in pred if _tok_presente(t, n)]
        out.update({"predicado_exigido": True, "tokens_predicado": pred, "predicado_presentes": p_pres,
                    "predicado_requeridos": req, "ok_predicado": len(p_pres) >= req})
        out["ok"] = ok_valor and out["ok_predicado"]
    return out


def elegir_span(chunks: list[dict], span_grep: str, valor: str, texto: str | None = None, *,
                extender_lineas: int = 2, max_chars: int = 600) -> dict:
    """Elige el span del oráculo `appendix` CON guard de cobertura (defecto 2).

    Antes: la PRIMERA línea que casaba el regex (split en `.;:`, len>25) — sin comprobar que cubría el
    hecho; partía «etiqueta: definición» y descartaba etiquetas ≤25 chars (hp017#1 → «no construible»
    con el carrier servido); un span de una frase no cubría hechos de dos frases (cat016#1, hp009#0).

    Ahora: se parte SOLO por frase/línea (`.` `;` y saltos), no por `:`; cada candidato que casa el regex
    se comprueba con `span_cubre`; si no cubre, se EXTIENDE con hasta `extender_lineas` líneas siguientes
    (cap `max_chars`) y se re-comprueba; se devuelve el primer candidato que cubre. Si ninguno cubre, se
    devuelve el mejor (más tokens presentes) con `cubre=False` — el probe lo declara INCONCLUYENTE, no
    lo usa a ciegas. Devuelve dict: span, fragment_number, cubre (detalle), candidatos_probados,
    extendido (bool)."""
    pattern = _re.compile(span_grep, _re.IGNORECASE)
    mejor = None
    probados = 0
    for position, chunk in enumerate(chunks, start=1):
        content = str(chunk.get("content") or "")
        lineas = [l.strip() for l in _re.split(r"(?<=[.;])\s+|\n", content)]
        lineas = [l for l in lineas if l]
        for i, line in enumerate(lineas):
            if not pattern.search(line):
                continue
            probados += 1
            span = line
            cob = span_cubre(span, valor, texto)
            extendido = False
            k = 0
            while not cob["ok"] and k < extender_lineas and i + k + 1 < len(lineas):
                k += 1
                cand = " ".join(lineas[i:i + k + 1])
                if len(cand) > max_chars:
                    break
                span, extendido = cand, True
                cob = span_cubre(span, valor, texto)
            cand_row = {"span": span, "fragment_number": position, "cubre": cob,
                        "extendido": extendido, "candidatos_probados": probados}
            if cob["ok"]:
                return cand_row
            if mejor is None or len(cob["presentes"]) > len(mejor["cubre"]["presentes"]):
                mejor = cand_row
    if mejor is None:
        return {"span": None, "fragment_number": None, "cubre": span_cubre("", valor, texto),
                "extendido": False, "candidatos_probados": probados}
    mejor["candidatos_probados"] = probados
    return mejor


def carriers_ya_servidos(base_served_ids: list[str], inject_prefixes: list[str]) -> list[str]:
    """Defecto 5: en `serve`, si un carrier del `--inject` YA está en la vista base, el oráculo mide
    PROMINENCIA (no evidencia ausente) — hay que declararlo. Devuelve los prefijos ya servidos."""
    return [p for p in inject_prefixes
            if any(str(cid).startswith(p) for cid in base_served_ids)]


def elegir_receipt(paths: list[str], explicito: str | None = None) -> str:
    """Defecto 1: el recibo FULL por defecto es el MÁS RECIENTE (por la fecha del nombre), no uno
    pineado en el código; `--receipt` explícito manda. Acepta rutas o nombres; devuelve la elegida."""
    if explicito:
        return explicito
    def fecha(p: str):
        m = _re.search(r"(20\d{6})", p.replace("\\", "/").rsplit("/", 1)[-1])
        return m.group(1) if m else "00000000"
    nombre = lambda p: p.replace("\\", "/").rsplit("/", 1)[-1]  # noqa: E731
    cands = [p for p in paths if _re.match(r"s100_factlevel_full_v3.*\.yaml$", nombre(p)) and "INVALIDO" not in p]
    if not cands:
        raise ValueError("no hay recibos FULL v3* disponibles")
    return sorted(cands, key=fecha)[-1]
