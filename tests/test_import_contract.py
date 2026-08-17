"""El blueprint de arquitectura como INVARIANTE de CI, no como disciplina (s300).

Contrato que se fija aquí — y por qué en un test y no en un doc: las fronteras de
`src/` las escriben varias manos (sesiones, lanes, modelos distintos); un mapa que solo
vive en `docs/` se degrada en silencio. Este fichero ES el contrato: sus constantes son
la matriz de dependencias, las excepciones vigentes (cada una con ancla y trigger de
retiro) y la cuarentena de la isla-harness. Misma filosofía que la ventana RGPD (la
garantía vive en el motor): aquí la arquitectura vive en el CI.

  · MATRIZ de paquetes: qué paquete puede importar de cuál (pocas reglas, duras);
  · EXCEPCIONES vigentes: E2/E6 violan la matriz (E1 retirada en L1/s309); E3a-b violan la CUARENTENA de la
    lane vetada (su celda rag→rag es legal; E3c retirada en L2c/s313); E4/E5 son los 2 ciclos deliberados. El
    trinquete exige que EXISTAN (retirarlas obliga a borrarlas de aquí, en el diff);
  · CUARENTENA de lane vetada: `rerank_pool_coverage` (vetada bajo todo perfil C1) solo
    es importable desde sus 2 deudores declarados (post-split L2c/s313: el motor vive
    en `pool_selection` y la reserva viva en `obligation_warning`);
  · ISLA-HARNESS en cuarentena LÓGICA: los 35 módulos que solo scripts/tests importan
    no pueden ser importados por el producto — la garantía estructural llega HOY; el
    movimiento físico a `harness/` (L2a) es legibilidad, no seguridad;
  · NOMBRES PROHIBIDOS: `src/` no importa nada cuyo primer segmento sea `harness`,
    `scripts`, `tests` o `evals` — la regla nace CERRADA (sin constante de excepciones
    donde apuntar), así que vale también para el `harness/` que aún no existe;
  · PRECONDICIÓN: 0 imports dinámicos Y 0 `importlib` en `src/` — es lo que hace
    fiable este análisis estático, y el propio test lo re-verifica. Alcance honesto:
    esto corta el ACCIDENTE y la deriva; una evasión deliberada (exec, loaders ad-hoc)
    no es detectable estáticamente y la frontera contra eso es la revisión, no este
    test.

Censo base y veredictos: workflow s300 + dúo (2 rondas), cifras de control al pie.
"""

import ast
from pathlib import Path
from typing import NamedTuple

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "src"

# --------------------------------------------------------------------- la matriz
# Paquete → paquetes de los que PUEDE importar. Todo lo no listado = prohibido.
# "raiz" = módulos sueltos de src/ (config, logging_db, release_profiles, version).
ALLOWED = {
    "raiz": {"raiz"},
    "ingestion": {"raiz", "ingestion"},
    "rag": {"raiz", "ingestion", "rag"},
    "reingest": {"raiz", "ingestion", "reingest"},
    "orchestrator": {"raiz", "rag", "orchestrator"},
    "bot": {"raiz", "rag", "orchestrator", "bot"},
}
# Y una regla que la matriz implica pero conviene nombrar: NADIE importa `bot`
# (transporte puro consumidor — hoy 0 aristas entrantes, y así se queda).


class Exc(NamedTuple):
    importador: str      # módulo que viola
    importado: str       # módulo importado (un stem bare de scripts/ también valdría)
    regla: str
    retiro: str          # el lote/decisión que la elimina — al retirarla, BORRAR de aquí


# Las CUATRO excepciones vigentes (6 aristas; E1 retirada en L1/s309, E3c en L2c/s313).
# Lista EXACTA a nivel módulo→módulo, verificada
# adversarialmente contra el árbol (s300): el contrato nace verde con estas y cero más.
EXCEPCIONES = frozenset({
    # E1 — RETIRADA (L1/s309): catalog_store graduado a src/rag/, import relativo
    # estático. El trinquete solo encoge: esta lista pasó de 6 a 5.
    # E2 · embedder.py:160 (lazy pero corre en CADA query v2) — el producto ejecuta un
    # módulo del pipeline offline B8. Retiro: embed.py → src/ingestion/ (L3).
    # La excepción es por FORMA canónica a propósito: reescribir el import como
    # `from src.reingest import embed` (misma dependencia) pone el test rojo — se usa
    # la forma de aquí o se retira la arista, no se re-fraseá (dúo s300).
    Exc("src.ingestion.embedder", "src.reingest.embed",
        "ingestion-no-importa-reingest", "L3: embed.py a src/ingestion/"),
    # E3a-b · los 2 deudores restantes de la lane vetada tras el split L2c/s313
    # (E3c —must_preserve— retirada: su import function-local migró a
    # obligation_warning/pool_selection). Solo queda el import en cuarentena de la
    # selectora vetada `select_rerank_pool_coverage` (+ LANE en E3b).
    Exc("src.rag.document_local_coverage", "src.rag.rerank_pool_coverage",
        "cuarentena-lane", "muerte de la lane vetada (C1 la veta bajo todo perfil)"),
    Exc("src.rag.post_rerank_coverage", "src.rag.rerank_pool_coverage",
        "cuarentena-lane", "muerte de la lane vetada (C1 la veta bajo todo perfil)"),
    # E6 · logging_db.py:15 — la raíz transversal importa dominio (runtime_trace).
    # Retiro: inyección del validador como callable, post-L3 (con dúo: zona telemetría).
    Exc("src.logging_db", "src.rag.runtime_trace",
        "raiz-no-importa-dominio", "post-L3: inyectar el validador"),
})

# E4/E5 · los 2 ciclos deliberados, ambos con al menos un lado function-local y motivo
# comentado in-situ. E4: el lado impl→interface es TOP-LEVEL a propósito
# (conversation_policy_impl.py:61) — el lazy es el otro (conversation_policy.py:242-245):
# que nadie «arregle» el ciclo lazificando el lado equivocado. E5: ambos lados
# function-local para mantener document_local fuera del closure de coverage_c1_v1.
CICLOS_PERMITIDOS = frozenset({
    frozenset({"src.orchestrator.conversation_policy",
               "src.orchestrator.conversation_policy_impl"}),
    frozenset({"src.rag.document_local_coverage", "src.rag.post_rerank_coverage"}),
})

# L1/s309: E1 retirada → CERO mutaciones de sys.path permitidas en src/. El conjunto
# vacío es el estado FINAL del contrato, no un placeholder.
SYS_PATH_EXCEPCIONES: set = set()

# Lane vetada bajo todo perfil C1 (release_profiles.py) — importable SOLO por sus
# deudores E3a-b (post-split L2c/s313). scripts/ y tests/ son libres (no los mira
# este contrato).
CUARENTENA = {
    "src.rag.rerank_pool_coverage": {
        "src.rag.document_local_coverage",
        "src.rag.post_rerank_coverage",
    },
}

# La ISLA-HARNESS: 35 módulos que NINGÚN módulo vivo de src/ importa (solo scripts/ y
# tests/). Cuarentena lógica desde HOY: el producto no puede cablearlos por accidente.
# El movimiento físico a harness/ (L2a) los sacará de src/; entonces esta constante se
# vacía y la regla pasa a ser la propia matriz (src no importa harness).
# `fake_convo_store` NO está aquí: es fake first-class exportado por
# src/orchestrator/__init__.py (alcanzable en runtime vía el paquete).
ISLA = frozenset({
    # 31 de src/rag
    "src.rag.visual_gold", "src.rag.principal_visual_gold",
    "src.rag.multisource_visual_gold", "src.rag.source_unit_gold",
    "src.rag.planner_holdout_gold", "src.rag.holdout_evidence",
    "src.rag.planner_support_review", "src.rag.evidence_units",
    "src.rag.evidence_units_v2", "src.rag.evidence_selector",
    "src.rag.evidence_coverage_verifier", "src.rag.decomposed_evidence_planner",
    "src.rag.decomposed_evidence_planner_v2", "src.rag.decomposed_synthesis",
    "src.rag.clause_bound_synthesis", "src.rag.sharded_unit_selector",
    "src.rag.omission_correction", "src.rag.query_evidence_compiler",
    "src.rag.query_evidence_compiler_v2", "src.rag.query_evidence_compiler_v3",
    "src.rag.query_evidence_obligations", "src.rag.typed_relations",
    "src.rag.typed_relations_v2", "src.rag.quantitative_claim_contract",
    "src.rag.relation_complete_highlights", "src.rag.frontier_visual_schemas",
    "src.rag.frontier_visual_runtime", "src.rag.frontier_visual_runtime_v2",
    "src.rag.frontier_visual_runtime_v3", "src.rag.procedure_bundle_coverage",
    "src.rag.reference_edge_coverage",
    # 4 de src/reingest
    "src.reingest.chunk_provenance", "src.reingest.extraction_derivation",
    "src.reingest.retrieval_policy", "src.reingest.superscript_overlay",
})


# ------------------------------------------------------------------ el recolector


def _modulo_de(path: Path) -> str:
    rel = path.relative_to(REPO).with_suffix("")
    partes = list(rel.parts)
    if partes[-1] == "__init__":
        partes = partes[:-1]
    return ".".join(partes)


def _paquete(mod: str) -> str:
    partes = mod.split(".")
    if len(partes) < 2:
        return "raiz"                      # src/__init__.py
    # "src.orchestrator" (el __init__ del paquete) pertenece a SU paquete, no a la raíz
    if (SRC / partes[1]).is_dir():
        return partes[1]
    return "raiz"                          # módulo suelto de src/ (config, logging_db…)


def _recolectar():
    """Una pasada AST sobre src/: aristas módulo→módulo (top-level Y function-local —
    con 0 imports dinámicos y 0 TYPE_CHECKING, toda arista estática es de runtime),
    imports de stems externos (scripts/), mutaciones de sys.path e imports dinámicos."""
    modulos = {}
    for path in sorted(SRC.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        modulos[_modulo_de(path)] = path
    nombres = set(modulos)
    paquetes_src = {m for m in nombres if (SRC / Path(*m.split(".")[1:]) ).is_dir()} | {"src"}
    stems_scripts = {p.stem for p in (REPO / "scripts").glob("*.py")}

    aristas = set()            # (importador, importado_modulo_src)
    externas = set()           # (importador, stem_de_scripts) — bare, vía sys.path
    prohibidos = set()         # (importador, nombre) con 1er segmento harness/scripts/…
    sys_path_mut = set()       # rutas relativas con sys.path.insert/append
    dinamicos = set()          # módulos con __import__/import_module/importlib

    def _resolver(base_mod, node):
        objetivo = []
        if isinstance(node, ast.Import):
            for alias in node.names:
                objetivo.append(alias.name)
        else:  # ImportFrom
            if node.level:
                partes = base_mod.split(".")
                # nivel 1 dentro de un módulo = su paquete; __init__ ya viene sin sufijo
                ancla = partes[: len(partes) - node.level] if modulos[base_mod].name != "__init__.py" \
                    else partes[: len(partes) - node.level + 1]
                prefijo = ".".join(ancla + ([node.module] if node.module else []))
            else:
                prefijo = node.module or ""
            for alias in node.names:
                objetivo.append(f"{prefijo}.{alias.name}" if prefijo else alias.name)
                objetivo.append(prefijo)
        return [o for o in objetivo if o]

    # Primeros segmentos SIEMPRE prohibidos en src/ (dúo s300): la regla nace CERRADA y
    # cubre el `harness/` que aún no existe — sin esto, vaciar ISLA tras L2a dejaría a
    # src/ libre de importar harness sin poner nada rojo. `importlib` va con ellos:
    # prohibirlo entero cierra el alias-evasión (`from importlib import x as y`).
    RAICES_PROHIBIDAS = {"harness", "scripts", "tests", "evals"}

    for mod, path in modulos.items():
        arbol = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(arbol):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                for candidato in _resolver(mod, node):
                    raiz = candidato.split(".")[0]
                    if candidato in nombres and candidato != mod:
                        aristas.add((mod, candidato))
                    elif candidato in paquetes_src and candidato not in ("src", mod):
                        aristas.add((mod, candidato))
                    elif raiz in RAICES_PROHIBIDAS:
                        prohibidos.add((mod, candidato))
                    elif raiz == "importlib":
                        dinamicos.add(mod)
                    elif raiz in stems_scripts:
                        # Colisión stem-vs-lib DELIBERADAMENTE ruidosa: si alguien crea
                        # scripts/<nombre-de-lib>.py, este test se pone rojo ESPURIO —
                        # falla FP, nunca FN, y ese nombre ya era un smell (dúo s300).
                        externas.add((mod, raiz))
            elif isinstance(node, ast.Call):
                f = node.func
                nombre = f.id if isinstance(f, ast.Name) else (
                    f.attr if isinstance(f, ast.Attribute) else "")
                if nombre == "__import__" or nombre == "import_module":
                    dinamicos.add(mod)
                if (isinstance(f, ast.Attribute) and f.attr in ("insert", "append")
                        and isinstance(f.value, ast.Attribute) and f.value.attr == "path"
                        and isinstance(f.value.value, ast.Name) and f.value.value.id == "sys"):
                    sys_path_mut.add(path.relative_to(REPO).as_posix())
    return modulos, aristas, externas, prohibidos, sys_path_mut, dinamicos


MODULOS, ARISTAS, EXTERNAS, PROHIBIDOS, SYS_PATH_MUT, DINAMICOS = _recolectar()
_EXC_ARISTAS = {(e.importador, e.importado) for e in EXCEPCIONES}


def _sccs():
    """Tarjan sobre el grafo módulo→módulo (solo nodos de src/)."""
    grafo = {}
    for a, b in ARISTAS:
        if a in MODULOS and b in MODULOS:
            grafo.setdefault(a, set()).add(b)
    indice, low, en_pila, pila, sccs = {}, {}, set(), [], []
    contador = [0]

    def visitar(v):
        indice[v] = low[v] = contador[0]
        contador[0] += 1
        pila.append(v)
        en_pila.add(v)
        for w in grafo.get(v, ()):
            if w not in indice:
                visitar(w)
                low[v] = min(low[v], low[w])
            elif w in en_pila:
                low[v] = min(low[v], indice[w])
        if low[v] == indice[v]:
            comp = set()
            while True:
                w = pila.pop()
                en_pila.discard(w)
                comp.add(w)
                if w == v:
                    break
            if len(comp) > 1:
                sccs.append(frozenset(comp))

    import sys as _sys
    limite = _sys.getrecursionlimit()
    _sys.setrecursionlimit(max(limite, len(MODULOS) * 4 + 100))
    try:
        for v in list(MODULOS):
            if v not in indice:
                visitar(v)
    finally:
        _sys.setrecursionlimit(limite)
    return sccs


# ----------------------------------------------------------------------- tests


def test_precondicion_sin_imports_dinamicos():
    """Lo que hace VÁLIDO todo lo demás: sin `__import__`/`import_module` NI `importlib`
    (entero — prohibirlo cierra el alias-evasión) en src/, el grafo estático es el de
    runtime para todo lo no-deliberado. Un import dinámico nuevo invalida el análisis
    entero — por eso es fallo aquí, no una curiosidad."""
    assert not DINAMICOS, (
        f"imports dinámicos/importlib en src/ (invalidan el contrato): {sorted(DINAMICOS)}"
    )


def test_src_no_importa_raices_prohibidas():
    """`harness`/`scripts`/`tests`/`evals` como nombre importado: prohibido SIN
    constante de excepciones — la regla nace cerrada y ya gobierna el `harness/` que
    L2a creará. (La vía bare-stem de scripts/ vive en el test de abajo — sin excepciones desde L1/s309.)"""
    assert not PROHIBIDOS, (
        "src/ importa raíces prohibidas:\n  "
        + "\n  ".join(f"{a} → {b}" for a, b in sorted(PROHIBIDOS))
    )


def test_matriz_de_paquetes():
    violaciones = []
    for a, b in sorted(ARISTAS):
        pa, pb = _paquete(a), _paquete(b)
        if pb in ALLOWED.get(pa, set()):
            continue
        if (a, b) in _EXC_ARISTAS:
            continue
        violaciones.append(f"{a} → {b} ({pa}→{pb} prohibido)")
    assert not violaciones, (
        "aristas fuera de la matriz (¿frontera nueva? decídela en el blueprint y "
        "añádela a ALLOWED, o retírala — NO añadas excepciones sin dúo):\n  "
        + "\n  ".join(violaciones)
    )


def test_src_no_importa_scripts_ni_muta_sys_path():
    fuera = {(a, b) for a, b in EXTERNAS} - _EXC_ARISTAS
    assert not fuera, f"src/ importa de scripts/ fuera de excepción: {sorted(fuera)}"
    mutaciones = SYS_PATH_MUT - SYS_PATH_EXCEPCIONES
    assert not mutaciones, f"mutación de sys.path fuera de excepción: {sorted(mutaciones)}"


def test_sin_ciclos_nuevos():
    """Toda SCC>1 debe ser EXACTAMENTE uno de los 2 ciclos permitidos — un ciclo
    conocido que CRECE (SCC de 3 que contenga un par permitido) también es fallo."""
    actuales = {frozenset(s) for s in _sccs()}
    nuevas = actuales - CICLOS_PERMITIDOS
    assert not nuevas, f"ciclos NUEVOS en src/: {[sorted(s) for s in nuevas]}"


def test_cuarentena_de_lane_vetada():
    for vetado, permitidos in CUARENTENA.items():
        importadores = {a for a, b in ARISTAS if b == vetado}
        intrusos = importadores - permitidos
        assert not intrusos, (
            f"{sorted(intrusos)} importan la lane vetada {vetado} — solo los deudores "
            f"E3a-b pueden, hasta la muerte de la lane"
        )


def test_la_isla_esta_en_cuarentena():
    """Ningún módulo VIVO de src/ importa un módulo isla. Es la garantía estructural
    contra la acreción (los experimentos sedimentaban en src/ porque nada lo impedía);
    el movimiento físico a harness/ (L2a) es legibilidad encima de esto, no al revés."""
    intrusos = [
        f"{a} → {b}" for a, b in sorted(ARISTAS)
        if b in ISLA and a not in ISLA
    ]
    assert not intrusos, (
        "el producto importa módulos de la isla-harness (¿cableado accidental? si es "
        "un nacimiento deliberado de lane, sácalo de ISLA en el mismo PR, con dúo):\n  "
        + "\n  ".join(intrusos)
    )


def test_trinquete_las_excepciones_siguen_vivas():
    """La lista solo ENCOGE: si un lote retira una arista, este test obliga a borrar su
    excepción en el mismo diff — cero zombis, y el retiro queda visible en el PR."""
    zombis = []
    for e in EXCEPCIONES:
        existe = (e.importador, e.importado) in ARISTAS or \
                 (e.importador, e.importado) in EXTERNAS
        if not existe:
            zombis.append(f"{e.importador} → {e.importado} (retiro: {e.retiro})")
    assert not zombis, (
        "excepciones ZOMBI (la arista ya no existe — retíralas del contrato):\n  "
        + "\n  ".join(zombis)
    )
    ciclos = {frozenset(s) for s in _sccs()}
    muertos = [sorted(c) for c in CICLOS_PERMITIDOS if c not in ciclos]
    assert not muertos, f"ciclos permitidos que ya no existen (retíralos): {muertos}"


def test_cifras_de_control():
    """Ancla el censo s300 con tolerancia CERO en lo que protege: si estas cifras se
    mueven, que sea en un diff que las explique. Fricción DELIBERADA anti-acreción:
    un módulo nuevo en src/ paga un toque aquí."""
    # L1/s309: 113→114 (catalog_store graduado). L2b/s311: 114→115 (src/flags.py,
    # el registro declarativo). L2c/s313: 115→117 — split del doble-inquilino
    # rerank_pool_coverage en pool_selection (motor compartido) + obligation_warning
    # (reserva viva); el residual queda como lane vetada en cuarentena. Cero código
    # nuevo: solo bloques movidos.
    # 117→118 (s316e): + orchestrator/turn_plan.py — el punto de decisión único del
    # despacho conversacional (fase A del rediseño DEC-200). PRODUCTO deliberado, no
    # instrumento: handle_message despacha lo que este módulo decide.
    # 118→119 (s316g): + orchestrator/intent_llm.py — el clasificador del lever
    # INTENT_LLM (DEC-203b): prompt/parser fuente única para gate y serving. Producto.
    # 119→120 (s317): + reingest/revision_gate.py — puerta de revisiones
    # supersedidas de la ingesta (#73): señales de edición + cruce contra
    # documents. Producto del pipeline (lo consume ingest_new), no instrumento.
    # 120→121 (s317/#72): + http_pool.py (raíz) — cliente HTTP compartido de
    # proceso; 55 sitios de serving migrados del patrón cliente-por-llamada
    # (perfil: 14 clientes/consulta = ~10 s/turno). Producto transversal.
    # 121→122 (s323/fase C): + rag/identidad_gate.py — los invariantes de
    # coherencia corpus↔catálogo (#80/#81). Vive en src/ y no en scripts/ porque
    # la INGESTA lo ejecuta en cada corrida: es lógica de producción. El primer
    # cableado lo puso en scripts/ y ESTE MISMO contrato lo cazó.
    # 122→123 (s324d/#87): + ingestion/page_content.py — la guarda de MARKDOWN
    # DEGENERADO (LlamaParse devolvió md=34 chars y text=3.708 en el mismo JSON y
    # el `md or text` dejó un documento en 47 chars). Es lógica de PRODUCCIÓN: la
    # ejecuta la ingesta (reingest/pipeline.py) en cada corrida y el serving
    # (rag/deep_lookup.py) al leer el store. Vive en `ingestion` y no en
    # `reingest` porque ESTE MISMO contrato lo cazó: `rag → reingest` está
    # prohibido y `ingestion` es el único paquete que ambos pueden importar
    # (mismo motivo por el que embed.py vive ahí).
    # 123→124 (s324e): + bot/error_taxonomy.py — la taxonomía de errores del
    # bot (clase de fallo → qué se le dice al técnico, si reintentar, con qué
    # severidad). Es PRODUCTO: la ejecuta el serving en cada excepción, desde
    # `_reportar_error` y desde la red global `add_error_handler`. Vive en
    # `bot` y no en la raíz porque sus salidas son mensajes de transporte
    # (español, texto plano para Telegram); es hoja PURA — sin I/O, sin
    # entorno y sin importar ningún SDK — para poder testearla sin red.
    assert len(MODULOS) == 124, (
        f"módulos en src/: {len(MODULOS)} (censo: 121). Si es PRODUCTO nuevo "
        f"deliberado: sube esta cifra y explica el módulo en el PR. Si es un "
        f"experimento/instrumento: NO va en src/ — su casa es scripts/ (o harness/ "
        f"tras L2a). La acreción empezaba exactamente así."
    )
    assert len(ISLA) == 35
    assert len(EXCEPCIONES) == 4   # L1/s309: E1 · L2c/s313: E3c — el trinquete solo encoge
    assert sum(1 for m in ISLA if m not in MODULOS) == 0, "ISLA cita módulos inexistentes"
