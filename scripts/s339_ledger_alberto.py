#!/usr/bin/env python3
"""s339 — el ledger de adjudicaciones de Alberto, machine-readable.

Por qué existe
--------------
`docs/REVISION_ALBERTO_HUERFANOS.md` es hoy la ÚNICA fuente de 46 correcciones de
dominio que yo no puedo deducir del catálogo («este también sirve para el MAD-401»,
«el pdf está girado», «es la VSN Plus de Morley»). Mientras vivan sólo como prosa
dentro de un fichero GENERADO, son (a) no accionables por un script y (b) frágiles:
basta un `s337` sin el guardarraíl de conservación para borrarlas.

Este script las saca a `evals/s339_ledger_alberto.json`, con una separación que es
el punto entero del diseño:

  · lo MECÁNICO  — sección, propuesta original, casilla marcada, texto LITERAL de
    Alberto, ids y manuales. Sale del fichero, sin interpretación.
  · lo INTERPRETADO — mi lectura de su prosa en acciones de catálogo. Va en el mapa
    `LECTURA` de ABAJO, escrito a mano, y cada entrada CITA el fragmento del que la
    deduzco. Así el dúo adversarial (y él) pueden auditar la lectura contra sus
    palabras sin volver a leerse el packet.

No mezclar las dos es lo que evita que «lo que Alberto dijo» y «lo que yo entendí»
acaben siendo la misma celda —el fallo que este packet existe para prevenir.

READ-ONLY sobre el packet. No lo edita ni lo regenera.
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
PACKET = RAIZ / "docs" / "REVISION_ALBERTO_HUERFANOS.md"
SALIDA = RAIZ / "evals" / "s339_ledger_alberto.json"


# ── lo MECÁNICO ────────────────────────────────────────────────────────────────

def parsea(path: Path) -> dict:
    """Saca del packet lo que es estructura, sin interpretar una sola palabra."""
    secciones: dict[str, dict] = {}
    orden: list[str] = []
    sec = None
    for l in path.read_text("utf-8").splitlines():
        m = re.match(r"^(#{2,3})\s+(.*)$", l)
        if m:
            titulo = m.group(2).strip()
            # Las secciones que nos interesan llevan número («1.2 — …», «3 · …»).
            n = re.match(r"^(\d+(?:\.\d+|\.[a-z])?)\s*[·—-]", titulo)
            sec = n.group(1) if n else None
            if sec:
                secciones.setdefault(sec, {
                    "seccion": sec, "titulo": titulo, "casilla": None,
                    "texto_alberto": None, "manuales": [], "ids": [], "filas": [],
                })
                orden.append(sec) if sec not in orden else None
            continue
        if not sec:
            continue
        d = secciones[sec]

        # Línea de decisión: casillas + texto libre al lado.
        if re.match(r"\s*- \[[ Xx]\]", l):
            d["casilla"] = l.strip()
            # El texto de Alberto es lo que sigue a la opción que marcó, o lo que
            # escribió en un hueco. Se guarda la línea entera: recortar aquí sería
            # ya interpretar.
            continue

        # Manuales enumerados en prosa: «- Manuales: `A`, `B`».
        if l.strip().startswith("- Manuales:"):
            d["manuales"] += re.findall(r"`([^`]+)`", l)
            continue

        # Ids que se disputan / origen y destino del redirect.
        d["ids"] += [i for i in re.findall(r"`((?:unresolved|notifier|morley|detnov|aritech|desico|xtralis)[^`]*)`", l)
                     if i not in d["ids"]]

        # Filas de tabla. La columna del manual NO está en el mismo índice en todas
        # (§3 lleva un `#` delante, §3.b no), así que se localiza por el backtick en
        # vez de por posición: fijar el índice perdía la tabla entera de §3.b.
        if l.lstrip().startswith("|"):
            celdas = [c.strip() for c in l.split("|")]
            idx = next((i for i, c in enumerate(celdas) if c.startswith("`")), None)
            if idx is not None and len(celdas) >= 4:
                nota = celdas[-1] if celdas[-1] else (celdas[-2] if len(celdas) > 5 else "")
                if nota.startswith(("FICHERO", "ref.", "---")) or "·  [fuente]" in nota:
                    nota = ""
                # Se guardan TAMBIÉN las filas sin nota: en §3 él marcó «mira los
                # ajustes», así que una fila sin ajuste significa «acepta la propuesta»
                # — y eso es una decisión, no una ausencia.
                d["filas"].append({"manual": celdas[idx].strip("`"), "nota": nota,
                                   "anotada": bool(nota)})

    # El suelo (§8) y la pregunta final no llevan cabecera numerada con `·` en el
    # mismo formato; se recogen aparte para no perderlos.
    return {"secciones": [secciones[s] for s in orden]}


def suelo_y_pregunta(path: Path) -> tuple[list[dict], dict]:
    """§8 (el suelo) y la pregunta abierta del final, que no son `### n.m`."""
    txt = path.read_text("utf-8")
    filas: list[dict] = []
    bloque = txt.split("## 8 ·", 1)
    if len(bloque) == 2:
        for l in bloque[1].splitlines():
            if not l.lstrip().startswith("|"):
                continue
            celdas = [c.strip() for c in l.split("|")]
            if len(celdas) >= 4 and celdas[1].startswith("`"):
                nota = celdas[-1] if celdas[-1] else ""
                filas.append({"manual": celdas[1].strip("`"),
                              "motivo_original": celdas[2],
                              "nota": nota,
                              "resuelto_por_alberto": bool(nota)})
    preg = {"pregunta": "desico:tg-1020 — ¿atribución equivocada, homónimo, o dejarlo?",
            "respondida": False, "casilla": None}
    for l in txt.split("Y una pregunta que sale", 1)[-1].splitlines():
        if re.match(r"\s*- \[[ Xx]\]", l):
            preg["casilla"] = l.strip()
            preg["respondida"] = "[x]" in l.lower()
    return filas, preg


# ── lo INTERPRETADO ────────────────────────────────────────────────────────────
# Mi lectura de su prosa. `cita` = el fragmento del que la deduzco, para auditarla.
# `tipo` = qué operación de catálogo pide. `bloqueo` = por qué NO es aplicable tal cual.

# NOTA transversal (la cazó `s339b` contra el catálogo vivo): en §2.2, §2.4, §4.1, §4.2
# y §4.3 el id GANADOR está él mismo en cuarentena. Fusionar es por tanto de TRES pasos
# —promover al ganador, redirigir al perdedor, `vendido_bajo` con las dos marcas—, no de
# dos: redirigir hacia un `candidate` no rescata ni un manual, porque `_consumable()`
# sigue el redirect y se encuentra la cuarentena al otro lado.
LECTURA: dict[str, dict] = {
    "1.1": {"tipo": "redirect", "de": "unresolved:id50", "a": "notifier:id-50",
            "cita": "[X] OK", "listo": True},
    "1.2": {"tipo": "redirect+vendido_bajo", "de": "unresolved:tg", "a": "notifier:tg",
            "vendido_bajo": ["notifier", "morley"], "software": True,
            "cita": "TG sale tanto para Morley como para Notifier, por lo que debería ser findable para ambas marcas",
            "listo": True,
            "nota": "NO es sólo redirect: R3 vendido_bajo, si no queda findable sólo bajo Notifier"},
    "1.3": {"tipo": "redirect", "de": "unresolved:mad-450", "a": "detnov:mad-450",
            "cita": "[X] OK", "listo": True},
    "1.4": {"tipo": "redirect", "de": "unresolved:id60", "a": "notifier:id-60",
            "cita": "[X] OK", "listo": True},
    "1.5": {"tipo": "redirect+familia", "de": "unresolved:tg-gsm", "a": "notifier:tg-gsm",
            "familia": "notifier:tg", "software": True,
            "cita": "OK a lo que propone (ten en cuenta que es software). no obstante, TG-GSM debería pertenecer a la familia de software TG",
            "listo": True,
            "nota": "la pertenencia a familia es `umbrellas`/`relations`, no el redirect"},
    "2.1": {"tipo": "adjudicacion+promocion", "gana": "morley:vsn12-2plus",
            "promover_tambien": ["morley:vsn4-2plus", "morley:vsn8-2plus"],
            "cita": "era: Morley. no obstante, ojo que hay más modelos de la familia VSN-2Plus, en concreto VSN4-2Plus, VSN8-2Plus, y VSN12-2Plus. los 3 son Morley",
            "listo": True},
    "2.2": {"tipo": "adjudicacion+familia+promocion", "gana": "notifier:tg-1020", "familia": "notifier:tg",
            "cita": "confirmado. no obstante, que pertenezca a la familia TG al igual que el TG-GSM",
            "listo": False,
            "bloqueo": "promoverlo choca de frente con `desico:tg-1020`, que ya es consumible: "
                       "`validate` sobre la simulación lo caza como canonical_model DUPLICADO "
                       "(«exact sería last-wins silencioso»). Es LA pregunta abierta del final "
                       "del packet, que sigue sin responder. Sale del lote hasta que la conteste: "
                       "¿atribución equivocada de Desico, homónimo, o se queda como está?"},
    "2.3": {"tipo": "redirect", "de": "notifier:id-3000", "a": "notifier:id3000",
            "cita": "[X] OK al redirect", "listo": True},
    "2.4": {"tipo": "fusion+promocion", "gana": "morley:vsn-co", "redirige": "notifier:vsn-co",
            "vendido_bajo": ["morley", "notifier"],
            "cita": "[X] fusionar, canónico `Morley`", "listo": True},
    "4.1": {"tipo": "fusion+promocion", "gana": "notifier:nfs8rel", "redirige": "morley:nfs8rel",
            "vendido_bajo": ["notifier", "morley"],
            "cita": "fusionar, canónico `Notifer`, pero es el mismo producto vendido bajo Notifier y Morley",
            "listo": True, "nota": "«Notifer» es errata suya por Notifier"},
    "4.2": {"tipo": "fusion+promocion", "gana": "notifier:mcx-55m", "redirige": "morley:mcx-55m",
            "vendido_bajo": ["notifier", "morley"],
            "cita": "fusionar, canónico `Notifier`, pero es el mismo producto vendido bajo Notifier y Morley",
            "listo": True},
    "4.3": {"tipo": "fusion+promocion", "gana": "notifier:mmx-10m", "redirige": "morley:mmx-10m",
            "vendido_bajo": ["notifier", "morley"],
            "cita": "fusionar, canónico `Notifier`, pero es el mismo producto vendido bajo Notifier y Morley",
            "listo": True},
    "4.4": {"tipo": "ya_aplicado", "ids": ["aritech:apic", "notifier:apic"],
            "cita": "prefiero tratarlos como productos que se llaman igual pero que son de distinto fabricante, por lo que entiendo que si un técnico pregunta por ello debería clarificar el bot",
            "listo": True, "cambio_de_catalogo": False,
            "nota": "RECHAZA la fusión que yo proponía — y RE-CONFIRMA lo que ya está: "
                    "`homonyms.jsonl` lleva `APIC` con `politica: clarify` desde s91, "
                    "adjudicado por él (G4 B-clarify: tarjetas INCOMPATIBLES Aritech/ModuLaser "
                    "vs Notifier/Stratos, ambos productos candidate A PROPÓSITO). Cero cambios. "
                    "Mi packet proponía fusionar sin haber grepeado homonyms primero. "
                    "CONSECUENCIA: su manual queda huérfano PERMANENTE y legítimo — el precio "
                    "de la política clarify es que ningún producto consumible lo posee."},
    "5.1": {"tipo": "redirect", "de": "notifier:notifier-inspire-e10", "a": "notifier:inspire-e10",
            "cita": "aquí lo llamaría directamente `notifier:inspire-e10`, para evitar tener los dos nombres en la BD via redirect",
            "listo": True, "explicar_a_alberto": True,
            "nota": "Él pide ELIMINAR la fila en vez de redirigirla, y no se puede: el contrato "
                    "(`docs/IDENTITY_CATALOG_CONTRACT.md`) dice literal «Los ids son INMUTABLES: "
                    "nunca se borran ni se reciclan», y prescribe que en un merge el perdedor quede "
                    "en `redirect` (alias-forwarding PERMANENTE). No hay excepción para `candidate`. "
                    "Mi premisa de que «nada externo lo referenció» era además FALSA: el id está en "
                    "4 entradas de `doc_map` y 1 alias. "
                    "PERO el redirect le da exactamente lo que pide: `notifier:notifier-inspire-e10` "
                    "deja de existir como producto consultable —no aparece en inventarios ni resuelve "
                    "como fila propia—, sólo reenvía. No quedan «dos nombres en la BD» de cara al bot; "
                    "queda un puntero interno que evita que se rompa lo ya etiquetado. Decírselo."},
    "5.2": {"tipo": "redirect+vendido_bajo", "de": "unresolved:tg-honeywell", "a": "notifier:tg",
            "vendido_bajo": ["notifier", "morley"],
            "cita": "no se si tiene sentido que el canónico sea Notifier pero que también sea \"findable\" bajo Morley",
            "listo": True, "nota": "mismo tratamiento que 1.2 — es el mismo producto"},
    "6.1": {"tipo": "promover", "id": "notifier:am-lcd", "stopwords": ["fm/am lcd"],
            "cita": "esto es un producto en sí \"AM-LCD\", como puedes ver en la portada del manuual que me has indicado",
            "listo": True,
            "nota": "confirma el producto Y deja en pie el falso positivo del manual de radio → DETECT_STOPWORDS"},
    "6.2": {"tipo": "no_es_producto", "id": "notifier:eev2",
            "cita": "no es un producto, sino una \"TABLA DE APROXIMACIONES A GAS PATRÓN\"",
            "listo": True,
            "nota": "MADT608 queda huérfano LEGÍTIMO: su sujeto no es un producto"},
    "6.3": {"tipo": "promover+bajas", "id": "notifier:nas",
            "canonico_nuevo": "Notifier Air Sample",
            "evidencia": "evals/s339g_bateria.json",
            "bajas": ["MNDT740P"], "bajas_condicionales": ["MNDT741I"],
            "cita": "el manual \"MNDT740P\" es portugués, así que deberíamos sacarlo … es el Notifier Air Sample (equipo de muestreo de aire) … si los documentos 2 y 3 son iguales, y solo cambia el idioma, quitaría el de \"MNDT741I\"",
            "listo": True, "explicar_a_alberto": True,
            "nota": "Su adjudicación de PRODUCTO-HOOD es correcta y se aplica: NAS existe, es el "
                    "Notifier Air Sample, y el id es `notifier:nas` como él dijo. Pero producto-hood "
                    "y DETECTABILIDAD son preguntas distintas y yo las había juntado. Medido en la "
                    "batería: el token «NAS» dispara en los TRES negativos —«insira os condutores "
                    "nas respectivas portas» (preposición portuguesa, literal en el corpus), la "
                    "misma intercalada en español, y «un NAS de red» (Network Attached Storage)—. "
                    "Es el precedente DEC-272 reproducido. `DETECT_STOPWORDS` no sirve: es una "
                    "lista global y mataría NAS del todo. "
                    "SOLUCIÓN: el canónico pasa a «Notifier Air Sample», que es como ÉL describe el "
                    "producto; el id no se toca. Los manuales dejan de ser huérfanos igual y el "
                    "token corto ya no dispara. Si quiere «NAS» alcanzable pese a los falsos "
                    "positivos, es UNA línea: añadirlo como alias. Preguntárselo. "
                    "La baja de MNDT741I es CONDICIONAL y ya está comprobada: 741 es `language=es` "
                    "y 741I `language=en`, mismo índice y mismo producto → sólo cambia el idioma"},
    "6.4": {"tipo": "renombrar_canonico", "id": "notifier:rhistorico.exe",
            "canonico_nuevo": "Utilidad de Reparación de Históricos",
            "alias": ["RHistorico.exe"], "familia": "notifier:tg",
            "cita": "es un ejecutable que pertenece al software TG, así que OK a tu recomendación",
            "listo": False,
            "bloqueo": "dos razones independientes. (a) Fable: s334 dejó `rhistorico.exe` FUERA a "
                       "propósito por riesgo léxico —«R10 se cumple, la GRAFÍA no»— y esto "
                       "reintroduce esa grafía como alias INDEXADO; merece re-adjudicación "
                       "explícita, no colarse dentro de un «renombrar». (b) La puerta `s324` no "
                       "sabe reescribir un `canonical_model`, así que el renombrado no es "
                       "expresable en el plan sin tocar el writer por algo que ya está en duda. "
                       "A favor: la huella medida de «RHistorico.exe» es 2 documentos, 1 suyo, "
                       "0 robados — el riesgo de s334 no se materializa en ESTE término",
            "nota": "NO es un id nuevo: `notifier:rhistorico.exe` ya existe (candidate) y ya lleva "
                    "«Utilidad de Reparación de Históricos» como alias. Crear una fila aparte "
                    "colisionaba con ese alias (lo cazó `validate` en la simulación). El id es "
                    "INMUTABLE y se queda; lo que cambia es el `canonical_model`, que no lo es: "
                    "el nombre humano pasa a canónico y el ejecutable baja a alias"},
    "6.5": {"tipo": "promover", "id": "notifier:serie-800", "nombre": "Serie-800",
            "cita": "déjalo como Serie-800",
            "listo": False,
            "bloqueo": "mi lectura («rechaza el umbrella, lo quiere como producto») NO se sigue de "
                       "la casilla: las opciones eran `adelante`/`déjalo`, donde `adelante` era mi "
                       "propuesta de umbrella — así que `[X] déjalo` significa «no hagas eso», y "
                       "«déjalo como Serie-800» admite las dos lecturas (déjalo QUIETO, o déjalo "
                       "COMO producto llamado así). Y la huella de detección la desempata hacia la "
                       "prudencia: «Serie 800» dispara en 14 documentos y 11 de ellos YA tienen "
                       "dueño consumible. Promoverlo por una lectura ambigua es justo lo que R20 "
                       "prohíbe. Preguntárselo."},
    "7": {"tipo": "promover_uno_a_uno", "listo": True,
          "filas": {
              "unresolved:tg-ip-1-sec": {"marca": "notifier", "producto_fisico": True,
                  "nombre": "Módulo IP con encriptación para red",
                  "cita": "es sfotware de Notifier (aunque este es un producto físico, no meramente un software) … Módulo IP con encriptación para red"},
              "unresolved:itac": {"marca": "notifier", "vendido_bajo": ["notifier", "morley"],
                  "nombre": "Interface de Transmisión Analógica-Convencional",
                  "cita": "se vende tanto para Morley como para Notifier, así que sigue la misma lógica que con otros productos que se venden bajo las dos marcas"},
              "unresolved:trd-100": {"redirect_a": "detnov:trd-100",
                  "modelos": ["detnov:trd-100", "detnov:tsd-100"],
                  "cita": "modelos de Detnov TRD-100 y TSD-100",
                  "nota": "promoverlo Y crear `detnov:trd-100` dejaría dos filas con el mismo "
                          "canónico («TRD-100»), que `validate` rechaza. Es un redirect al id "
                          "con marca. Y el manual atesta DOS productos: el doc_map lleva los dos"},
              "unresolved:indicator": {"accion": "baja_de_corpus",
                  "cita": "Elimínalo del corpus"},
              "unresolved:vision-plus": {"marca": "morley", "canonico": "VSN Plus",
                  "cita": "es la VSN Plus de Morley",
                  "nota": "el canónico de hoy es «VISION PLUS» y él lo llama «VSN Plus». El "
                          "traductor no consumía este campo (Sol), así que la corrección no "
                          "llegaba a la mutación. Importa además por huella: «VISION PLUS» "
                          "dispara en 12 documentos y roba 11; «VSN Plus» es otro patrón"},
          }},
}

# §3 y §3.b — la tabla Detnov. Sol (crítico): estaban EXCLUIDAS del cruce de integridad
# y sin entrada aquí, así que sus 19 anotaciones no generaban ni una mutación mientras
# la propuesta afirmaba «traduce las adjudicaciones». Es el gap más grande que cazó el dúo.
#
# Lo que Alberto anotó ahí es casi todo la misma clase: «este manual TAMBIÉN sirve para
# el modelo hermano». Un manual que atesta dos productos necesita las DOS entradas en el
# `doc_map`, no una: si sólo se declara uno, el técnico que pregunta por el otro no llega.
LECTURA_S3: dict[str, dict] = {
    "55320103 Manual Zocalo Conexion ES FR GB IT_": {
        "modelos": ["detnov:z-200"], "canonicos": {"detnov:z-200": "Z-200"},
        "cita": "este es el Z-200",
        "nota": "el plan lo tenía como producto «55320103» — un número de referencia, no un modelo"},
    "55340103 Manual Modulo 1-2 Entradas Tecnicas": {
        "modelos": ["detnov:mad-401"], "canonicos": {"detnov:mad-401": "MAD-401"},
        "cita": "Este también sirve para el MAD-401."},
    "55341101 Manual Modulo 1-2 Reles libre de te": {
        "modelos": ["detnov:mad-411"], "canonicos": {"detnov:mad-411": "MAD-411"},
        "cita": "este también sirve para el MAD-411"},
    "55342102 Manual Modulo 1-2 Entradas 1-2 Sali": {
        "modelos": ["detnov:mad-421"], "canonicos": {"detnov:mad-421": "MAD-421"},
        "cita": "Este también sirve para el MAD-421."},
    "55343101 Manual Modulo 1-2 Sirenas Convencio": {
        "modelos": ["detnov:mad-431"], "canonicos": {"detnov:mad-431": "MAD-431"},
        "cita": "este también sirve para el MAD-431"},
    "55344103 Manual Modulo 1-2 Zonas MAD-442 ES ": {
        "modelos": ["detnov:mad-441"], "canonicos": {"detnov:mad-441": "MAD-441"},
        "cita": "este también sirve para el MAD-441"},
    "55347200 Manual Sirena Analogica MAD-472 ES ": {
        "modelos": ["detnov:mad-473"], "canonicos": {"detnov:mad-473": "MAD-473"},
        "cita": "este también sirve para el MAD-473",
        "superseded_por": "https://www.detnov.com/wp-content/uploads/2019/04/Manual-MAD-472_MAD-473-55347200-MI-634.pdf",
        "nota": "él pide además descargar el manual vivo de la web, ingestarlo y marcar "
                "superseded las filas 16 y 17. Eso es CORPUS, no catálogo: va por s339e"},
    "55349102 Manual Modulo Aislador MAD-491 ES F": {
        "modelos": ["detnov:mad-490", "detnov:mad-492"],
        "canonicos": {"detnov:mad-490": "MAD-490", "detnov:mad-492": "MAD-492"},
        "cita": "parece MAD-490 y MAD-492",
        "superseded_por": "https://www.detnov.com/wp-content/uploads/2019/04/Manual-MAD-490-55349102-MI-628-m-2024-b.pdf",
        "listo": False,
        "bloqueo": "dice «PARECE MAD-490 y MAD-492» — es una conjetura suya, no una firma. "
                   "Y el manual vivo de la web se titula sólo MAD-490. Confirmar antes de "
                   "crear dos productos sobre un «parece»"},
    "55350005 Manual Central Monoxido CMD-500 ES ": {
        "modelos": ["detnov:cmd-501", "detnov:cmd-502", "detnov:cmd-503"],
        "canonicos": {"detnov:cmd-501": "CMD-501", "detnov:cmd-502": "CMD-502",
                      "detnov:cmd-503": "CMD-503"},
        "cita": "la familia es la CMD-500, pero están la CMD-501, CMD-502, y CMD-503, en función del número de zonas",
        "familia": "detnov:cmd-500"},
    "55350007 Manual Tarjeta Regulacion Motores T": {
        "modelos": ["detnov:trmd-501", "detnov:trmd-502"],
        "canonicos": {"detnov:trmd-501": "TRMD-501", "detnov:trmd-502": "TRMD-502"},
        "cita": "es la familia TRMD-500, que incluyela TRMD-501 y la TRMD-502",
        "nota": "el plan lo tenía como «55350007» y «TRMD-50X»; ninguno es un modelo real"},
    "55350008 Manual Detectores Monoxido DMDX-500": {
        "modelos": ["detnov:dmd-500", "detnov:dmdp-500"],
        "canonicos": {"detnov:dmd-500": "DMD-500", "detnov:dmdp-500": "DMDP-500"},
        "cita": "la familia es DMDX-500, pero hay dos modelos: DMD-500 … y DMDP-500"},
    # §3.b — sus correcciones a lo que el canal web PROPUSO. Dos son rechazos, y valen
    # tanto como las altas: confirman que el aviso honesto del packet era correcto.
    "55310007 Manual Tarjeta Expansion TRD-10": {
        "modelos": ["detnov:trd-100", "detnov:tsd-100"],
        "canonicos": {"detnov:trd-100": "TRD-100", "detnov:tsd-100": "TSD-100"},
        "cita": "son las TSD-100 y TRD-100, que son accesorios para la CCD-100",
        "rechaza": "detnov:ccd-100",
        "nota": "CONFIRMA el aviso honesto del packet: CCD-100 era el vecino de contexto "
                "(la central donde se enchufan), no el sujeto del manual. No se da de alta"},
    "55310008 Manual Tarjeta Modbus TMD-100 I": {
        "modelos": [], "cita": "es la TMD-100", "rechaza": "detnov:tsd100",
        "nota": "rechaza la propuesta «TSD100» del canal web; el producto ya está bien"},
}

# El suelo del `Manual-de-Usuario-S3-T2-y-S2-T2` NO necesita productos nuevos: `fidegas:s3-t2`
# («S/3-T2») y `fidegas:s2-t2` («S/2-T2») YA existen y son consumibles. Y el `_core`
# separator-insensitive hace que «S3-T2» y «S/3-T2» casen el mismo patrón, así que el
# detector ya los alcanza desde cualquiera de las dos grafías. Lo que falta es el doc_map.


# §8 — el suelo. Cada fila que él resolvió deja de ser suelo.
LECTURA_SUELO: dict[str, dict] = {
    "55310600 Manual TCD-106 kit_ES": {"producto": "detnov:tcd-106", "listo": True},
    "55312000 SCD-120_Manual_ES": {"producto": "detnov:scd-120",
        "nombre": "Sirena Exterior de Incendios 24V", "listo": True,
        "nota": "el PDF está GIRADO — por eso falló la lectura multimodal; rotar antes de releer"},
    "55393002 Manual Fuentes de Alimentacion FAD-905 ES F": {"producto": "detnov:fad-905",
        "nombre": "Fuente de alimentación 24V", "listo": True},
    "D 1100-4 Sounder": {"fabricante": "kac", "modelos_patron": "CWSO-xx-{S1,S2,W1,W2}",
        "listo": False,
        "bloqueo": "«xx» es el color, no un modelo: hay que enumerar los colores reales "
                   "antes de crear ids, o el patrón no es instanciable"},
    "F3000M_Spanish User Guide_0044-047-02-ES": {"producto": "notifier:f3000m",
        "nombre": "Detector de humo de haz óptico", "listo": True},
    "F5K-2H-UserGuide-SPANISH_Manual F5000": {"producto": "ffe:f5000",
        "alias": ["F5K"], "vendido_bajo": ["Fire Fighting Enterprises", "Morley-IAS"],
        "nombre": "Detector de humos con haz óptico infrarrojo motorizado",
        "listo": False,
        "bloqueo": "divergencia declarada: no puede mutar sin confirmarla (Sol). Ver `divergencia`",
        "divergencia": "Él dice «el modelo F5000 de Morley»; el catálogo ya lo tiene como "
                       "`ffe:f5000` consumible, adjudicado por ÉL en s91 (gt-s91-alberto-c2). "
                       "Crear `morley:f5000` duplicaría el canónico y `validate` lo rechaza. "
                       "FFE fabrica la barrera y Morley la revende → `vendido_bajo` con las dos "
                       "marcas sirve las dos lecturas sin duplicar. CONFIRMAR con él."},
    "F5K-Additional-Information-Spanish": {"producto": "ffe:f5000", "listo": False,
        "bloqueo": "misma divergencia que la fila anterior",
        "divergencia": "misma que la fila anterior"},
    "FS2-1": {"familia": "notifier:fs", "listo": False,
        "bloqueo": "dice «la familia FS … de 1, 2 y 4 zonas», no un modelo. ¿el id es la familia "
                   "`notifier:fs` o los tres modelos? Necesita una línea suya o una fuente"},
    "MADT190_10": {"fabricante": "notifier", "categoria": "accesorio/rack",
        "modelos": ["020-596", "020-606", "020-590", "020-591", "020-593",
                    "020-592", "020-598", "020-594", "020-595"],
        "listo": False,
        "bloqueo": "todos los canónicos son SÓLO DÍGITOS y el detector los excluye a propósito. "
                   "Crearlos no los hace alcanzables: hay que darles un nombre, o aceptar que "
                   "sólo se alcancen por el nombre del rack"},
    "MNDT021": {"listo": False, "bloqueo": "ÚNICA fila del suelo que Alberto no anotó"},
    "MNDT635": {"producto": "notifier:lisa-2", "nombre": "Detectores infrarrojos para gas",
        "listo": True},
    "Manual-de-Usuario-S3-T2-y-S2-T2": {"modelos": ["fidegas:s3-t2", "fidegas:s2-t2"],
        "listo": True,
        "nota": "NO hacen falta altas: `fidegas:s3-t2` («S/3-T2») y `fidegas:s2-t2` («S/2-T2») ya "
                "existen y son CONSUMIBLES. Y su propio aviso —«igual en algún otro sitio lo "
                "tenemos como S/3-T2»— ya está cubierto: el `_core` separator-insensitive hace que "
                "«S3-T2» y «S/3-T2» casen el mismo patrón, así que el detector los alcanza desde "
                "las dos grafías. Lo que falta es sólo el `doc_map`: hoy el manual cuelga de "
                "`fidegas:00051`/`00052`, que son digit-only y por eso el detector no los ve"},
    "S3466R_Eng_ital": {"accion": "baja_de_corpus", "listo": True},
}


def main() -> int:
    if not PACKET.exists():
        raise SystemExit(f"no existe {PACKET}")
    est = parsea(PACKET)
    filas_suelo, pregunta = suelo_y_pregunta(PACKET)

    # Cruce: toda sección parseada debe tener lectura, y toda lectura debe
    # corresponder a una sección real. Un desajuste = el packet cambió bajo mis pies.
    vistas = {s["seccion"] for s in est["secciones"]}
    # Una cabecera `## n` que tiene subsecciones `n.m` es contenedor, no decisión:
    # la decisión vive en las hijas. §3 y §8 sí deciden a nivel de sección.
    contenedor = {v for v in vistas if "." not in v and any(w.startswith(v + ".") for w in vistas)}
    sin_lectura = sorted(v for v in vistas
                         if v not in LECTURA and v not in contenedor
                         and not v.startswith("3") and v != "8")
    sin_seccion = sorted(k for k in LECTURA if k not in vistas)

    entradas = []
    for s in est["secciones"]:
        lec = LECTURA.get(s["seccion"])
        entradas.append({**s, "lectura": lec,
                         "estado": "LISTO" if (lec or {}).get("listo") else
                                   ("BLOQUEADO" if lec else "SIN_LECTURA")})

    suelo = []
    for f in filas_suelo:
        lec = LECTURA_SUELO.get(f["manual"])
        suelo.append({**f, "lectura": lec,
                      "estado": "LISTO" if (lec or {}).get("listo") else "BLOQUEADO"})

    doc = {
        "fuente": str(PACKET.relative_to(RAIZ)),
        "aviso": "Las claves `lectura` son MI interpretación de la prosa de Alberto, no sus "
                 "palabras. Cada una cita el fragmento del que sale. Audítalas contra el packet.",
        "secciones": entradas,
        "suelo": suelo,
        "pregunta_abierta": pregunta,
        "integridad": {"secciones_sin_lectura": sin_lectura,
                       "lecturas_sin_seccion": sin_seccion},
    }
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(json.dumps(doc, ensure_ascii=False, indent=2), "utf-8")

    listos = [e for e in entradas if e["estado"] == "LISTO"]
    bloq = [e for e in entradas if e["estado"] == "BLOQUEADO"]
    print(f"secciones parseadas : {len(entradas)}")
    print(f"  LISTO             : {len(listos)}  → {', '.join(e['seccion'] for e in listos)}")
    print(f"  BLOQUEADO         : {len(bloq)}  → {', '.join(e['seccion'] for e in bloq)}")
    print(f"suelo               : {len(suelo)} filas, "
          f"{sum(1 for f in suelo if f['estado']=='LISTO')} LISTO, "
          f"{sum(1 for f in suelo if f['estado']!='LISTO')} bloqueadas")
    print(f"pregunta abierta    : {'respondida' if pregunta['respondida'] else 'SIN RESPONDER'}")
    if sin_lectura or sin_seccion:
        print(f"⚠ integridad        : sin_lectura={sin_lectura} sin_seccion={sin_seccion}")
    print(f"→ {SALIDA.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
