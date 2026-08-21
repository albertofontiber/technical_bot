#!/usr/bin/env python3
"""s331 — DERIVACIÓN de la pasada completa de Alberto sobre el packet v3.

Alberto anotó las **56 filas vivas** (100% de cobertura, medido por
`s331_censo_anotaciones.py`). Este script convierte esas anotaciones en la lista
de OPERACIONES concretas sobre el catálogo gobernado, y separa las que se pueden
aplicar de las que todavía necesitan una palabra suya.

EL GUARDARRAÍL, que es la razón de que esto sea un script y no un documento
escrito a mano: **toda fila anotada tiene que tener entrada en el mapeo**. Si
añado una decisión al mapeo que él no escribió, o —peor— si se me cae una que sí
escribió, el script FALLA con la lista de las descuadradas. Un documento a mano
puede perder una nota suya sin que nadie se entere; esto no.

Lo que este script NO hace: escribir en el catálogo. Cada operación de abajo
pasa después por `scripts/s324_lote_firmado_writer.py` (dry-run → censo del
radio de explosión → dúo si es medio/alto → `--aplicar` con recibo). Aquí sólo
se deriva y se declara.

Uso:  python scripts/s331_derivar_pasada.py [--md salida.md]
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ANOTADO = ROOT / "evals/s331_packet_v3_anotado_alberto.md"

#: LISTO   — la operación está determinada por su nota; se aplica con gate.
#: PALABRA — falta UNA frase suya; sin ella no se puede elegir sin inventar.
#: BLOQUEO — necesita un cambio de esquema o una medida antes de poder aplicarse.
LISTO, PALABRA, BLOQUEO = "LISTO", "PALABRA", "BLOQUEO"

#: id del packet → (estado, regla, operación, nota mía).
#: Una entrada por id ANOTADO. El orden es el de lectura del packet.
MAPEO: dict[str, tuple[str, str, str, str]] = {
    "aritech:2x-a": (
        PALABRA, "R2",
        "Paraguas «2X-A» (familia). NO se crea el producto `aritech:2x-a`.",
        "Tu OK era condicional: «¿tenemos algún manual de la serie 2X-AT? si no, OK a 2X-A». "
        "RESPUESTA: SÍ, tenemos DOS, los dos en español — `00 3280 508 4109 06 r006 2x at series "
        "quick start guide` y `00 3280 508 4209 02 r002 2x at series quick operation gu`. O sea que "
        "la condición NO se cumple y la pregunta sigue viva: ¿el paraguas 2X-A lleva dentro los 11 "
        "táctiles (38 modelos) o no (27, porque 2X-AT ya tiene paraguas propio)? Medido: 0 gold "
        "perdidas, +2 golds ganan 12 fuentes, 0 disparos en 111 consultas reales."),

    "morley:efs-em-8": (
        PALABRA, "R3+R18",
        "ALTA del panel convencional de 8 zonas EFS/EM 8, `vendido_bajo` Notifier + Morley-IAS.",
        "Dijiste OK a las DOS filas (`morley:` y `notifier:`), que es coherente con R3: `MS8` y "
        "`FS8` son el MISMO manual (código 997-201-103) archivado bajo las dos marcas. Pero un "
        "producto tiene UN id inmutable y el otro se modela como redirect. Propongo canónico "
        "`notifier:efs-em-8` (es Notifier quien lo publica hoy, en `manualesobs`) con "
        "`morley:efs-em-8` → redirect. Si lo prefieres al revés, es una palabra."),
    "notifier:efs-em-8": (
        LISTO, "R3+R18",
        "Fila hermana de la anterior: se resuelve con ella, no por separado.",
        "Obsoleto y se da de alta IGUAL — R18: hay instalaciones que lo llevan."),

    "notifier:nx2-r-r-y-nx5-r-r": (
        LISTO, "R7+R8+R18",
        "DOS altas: `notifier:nx2-r-r` (NX2/R/R) y `notifier:nx5-r-r` (NX5/R/R). "
        "El id concatenado NO se crea.",
        "Validado en la ficha del fabricante: NX2/R/R es flash rojo de 2 W y NX5/R/R sirena-estrobo "
        "de 14 tonos con flash de 5 W. La grafía con barras es la suya (R8)."),

    "notifier:pul-d-ext": (LISTO, "R4+R8", "ALTA `notifier:pul-d-ext` (PUL-D/EXT).",
                           "Pulsador de exterior. Cita de portada; 1 mención."),
    "notifier:pul-p-ext": (LISTO, "R4+R8", "ALTA `notifier:pul-p-ext` (PUL-P/EXT).",
                           "Hermano del anterior, con cita verificada."),
    "sensitron:sts-ckd": (LISTO, "R4+R8", "ALTA `sensitron:sts-ckd` (STS/CKD+).",
                          "Título del manual de instrucciones."),
    "spectrex:20-20mi": (
        LISTO, "R4", "YA APLICADA en el lote A+E (20-ago): existe `spectrex:s20-20mi` con alias "
                     "«20/20MI».",
        "Tu OK confirma lo ya escrito; no hay operación nueva."),

    "morley:miw": (
        LISTO, "R2+R18",
        "Paraguas «MIW» (gama de equipos vía radio) + entrada en la COLA DE MANUALES QUE FALTAN "
        "para MIW-INT, MIW-PSE y MIW-SND.",
        "Validaste la gama con tres enlaces del fabricante. Hoy sólo tenemos 1 FAQ de MIW; los "
        "manuales de los equipos no están ingestados — eso es cola de ingesta, no de catálogo."),

    "morley:tg": (
        LISTO, "R10",
        "ALTA `morley:tg` con `categoria: software` + doc_map a los 15 documentos de TG.",
        "«Aunque sea software, los técnicos también deberían poder preguntar sobre ello». Es la "
        "clase MÁS CARA de tu pasada: 15 de tus 57 anotaciones son esta misma frase. La cuarentena "
        "por «acrónimo corto» trataba TG como una sigla sospechosa; para un software la sigla ES el "
        "nombre."),

    "morley:vsn": (
        LISTO, "R2",
        "«VSN» NO se da de alta como producto: es la etiqueta de la familia VSN PLUS, cuyo paraguas "
        "ya está adjudicado (VSN 4/8/12 PLUS).",
        "Tu nota confirma R2 con la cita del manual («Acceso a Nivel 2…»)."),

    "kidde:kit-2x-afr-c-09": (
        LISTO, "R8", "RETIRAR el candidate; la grafía real es `2X-AFR-C` (repetidor compacto).",
        "«OK con propuesta del juez». El sufijo `-09` venía del nombre del fichero."),

    "kidde:zlsm-md": (
        LISTO, "R12",
        "Un producto con DOS accesos: canónico + alias. Portada: «9-30501-KID» y justo debajo "
        "«Kidde MiniLaser» → los dos entran, uno como canónico y otro como alias.",
        "Tu nota es la que hace nacer R12 («aquí extrayendo el nombre del doc de la portada deberías "
        "haber detectado también lo de 9-30501-KID»). Y tu aviso del homónimo va con ella: Notifier "
        "tiene su propio Minilaser100, así que el alias «minilaser» sólo puede resolver con la marca "
        "puesta — si no, va a `homonyms.jsonl` con política clarify. "
        "TU OTRA PREGUNTA («¿tenemos este doc repetido en ESP?»): NO son duplicados — el ES es la "
        "FICHA (`DS_KIDDE_ZLSM_MD…ES`) y el EN es el MANUAL DE INSTALACIÓN (`MI_KIDDE_ZLSM_MD…ING`). "
        "Distinto tipo de documento, los dos se quedan. Mismo patrón en ZLSM_ME y ZLSM_MR."),

    "kidde:zlsm-mr": (
        LISTO, "R8+R12", "RETIRAR el candidate `ZLSM-MR`; el sujeto es el módulo funcional de "
                         "entrada/salida MiniLaser, referencia `9-30521`.",
        "Dos filas, las dos con tu OK al juez."),

    "morley:fl-20": (
        LISTO, "R11",
        "BAJA del documento `I56-3956-201_PT Morley Loop FAAST LT QIG.pdf` (clase: fragmento PT con "
        "hermano ES).",
        "«esto es documentación en portugués. retíralo del corpus»."),

    "morley:morley-ias-max": (
        LISTO, "R11", "BAJA del documento `Docs Morley-IAS Max - QR` (clase: sólo un enlace).",
        "«solo es un QR que además no funciona»."),

    "notifier:hssd": (
        LISTO, "R2+R18", "ALTA `notifier:hssd` (gama de detección por aspiración de alta "
                         "sensibilidad) + relación con HSSD-2.",
        "«OK a HSSD». Tu nota de `notifier:airsense` la completa: la gama viva es HSSD-2."),

    "notifier:nfs-32-001": (
        BLOQUEO, "R14",
        "RETIRAR el candidate (es la norma francesa AFNOR NF S 32-001, no un producto) en las DOS "
        "filas, y adjudicar el sujeto real de cada documento: "
        "`D1056-1_NFXI-BS-BSF` → NFXI-BS / NFXI-BSF · `D838-1_kac sounders` → gama WMSOU.",
        "CONFIRMADO lo que pediste que confirmara. El D838 es la hoja de instalación de las sirenas "
        "de pared de System Sensor Europe: las OCHO especificaciones del documento coinciden "
        "LITERALMENTE con la hoja publicada de WMSOU (15-32 VDC sin aislador / 15-28 con aislador, "
        "<6,81 mA, 100 dB(A) ±3, −25 a +70 °C, 95% sin condensación, IP24/IP65, 2,5 mm², y el mismo "
        "pie «System Sensor Europe, Units 15-19 Trescott Road, Redditch»), y NO coinciden con las de "
        "sus hermanos de otra marca (el KAC `WSO-` y el Notifier Opal `NFX-WS-`, que dan 95 dB(A) e "
        "IP21C/IP44). El propio documento cubre las DOS variantes: imprime los dos rangos de tensión, "
        "que es exactamente el corte P01 (sin aislador) / P02 (con aislador). "
        "BLOQUEO declarado: el documento NO imprime ningún sufijo de color (-RR / -WW), así que dar "
        "de alta los cuatro SKU sería inventar cuatro tokens que no aparecen en el corpus. Propongo "
        "dar de alta la GAMA `systemsensor:wmsou` y esperar a un documento que enumere los SKU "
        "(R1' invertida: si el doc no nombra modelos, se atesta al nivel que sí sostiene)."),

    "notifier:repetidor-serie-1000": (
        LISTO, "R15",
        "ALTA con la grafía del juez («Repetidor de la Serie 1000») + alias «repetidor central "
        "ID1000» + relación con `notifier:id1000`.",
        "Tu nota es la que hace nacer R15: un nombre genérico necesita su sistema, o nadie lo "
        "encuentra."),

    "notifier:securnet-plus-02": (
        LISTO, "R8+R10", "Grafía `SECURNET PLUS` (sin el `02`, que es el número de adenda) y "
                         "`categoria: software`.",
        "«OK con el juez. esto es un software, no un producto físico»."),

    "spectrex:40-40l": (
        LISTO, "R9",
        "CUATRO modelos, no uno: S40/40L, S40/40LB, S40/40L4 y S40/40L4B. El sufijo «B» = función "
        "de prueba incorporada (BIT) → al campo `atributos`.",
        "Tu nota es la que hace nacer R9, y es la corrección más instructiva de la pasada: el juez "
        "leyó la PORTADA y tú leíste la §1.1 «Descripción general» de la P9, que es donde el "
        "fabricante los diferencia."),

    "xtralis:vesda": (
        LISTO, "R11+R16",
        "DOS operaciones distintas para dos documentos distintos: "
        "(a) `Cursos formacion_Marzo 2026.pdf` → BAJA del corpus, y la clase entera con él; "
        "(b) `HSLI_IN_020 Tabla equivalencia TG` → NO es de VESDA: es la tabla de renombrado del "
        "software TG (post-2021 pasa a TG-BASE) → se atesta al software, no a VESDA.",
        "«aplica esto a documentos del mismo estilo» — lo tomo como instrucción de CLASE: el censo "
        "de documentos sin contenido técnico se hace entero y se te presenta en bloque, no fila a "
        "fila. Y (b) es el caso de libro de R16: VESDA sale 91 veces en un documento que no va de "
        "VESDA — el token más repetido no es el sujeto."),

    "notifier:airsense": (
        LISTO, "R10+R18",
        "`AIRSENSE` NO es producto: es el FABRICANTE (AirSense Technology Ltd). Dos documentos, dos "
        "sujetos: `MADT731_04` → gama HSSD-2 · `TIDT109` → software `Classifire`.",
        "Tus dos notas. La segunda añade un dato que hay que verificar antes de cablearlo: "
        "«Classifire se utiliza en el Minilaser100 de Notifier (MIDT734), y puede que en otros "
        "(tendrás que validarlo)» — queda como verificación pendiente, no como atestación."),

    "notifier:faast-lt": (
        LISTO, "R2+R17", "«FAAST LT» es PARAGUAS de familia, no producto.",
        "Tus dos notas insisten en lo mismo: es la familia y tiene muchos modelos."),

    "notifier:lt-200": (
        LISTO, "R17",
        "NO se crea una familia aparte para «FAAST LT-200»: es la misma gama que FAAST LT. "
        "`notifier:lt-200` y `xtralis:lt-200` se resuelven contra ese paraguas.",
        "Tu nota es la que hace nacer R17, con el catálogo del fabricante como desempate. Y es la "
        "nota donde pediste la WIKI DE MODELOS — ya está construida, en `/catalogo` del panel."),

    "xtralis:lt-200": (
        LISTO, "R17", "Se resuelve con la fila anterior (misma familia).",
        "«OK con juez. este doc va sobre la familia FAAST LT»."),

    "kidde:ke-dba-sktw": (
        BLOQUEO, "R13",
        "ALTA `kidde:ke-dba-sktw` (falda embellecedora para base de montaje) + relación "
        "`accessory-of` → `kidde:ke-db3010w`.",
        "El alta se puede hacer hoy; la RELACIÓN no: `relations.jsonl` admite "
        "`variant-of|rebrand-of|shared-doc|supersedes` y NO tiene `accessory-of`. Es un cambio de "
        "esquema — va con dúo y gate, no de tapadillo."),

    "spectrex:40-40-air": (
        BLOQUEO, "R12+R13",
        "ALTA del Air Shield (referencia `TM777650`, con `777650` como alias) + relación "
        "`accessory-of` → la FAMILIA 40/40, no un modelo.",
        "Mismo bloqueo de esquema que el anterior. Tu enlace de Emerson lo dice explícito: «can be "
        "used with all Spectrex 40/40 series flame detectors» — el padre es la familia entera."),

    "kidde:2a-pak-hpl": (
        LISTO, "R8", "Grafía `2010-2A-PAK-HPL` (la del fabricante) en las dos filas.",
        "«OK con juez» ×2."),

    "notifier:serie-ps": (
        LISTO, "R9+R2",
        "Paraguas «Serie PS» (fuentes de alimentación) con los modelos de la tabla de la P2: PS-12 "
        "y PS-24, y sus variantes de intensidad (PS-12: 3 y 5 A · PS-24: 1,4, 2,5 y 5 A) en "
        "`atributos`.",
        "Segundo caso de R9: los modelos estaban en una tabla del cuerpo, no en el título."),

    "notifier:id1000": (
        LISTO, "R16",
        "`TIDT066_copia.pdf` → doc_map a CINCO: SC-6, CZ-6, IM-10, CR-6 **y** la central ID1000 "
        "(que es el sujeto principal).",
        "Tu nota es la que hace nacer R16. Es un boletín de incompatibilidad, y esos no tienen «un "
        "modelo»: tienen los afectados más el sistema donde ocurre."),

    "spectrex:40-40i": (LISTO, "R8", "Grafía `S40/40I` (la del fabricante).", "«OK con el juez»."),

    "morley:mie-ma-100": (
        LISTO, "R9+R2",
        "Paraguas «HRZ» (centrales convencionales) con HRZ-2, HRZ-4 y HRZ-8. El documento hermano "
        "`MIE-MI-100` es el que lleva el detalle de los modelos.",
        "Tercer caso de R9, con una vuelta de tuerca: la enumeración no está ni en la portada ni en "
        "el cuerpo de ESTE documento, está en su hermano de la misma serie documental."),

    "997-493-002-2": (
        LISTO, "R11+R14",
        "BAJA del documento (clase: nunca imprime un modelo comercial; «EN54 2-8 Zone» es la norma "
        "más una descripción funcional).",
        "«retira este manual del corpus». Confirma de paso la clase (d) de R11."),
}


def _ids_anotados(ruta: Path) -> list[str]:
    """Los ids de las filas del packet que llevan nota de Alberto, en orden."""
    texto = ruta.read_text("utf-8")
    vistos, orden = set(), []
    for bloque in re.split(r"\n(?=- \[[ xX]\] )", texto):
        m = re.match(r"- \[[ xX]\] `([^`]+)`", bloque)
        if not m or not re.search(r"^\s*alberto:", bloque, re.I | re.M):
            continue
        pid = m.group(1)
        if pid not in vistos:
            vistos.add(pid)
            orden.append(pid)
    return orden


def main(argv: list[str]) -> int:
    anotados = _ids_anotados(ANOTADO)

    # EL GUARDARRAÍL. Sin esto, este script sería un documento a mano con pasos
    # extra: una nota suya podría caerse sin que nadie se enterase.
    faltan = [p for p in anotados if p not in MAPEO]
    sobran = [p for p in MAPEO if p not in anotados]
    if faltan or sobran:
        print("DESCUADRE entre las filas anotadas y el mapeo:")
        for p in faltan:
            print(f"  · ANOTADA POR ALBERTO Y SIN DERIVAR: {p}")
        for p in sobran:
            print(f"  · DERIVADA Y NO ANOTADA (¿inventada?): {p}")
        return 1

    por_estado = {LISTO: [], PALABRA: [], BLOQUEO: []}
    for pid in anotados:
        estado, regla, op, nota = MAPEO[pid]
        por_estado[estado].append((pid, regla, op, nota))

    print(f"=== DERIVACIÓN de la pasada de Alberto ({len(anotados)} ids anotados) ===")
    for estado, titulo in ((LISTO, "SE APLICAN (con gate; no necesitan nada de ti)"),
                           (PALABRA, "NECESITAN UNA FRASE TUYA"),
                           (BLOQUEO, "BLOQUEADAS POR ALGO QUE HAY QUE HACER ANTES")):
        filas = por_estado[estado]
        print(f"\n--- {estado}: {titulo} — {len(filas)} ---")
        for pid, regla, op, _ in filas:
            print(f"  · [{regla:9s}] {pid:32s} {op[:90]}")

    if "--md" in argv:
        destino = Path(argv[argv.index("--md") + 1])
        destino.write_text(_markdown(anotados, por_estado), "utf-8")
        print(f"\n→ {destino}")
    return 0


def _markdown(anotados: list[str], por_estado: dict) -> str:
    partes = [
        "# s331 — lo que produjo tu pasada completa del packet v3\n",
        f"> Anotaste **las 56 filas vivas** ({len(anotados)} ids distintos): el packet E1 queda "
        "CERRADO — no hay ninguna fila esperando respuesta tuya.\n>\n"
        "> Generado por `scripts/s331_derivar_pasada.py`, que **falla si alguna nota tuya se queda "
        "sin derivar** — la cobertura no es una afirmación mía, es una comprobación.\n",
    ]
    for estado, titulo, intro in (
        (LISTO, "✅ Se aplican sin ti",
         "Tu nota determina la operación. Cada una pasa por el gate (dry-run → censo del radio de "
         "explosión → recibo) antes de escribirse."),
        (PALABRA, "🟡 Necesitan una frase tuya",
         "Aquí no puedo elegir sin inventar. Son las únicas que te bloquean."),
        (BLOQUEO, "🔴 Bloqueadas por algo previo",
         "La decisión está tomada; lo que falta es un cambio de esquema o una medida."),
    ):
        filas = por_estado[estado]
        partes.append(f"\n## {titulo} — {len(filas)}\n\n{intro}\n")
        for pid, regla, op, nota in filas:
            partes.append(f"\n### `{pid}`  ·  {regla}\n\n**Operación:** {op}\n\n{nota}\n")
    return "".join(partes)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
