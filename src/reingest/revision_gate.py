# -*- coding: utf-8 -*-
"""s317 — Puerta de REVISIÓN de la ingesta (TECH_DEBT #73, fail-closed dirigido).

El sha256 prueba bytes distintos, no información nueva: una revisión ANTIGUA del
mismo manual tiene otro sha por definición, y el dedup por contenido la dejaba
pasar (s316d: INS570-3 con el corpus en issue 8; P/N ...-03 con el corpus en -04
— 2 de 2 candidatos «nuevos» eran revisiones viejas, cazadas A MANO). Ingestar
una revisión vieja junto a la nueva = dos documentos ACTIVOS del mismo manual
sin cadena de supersede, y el bot puede citar el caducado a un técnico.

DISEÑO v1.1 (tras dúo r13 — Sol 8 · Fable 7; precisión-primero: el daño de un
falso BLOQUEO es perder un manual legítimo, lección de la guardia #70):

  1. Señales de edición $0, extraídas del texto CRUDO (Fable r13 F1: sobre el
     texto normalizado las fechas se colaban en la TUPLA de revisión — «rev 4
     30-10-2024» daba rev=(4,30,10) y un falso bloqueo por comparación de días;
     en crudo, las revisiones multi-parte reales usan `.`/`_` y las fechas
     usan espacios/guiones, y el valor de la señal se EXCINDE antes de podar).
     Familias muestreadas del corpus real (s317):
       · pn_utc    — «00-3301-501-4000-04_r004_…»: último grupo del P/N =
                     revisión, CONFIRMADA por _rNNN con el MISMO valor.
       · rnnn      — «3102984-ml_r003_…»: el token solo; base = nombre sin él.
       · issue     — «4188-1124-ES issue 6», «D391 Issue 3», «INS570-8».
       · iss_fecha — «ISS 07NOV23» (Notifier, portada/filename; ddMMMyy).
       · rev       — numérica («rev 4», «Rev 3.2», «rev1_1_4») y letra
                     («RevB», «Rev. A.1»); JAMÁS comparadas entre sí.
       · fecha     — «_202503_» AAAAMM (portal Casmar).
       · v         — «MNDT951_v5-87».
  2. La base CONSERVA idioma (es/en/pt/ml…): una edición ES jamás supersede a
     la PT por NOMBRE. Límite declarado (Sol r13 M1): el lookup canónico es
     (manufacturer, family, language) y esta puerta solo ve filenames — si un
     mismo (base, formato) del corpus aparece con `language` DISTINTO en
     `documents`, se degrada a NO_COMPARABLE en vez de bloquear.
  3. El corpus se indexa por (base, formato) → TODAS las revisiones activas
     (Sol r13 M4/Fable F7: quedarse una sola dependía del orden de llegada);
     el cruce compara contra la MÁXIMA de la MISMA aridad.
  4. Contrato #73 LITERAL: corpus >= candidata ⇒ BLOQUEADO (r13, Sol M2/Fable
     F5 — la v1 dejaba pasar la misma-revisión-bytes-distintos; el override
     --ignorar-revision existe para el caso adjudicado).
  5. La señal ELEGIDA se PERSISTE en `documents.revision` (columna diseñada
     para esto en migrations/001, hoy siempre NULL) — sin esto, una revisión
     solo-detectable-por-portada quedaba INVISIBLE para lotes futuros (Sol r13
     C2). `indice_corpus` lee filename + columna.
  6. PORTADA: SOLO la familia INS (span-independiente). Las familias cuya base
     es «portada-menos-span» jamás casarían con bases-filename (Fable F3) —
     peso muerto retirado, no prometido. Recorte a 600 chars (zona de título)
     y guarda anti-cita («ver INS570-2» de un doc hermano no dispara —
     Fable F4; las remisiones internas son frecuentes: 329 en el censo s294).
  7. Fail-open declarado: sin señal legible ⇒ procede LISTADO como «edición no
     verificable». Evidencia en conflicto (filename↔portada, P/N↔_rNNN) ⇒ la
     señal se retira, nunca bloquea.

El llamador pagina `documents` COMPLETO (PostgREST corta a 1000 en silencio —
clase #72; una página perdida = un supersede invisible) y cruza INTRA-LOTE
(Sol r13 C1/Fable F2: dos revisiones del mismo manual en el mismo lote pasaban
juntas; el par vivo 202503/202512 pudo nacer exactamente así).
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

_IDIOMAS = frozenset({"es", "en", "pt", "fr", "de", "it", "ml", "ing", "esp",
                      "spa", "eng", "sp", "ar"})

_MESES = {"jan": 1, "ene": 1, "feb": 2, "mar": 3, "apr": 4, "abr": 4,
          "may": 5, "jun": 6, "jul": 7, "aug": 8, "ago": 8, "sep": 9,
          "oct": 10, "nov": 11, "dec": 12, "dic": 12}

BLOQUEADO = "BLOQUEADO"
SUPERSEDE = "SUPERSEDE"
NO_COMPARABLE = "NO_COMPARABLE"
SIN_SENAL = "SIN_SENAL"

_PORTADA_CHARS = 600      # zona de título; el cuerpo cita documentos hermanos
_ANTI_CITA = re.compile(r"(?:\bver\b|\bsee\b|\bconsulte?\b|\brefer\b)[^\n]{0,40}$")


@dataclass(frozen=True)
class Senal:
    """Una señal de edición: (base normalizada, revisión comparable, formato)."""
    base: str
    rev: tuple
    formato: str        # pn_utc | rnnn | issue | iss_fecha | rev_num | rev_letra | fecha | v
    fuente: str         # filename | portada | columna


@dataclass(frozen=True)
class Veredicto:
    resultado: str      # BLOQUEADO | SUPERSEDE | NO_COMPARABLE | SIN_SENAL
    motivo: str
    contra: str | None = None       # source_pdf_filename del doc que decide
    senal: Senal | None = None      # la señal que decidió (para persistirla)


@dataclass
class _Entrada:
    """Todas las revisiones ACTIVAS de una (base, formato) del corpus."""
    revisiones: list[tuple[tuple, str]] = field(default_factory=list)
    idiomas: set[str] = field(default_factory=set)


def _normalizar(texto: str) -> str:
    plano = unicodedata.normalize("NFKD", texto)
    plano = "".join(c for c in plano if not unicodedata.combining(c)).lower()
    return re.sub(r"[\s_\-.]+", " ", plano).strip()


def _sin_extension(filename: str) -> str:
    return re.sub(r"\.pdf$", "", filename.strip(), flags=re.IGNORECASE)


def _podar_sufijos_cms(tokens: list[str], hash_con_digitos: bool = False) -> list[str]:
    """Poda por la DERECHA sufijos del CMS: hash hex de 4 («ac3d»; con
    `hash_con_digitos` también «1065» — solo familia fecha, el patrón
    _AAAAMM_XXXX del portal lo garantiza) y contadores «0»/«1»."""
    tokens = list(tokens)
    while tokens:
        t = tokens[-1]
        es_hash = re.fullmatch(r"[0-9a-f]{4}", t) and (
            hash_con_digitos or not t.isdigit())
        if es_hash or re.fullmatch(r"[01]", t):
            tokens.pop()
        else:
            break
    return tokens


def _podar_fechas(tokens: list[str]) -> list[str]:
    """Retira RACHAS de fecha de la BASE: un año (1990-2049, Fable F6) y hasta
    2 tokens numéricos de 1-2 cifras contiguos por lado («30 10 2024»,
    «01 2026»). El VALOR de la señal ya fue excindido antes (Fable F1), así
    que la racha no puede comerse un número de revisión."""
    fuera: set[int] = set()
    for i, t in enumerate(tokens):
        if re.fullmatch(r"(?:19[6-9]\d|20[0-4]\d)", t):
            fuera.add(i)
            for j in range(i - 1, max(i - 3, -1), -1):
                if j in fuera or not re.fullmatch(r"\d{1,2}", tokens[j]):
                    break
                fuera.add(j)
            for j in range(i + 1, min(i + 3, len(tokens))):
                if not re.fullmatch(r"\d{1,2}", tokens[j]):
                    break
                fuera.add(j)
    return [t for i, t in enumerate(tokens) if i not in fuera]


# --- extractores (sobre texto CRUDO en minúsculas; Fable r13 F1) -------------
# Multi-parte SOLO con `.`/`_` como separador de continuación: las revisiones
# reales son «rev 3.2» / «rev1_1_4»; las fechas van con espacio/guión y quedan
# fuera de la tupla por construcción.

# OJO: sobre texto CRUDO `\b` no sirve — el `_` es \w y «_v5-20» / «\nins570-3»
# no tienen frontera de palabra. Prefijo de separador explícito (no capturante).
_SEP = r"(?:^|[\s_\-.(])"
_RE_RNNN = re.compile(rf"{_SEP}r(\d{{2,3}})(?=$|[\s_\-])")
_RE_PN = re.compile(r"^([0-9][0-9a-z]{1,3}(?:-[0-9a-z]{2,6}){2,5})-(\d{2})(?=[\s_\-]|$)")
_RE_ISSUE = re.compile(rf"{_SEP}(?:issue|iss)[\s_.\-]*(\d{{1,2}})(?![a-z0-9])")
_RE_ISS_FECHA = re.compile(
    rf"{_SEP}iss[\s_.\-]*(\d{{2}})"
    r"(jan|ene|feb|mar|apr|abr|may|jun|jul|aug|ago|sep|oct|nov|dec|dic)"
    r"(\d{2})(?![0-9])")
_RE_REV_NUM = re.compile(
    rf"{_SEP}rev(?:ision)?[\s_.\-]*(\d{{1,2}})"
    r"(?:[._](\d{1,2}))?(?:[._](\d{1,2}))?(?![a-z0-9])")
_RE_REV_LETRA = re.compile(
    rf"{_SEP}rev(?:ision)?[\s_.\-]*([a-z])(?![a-z])(?:[.\s](\d{{1,2}}))?")
_RE_FECHA = re.compile(r"\b(20[2-4]\d)(0[1-9]|1[0-2])\b")   # sobre texto_norm
_RE_V = re.compile(rf"{_SEP}v(\d{{1,2}})[-._](\d{{1,3}})(?![0-9])")
_RE_INS = re.compile(rf"{_SEP}(ins\d{{3}})[\s\-.](\d{{1,2}})(?![0-9])")


def _base_de(crudo_low: str, span: tuple[int, int],
             hash_con_digitos: bool = False) -> str:
    """Base = el crudo SIN el span de la señal, normalizado y podado."""
    recortado = crudo_low[:span[0]] + " " + crudo_low[span[1]:]
    tokens = _podar_fechas(_normalizar(recortado).split())
    return " ".join(_podar_sufijos_cms(tokens, hash_con_digitos))


def _extraer(crudo: str, fuente: str, familias: frozenset[str] | None = None) -> list[Senal]:
    senales: list[Senal] = []
    low = crudo.lower()

    def activa(f: str) -> bool:
        return familias is None or f in familias

    m_r = _RE_RNNN.search(low)
    m_pn = _RE_PN.match(low)
    if activa("pn_utc") and m_pn and m_r and int(m_pn.group(2)) == int(m_r.group(1)):
        senales.append(Senal(base=_normalizar(m_pn.group(1)),
                             rev=(int(m_pn.group(2)),),
                             formato="pn_utc", fuente=fuente))
    if activa("rnnn") and m_r and not (m_pn and int(m_pn.group(2)) != int(m_r.group(1))):
        senales.append(Senal(base=_base_de(low, m_r.span()),
                             rev=(int(m_r.group(1)),),
                             formato="rnnn", fuente=fuente))

    m = _RE_ISS_FECHA.search(low)
    if activa("iss_fecha") and m:
        senales.append(Senal(base=_base_de(low, m.span()),
                             rev=(2000 + int(m.group(3)), _MESES[m.group(2)],
                                  int(m.group(1))),
                             formato="iss_fecha", fuente=fuente))
    elif activa("issue"):
        m = _RE_ISSUE.search(low)
        if m:
            senales.append(Senal(base=_base_de(low, m.span()),
                                 rev=(int(m.group(1)),),
                                 formato="issue", fuente=fuente))

    if activa("rev"):
        m = _RE_REV_NUM.search(low)
        if m:
            partes = tuple(int(g) for g in m.groups() if g is not None)
            senales.append(Senal(base=_base_de(low, m.span()), rev=partes,
                                 formato="rev_num", fuente=fuente))
        else:
            m = _RE_REV_LETRA.search(low)
            if m and m.group(1) not in _IDIOMAS:
                rev = (ord(m.group(1)),) + (
                    (int(m.group(2)),) if m.group(2) else ())
                senales.append(Senal(base=_base_de(low, m.span()), rev=rev,
                                     formato="rev_letra", fuente=fuente))

    if activa("fecha"):
        norm = _normalizar(low)
        m = _RE_FECHA.search(norm)
        if m:
            recortado = norm[:m.start()] + " " + norm[m.end():]
            tokens = _podar_fechas(_normalizar(recortado).split())
            senales.append(Senal(
                base=" ".join(_podar_sufijos_cms(tokens, hash_con_digitos=True)),
                rev=(int(m.group(1)), int(m.group(2))),
                formato="fecha", fuente=fuente))

    if activa("v"):
        m = _RE_V.search(low)
        if m:
            senales.append(Senal(base=_base_de(low, m.span()),
                                 rev=(int(m.group(1)), int(m.group(2))),
                                 formato="v", fuente=fuente))

    if activa("ins"):
        m = _RE_INS.search(low)
        if m:
            senales.append(Senal(base=m.group(1), rev=(int(m.group(2)),),
                                 formato="issue", fuente=fuente))

    return senales


def senales_de_filename(filename: str) -> list[Senal]:
    return _extraer(_sin_extension(filename), "filename")


_FAMILIAS_PORTADA = frozenset({"ins"})


def senales_de_portada(texto_portada: str) -> list[Senal]:
    """SOLO familias span-independientes (hoy: INS — el caso real s316d). Las
    demás tendrían base = portada-menos-span, que jamás casa con una base de
    filename (Fable F3). Recorte a la zona de título + guarda anti-cita
    (Fable F4: «ver INS570-2» de un doc hermano no puede bloquear)."""
    if not texto_portada:
        return []
    recorte = texto_portada[:_PORTADA_CHARS]
    low = recorte.lower()
    senales = []
    for s in _extraer(recorte, "portada", _FAMILIAS_PORTADA):
        m = re.search(rf"{re.escape(s.base)}", low)
        if m and _ANTI_CITA.search(low[:m.start()]):
            continue                      # citado, no titulado
        senales.append(s)
    return senales


def senales_documento(filename: str, texto_portada: str | None) -> list[Senal]:
    """Señales combinadas. Dos fuentes que AFIRMAN la misma (base, formato) con
    valores DISTINTOS → se retiran ambas (evidencia en conflicto no bloquea)."""
    todas = senales_de_filename(filename) + senales_de_portada(texto_portada or "")
    por_clave: dict[tuple[str, str], list[Senal]] = {}
    for s in todas:
        por_clave.setdefault((s.base, s.formato), []).append(s)
    resultado: list[Senal] = []
    for grupo in por_clave.values():
        if len({s.rev for s in grupo}) > 1:
            continue
        resultado.append(grupo[0])
    return resultado


# --- persistencia de la señal (documents.revision — Sol r13 C2) --------------

def serializar_senal(s: Senal) -> str:
    """Forma legible Y parseable para `documents.revision` (la columna existe
    desde migrations/001 con este propósito y estaba siempre NULL)."""
    if s.formato == "rev_letra":
        rev = chr(s.rev[0]).upper() + ("." + ".".join(map(str, s.rev[1:]))
                                       if len(s.rev) > 1 else "")
    else:
        rev = ".".join(map(str, s.rev))
    return f"[{s.formato}] {s.base} = {rev}"


_RE_SERIAL = re.compile(r"^\[(\w+)\] (.+) = (.+)$")


def parsear_senal(texto: str | None) -> Senal | None:
    m = _RE_SERIAL.match((texto or "").strip())
    if not m:
        return None
    formato, base, rev_txt = m.group(1), m.group(2), m.group(3)
    try:
        if formato == "rev_letra":
            partes = rev_txt.split(".")
            rev = (ord(partes[0].lower()),) + tuple(int(p) for p in partes[1:])
        else:
            rev = tuple(int(p) for p in rev_txt.split("."))
    except (ValueError, IndexError):
        return None
    return Senal(base=base, rev=rev, formato=formato, fuente="columna")


# --- índice del corpus y cruce -----------------------------------------------

def indice_corpus(filas_documents: list[dict]) -> dict[tuple[str, str], _Entrada]:
    """(base, formato) → TODAS las revisiones activas + idiomas vistos.
    Fuentes: filename Y la columna `revision` persistida (una revisión que solo
    la portada delató sigue visible para lotes futuros — Sol r13 C2)."""
    indice: dict[tuple[str, str], _Entrada] = {}
    for fila in filas_documents:
        fn = fila.get("source_pdf_filename") or ""
        idioma = (fila.get("language") or "").strip().lower()
        senales = senales_de_filename(fn)
        persistida = parsear_senal(fila.get("revision"))
        if persistida is not None:
            senales.append(persistida)
        vistas: set[tuple[str, str, tuple]] = set()
        for s in senales:
            clave = (s.base, s.formato)
            firma = (*clave, s.rev)
            if firma in vistas:
                continue
            vistas.add(firma)
            entrada = indice.setdefault(clave, _Entrada())
            entrada.revisiones.append((s.rev, fn))
            if idioma:
                entrada.idiomas.add(idioma)
    return indice


def indice_de_senales(pares: list[tuple[Senal, str]]) -> dict[tuple[str, str], _Entrada]:
    """Índice INTRA-LOTE (Sol r13 C1/Fable F2): señales de los OTROS candidatos
    del mismo lote — dos revisiones del mismo manual llegando juntas ya no
    pasan las dos."""
    indice: dict[tuple[str, str], _Entrada] = {}
    for s, fn in pares:
        entrada = indice.setdefault((s.base, s.formato), _Entrada())
        entrada.revisiones.append((s.rev, fn))
    return indice


def cruzar(senales: list[Senal],
           indice: dict[tuple[str, str], _Entrada],
           igualdad_bloquea: bool = True) -> Veredicto:
    """Veredicto del candidato contra un índice (corpus o intra-lote).
    Prioridad: BLOQUEADO > SUPERSEDE > NO_COMPARABLE > SIN_SENAL.

    `igualdad_bloquea`: contra el CORPUS la igualdad bloquea (contrato #73:
    corpus >= candidata ⇒ no ingesta — el duplicado activo de la misma edición
    es exactamente la clase #4). INTRA-LOTE es False: dos candidatos con la
    misma revisión se bloquearían mutuamente — ahí la igualdad degrada a
    NO_COMPARABLE (listado, ojo humano)."""
    if not senales:
        return Veredicto(SIN_SENAL,
                         "sin señal de edición legible (filename+portada)")
    encontrados: list[Veredicto] = []
    for s in senales:
        entrada = indice.get((s.base, s.formato))
        if entrada is None:
            continue
        if len(entrada.idiomas) > 1:
            # (Sol r13 M1) misma base con `language` distinto en documents:
            # el nombre no distingue idioma → no se bloquea a ciegas.
            encontrados.append(Veredicto(
                NO_COMPARABLE,
                f"base «{s.base}» [{s.formato}] existe en varios idiomas "
                f"({', '.join(sorted(entrada.idiomas))}) — revisar a mano",
                entrada.revisiones[0][1], s))
            continue
        comparables = [(r, fn) for r, fn in entrada.revisiones
                       if len(r) == len(s.rev)]
        if not comparables:
            r0, fn0 = entrada.revisiones[0]
            encontrados.append(Veredicto(
                NO_COMPARABLE,
                f"base «{s.base}» [{s.formato}]: revisión de aridad distinta "
                f"({_fmt(s.rev)} vs {_fmt(r0)}) — revisar a mano", fn0, s))
            continue
        rev_max, fn_max = max(comparables)
        if rev_max == s.rev and not igualdad_bloquea:
            encontrados.append(Veredicto(
                NO_COMPARABLE,
                f"base «{s.base}» [{s.formato}]: misma revisión "
                f"{_fmt(s.rev)} que otro candidato del lote — revisar a mano",
                fn_max, s))
        elif rev_max >= s.rev:
            # Contrato #73 LITERAL (r13): corpus >= candidata ⇒ BLOQUEADO —
            # también la misma revisión con bytes distintos (duplicado activo).
            det = (f"misma revisión {_fmt(s.rev)} ya activa (bytes distintos)"
                   if rev_max == s.rev else
                   f"revisión {_fmt(s.rev)} supersedida por {_fmt(rev_max)}")
            encontrados.append(Veredicto(
                BLOQUEADO, f"base «{s.base}» [{s.formato}]: {det}",
                fn_max, s))
        else:
            encontrados.append(Veredicto(
                SUPERSEDE,
                f"base «{s.base}» [{s.formato}]: {_fmt(s.rev)} > "
                f"{_fmt(rev_max)} — candidata a cadena de supersede (#4)",
                fn_max, s))
    for resultado in (BLOQUEADO, SUPERSEDE, NO_COMPARABLE):
        for v in encontrados:
            if v.resultado == resultado:
                return v
    return Veredicto(SIN_SENAL,
                     "señales presentes pero ninguna base coincide con el corpus")


def _fmt(rev: tuple) -> str:
    return ".".join(str(x) for x in rev)
