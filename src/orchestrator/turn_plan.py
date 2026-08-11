# -*- coding: utf-8 -*-
"""Fase A del rediseño DEC-200: el PLAN DE TURNO — clasificación pura del despacho.

QUÉ ES. El punto de decisión ÚNICO del turno conversacional (diseño
`evals/s316_rediseno_punto_decision_unico_v3.md`): una función pura que, dado el texto,
el estado, la metadata del transporte y un mapa de HECHOS resueltos por el shell,
devuelve el `TurnPlan` completo — ruta, fallback, transición de estado, política de log
y typing. El transporte (telegram_bot) EJECUTA el plan sin re-examinar el texto.

CONTRATO DE HECHOS (invariante 1 del diseño). La decisión necesita datos que viven en
la DB (¿de quién es este modelo?, ¿servimos esta marca?, la lista de marcas). El plan
los DECLARA (`plan_turn_hechos`) y el shell los trae con las MISMAS funciones y cachés
de hoy, sin decidir nada (`telegram_bot._resolver_hechos` — test de mecanicidad). La
degradación inventario→RAG es una decisión DEL PLAN, expresada como `fallback_ruta`.

PUREZA con pereza controlada: los cores de resolución de marca aceptan la lista de
marcas como secuencia (plan: inyectada desde hechos) o como CALLABLE (la guardia de
grupo −1, fuente activa de la fase A, mantiene su fetch perezoso post-regex — el
pre-gate barato que evita 0,54 s de httpx frío por mensaje). Una sola implementación
para ambos llamadores = sin drift.

FASE A (vigente): la guardia −1 sigue siendo la fuente ACTIVA de invalidación; el plan
la calcula pero el despachador NO la aplica (v3 §5 — una fuente por fase). La lógica
portada se verifica aquí como función pura contra snapshots pre-guardia.

Orden de la cascada = el de `handle_message` HOY, byte-equivalente
(`tests/test_s316e_fase_a_equivalencia.py`, escrito ANTES del refactor y verde sobre
el código previo): cortesía → catálogo → marca(modelo→mismatch/no-servida; sin
modelo→no-servida/inventario) → 5-bis dinámico → feedback → conversacional.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Mapping, Sequence

from ..rag import retriever as _retriever
from ..rag.retriever import _MANUFACTURER_ALIASES, resolve_manufacturer_alias

# --- patrones (movidos VERBATIM de telegram_bot; re-exportados allí) ----------

_GREETING_PATTERNS = re.compile(
    r"^(hola|hey|buenas|buenos\s*días|buenas\s*tardes|buenas\s*noches|"
    r"saludos|qué\s*tal|que\s*tal|hi|hello)[\s!.,?]*$",
    re.IGNORECASE,
)
_THANKS_PATTERNS = re.compile(
    r"^(gracias|muchas\s*gracias|genial|perfecto|ok|vale|entendido|"
    r"de\s*acuerdo|recibido|thanks|thank\s*you)[\s!.,?]*$",
    re.IGNORECASE,
)
_BYE_PATTERNS = re.compile(
    r"^(adiós|adios|hasta\s*luego|chao|nos\s*vemos|bye)[\s!.,?]*$",
    re.IGNORECASE,
)
_CATALOG_PATTERNS = re.compile(
    r"(qué\s+(productos?|modelos?|equipos?|detectores?|centrales?|fabricantes?|marcas?|empresas?)\s+(tienes|hay|tenéis|tienen|soporta)|"
    r"(listado|catálogo|catalogo|lista)\s+de\s+(productos?|modelos?|equipos?|fabricantes?|marcas?)|"
    r"para\s+qué\s+(productos?|modelos?|equipos?|fabricantes?|marcas?)\s+tienes\s+información|"
    r"qué\s+información\s+tienes|"
    r"qué\s+tienes)",
    re.IGNORECASE,
)
_ENUM_FABRICANTE = re.compile(
    r"(qu[eé]|cu[aá]l(?:es)?)\s+(productos?|modelos?|equipos?|centrales?|detectores?|"
    r"manuales?|documentaci[oó]n|informaci[oó]n)[^?]{0,40}"
    r"\b(tienes|ten[eé]is|tienen|hay|dispones?|dispon[eé]is|disponen|"
    r"soportas?|cubres?|conoces)\s*\??\s*$"
    r"|\b(listado|lista|cat[aá]logo|inventario)\s+de\s+"
    r"(productos?|modelos?|equipos?|detectores?|centrales?|manuales?|documentaci[oó]n)\b"
    r"|(what|which)\s+(?:[\w-]+\s+){0,2}(products?|models?|equipment|panels?|detectors?)"
    r"[^?]{0,40}\b(do\s+you\s+(have|know|support|cover)|are\s+(there|available))\s*\??\s*$"
    r"|\b(list|catalog(?:ue)?|inventory)\s+of\s+(?:[\w-]+\s+){0,2}"
    r"(products?|models?|equipment|detectors?|panels?)\b",
    re.IGNORECASE,
)
_PREGATE_INVENTARIO = re.compile(
    r"\b(productos?|modelos?|equipos?|centrales?|detectores?|manuales?|"
    r"documentaci[oó]n|informaci[oó]n|listado|lista|cat[aá]logo|inventario|"
    r"products?|models?|equipment|panels?|detectors?|list|catalog|inventory)\b",
    re.IGNORECASE,
)
_FEEDBACK_PATTERNS = re.compile(
    r"(no\s+es\s+correcto|incorrecto|está\s+mal|esta\s+mal|"
    r"eso\s+no\s+es|el\s+manual\s+dice\s+otra\s+cosa|"
    r"error\s+en\s+la\s+respuesta|dato\s+erróneo|dato\s+erroneo|"
    r"respuesta\s+incorrecta|información\s+incorrecta|informacion\s+incorrecta)",
    re.IGNORECASE,
)
_MANUFACTURER_NAMES = re.compile(
    r"\b(notifier|honeywell|siemens|bosch|esser|kilsen|cerberus|"
    r"tyco|johnson\s*controls|simplex|edwards|kidde|hochiki|"
    r"apollo|nittan|morley|ziton|argus|fenwal|minimax|"
    r"system\s*sensor|gamewell|vigilant|autronica|schrack|"
    r"detnov|securiton|pfannenberg|spectrex|lda)\b",
    re.IGNORECASE,
)
_SWITCH_FRASE = re.compile(
    r"\b(?:pasemos|pasamos|pasa|cambiemos|cambiamos|cambiando|saltemos|"
    r"hablemos|hablando)\b[^,.;:?!]*?\ba\b"
    r"|\bahora\s+(?:con|para|de|el|los|las)\b"
    r"|\by\s+ahora\b",
    re.IGNORECASE,
)
_MARCAS_AMBIGUAS = frozenset({"fuego"})
_VOCABULARIO_DOMINIO = frozenset({
    "fuego", "incendio", "incendios", "alarma", "alarmas", "central", "centrales",
    "detector", "detectores", "sirena", "sirenas", "pulsador", "pulsadores", "zona",
    "zonas", "lazo", "bucle", "panel", "humo", "temperatura", "extincion", "extinción",
    "evacuacion", "evacuación", "bateria", "batería", "aviso", "avisador",
})

MarcasDB = Sequence[str] | Callable[[], Sequence[str]] | None


def _lista(marcas_db: MarcasDB) -> Sequence[str] | None:
    """Resuelve el proveedor perezoso; None = lista no disponible (fail-open)."""
    if callable(marcas_db):
        try:
            return marcas_db() or []
        except Exception:                          # noqa: BLE001 — nunca bloquea
            return None
    return marcas_db


def _intencion_inventario(query: str, marca: str | None = None) -> bool:
    """¿La consulta pide el INVENTARIO? Regex estático + la variante con el nombre
    del fabricante («catálogo de securiton»), que no puede pre-compilarse."""
    if _ENUM_FABRICANTE.search(query):
        return True
    if marca:
        return bool(re.search(
            rf"\b(listado|lista|cat[aá]logo|inventario)\s+(de\s+)?{re.escape(marca)}\b",
            query, re.IGNORECASE,
        ))
    return False


def marca_en_texto(query: str, marcas_db: MarcasDB) -> str | None:
    """Core PURO de `_marca_en_consulta` (5-bis): alias curados → nombre completo →
    primera palabra única ≥4 chars. Idéntico al original; la lista se inyecta."""
    for alias, real in _MANUFACTURER_ALIASES.items():
        if re.search(rf"\b{re.escape(alias)}\b", query, re.IGNORECASE):
            return real
    marcas = _lista(marcas_db)
    if marcas is None:
        return None
    primeras: dict[str, list[str]] = {}
    for nombre in marcas:
        primeras.setdefault(nombre.split()[0].lower(), []).append(nombre)
    for nombre in marcas:
        if re.search(rf"\b{re.escape(nombre)}\b", query, re.IGNORECASE):
            return nombre
        primera = nombre.split()[0]
        if (len(primera) >= 4 and len(primeras[primera.lower()]) == 1
                and re.search(rf"\b{re.escape(primera)}\b", query, re.IGNORECASE)):
            return nombre
    return None


def marca_mencionada(texto: str, marcas_db: MarcasDB) -> str | None:
    """Resolución ESTRICTA para la decisión de invalidación (guardia/plan): nombre
    COMPLETO con frontera, sin heurística de primera-palabra, sin marcas ambiguas."""
    m = _MANUFACTURER_NAMES.search(texto)
    if m and m.group(0).lower() not in _MARCAS_AMBIGUAS:
        return m.group(0)
    marcas = _lista(marcas_db)
    if marcas is None:
        return None
    for marca in sorted(marcas, key=len, reverse=True):
        if marca.lower() in _MARCAS_AMBIGUAS:
            continue
        if re.search(rf"\b{re.escape(marca)}\b", texto, re.IGNORECASE):
            return marca
    return None


def marca_destino(query: str, marcas_db: MarcasDB) -> str | None:
    """La marca a la que el usuario DECLARA cambiar, o None. POSICIONAL (dúo s316):
    «pasemos de Kidde a Morley» resuelve Morley — la cola tras la frase de switch."""
    m = _SWITCH_FRASE.search(query)
    if m:
        destino = marca_mencionada(query[m.end():], marcas_db)
        if destino:
            return destino
    # el pre-gate barato PRIMERO (dúo s316: sin él, el fetch de marcas costaba 0,54 s
    # en frío en cada mensaje sin switch — la razón de ser de _PREGATE_INVENTARIO)
    if not _PREGATE_INVENTARIO.search(query):
        return None
    unica = marca_mencionada(query, marcas_db)
    if unica:
        otras = {mm.group(0).lower() for mm in _MANUFACTURER_NAMES.finditer(query)
                 if mm.group(0).lower() not in _MARCAS_AMBIGUAS}
        if len(otras) <= 1 and _intencion_inventario(query, unica):
            return unica
    return None


def modelos_reales(query: str) -> list[str]:
    """`extract_product_models` sin códigos NO-producto NI normativos (dúo s316:
    RS-485 y NFPA-13 —que está en el catálogo COMO MODELO— suprimían la guardia)."""
    from .conversation_policy import NON_PRODUCT_CODES
    from .conversation_policy_impl import _NORMATIVE_CODE_RE

    fuera = {c.upper().replace("-", "").replace(" ", "") for c in NON_PRODUCT_CODES}
    return [m for m in (_retriever.extract_product_models(query) or [])
            if m.upper().replace("-", "").replace(" ", "") not in fuera
            and not _NORMATIVE_CODE_RE.fullmatch(m.strip())]


# --- el contrato del plan -----------------------------------------------------

_TIPOS_HECHO = frozenset({"marca_de_modelo", "marca_servida", "lexico_marcas"})


@dataclass(frozen=True)
class Hecho:
    """Un dato que el plan necesita y el shell resuelve. Los args son TOKENS
    (modelo del detector / marca de un regex o del léxico), nunca texto libre —
    y se VALIDA (dúo s316d rondas 7-8: el vector real de un shell «mecánico» era
    colar texto como arg; la disciplina nominal no basta, Sol ronda 8)."""
    tipo: str
    arg: str = ""

    def __post_init__(self):
        if self.tipo not in _TIPOS_HECHO:
            raise ValueError(f"tipo de hecho desconocido: {self.tipo!r}")
        if len(self.arg) > 64 or "\n" in self.arg:
            raise ValueError("el arg de un hecho es un TOKEN corto, no texto libre")


@dataclass(frozen=True)
class Meta:
    """Metadata del transporte que la decisión necesita (dúo s316d: la exclusión de
    replies es restricción PAGADA de s316b; la fuente restringe las rutas en voz)."""
    es_reply: bool = False
    fuente: str = "texto"          # "texto" | "voz"


PRESERVAR = "preservar"
INVALIDAR = "invalidar"


@dataclass(frozen=True)
class TurnPlan:
    ruta: str
    fallback_ruta: str | None = None
    transicion: str = PRESERVAR
    transicion_marca: str | None = None       # marca destino si INVALIDAR
    log_consulta: bool = False                # SOLO query_logs (la persistencia propia
                                              # de cada ruta —feedback— es del handler)
    typing: bool = False
    datos: Mapping[str, str] = field(default_factory=dict)


def _necesita_lexico_para_invalidar(texto: str, estado_modelos: Sequence[str],
                                    meta: Meta) -> bool:
    """¿La decisión de invalidación necesitará la lista de marcas? Réplica EXACTA del
    camino perezoso de la guardia: solo si hay señal (switch o pregate) Y el regex
    curado no resuelve ya la marca en el tramo relevante."""
    if meta.es_reply or not estado_modelos:
        return False
    m = _SWITCH_FRASE.search(texto)
    if m:
        cand = _MANUFACTURER_NAMES.search(texto[m.end():])
        if not (cand and cand.group(0).lower() not in _MARCAS_AMBIGUAS):
            return True                       # cola sin marca curada → hará falta la DB
    if _PREGATE_INVENTARIO.search(texto):
        cand = _MANUFACTURER_NAMES.search(texto)
        if not (cand and cand.group(0).lower() not in _MARCAS_AMBIGUAS):
            return True
    return False


def plan_turn_hechos(texto: str, estado_modelos: Sequence[str],
                     meta: Meta) -> frozenset[Hecho]:
    """Pasada 1 (pura): qué hechos necesita la cascada para ESTE texto. Replica los
    cortocircuitos de hoy — una cortesía o un catálogo no piden nada a la DB."""
    necesita: set[Hecho] = set()
    if _necesita_lexico_para_invalidar(texto, estado_modelos, meta):
        necesita.add(Hecho("lexico_marcas"))
    if (_GREETING_PATTERNS.match(texto) or _THANKS_PATTERNS.match(texto)
            or _BYE_PATTERNS.match(texto) or _CATALOG_PATTERNS.search(texto)):
        return frozenset(necesita)
    m = _MANUFACTURER_NAMES.search(texto)
    if m:
        mencionada = m.group(0)
        modelos = _retriever.extract_product_models(texto)
        if modelos:
            necesita.add(Hecho("marca_de_modelo", modelos[0]))
            necesita.add(Hecho("marca_servida", mencionada))
        else:
            necesita.add(Hecho("marca_servida", mencionada))
    elif _PREGATE_INVENTARIO.search(texto) \
            and not _retriever.extract_product_models(texto):
        necesita.add(Hecho("lexico_marcas"))
    return frozenset(necesita)


def _decidir_transicion(texto: str, estado_modelos: Sequence[str], meta: Meta,
                        marcas_db: MarcasDB) -> tuple[str, str | None]:
    """El predicado de la guardia #70, como función pura (las restricciones PAGADAS de
    s316b-c intactas: replies fuera; precisión-primero; marcas ambiguas; normativos;
    exencion de misma marca con identidad directa). PROPAGA sus excepciones: el
    fail-open con warning es del LLAMADOR (la guardia loggea «no aplicada», HEAD-parity;
    plan_turn preserva en silencio — alli la transicion esta enmascarada en fase A)."""
    if True:
        if meta.es_reply or not estado_modelos:
            return PRESERVAR, None
        destino = marca_destino(texto, marcas_db)
        if not destino or modelos_reales(texto):
            return PRESERVAR, None
        marcas_estado = {_retriever.classify_model_manufacturer(mm)
                         for mm in estado_modelos}
        marcas_estado.discard(None)
        if not marcas_estado:
            return PRESERVAR, None
        from .conversation_policy_impl import DeterministicConversationPolicy

        d = destino.lower()
        if DeterministicConversationPolicy._same_manufacturer(
                [d], tuple(estado_modelos)) or \
                any(d == (mm or "").lower() for mm in marcas_estado):
            return PRESERVAR, None
        return INVALIDAR, destino


def plan_turn(texto: str, estado_modelos: Sequence[str], meta: Meta,
              hechos: Mapping[Hecho, object]) -> TurnPlan:
    """Pasada 2 (pura): el plan completo. Cascada = `handle_message` de hoy, en orden."""
    lexico = hechos.get(Hecho("lexico_marcas"))
    try:
        transicion, t_marca = _decidir_transicion(
            texto, estado_modelos, meta, lexico)  # type: ignore[arg-type]
    except Exception:                          # noqa: BLE001 — plan total: fail-open
        transicion, t_marca = PRESERVAR, None

    def _plan(**kw) -> TurnPlan:
        return TurnPlan(transicion=transicion, transicion_marca=t_marca, **kw)

    # meta.fuente=="voz" NO tiene rama propia en fase A: la voz sigue entrando por su
    # llamada explícita a la guardia + _process_query (v3 §2 — expandirla al plan es
    # una decisión de producto de fase B, y una rama aquí sería código muerto, Sol r8).

    if _GREETING_PATTERNS.match(texto):
        return _plan(ruta="cortesia_saludo")
    if _THANKS_PATTERNS.match(texto):
        return _plan(ruta="cortesia_gracias")
    if _BYE_PATTERNS.match(texto):
        return _plan(ruta="cortesia_adios")
    if _CATALOG_PATTERNS.search(texto):
        return _plan(ruta="catalogo", log_consulta=True, typing=True)

    _post_marca = "feedback" if _FEEDBACK_PATTERNS.search(texto) else "conversacional"
    m = _MANUFACTURER_NAMES.search(texto)
    if m:
        mencionada = m.group(0)
        modelos = _retriever.extract_product_models(texto)
        if modelos:
            modelo = modelos[0]
            real = hechos.get(Hecho("marca_de_modelo", modelo))
            if real:
                if str(real).lower() != resolve_manufacturer_alias(mencionada).lower():
                    return _plan(ruta="mismatch", log_consulta=True,
                                 datos={"modelo": modelo, "marca_real": str(real),
                                        "marca_mencionada": mencionada})
                # misma marca → sigue la cascada (feedback → RAG), como hoy
            else:
                if not hechos.get(Hecho("marca_servida", mencionada)):
                    return _plan(ruta="marca_no_servida", log_consulta=True,
                                 datos={"marca_mencionada": mencionada})
                # índice desincronizado (TECH_DEBT #49) → cascada
        else:
            if not hechos.get(Hecho("marca_servida", mencionada)):
                return _plan(ruta="marca_no_servida", log_consulta=True,
                             datos={"marca_mencionada": mencionada})
            if _intencion_inventario(texto, mencionada):
                return _plan(ruta="inventario", fallback_ruta=_post_marca,
                             log_consulta=True, datos={"marca": mencionada})
            # marca servida sin intención de inventario → cascada
    elif _PREGATE_INVENTARIO.search(texto) \
            and not _retriever.extract_product_models(texto):
        marca_db = marca_en_texto(texto, lexico)  # type: ignore[arg-type]
        if marca_db and _intencion_inventario(texto, marca_db):
            return _plan(ruta="inventario", fallback_ruta=_post_marca,
                         log_consulta=True, datos={"marca": marca_db})

    if _FEEDBACK_PATTERNS.search(texto):
        return _plan(ruta="feedback")
    return _plan(ruta="conversacional", typing=True)
