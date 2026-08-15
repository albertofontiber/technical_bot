# -*- coding: utf-8 -*-
"""s322f — Encoge la SECCIÓN 1 del packet E2: las 1.235 ALTAS del detector.

QUÉ HACE (y por qué, que es lo que importa dentro de seis meses)
================================================================
El packet `evals/s320_e2_snapshot_diff_v1.json` propone dar de alta 1.235
términos en el snapshot vivo del detector (`data/model_catalog.json`). Ese
packet se congeló el 12-ago y desde entonces el catálogo gobernado se ha movido
(s322d/s322e: retags, cirugía FD2705, split ZXr). Pedirle a Alberto que revise
1.235 filas una a una es inviable; pedirle que las apruebe en bloque sin
separar el grano de la paja es peligroso. Este script hace las dos cosas que
convierten el packet en decidible:

  (A) REFRESCO contra el estado de HOY. Una fila del packet sólo sigue siendo
      un alta válida si HOY: (1) el término sigue siendo resoluble por la puerta
      del catálogo gobernado (`_resolvable_terms` — alias revocados y productos
      retirados dejan de contar), (2) sigue ATESTADO (algún producto suyo tiene
      doc_map a documento ACTIVO con chunks servibles, o su normkey aparece como
      product_model en chunks de docs activos) y (3) el snapshot vivo NO lo
      conoce ya. Los tres son los mismos criterios con los que se generó el
      packet (`scripts/s320_e2_snapshot_derivado.py`), aplicados sobre el estado
      de hoy: si el criterio cambió de veredicto, la fila está OBSOLETA.

  (B) SPLIT POR RIESGO LÉXICO. El coste de un alta NO es simétrico: un código
      inequívoco que nadie escribe por accidente es gratis; una palabra común
      metida en el detector envenena el contexto de TODAS las consultas. El caso
      histórico del repo es el fabricante «FUEGO» (la palabra más común del
      sector). Las reglas de abajo son explícitas y auditables — cada término
      del recibo lleva la lista de reglas que disparó, así que Alberto puede
      discutir la REGLA, no la fila.

MECÁNICA REAL DEL DETECTOR que justifica las reglas (leída en src/rag/catalog.py,
no supuesta) — es la parte que hace que reglas «obvias» no basten:

  · El patrón es `\\b(core)(?!\\d)` con `core` = segmentos letra/dígito unidos por
    `[-\\s/.+]*` (CERO o más separadores). NO hay `\\b` de cierre: un término que
    acaba en letra matchea como PREFIJO de palabras más largas. «BASE» matchearía
    «bases»; «RED» matchearía «redundante». De ahí la lista de palabras comunes y
    la regla de prefijo.
  · `_base_aliases()` añade AUTOMÁTICAMENTE una forma base a todo término de 3+
    partes: dar de alta «0786-CPD-20644» crea además el alias «0786-CPD», que
    matchea CUALQUIER número de certificado de ese organismo notificado. El alta
    es más ancha de lo que aparenta → se audita la base generada, no sólo el
    término.
  · `_normkey_to_model.setdefault()`: si el normkey del alta ya existe en el
    snapshot vivo (como modelo o como alias-base generado), el alta NO añade
    detección — cambia qué forma canónica se devuelve. Eso es un cambio de
    conducta sobre una ruta que ya funciona → jamás va en bloque.
  · `all_models()` (ordenado por chunk_count desc) alimenta el vocabulario de
    Whisper, que está capado a ~1000 chars. Un alta con chunk_count=0 cae a la
    cola y NUNCA llega al dictado: el beneficio real de estas altas es la query
    ESCRITA, no la dictada. Se reporta en los hallazgos para no vender humo.

SALIDA: `evals/s322f_e2_altas_split_v1.json` — SECCIÓN 0 (bloque, un solo sí) y
SECCIÓN 1 (individual, agrupada por motivo y con evidencia junta). NO ESCRIBE
NADA MÁS: ni catálogo, ni Supabase, ni el snapshot del detector. Es una
PROPUESTA para que Alberto adjudique.

USO:
    python scripts/s322f_e2_altas_split.py            # con sondas de menciones
    python scripts/s322f_e2_altas_split.py --sin-sondas   # dry, sin HTTP extra
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=False)

from src.http_pool import abierto  # noqa: E402
from src.rag import catalog as C  # noqa: E402
from src.rag import catalog_store  # noqa: E402
from src.rag.catalog_resolver import _resolvable_terms, catalog_commit  # noqa: E402

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
KEY = os.environ["SUPABASE_SERVICE_KEY"]
H = {"apikey": KEY, "Authorization": f"Bearer {KEY}"}

PACKET = ROOT / "evals" / "s320_e2_snapshot_diff_v1.json"
RECON_E1 = ROOT / "evals" / "s320_e1_reconciliacion_censo_v1.json"
VIVO = ROOT / "data" / "model_catalog.json"
DESTINO = ROOT / "evals" / "s322f_e2_altas_split_v1.json"

# ---------------------------------------------------------------------------
# Léxico de riesgo. Deliberadamente EXPLÍCITO (no un modelo, no una heurística
# opaca): Alberto tiene que poder discutir la lista. Mezcla castellano y inglés
# porque el corpus y las consultas mezclan ambos. Todo se compara en minúsculas
# y sin acentos (misma normalización que el detector: C._fold).
# ---------------------------------------------------------------------------
PALABRAS_RIESGO = {
    # el caso histórico + el núcleo del vocabulario del sector (es)
    "fuego", "incendio", "agua", "aire", "humo", "gas", "calor", "llama",
    "chispa", "alarma", "prealarma", "aviso", "sirena", "campana", "panel",
    "central", "centralita", "modulo", "tarjeta", "placa", "detector",
    "sensor", "pulsador", "base", "zocalo", "lazo", "bucle", "zona", "red",
    "linea", "punto", "canal", "salida", "entrada", "rele", "contacto",
    "fuente", "bateria", "cargador", "tension", "corriente", "potencia",
    "aislador", "repetidor", "sounder", "flash", "optico", "termico",
    "ionico", "laser", "haz", "barrera", "aspiracion", "extincion",
    "rociador", "hidrante", "valvula", "bomba", "presion", "caudal",
    "tuberia", "boquilla", "deposito", "espuma", "polvo", "manguera",
    "puerta", "compuerta", "exutorio", "techo", "pared", "sala", "planta",
    "edificio", "sistema", "equipo", "unidad", "conjunto", "kit", "serie",
    "series", "tipo", "clase", "nivel", "modo", "estado", "prueba", "test",
    "manual", "guia", "ficha", "hoja", "tabla", "figura", "anexo", "seccion",
    "capitulo", "version", "revision", "codigo", "referencia", "articulo",
    "art", "ref", "modelo", "producto", "general", "total", "local",
    "remoto", "auto", "digital", "analogico", "convencional", "direccionable",
    "instalacion", "programacion", "mantenimiento", "averia", "supervision",
    "nuevo", "viejo", "alto", "bajo", "medio", "grande", "pequeno", "largo",
    "corto", "blanco", "negro", "rojo", "verde", "azul", "amarillo", "gris",
    "solo", "dimension", "cable", "caja", "soporte", "tapa", "carcasa",
    "alimentacion", "tuberia", "independiente", "convencionales",
    "direccionable", "monitor", "chasis", "chassis", "subcentral", "subpanel",
    "interfaz", "interface", "ampliacion", "transformador", "transformer",
    "doc", "documento", "document", "one", "two", "three", "uno", "dos",
    "tres", "cuatro", "four", "five", "accesorio", "accessory", "repuesto",
    "conmutador", "concentrador", "switch", "hub", "controlador", "controller",
    "family", "familia", "gama", "range", "procesador", "processor",
    "simulator", "simulador", "probador", "tester", "tarjetas", "conjunto",
    # inglés de manual
    "fire", "water", "smoke", "heat", "flame", "alarm", "panel", "control",
    "module", "card", "board", "detector", "sensor", "call", "point", "base",
    "loop", "zone", "line", "channel", "output", "input", "relay", "power",
    "supply", "battery", "charger", "voltage", "current", "isolator",
    "repeater", "sounder", "beacon", "strobe", "optical", "thermal", "beam",
    "aspirating", "suppression", "sprinkler", "hydrant", "valve", "pump",
    "pressure", "flow", "pipe", "nozzle", "tank", "foam", "powder", "hose",
    "door", "damper", "ceiling", "wall", "room", "floor", "building",
    "system", "unit", "assembly", "kit", "series", "type", "class", "level",
    "mode", "status", "test", "manual", "guide", "sheet", "table", "figure",
    "annex", "section", "chapter", "version", "revision", "code", "reference",
    "article", "model", "product", "general", "total", "local", "remote",
    "auto", "digital", "analogue", "analog", "conventional", "addressable",
    "installation", "programming", "maintenance", "fault", "supervisory",
    "new", "old", "high", "low", "mid", "large", "small", "long", "short",
    "white", "black", "red", "green", "blue", "yellow", "grey", "gray",
    "cable", "box", "bracket", "cover", "enclosure", "housing", "adapter",
    "standard", "waterproof", "indoor", "outdoor", "surface", "flush",
}

# Conectores de lengua natural: su presencia delata una DESCRIPCIÓN, no un
# código. El resolver ya avisa de esto ("los nombre-largo son DESCRIPCIONES de
# la extracción… venenosas como detector en prosa") pero deja pasar las que
# llevan dígito, y ahí es donde viven estas filas del packet.
CONECTORES = {"de", "del", "la", "el", "los", "las", "para", "con", "sin",
              "por", "en", "y", "o", "a", "of", "for", "with", "without",
              "the", "and", "or", "to", "in", "on", "at", "und", "fur"}

# Prefijos de norma técnica: sólo cuentan si les sigue un DÍGITO. Sin esa
# guarda, «ISO-X» (aislador Notifier real, en el packet) se clasificaría como
# norma y se perdería un alta legítima.
RE_NORMA = re.compile(
    r"^\s*(?:une[-\s]?)?(?:en|iec|iso|nfpa|bs|din|vde|nf|cei|cenelec|ul|fm|"
    r"une)[-\s/]?\d", re.I)
# Certificado CPD/CPR clásico: NNNN-CPD-NNNNN. Exige separador para no
# confundirlo con códigos comerciales que llevan «CPR» pegado (SG1910CPR,
# PY X-L-15-CPR son PRODUCTOS marcados CPR, no certificados).
RE_CERT = re.compile(r"\d{3,4}[-\s]cp[dr][-\s]?\d", re.I)
RE_CERT_DUDOSO = re.compile(r"cp[dr]\s*\d{4,}", re.I)
RE_ANIO = re.compile(r"^(19|20)\d{2}$")

# Reglas cuya evidencia SÍ cambia la decisión de Alberto: son las que dicen
# «esto podría matchear prosa». Para las demás la sonda de contenido no aporta.
REGLAS_SONDA = {"palabra-comun-o-jerga", "demasiado-corto",
                "solo-letras-sin-digitos", "prefijo-de-palabra-comun",
                "solo-digitos", "anio"}

LONG_MIN_SEGURO = 5      # caracteres útiles (alfanuméricos) mínimos
MIN_CORTO = 4            # <= esto es "demasiado corto" (criterio de la tarea)
MAX_TOKENS_CODIGO = 4    # más tokens que esto = frase, no código
MAX_CHARS_CODIGO = 24
# Puntuación que delata prosa, NO un código. El punto queda FUERA a propósito:
# 'MOD.REL-2000' y 'VSN-CRA-GSM v2.0.5' son códigos reales del catálogo.
RE_PUNT_PROSA = re.compile(r"[,;:()\[\]«»\"¡!¿?]")
RE_COMODIN = re.compile(r"(?:^|[^a-z0-9])(x{2,}|n{3,}|#+)(?:[^a-z0-9]|$)", re.I)
RE_PLACEHOLDER_PARTE = re.compile(r"^[xyzn#]{2,}$", re.I)
# Artefactos de extracción del PDF: guion suelto ('M700KAC -SG'), puntos
# suspensivos de código truncado ('PA X 10..', 'MCP3A...').
RE_ARTEFACTO = re.compile(r"\s-|-\s|-$|\.\.")
# Prefijo abreviado de catálogo ('Mod.HEF20RL', 'Ref.: 002-467', 'Art. 1555',
# 'F.A. PSU7A'): lo que identifica al equipo es lo que va DETRÁS.
RE_PREFIJO_ABREV = re.compile(r"^(mod|ref|art|doc|cod|num|p/n|pn|f\.a)\.", re.I)
RE_COLA_COMODIN = re.compile(r"x{2,}$", re.I)
# Sufijo de idioma: marca la EDICIÓN de un documento (…-KID-EN, …-VSN4-PLUS-ITA),
# no una variante de equipo. Va a individual, no se descarta: un modelo puede
# acabar en -ES por otra razón.
RE_SUF_IDIOMA = re.compile(
    r"[-_](EN|ES|SP|IT|ITA|POR|PORT|PT|FR|FRA|DE|GER|NL|GB|UK)$")


def _es_generica(s: str) -> bool:
    """Palabra del sector, tolerando plural es/en ('detectors', 'repetidores',
    'bases'). Sin esto, el plural se colaba en el bloque."""
    if s in PALABRAS_RIESGO:
        return True
    if s.endswith("es") and s[:-2] in PALABRAS_RIESGO:
        return True
    return s.endswith("s") and s[:-1] in PALABRAS_RIESGO


def _utiles(t: str) -> str:
    """Caracteres que el detector realmente usa como identidad (fold + sólo
    alfanuméricos). 'ZX-5e' -> 'zx5e' (4 útiles)."""
    return re.sub(r"[^0-9a-z]", "", C._fold(t))


def _tokens_alfa(t: str) -> list[str]:
    """Runs de letras (la misma segmentación que usa el core del detector)."""
    return re.findall(r"[a-z]+", C._fold(t))


def _partes(t: str) -> list[str]:
    """Partes separadas como las separa el propio detector/_base_aliases
    ([-\\s/.]). OJO: NO se segmenta por transición letra/dígito — esa distinción
    es la que salva a '140KIT160' (código compacto: 'KIT' va fusionado con
    dígitos, no es una palabra suelta) frente a 'AS2300 Series' o 'B501
    STANDARD BASE' (donde la palabra genérica va SUELTA y sí puede aparecer en
    prosa)."""
    return [p for p in re.split(r"[-\s/.]+", C._fold(t)) if p]


def _char_raro(t: str) -> str | None:
    """Caracteres no-ASCII que NO son letras acentuadas (guion U+2212, rayas,
    comillas tipográficas...). Rompen la intuición sobre normkey/_base_aliases
    y suelen delatar un copy-paste del PDF, no un código."""
    import unicodedata as _u
    for ch in t:
        if ord(ch) > 127 and not _u.category(ch).startswith("L"):
            return f"U+{ord(ch):04X}"
    return None


def _paginado(client, tabla: str, params: dict) -> list[dict]:
    filas, off = [], 0
    while True:
        r = client.get(f"{SUPABASE_URL}/rest/v1/{tabla}", headers=H,
                       params={**params, "offset": str(off), "limit": "1000"})
        r.raise_for_status()
        lote = r.json()
        filas.extend(lote)
        if len(lote) < 1000:
            return filas
        off += 1000


# ---------------------------------------------------------------------------
# (B) Clasificador de riesgo léxico
# ---------------------------------------------------------------------------
def clasifica(term: str, nk_vivos: dict[str, str], nk_base_vivos: dict[str, str],
              marcas: frozenset[str] = frozenset(),
              cores_vivos: dict[str, str] | None = None
              ) -> tuple[str, list[dict]]:
    """Devuelve (clase, motivos). clase ∈ {SEGURO, RIESGO, NO-PRODUCTO}.

    Se acumulan TODOS los motivos (no se corta en el primero): el recibo debe
    dejar ver por qué una fila cae a individual aunque haya varias razones, para
    que Alberto pueda relajar una regla concreta sin perder las otras.
    """
    motivos: list[dict] = []
    utiles = _utiles(term)
    tokens = [t for t in re.split(r"\s+", term.strip()) if t]
    partes = _partes(term)
    # Palabras SUELTAS = tokens separados por ESPACIO (sin la puntuación de los
    # bordes). Sólo estas cuentan como «palabra común»: '4XRFI-KIT' lleva el
    # sustantivo pegado con guion — es parte del código serigrafiado en el
    # equipo —, mientras que '5451EIS detector' lo lleva suelto, que es la marca
    # de una descripción extraída del manual.
    sueltas = [re.sub(r"^[^a-z0-9]+|[^a-z0-9]+$", "", C._fold(t))
               for t in tokens]
    sueltas = [s for s in sueltas if s]
    genericas = [s for s in sueltas if s.isalpha() and len(s) >= 3
                 and _es_generica(s)]
    # Distintiva = parte que identifica de verdad. Los tramos SÓLO numéricos no
    # cuentan: 'Art. 1555' matchea "art. 1555" en cualquier lista de despiece,
    # así que pertenece a la clase FUEGO aunque lleve un número al lado.
    distintivas = [p for p in partes
                   if len(_utiles(p)) >= 3 and not p.isdigit()
                   and p not in PALABRAS_RIESGO and p not in CONECTORES]

    # --- NO-PRODUCTO: no es un equipo, es un papel -------------------------
    if RE_NORMA.search(term):
        motivos.append({"regla": "norma-tecnica",
                        "detalle": "prefijo de norma (EN/UNE/IEC/ISO/...) "
                                   "seguido de dígito"})
    if RE_CERT.search(term):
        motivos.append({"regla": "numero-certificacion",
                        "detalle": "patrón NNNN-CPD/CPR-NNNNN (certificado de "
                                   "organismo notificado, no un modelo)"})
    if any(m["regla"] in ("norma-tecnica", "numero-certificacion")
           for m in motivos):
        return "NO-PRODUCTO", motivos

    # --- RIESGO ------------------------------------------------------------
    if RE_CERT_DUDOSO.search(term):
        motivos.append({"regla": "posible-referencia-cpr",
                        "detalle": "lleva CPD/CPR pegado a 4+ dígitos: puede "
                                   "ser DoP/certificado o un código comercial "
                                   "marcado CPR — hay que mirarlo"})
    if not any(c.isdigit() for c in utiles):
        motivos.append({"regla": "solo-letras-sin-digitos",
                        "detalle": "no es un código alfanumérico (la mezcla "
                                   "letras+dígitos es lo que hace inequívoco a "
                                   "un modelo); puede ser prefijo de palabra"})
    if not any(c.isalpha() for c in utiles):
        motivos.append({"regla": "solo-digitos",
                        "detalle": "sin letras: colisiona con cualquier cifra "
                                   "de la prosa"})
    if RE_ANIO.match(utiles):
        motivos.append({"regla": "anio", "detalle": "parece un año"})
    if len(utiles) <= MIN_CORTO:
        motivos.append({"regla": "demasiado-corto",
                        "detalle": f"{len(utiles)} caracteres útiles ({utiles!r})"})
    # Palabra común/jerga SUELTA. Dos severidades distintas, porque el riesgo
    # es distinto: si no queda NADA distintivo, el término ES una palabra del
    # sector (clase FUEGO); si hay un código distintivo al lado, el término es
    # un código con un sustantivo pegado ('5451EIS detector') — no matchea en
    # prosa, pero tampoco es un «código inequívoco» y ensucia el catálogo.
    if genericas and not distintivas:
        motivos.append({"regla": "palabra-comun-o-jerga",
                        "detalle": f"sus únicas palabras sueltas son jerga "
                                   f"PCI/común: {genericas} — clase FUEGO"})
    elif genericas:
        motivos.append({"regla": "contiene-palabra-generica",
                        "detalle": f"código + sustantivo genérico suelto "
                                   f"({genericas}): probablemente el catálogo "
                                   f"deba guardarlo sin la coletilla"})
    if RE_PUNT_PROSA.search(term):
        motivos.append({"regla": "puntuacion-de-prosa",
                        "detalle": "lleva coma/dos puntos/paréntesis: es una "
                                   "frase extraída del manual, no un código"})
    if "_" in term or re.search(
            r"\.(pdf|docx?|xlsx?|zip|exe|dll|dfs|cfg|bin|hex|txt)$", term, re.I):
        motivos.append({"regla": "parece-nombre-de-fichero",
                        "detalle": "lleva '_' o extensión de fichero: es el "
                                   "nombre de un PDF/archivo, no el código "
                                   "impreso en el equipo"})
    if marcas and sueltas and len(sueltas) > 1 and sueltas[0] in marcas:
        motivos.append({"regla": "lleva-marca-delante",
                        "detalle": f"empieza por el fabricante "
                                   f"({sueltas[0]!r}): el detector debería "
                                   f"llevar el código desnudo, no "
                                   f"'marca + modelo'"})
    if RE_ARTEFACTO.search(term):
        motivos.append({"regla": "artefacto-de-extraccion",
                        "detalle": "guion suelto o '..' de código truncado: "
                                   "el término almacenado no es lo que lleva "
                                   "impreso el equipo"})
    if RE_SUF_IDIOMA.search(term):
        motivos.append({"regla": "sufijo-de-idioma",
                        "detalle": "acaba en sufijo de idioma: suele "
                                   "identificar la edición de un DOCUMENTO"})
    if RE_PREFIJO_ABREV.match(term.strip()):
        motivos.append({"regla": "prefijo-abreviado-de-catalogo",
                        "detalle": "empieza por Mod./Ref./Art./Doc.: el "
                                   "identificador del equipo es lo que va "
                                   "detrás"})
    if (RE_COMODIN.search(term) or RE_COLA_COMODIN.search(_utiles(term))
            or any(RE_PLACEHOLDER_PARTE.match(p) for p in partes)):
        motivos.append({"regla": "comodin-en-el-codigo",
                        "detalle": "lleva un comodín (xx/nnn/###): el código "
                                   "real varía, así almacenado no identifica "
                                   "una unidad"})
    raro = _char_raro(term)
    if raro:
        motivos.append({"regla": "caracter-no-ascii-raro",
                        "detalle": f"contiene {raro} (no es una letra "
                                   f"acentuada): normkey y _base_aliases se "
                                   f"comportan de forma no obvia"})
    # prefijo de palabra común: el patrón NO cierra con \b, así que un término
    # sin dígitos que sea prefijo de una palabra del sector matchea dentro de
    # ella ('sire' dentro de 'sirena').
    if not any(c.isdigit() for c in utiles) and len(utiles) >= 3:
        pref = [w for w in PALABRAS_RIESGO
                if w.startswith(utiles) and w != utiles]
        if pref:
            motivos.append({"regla": "prefijo-de-palabra-comun",
                            "detalle": f"el patrón no cierra en \\b: matchearía "
                                       f"dentro de {sorted(pref)[:4]}"})
    # Descripción larga: no es un código, es una frase extraída del manual.
    # El test de CONECTORES va sobre partes SUELTAS, nunca sobre los runs de
    # letras: 'MCP1A' segmenta como ['mcp','a'] y la 'a' haría saltar «lleva
    # conector» en decenas de códigos legítimos (bug cazado en la 1ª pasada).
    conect = [s for s in sueltas if s in CONECTORES] if len(sueltas) > 1 else []
    if (len(tokens) > MAX_TOKENS_CODIGO or len(term) > MAX_CHARS_CODIGO
            or conect):
        motivos.append({"regla": "descripcion-no-codigo",
                        "detalle": f"{len(tokens)} tokens / {len(term)} chars"
                                   + (f" / conectores de lengua natural "
                                      f"{conect}" if conect else "")})
    # colisión de normkey con el snapshot VIVO (modelo o alias-base generado):
    # no añade detección, CAMBIA la forma canónica devuelta (setdefault).
    nk = C.normkey(term)
    if nk in nk_vivos:
        motivos.append({"regla": "colision-normkey-vivo",
                        "detalle": f"el snapshot vivo ya tiene {nk_vivos[nk]!r} "
                                   f"con ese normkey"})
    if nk in nk_base_vivos:
        motivos.append({"regla": "colision-con-alias-base-vivo",
                        "detalle": f"ya se detecta hoy como alias-base de "
                                   f"{nk_base_vivos[nk]!r}; darlo de alta cambia "
                                   f"la forma canónica devuelta, no añade "
                                   f"detección"})
    # Colisión de CORE (no de normkey): el core une los segmentos con
    # separadores OPCIONALES, así que 'MPS 1.5' y 'MPS15' generan el MISMO
    # regex. Si el core ya existe en el snapshot vivo con otra identidad, el
    # alta no añade detección: reparte la misma detección entre dos formas.
    firma = _utiles(term)
    if cores_vivos and firma in cores_vivos and C.normkey(term) != C.normkey(
            cores_vivos[firma]):
        motivos.append({"regla": "core-identico-a-modelo-vivo",
                        "detalle": f"mismo core regex que {cores_vivos[firma]!r} "
                                   f"del snapshot vivo (los separadores son "
                                   f"opcionales): dos identidades para una "
                                   f"misma detección"})

    # La BASE que el alta genera automáticamente puede ser mucho más ancha que
    # el término. Se le aplica EL MISMO listón que al término (<=4 útiles =
    # corto, sin letras = colisiona con cifras, sólo palabras comunes): si la
    # base pasaría el filtro por sí sola, el alta no ensancha el riesgo.
    for base in C._base_aliases(term):
        u_base = _utiles(base)
        pal_base = [p for p in _partes(base) if p.isalpha()]
        base_comun = (pal_base and all(
            p in PALABRAS_RIESGO or p in CONECTORES or len(p) < 3
            for p in pal_base))
        if (len(u_base) <= MIN_CORTO or base_comun
                or not any(c.isalpha() for c in u_base)):
            motivos.append({"regla": "base-alias-riesgosa",
                            "detalle": f"_base_aliases() añadiría {base!r} "
                                       f"({len(u_base)} útiles), que matchea "
                                       f"mucho más ancho que el término"})

    if motivos:
        return "RIESGO", motivos
    return "SEGURO", []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sin-sondas", action="store_true",
                    help="no consulta menciones en contenido (dry, sin HTTP "
                         "por término)")
    ap.add_argument("--cap-sondas", type=int, default=600,
                    help="tope de términos sondados (coste)")
    args = ap.parse_args()

    packet = json.loads(PACKET.read_text(encoding="utf-8"))
    altas = packet["altas"]

    # --- estado de HOY del catálogo gobernado (SOLO LECTURA) ---------------
    cat = catalog_store.load()
    terms_hoy = _resolvable_terms(cat)          # normkey -> término almacenado

    # Marcas REALES (del gobernado + del snapshot vivo), no una lista a mano:
    # 'ARGUS SECURITY SG350' o 'Notifier INSPIRE E15' son «marca + modelo», y el
    # detector debe llevar el código desnudo.
    marcas: set[str] = set()
    for p in cat.products.values():
        for m in p.get("vendido_bajo") or []:
            for w in re.split(r"\s+", C._fold(m)):
                if len(w) >= 4:
                    marcas.add(w)

    vivo = json.loads(VIVO.read_text(encoding="utf-8"))
    nk_vivos = {C.normkey(m["model"]): m["model"] for m in vivo.get("models", [])}
    nk_base_vivos: dict[str, str] = {}
    cores_vivos: dict[str, str] = {}
    for m in vivo.get("models", []):
        for b in C._base_aliases(m["model"]):
            nk_base_vivos.setdefault(C.normkey(b), m["model"])
        cores_vivos.setdefault(_utiles(m["model"]), m["model"])

    # --- atestación de HOY: misma definición que el generador del packet ---
    with abierto(timeout=30.0) as client:
        # TODOS los documentos con su status (no sólo los activos): cuando una
        # fila cae por falta de atestación hay que poder decir POR QUÉ — un
        # manual en `needs_review` no es lo mismo que un manual inexistente, y
        # la acción de Alberto es distinta en cada caso (caso real: ZXr-P).
        docs_all = _paginado(client, "documents", {
            "select": "id,source_pdf_filename,status", "order": "id.asc"})
        docs = [d for d in docs_all if d.get("status") == "active"]
        chunks = _paginado(client, "chunks_v2", {
            "select": "product_model,source_file", "order": "id.asc"})

        recon = json.loads(RECON_E1.read_text(encoding="utf-8"))
        colision_ids = {c["id_viejo"] for tier in ("a", "b", "c")
                        for c in recon.get("colision", {}).get(tier, [])
                        if c.get("id_viejo")}
        activos = {d["id"] for d in docs} - colision_ids
        estado_doc = {d["id"]: d.get("status") for d in docs_all}
        sf_norm = {d["id"]: re.sub(r"\.pdf$", "",
                                   (d.get("source_pdf_filename") or "")
                                   .strip().lower()) for d in docs}
        sf_activos = {sf_norm[i] for i in activos if i in sf_norm}
        chunks_por_sf: Counter = Counter()
        pm_counter: Counter = Counter()
        for ch in chunks:
            sf = (ch.get("source_file") or "").strip().lower()
            chunks_por_sf[sf] += 1
            if sf in sf_activos:
                nk = C.normkey(ch.get("product_model") or "")
                if nk:
                    pm_counter[nk] += 1
        productos_atestados: set[str] = set()
        for dm in cat.doc_map:
            if dm.get("document_id") not in activos:
                continue
            if chunks_por_sf.get((dm.get("source_file") or "").strip().lower(), 0) == 0:
                continue
            for e in dm.get("entries", []):
                productos_atestados.add(e.get("id"))

        # ---------------- (A) refresco + (B) split ------------------------
        bloque, individual, obsoletas, notas = [], [], [], []
        for a in altas:
            term_packet = a["model"]
            nk = C.normkey(term_packet)
            term_hoy = terms_hoy.get(nk)

            # (A1) ¿sigue resoluble por la puerta del gobernado?
            if term_hoy is None:
                obsoletas.append({
                    "model": term_packet, "via_packet": a.get("via"),
                    "motivo": "ya-no-resuelve-en-gobernado",
                    "detalle": "el término salió de _resolvable_terms (alias "
                               "revocado, producto retirado/candidate o "
                               "renombrado) entre el 12-ago y hoy"})
                continue
            res = cat.resolve(term_hoy) or {}
            ids = res.get("ids", []) or []
            via_hoy = res.get("via")

            # (A2) ¿sigue atestado? (doc_map activo con chunks, o pm en chunks)
            atest_docmap = [i for i in ids if i in productos_atestados]
            cc_hoy = pm_counter.get(nk, 0)
            if not atest_docmap and cc_hoy == 0:
                # diagnóstico: qué documentos tiene y en qué estado están
                diag = []
                for dm in cat.doc_map:
                    if not any(e.get("id") in ids for e in dm.get("entries", [])):
                        continue
                    sf = (dm.get("source_file") or "").strip().lower()
                    diag.append({
                        "source_file": dm.get("source_file"),
                        "status": estado_doc.get(dm.get("document_id"),
                                                 "documento-no-existe"),
                        "chunks": chunks_por_sf.get(sf, 0)})
                obsoletas.append({
                    "model": term_packet, "ids": ids, "via_hoy": via_hoy,
                    "motivo": "sin-atestacion-activa-hoy",
                    "detalle": "ningún producto suyo tiene doc_map a documento "
                               "ACTIVO con chunks servibles y su normkey no "
                               "aparece como product_model",
                    "doc_map_hoy": diag,
                    "accion_sugerida": (
                        "revisar el STATUS del documento (si está en "
                        "needs_review, el alta depende de activarlo, no del "
                        "término)" if any(d["status"] not in ("active",)
                                          and d["chunks"] > 0 for d in diag)
                        else "sin corpus servible detrás: NO dar de alta hoy")})
                continue

            # (A3) ¿el snapshot vivo ya lo conoce? (sería un no-op)
            if nk in nk_vivos:
                obsoletas.append({
                    "model": term_packet, "motivo": "ya-en-snapshot-vivo",
                    "detalle": f"el detector ya lo tiene como "
                               f"{nk_vivos[nk]!r}"})
                continue

            # refresco no fatal: la fila vive, pero su evidencia cambió
            if via_hoy != a.get("via"):
                notas.append({"model": term_packet, "campo": "via",
                              "packet": a.get("via"), "hoy": via_hoy,
                              "ids_hoy": ids})
            if cc_hoy != a.get("chunk_count"):
                notas.append({"model": term_packet, "campo": "chunk_count",
                              "packet": a.get("chunk_count"), "hoy": cc_hoy})
            if term_hoy != term_packet:
                notas.append({"model": term_packet, "campo": "forma",
                              "packet": term_packet, "hoy": term_hoy})

            clase, motivos = clasifica(term_hoy, nk_vivos, nk_base_vivos,
                                       marcas, cores_vivos)
            fila = {"model": term_hoy, "clase": clase, "via_hoy": via_hoy,
                    "ids": ids, "chunk_count_hoy": cc_hoy,
                    "chunk_count_packet": a.get("chunk_count"),
                    "base_alias_generada": C._base_aliases(term_hoy)}
            if clase == "SEGURO":
                bloque.append(fila)
            else:
                fila["motivos"] = motivos
                fila["reglas"] = [m["regla"] for m in motivos]
                fila["recomendacion"] = (
                    "NO dar de alta (no es un equipo: es una norma o un número "
                    "de certificación)" if clase == "NO-PRODUCTO"
                    else "decidir una a una")
                individual.append(fila)

        # --- post-pase: colisión de CORE entre dos altas del propio bloque --
        # Dos términos distintos pueden generar el MISMO regex ('MPS 1.5' vs
        # 'MPS15': los separadores son opcionales). Cada uno se resuelve por el
        # normkey del texto tecleado, así que no rompe nada mecánicamente, pero
        # son dos identidades para una detección: eso se decide, no se aprueba
        # en bloque.
        por_firma: dict[str, list[dict]] = defaultdict(list)
        for fila in bloque:
            por_firma[_utiles(fila["model"])].append(fila)
        degradadas = [f for grupo in por_firma.values() if len(grupo) > 1
                      for f in grupo]
        for fila in degradadas:
            gemelos = [g["model"] for g in por_firma[_utiles(fila["model"])]
                       if g["model"] != fila["model"]]
            fila["clase"] = "RIESGO"
            fila["motivos"] = [{"regla": "core-identico-a-otra-alta",
                                "detalle": f"mismo core regex que {gemelos}: "
                                           f"dos identidades para una misma "
                                           f"detección"}]
            fila["reglas"] = ["core-identico-a-otra-alta"]
            fila["recomendacion"] = "decidir una a una"
            bloque.remove(fila)
            individual.append(fila)

        # --- evidencia extra SÓLO para la sección 1 (coste dirigido) -------
        # Cuántas veces aparece el término en el CONTENIDO de los chunks: si un
        # término de riesgo aparece cientos de veces en prosa, su alta es un
        # falso positivo esperando a pasar. Una sola query por término
        # (count=exact + muestra de source_file para contar documentos).
        sondados = 0
        if not args.sin_sondas:
            # SÓLO la clase FUEGO: son las filas donde el dato cambia la
            # decisión (¿esta palabra corta aparece en prosa por todo el
            # corpus?). Un 'código + sustantivo' no necesita sonda: su patrón
            # exige la frase entera. El ilike con comodín inicial NO usa índice
            # (~1 s por término): sondar las 662 costaba >10 min para nada.
            orden = sorted((f for f in individual
                            if set(f["reglas"]) & REGLAS_SONDA),
                           key=lambda f: len(_utiles(f["model"])))
            print(f"sondando {len(orden)} términos de clase FUEGO...")
            for fila in orden:
                if sondados >= args.cap_sondas:
                    fila["evidencia"] = {"sonda": "no-ejecutada (cap)"}
                    continue
                t = fila["model"]
                # OJO (bug pagado en esta sesión): el valor NO puede ir entre
                # comillas dobles — `ilike."*x*"` toma los '*' como literales y
                # devuelve SIEMPRE 0, que parece «no aparece nunca» y es un
                # falso negativo silencioso. Va con comodín desnudo. Y se omite
                # el término que lleve caracteres reservados del filtro o
                # comodines de LIKE ('%', '_'), que falsearían la cuenta.
                if any(ch in t for ch in '"\\%_,()'):
                    fila["evidencia"] = {"sonda": "omitida (chars reservados "
                                                  "del filtro ilike/LIKE)"}
                    continue
                try:
                    r = client.get(
                        f"{SUPABASE_URL}/rest/v1/chunks_v2",
                        headers={**H, "Prefer": "count=exact"},
                        params={"select": "source_file",
                                "content": f"ilike.*{t}*", "limit": "200"})
                    r.raise_for_status()
                    rango = r.headers.get("content-range", "")
                    total = int(rango.split("/")[-1]) if "/" in rango else -1
                    docs_m = {row.get("source_file") for row in r.json()}
                    fila["evidencia"] = {
                        "chunks_con_pm": fila["chunk_count_hoy"],
                        "menciones_en_contenido": total,
                        "docs_distintos_muestra": len(docs_m),
                        "muestra_capada_en": 200,
                        "como_leerlo": "muchas menciones repartidas en MUCHOS "
                                       "documentos = la cadena es genérica "
                                       "(riesgo FUEGO); muchas menciones en "
                                       "1-2 documentos = es su propio manual"}
                    sondados += 1
                    if sondados % 25 == 0:
                        print(f"  ...{sondados}/{len(orden)}")
                except Exception as e:                      # noqa: BLE001
                    fila["evidencia"] = {"sonda": f"error: {type(e).__name__}"}

    # --- recibo ------------------------------------------------------------
    por_regla = Counter(r for f in individual for r in f["reglas"])
    clases = Counter(f["clase"] for f in individual)
    motivos_obs = Counter(o["motivo"] for o in obsoletas)
    # sub-bloque candidato: filas cuya ÚNICA pega es no llevar dígitos pero son
    # nombres largos e inequívocos — Alberto puede barrerlas de un sí si relaja
    # esa regla concreta. Se calcula, no se aplica.
    relajable = [f["model"] for f in individual
                 if f["reglas"] == ["solo-letras-sin-digitos"]
                 and len(_utiles(f["model"])) >= 6]

    # Los más peligrosos, ordenados por la evidencia REAL (en cuántos
    # documentos distintos aparece la cadena): es el ranking que Alberto quiere
    # ver primero. OJO al leerlo: el ilike cuenta también las apariciones
    # DENTRO de códigos más largos ('B501' dentro de 'B501AP'), y eso no es
    # ruido de la medición — es exactamente el fallo que tendría el detector,
    # porque el patrón sólo se protege del dígito siguiente, no de la letra.
    sondadas = [f for f in individual
                if isinstance(f.get("evidencia"), dict)
                and "menciones_en_contenido" in f["evidencia"]]
    top = sorted(sondadas,
                 key=lambda f: (-f["evidencia"]["docs_distintos_muestra"],
                                -f["evidencia"]["menciones_en_contenido"]))[:20]
    sin_corpus = [f["model"] for f in bloque if f["chunk_count_hoy"] == 0]

    recibo = {
        "que_es": ("Split de las 1.235 ALTAS del packet E2 tras refrescarlas "
                   "contra el estado de HOY. SECCIÓN 0 = un solo sí; SECCIÓN 1 "
                   "= decisión una a una. PROPUESTA: no aplica nada."),
        "generado": datetime.now(timezone.utc).isoformat(),
        "fuente_packet": str(PACKET),
        "estado_de_hoy": {
            # stamp del catálogo (freeze-contract): sin él, dentro de un mes no
            # se sabe contra QUÉ estado se refrescó el packet
            "catalogo_commit": catalog_commit(),
            "terminos_resolubles_hoy": len(terms_hoy),
            "snapshot_vivo_modelos": len(nk_vivos),
            "snapshot_vivo_alias_base": len(nk_base_vivos),
            "docs_activos": len(docs), "chunks_leidos": len(chunks)},
        "reglas": {
            "SEGURO (bloque)": "mezcla letras+dígitos, >=5 caracteres útiles, "
                               "sin palabra común/jerga, no es norma ni "
                               "certificado, es un CÓDIGO (<=4 tokens, <=24 "
                               "chars, sin conectores), no colisiona con el "
                               "snapshot vivo ni genera un alias-base ancho",
            "RIESGO (individual)": sorted(set(por_regla) - {"norma-tecnica",
                                                            "numero-certificacion"}),
            "NO-PRODUCTO (individual, propuesta = NO alta)":
                ["norma-tecnica", "numero-certificacion"],
            "por_que": "el patrón del detector es \\b(core)(?!\\d) sin \\b de "
                       "cierre y _base_aliases() ensancha solo: un término "
                       "corto o común contamina TODAS las consultas (caso "
                       "FUEGO)"},
        "resumen": {
            "total_packet": len(altas),
            "obsoletas_por_refresco": len(obsoletas),
            "seccion_0_bloque": len(bloque),
            "seccion_1_individual": len(individual),
            "individual_por_clase": dict(clases),
            "individual_por_regla": dict(por_regla.most_common()),
            "obsoletas_por_motivo": dict(motivos_obs),
            "sondas_ejecutadas": sondados,
            "sub_bloque_relajable_solo_letras": len(relajable)},
        "top_peligrosos": [
            {"model": f["model"], "reglas": f["reglas"],
             "menciones_en_contenido": f["evidencia"]["menciones_en_contenido"],
             "docs_distintos_muestra": f["evidencia"]["docs_distintos_muestra"]}
            for f in top],
        "nota_whisper": (
            f"{len(sin_corpus)}/{len(bloque)} filas del bloque tienen "
            f"chunk_count=0 hoy. all_models() ordena por chunk_count desc y el "
            f"hint de Whisper está capado a ~1000 chars, así que estas altas "
            f"NO llegan al dictado: mejoran la query ESCRITA (y el imatch "
            f"posterior), no la transcripción de voz."),
        "seccion_0_bloque": sorted(bloque, key=lambda f: -f["chunk_count_hoy"]),
        "seccion_1_individual": sorted(
            individual, key=lambda f: (f["clase"], f["reglas"], f["model"])),
        "obsoletas": obsoletas,
        "refresco_notas": notas,
        "sub_bloque_relajable_solo_letras": relajable,
    }
    DESTINO.write_text(json.dumps(recibo, ensure_ascii=False, indent=1),
                       encoding="utf-8")
    print(f"total {len(altas)} · obsoletas {len(obsoletas)} · "
          f"bloque {len(bloque)} · individual {len(individual)} · "
          f"sondas {sondados}")
    print(f"recibo -> {DESTINO}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
