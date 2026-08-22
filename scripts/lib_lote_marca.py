# -*- coding: utf-8 -*-
"""Piezas COMPARTIDAS del lote de clasificación por vista de marca.

Nace del cierre de s336-lote (DEC-279) al parametrizar el pipeline: el método
quedó validado sobre Notifier y el contrato de la casa exige que escale a 30+
fabricantes SIN fricción por fabricante. Aquí vive lo único que de verdad se
comparte entre marcas — las rutas de recibo, la provenance DERIVADA y el
candado de vista — para que los scripts sigan siendo cada uno su etapa.

Dos decisiones con motivo, porque no son obvias:

1. **Los recibos de Notifier conservan su nombre histórico** (`s336_*_v1.json`).
   Están CITADOS en DEC-279 y en `evals/s336_resultado_v1.md`; renombrarlos
   rompería la traza de una decisión ya firmada. Las marcas nuevas llevan
   sufijo `_{marca}`. La asimetría es deliberada y se declara aquí.

2. **La provenance se DERIVA, no se escribe a mano.** La constante de s336
   llevaba incrustados los sha del GT y del censo de Notifier: correr otra
   marca con ella habría estampado en sus filas la procedencia de un gold que
   no las juzgó. Es un fallo de auditoría, no de estilo — por eso el sha sale
   del recibo que de verdad se usó en ESA corrida.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVALS = ROOT / "evals"

# La vista cuyo lote fijó el método; sus recibos son inmutables (ver docstring).
MARCA_HISTORICA = "notifier"

_ETAPAS = {
    "censo": "s336_censo_diana",
    "poblacion": "s336_poblacion",
    "elegibles": "s336_elegibles",
    "gate": "s336_gate_result",
    "escritura": "s336_escritura_result",
    "gt": "s336_gt",
}


def normaliza_marca(marca: str) -> str:
    """La MISMA normalización que usa el join de la vista, no una parecida.

    La primera versión de esta función quitaba espacios y bajaba a minúsculas —
    suficiente para «System Sensor», y divergente para todo lo demás: el join
    real hace NFKD y borra cuanto no sea `[a-z0-9]`, así que «Pepperl-Fuchs»
    daba `pepperl-fuchs` aquí y `pepperlfuchs` allí. Dos grafías de la MISMA
    vista producían rutas de recibo distintas y la guarda anti-pisado se
    saltaba sola. Reimplementar un normalizador es la forma cara de tener dos.
    """
    from src.bot.telegram_bot import _norm_marca
    return _norm_marca(marca or "")


def ruta(etapa: str, marca: str, ext: str = "json") -> Path:
    """Ruta del recibo de una etapa para una marca.

    Notifier mantiene el nombre histórico; el resto lleva sufijo de marca.
    """
    if etapa not in _ETAPAS:
        raise ValueError(f"etapa desconocida: {etapa} (conocidas: {sorted(_ETAPAS)})")
    marca = normaliza_marca(marca)
    base = _ETAPAS[etapa]
    if marca == MARCA_HISTORICA:
        return EVALS / f"{base}_v1.{ext}"
    return EVALS / f"{base}_{marca}_v1.{ext}"


def guarda_de_pisado(destino: Path, marca: str, force: bool) -> str | None:
    """Para artefactos que NO se re-escriben: censo (PRE-REGISTRA el suelo antes
    de ver resultados) y GT (el gold). Devuelve el motivo si hay que abortar.

    Re-correrlos contra el catálogo de hoy —que ya lleva las filas escritas—
    desploma la diana y pisa el artefacto cuyo sha promete la provenance de esas
    filas. Aprendido en carne propia al parametrizar.
    """
    if destino.exists() and not force:
        return (f"el recibo {destino.name} YA EXISTE. Es el artefacto citado por "
                f"la decisión del lote de «{marca}»: re-escribirlo rompe la traza "
                f"del sha que llevan sus filas. Use --force sólo si sabe que "
                f"quiere justamente eso.")
    return None


def ruta_no_destructiva(destino: Path) -> Path:
    """Para el recibo de ESCRITURA, que sí se genera en cada corrida.

    El writer es incremental por diseño (idempotente: salta lo ya clasificado),
    así que abortar sería romper su uso legítimo — pero sobrescribir tampoco
    vale: la corrida de recuperación del 22-ago machacó el recibo del lote
    original (361 filas, PASS) y su antes/después ya no era recomputable. Cada
    corrida conserva la anterior con sufijo `_rN`.
    """
    if not destino.exists():
        return destino
    n = 2
    while True:
        cand = destino.with_name(
            destino.name.replace(".json", f"_r{n}.json"))
        if not cand.exists():
            return cand
        n += 1


def ruta_gt_vigente(marca: str) -> Path:
    """El GT vigente = la versión MÁS ALTA que exista para esa marca.

    El gold se re-congela ENTERO cuando una adjudicación cambia lo que significa
    una etiqueta (DEC-126: nada de tocar sólo las filas que convienen), y las
    versiones viejas se conservan porque las decisiones las citan por sha. Quién
    juzgó una corrida no puede quedar implícito: el gate estampa en su recibo el
    fichero y el sha que usó.
    """
    marca = normaliza_marca(marca)
    base = ruta("gt", marca, "yaml")            # ..._v1.yaml
    import re as _re
    patron = base.name.replace("_v1.yaml", "_v*.yaml")
    def _num(p: Path) -> int:
        m = _re.search(r"_v(\d+)\.yaml$", p.name)
        return int(m.group(1)) if m else 0
    # Orden NUMÉRICO, no lexicográfico: con sorted() plano, `_v10` iría antes que
    # `_v9` y el gate elegiría en silencio un gold viejo — justo el «quién juzgó no
    # puede quedar implícito» fallando sin avisar.
    candidatas = sorted(base.parent.glob(patron), key=_num)
    return candidatas[-1] if candidatas else base


def sha_fichero(path: Path | str) -> str:
    """Sha corto del contenido de un recibo — la huella que va a provenance."""
    p = Path(path)
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def _relativa(path: Path | str) -> str:
    """Ruta legible en el recibo: relativa al repo cuando cuelga de él, y el
    nombre a secas cuando no (un `relative_to` pelado revienta fuera del repo)."""
    p = Path(path)
    try:
        return str(p.relative_to(ROOT))
    except ValueError:
        return p.name


def provenance(marca: str, gate_path: Path, gt_path: Path,
               censo_path: Path) -> str:
    """Provenance DERIVADA de los artefactos que juzgaron ESTA corrida.

    Nunca a mano: la constante de s336 incrustaba los sha de Notifier y habría
    viajado intacta a cualquier otra marca.
    """
    marca = normaliza_marca(marca)
    piezas = [
        f"s336 método s322b sobre la vista {marca} (pasada fable-5 + repesca "
        "dirigida + full-text + completitud de capacidad)",
        f"gate {_relativa(gate_path)}",
    ]
    if Path(gt_path).exists():
        piezas.append(f"GT {sha_fichero(gt_path)}")
    if Path(censo_path).exists():
        piezas.append(f"censo {sha_fichero(censo_path)}")
    return "; ".join(piezas)


def vista_de(cat, marca: str) -> dict[str, dict]:
    """La vista de marca indexada por id — EL join real, el mismo que sirve el
    inventario al técnico (`_productos_marca`, redirect-normalizado)."""
    from src.bot.telegram_bot import _productos_marca
    return {p["id"]: p for p in _productos_marca(cat, normaliza_marca(marca))}


def candado_de_vista(ids, cat, marca: str) -> list[str]:
    """Devuelve los ids que NO pertenecen a la vista de `marca`.

    El writer de s336 escribía todo lo elegible del recibo sin comprobar de qué
    vista salía: bastaba un `--marca` mal pasado en una etapa para escribir
    filas de una marca con el juicio de otra. Lista vacía = coherente.
    """
    vista = vista_de(cat, marca)
    return [i for i in ids if i not in vista]


def carga_recibo(path: Path | str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))
