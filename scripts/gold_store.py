#!/usr/bin/env python3
"""gold_store.py — ÚNICA puerta para leer/escribir el ruler (evals/gold_answers_v1.yaml).

Responsabilidad única: ALMACENAMIENTO + VALIDACIÓN. No verifica, no puntúa, no autora.
Sustituye los scripts throwaway (quick-fix a escala). A partir de aquí, ningún gold se
toca a mano: todo pasa por upsert()/write().

Esquema v2 es DRAFT: hasta que la rebanada vertical (2-3 golds end-to-end) lo valide,
las exigencias del v2 (atomic_facts, auditoría de localización) salen como WARNING, no
ERROR. Cuando el esquema sobreviva la rebanada, se promueven a ERROR y se endurece CI.

Validación TIERED por estado: 'verificado' exige el v2; 'cuarentena/pending' solo el
mínimo (qid/question/conducta) — así las 16 viejas conviven hasta verificarlas.

Diseño y decisiones: docs/RULER_DESIGN.md. Sin dependencias nuevas (dataclasses stdlib).

Uso CLI:
  python scripts/gold_store.py validate     # chequeo de esquema (lo corre CI)
  python scripts/gold_store.py normalize     # re-escribe en formato canónico (1 vez)
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
GOLD_PATH = ROOT / "evals" / "gold_answers_v1.yaml"

# Las 5 conductas (ver RULER_DESIGN.md §1). Las legacy se migran al verificar (Fase 1).
CONDUCTAS = {"answer", "answer-con-conflicto", "clarify", "admit", "refuse-inference"}
LEGACY_CONDUCTAS = {"ask_clarification", "admit_no_info"}
ESTADOS = {"verificado", "cuarentena", "needs_human", "pendiente"}
TIPOS_FACT = {"core", "supplementary"}
ESTADOS_FACT = {"presente", "ausente-probado"}

# split = partición del eval (embargo del held-out). Ortogonal a `estado`. Ausente = dev
# (los 22 legacy ya inspeccionados son dev por construcción; el held-out solo se puebla con
# autoría NUEVA embargada). Ver DECISIONS DEC-023.
SPLITS = {"dev", "held-out"}
# Vocabulario CONTROLADO de estratos (multi-tag). Reconcilia docs/PREREG_ab_context2gen.md +
# CATALOG_PLAN §4 + RULER_DESIGN §2. NO incluye las 5 conductas (eje `conducta_esperada`) ni
# `control-pass` (estado histórico, no propiedad de contenido → se selecciona en el A/B, no se
# hornea). Controlado (set cerrado) para que el conteo per-estrato no se rompa por typos.
# --- s50 (DEC-025): reframe — autorar por DIMENSIÓN DE FALLO, no por artefacto del chunking. ---
# --- s53 (DEC-032): consolidación §8 = reclasificación COMPLETADA (ya NO diferida). ---
# EJE DE AUTORÍA: dimensiones de fallo COGNITIVO, definibles desde la FUENTE e independientes de cómo
# el RAG extrajo. El gold se ELIGE por estas (chunks_v2 JAMÁS criterio de selección — vicio s50).
ESTRATOS_AUTORIA = {
    "multi-doc", "es-en", "conflicto-es-us", "oem-relabel", "familia-ambigua",
    # --- s51 (DEC-026): dims NUEVAS del canon (DEC-025c), source-puras → AUTORÍA.
    "conflicto-revision",   # 2 revisiones MISMO idioma del MISMO manual con un valor CAMBIADO → answer "latest-wins" (RULER §1:67)
    "sintesis-completitud", # la respuesta COMPLETA exige FUSIONAR >=2 secciones del MISMO manual (no >=2 manuales = multi-doc) → completitud intra-manual
}
# CAUSAS POST-HOC (capa extracción/chunking): se DESCUBREN al diagnosticar POR QUÉ falló un gold;
# NUNCA se usan para SELECCIONAR (exigiría mirar cómo extrajo el RAG = el vicio s50). Demotadas.
# s53 (DEC-032): tabla-matriz/scan-ocr/diagrama BAJAN aquí, completando lo que DEC-025(b) dejó
# diferido — son causas de la capa de extracción (RULER §2:156 + §7:412 las enrutan al lever #10),
# NO ejes cognitivos: el dato vive en el PDF, pero que FALLE depende de cómo LlamaParse lo extrajo.
# Discriminador limpio (dúo s53): AUTORÍA = fallo cognitivo fuente-puro; POST-HOC = causa de extracción.
ESTRATOS_POSTHOC = {"content-pobre", "fragmento-truncado", "tabla-matriz", "scan-ocr", "diagrama"}
# Vocabulario VÁLIDO = unión (los legacy con tag post-hoc —hp008 content-pobre, los tabla/scan/diagrama
# previos— siguen validando con WARNING, no error). Para autorar una dim NUEVA del canon aún sin tag
# (p.ej. `mezcla-cross-product`, RULER §0:19, n=0), AÑADE su tag a ESTRATOS_AUTORIA con su def
# (cambio-1-línea sancionado) — evaluando antes si no queda mejor como CONDUCTA (refuse-inference/clarify).
ESTRATOS = ESTRATOS_AUTORIA | ESTRATOS_POSTHOC

# Orden canónico de campos al serializar.
FIELD_ORDER = ["qid", "question", "conducta_esperada", "split", "estrato",
               "gold_answer", "atomic_facts", "citations", "notes", "confidence",
               "pdfs_used", "_provenance"]
# Campos del esquema (+ _usage, metadata legacy tolerada). raw/_needs_human_review/
# _review_note quedan FUERA a propósito → se marcan como cruft (caza hp006).
KNOWN_FIELDS = set(FIELD_ORDER) | {"_usage"}

HEADER = (
    "# === RULER (gold answers) — NO EDITAR A MANO ===\n"
    "# Editar SOLO vía scripts/gold_store.py (upsert/write).\n"
    "# Diseño, esquema y decisiones (D1-D11): docs/RULER_DESIGN.md\n"
)


@dataclass
class Issue:
    qid: str
    severity: str  # "error" | "warning"
    msg: str

    def __str__(self) -> str:
        return f"[{self.severity.upper()}] {self.qid}: {self.msg}"


def _estado(g: dict) -> str:
    return (g.get("_provenance") or {}).get("estado", "pendiente")


def _split(g: dict) -> str:
    # Embargo: split ausente = dev. Tras el retrofit, validate_entry lo exige en 'verificado'.
    return g.get("split") or "dev"


def _validate_facts(qid: str, facts) -> list[Issue]:
    out: list[Issue] = []
    if not isinstance(facts, list):
        return [Issue(qid, "error", "atomic_facts no es una lista")]
    for i, f in enumerate(facts):
        if not isinstance(f, dict) or not f.get("texto"):
            out.append(Issue(qid, "error", f"atomic_facts[{i}] sin 'texto'"))
            continue
        if f.get("tipo") not in TIPOS_FACT:
            out.append(Issue(qid, "error", f"atomic_facts[{i}].tipo inválido (core|supplementary)"))
        if f.get("estado") not in ESTADOS_FACT:
            out.append(Issue(qid, "error", f"atomic_facts[{i}].estado inválido (presente|ausente-probado)"))
    return out


def validate_entry(g: dict) -> list[Issue]:
    qid = g.get("qid", "(sin qid)") if isinstance(g, dict) else "(no-dict)"
    if not isinstance(g, dict):
        return [Issue(qid, "error", "la entrada no es un mapa")]
    out: list[Issue] = []

    # Errores estructurales (toda entrada).
    for f in ("qid", "question", "conducta_esperada"):
        if not g.get(f):
            out.append(Issue(qid, "error", f"falta campo obligatorio '{f}'"))
    estado = _estado(g)
    if estado not in ESTADOS:
        out.append(Issue(qid, "error", f"_provenance.estado '{estado}' inválido"))
    for f in g:
        if f not in KNOWN_FIELDS:
            out.append(Issue(qid, "warning", f"campo inesperado '{f}' (cruft a limpiar)"))

    # split (embargo dev/held-out): validar si presente; obligatorio en 'verificado'.
    sp = g.get("split")
    if sp is not None and sp not in SPLITS:
        out.append(Issue(qid, "error", f"split '{sp}' inválido {sorted(SPLITS)}"))
    if estado == "verificado" and sp is None:
        out.append(Issue(qid, "error", "verificado sin 'split' (dev|held-out obligatorio)"))
    # estrato (multi-tag de vocabulario controlado; lista vacía permitida = sin marcar).
    estr = g.get("estrato")
    if estr is not None:
        if not isinstance(estr, list):
            out.append(Issue(qid, "error", "estrato debe ser una lista de tags"))
        else:
            for t in estr:
                if t not in ESTRATOS:
                    out.append(Issue(qid, "error", f"estrato '{t}' fuera del vocabulario {sorted(ESTRATOS)}"))
            # Guard OPERATIVO anti-vicio (s50/DEC-025): un tag POST-HOC en `estrato` = usar una causa
            # del chunking como eje de autoría. Legacy (hp008) lo tiene → WARNING, no ERROR (no rompe).
            # Para autoría NUEVA es la señal de re-vicio (el procedimiento P4/§2 solo no bastó en s50).
            posthoc = [t for t in estr if t in ESTRATOS_POSTHOC]
            if posthoc:
                out.append(Issue(qid, "warning",
                                 f"estrato post-hoc {posthoc} como eje de autoría (s50/DEC-025; "
                                 "tabla/scan/diagrama s53/DEC-032): causa de la extracción, NO criterio "
                                 "de selección — legacy OK, nueva autoría = re-vicio"))

    cond = g.get("conducta_esperada")
    # Validación TIERED.
    if estado == "verificado":
        if cond not in CONDUCTAS:
            out.append(Issue(qid, "error",
                             f"conducta '{cond}' no está en las 5 válidas {sorted(CONDUCTAS)}"))
        prov = g.get("_provenance") or {}
        if not prov.get("localizacion"):
            out.append(Issue(qid, "warning",
                             "verificado sin _provenance.localizacion (DRAFT: warning)"))
        # Enforcement del procedimiento (DEC-024): evidencia mínima documentada para 'verificado'.
        # Control de DOCUMENTACIÓN (olvido→visible), no de ejecución (esa = dúo P3). RULER_DESIGN §2.
        if not prov.get("metodo"):
            out.append(Issue(qid, "error",
                             "verificado sin _provenance.metodo (evidencia del procedimiento: render + cross-model)"))
        if not prov.get("verificado_por"):
            out.append(Issue(qid, "error", "verificado sin _provenance.verificado_por"))
        facts = g.get("atomic_facts")
        if not facts:
            out.append(Issue(qid, "warning",
                             "verificado sin atomic_facts (pendiente retrofit; DRAFT: warning)"))
        else:
            out += _validate_facts(qid, facts)
    else:
        if cond not in CONDUCTAS and cond not in LEGACY_CONDUCTAS:
            out.append(Issue(qid, "warning", f"conducta '{cond}' no estándar (se migra al verificar)"))
    return out


def _read_raw(path: Path = GOLD_PATH) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return list(yaml.safe_load(f) or [])


def validate(golds: list[dict] | None = None) -> list[Issue]:
    golds = _read_raw() if golds is None else golds
    out: list[Issue] = []
    seen: set = set()
    for g in golds:
        out += validate_entry(g)
        qid = g.get("qid") if isinstance(g, dict) else None
        if qid in seen:
            out.append(Issue(str(qid), "error", "qid duplicado"))
        seen.add(qid)
    return out


def load(path: Path = GOLD_PATH, strict: bool = False) -> list[dict]:
    golds = _read_raw(path)
    errors = [i for i in validate(golds) if i.severity == "error"]
    if strict and errors:
        raise ValueError("golds con errores:\n" + "\n".join(map(str, errors)))
    return golds


def get(qid: str, path: Path = GOLD_PATH) -> dict | None:
    return next((g for g in load(path) if g.get("qid") == qid), None)


def verified(path: Path = GOLD_PATH, include_heldout: bool = False) -> list[dict]:
    # EMBARGO en la PUERTA (no en cada harness): held-out EXCLUIDO por defecto. Los 4
    # consumidores del juez (atomic_scorer/judge_kruns/judge_disagreement/
    # characterize_factual_variance) heredan el filtro sin cambios. La corrida final única
    # del A/B pasa include_heldout=True. Hoy es no-op (0 held-out). Ver DECISIONS DEC-023.
    out = [g for g in load(path) if _estado(g) == "verificado"]
    if not include_heldout:
        out = [g for g in out if _split(g) != "held-out"]
    return out


def quarantined(path: Path = GOLD_PATH) -> list[dict]:
    return [g for g in load(path) if _estado(g) != "verificado"]


def dev(path: Path = GOLD_PATH) -> list[dict]:
    return [g for g in verified(path, include_heldout=True) if _split(g) == "dev"]


def heldout(path: Path = GOLD_PATH) -> list[dict]:
    return [g for g in verified(path, include_heldout=True) if _split(g) == "held-out"]


# --- Serialización canónica ---
class _BlockDumper(yaml.SafeDumper):
    pass


def _str_representer(dumper, data):
    # Bloque literal (|) para multilínea → legible y sin bugs de comillas.
    style = "|" if "\n" in data else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=style)


_BlockDumper.add_representer(str, _str_representer)


def _ordered(g: dict) -> dict:
    return ({k: g[k] for k in FIELD_ORDER if k in g}
            | {k: g[k] for k in g if k not in FIELD_ORDER})


def write(golds: list[dict], path: Path = GOLD_PATH) -> None:
    body = yaml.dump([_ordered(g) for g in golds], Dumper=_BlockDumper,
                     allow_unicode=True, sort_keys=False, width=100)
    text = HEADER + "\n" + body
    # Safety: la normalización NO debe alterar el contenido (round-trip semántico).
    reparsed = list(yaml.safe_load(text))
    if reparsed != golds:
        raise AssertionError("write() alteró el contenido — abortado (revisar serialización)")
    Path(path).write_text(text, encoding="utf-8")


def upsert(gold: dict, path: Path = GOLD_PATH) -> None:
    # La PUERTA valida ANTES de escribir (DEC-024): un gold con errores de esquema NO entra.
    # Antes upsert solo round-trip-eaba (write); el enforcement vivía solo en validate/CI.
    errs = [i for i in validate_entry(gold) if i.severity == "error"]
    if errs:
        raise ValueError("upsert abortado — gold con errores de esquema:\n"
                         + "\n".join(map(str, errs)))
    golds = load(path)
    qid = gold["qid"]
    for i, g in enumerate(golds):
        if g.get("qid") == qid:
            golds[i] = gold
            break
    else:
        golds.append(gold)
    write(golds, path)


def _main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    cmd = sys.argv[1] if len(sys.argv) > 1 else "validate"
    if cmd == "validate":
        issues = validate()
        errs = [i for i in issues if i.severity == "error"]
        warns = [i for i in issues if i.severity == "warning"]
        for i in issues:
            print(i)
        print(f"\n{len(errs)} error(es), {len(warns)} warning(s) en {len(_read_raw())} golds.")
        return 1 if errs else 0
    if cmd == "normalize":
        write(load())
        print("Normalizado a formato canónico.")
        return 0
    print(f"comando desconocido: {cmd!r} (validate|normalize)")
    return 2


if __name__ == "__main__":
    sys.exit(_main())
