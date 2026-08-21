# -*- coding: utf-8 -*-
"""s331 — Genera el packet E1 **v3**: solo lo PENDIENTE, con la recomendación afinada.

Por qué un v3 y no seguir sobre el v2 (encargo de Alberto, 20-ago): el v2 arrastra 125 filas ya
resueltas entre las 67 vivas, y su forma de presentar cada fila causó DOS errores reales que él
mismo detectó al repasarlo:

  1. **Homónimos indistinguibles.** «Con que Sistema Operativo … de la DXc Connexion» y «… de la ZX
     y DX» se diferencian en tres letras, y una nota suya acabó aplicada al documento equivocado
     (6 productos ZX quedaron atados a la FAQ de la DXc → DEC-261). El v3 marca los homónimos con
     ⚠️ y añade un discriminador (cita de portada + document_id corto).
  2. **La línea `juez:` se lee como si fuera lo aplicado.** Criticó unos ids (ZXce/ZXhe/ZX50) que
     nunca se aplicaron: eran propuesta del juez que R1 descartó. El v3 separa **PROPUESTO** de
     **APLICADO** de forma explícita.

Además pre-clasifica cada fila viva por los PATRONES QUE ÉL YA FIRMÓ, para que la mayoría se
adjudique en bloque y su tiempo se gaste solo en lo que de verdad decide.

Uso:  python scripts/s331_packet_v3.py
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=False)
from src.http_pool import abierto  # noqa: E402

SB = os.environ["SUPABASE_URL"].rstrip("/")
HS = {"apikey": os.environ["SUPABASE_SERVICE_KEY"],
      "Authorization": f"Bearer {os.environ['SUPABASE_SERVICE_KEY']}"}
V2 = ROOT / "evals/s320_e1_packet_adjudicacion_v2.md"
V3 = ROOT / "evals/s320_e1_packet_adjudicacion_v3.md"
RESUELTA = re.compile(r"↳ \*\*s3\d\d[a-z]?:\*\* ✅")

# Patrones que Alberto YA firmó en s324/s331 → la recomendación deja de ser genérica.
PATRONES = [
    ("P1", "el juez propone otra grafía y hay cita ✓ de portada",
     lambda b: "el juez propone otra grafía" in b and "cita ✓" in b,
     "**seguir al juez**: es el patrón que firmaste 9 veces («OK con juez») en §1.B"),
    ("P2", "fragmento PT/FR de 1 chunk con hermano ES completo",
     lambda b: re.search(r"\((?:Morley|Notifier|Kidde|Aritech|Xtralis)[^)]*·\s*1 chunk", b) and
               re.search(r"_PT|_FR|P\.pdf|portugu|franc", b, re.I),
     "**baja del corpus**: firmaste esta clase 3 veces (996-130 FR, MIE-MI-120P, MNDT730P)"),
    ("P3", "ARTEFACTO_EXTRACCION con 0 menciones estrictas",
     lambda b: "ARTEFACTO_EXTRACCION" in b and re.search(r"estrictas (?:doc )?0", b),
     "**retirar**: sin ninguna mención del token, no es un producto"),
    ("P4", "nombre real CON barra (no es concatenación)",
     lambda b: "nombre real CON barra" in b or "nombre con barra" in b,
     "**tuya**: un «sí» lo da de alta; comprueba que la grafía es la del FABRICANTE (lección DOA: "
     "el sufijo del certificado no es parte del modelo)"),
    ("P5", "el doc va de una FAMILIA y el nombre del fichero engaña",
     lambda b: re.search(r"2x_at|2X-AT", b) and re.search(r"2X-A(?![T-])", b),
     "**R1'**: mira el CONTENIDO, no el nombre — validaste 2 veces que los `2x_at` van sobre los "
     "NO táctiles"),
]


# Filas VALIDADAS con la ficha del fabricante (encargo de Alberto, 20-ago) — su nota va bajo la fila.
VALIDADAS = {
    "morley:efs-em-8": (
        "✅ **VALIDADO online** (`evals/s331_validacion_efsem_nx_v1.md`): panel convencional de 8 zonas, "
        "**obsoleto** (Notifier lo publica en `manualesobs`). **El motivo por el que cayó era la "
        "respuesta**: `MS8` y `FS8` son EL MISMO manual (código `997-201-103`, misma edición) archivado "
        "bajo las DOS marcas ⇒ **R3 (OEM)**, se atesta bajo ambas. Lo único que queda es TU decisión de "
        "**namespace**: ¿`notifier:efs-em-8` o `morley:efs-em-8`?"),
    "notifier:nx2-r-r-y-nx5-r-r": (
        "✅ **VALIDADO online** (`evals/s331_validacion_efsem_nx_v1.md`): son **DOS** productos reales — "
        "`NX2/R/R` (flash estroboscópico rojo, 2 W) y `NX5/R/R` (sirena/estrobo de 14 tonos, flash 5 W). "
        "La grafía con barras es la del FABRICANTE (**R8** cumplida) ⇒ por **R7** el id concatenado NO se "
        "crea: son dos altas. Gap: 1 mención por modelo, en un documento que es solo un dibujo (su PDF "
        "tiene 17 caracteres de texto), pero la ficha del fabricante lo respalda."),
}


def clasifica(bloque: str) -> list[tuple[str, str, str]]:
    return [(k, d, r) for k, d, f, r in PATRONES if f(bloque)]


def main() -> int:
    texto = V2.read_text(encoding="utf-8")
    utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%MZ")

    with abierto(timeout=60.0) as c:
        docs, off = [], 0
        while True:
            r = c.get(f"{SB}/rest/v1/documents", headers=HS,
                      params={"select": "id,document_family,source_pdf_filename,status,manufacturer",
                              "limit": "1000", "offset": str(off)})
            r.raise_for_status()
            page = r.json()
            docs += page
            if len(page) < 1000:
                break
            off += 1000
    # homónimos: documentos activos cuyo nombre coincide en los primeros 34 caracteres
    act = [d for d in docs if d["status"] == "active"]
    por_prefijo = defaultdict(list)
    for d in act:
        por_prefijo[d["document_family"][:34].lower()].append(d["document_family"])
    homonimos = {n for v in por_prefijo.values() if len(v) > 1 for n in v}

    secciones, sec = defaultdict(list), None
    for bloque in re.split(r"\n(?=- \[ \] `)", texto):
        for linea in bloque.split("\n"):
            if linea.startswith("### "):
                sec = linea.strip("# ").strip()
        if not re.match(r"- \[ \] `", bloque) or RESUELTA.search(bloque):
            continue
        secciones[sec].append(bloque.rstrip())

    vivas = sum(len(v) for v in secciones.values())
    cuenta = Counter()
    cuerpo = []
    for s, bloques in secciones.items():
        cuerpo.append(f"\n### {s}  ·  {len(bloques)} vivas\n")
        for b in bloques:
            clave = re.match(r"- \[ \] `([^`]+)`", b).group(1)
            pats = clasifica(b)
            for k, _, _ in pats:
                cuenta[k] += 1
            # ¿el doc de esta fila tiene homónimo?
            aviso = ""
            for h in homonimos:
                if h[:26].lower() in b.lower():
                    aviso = (f"\n      ⚠️ **HOMÓNIMO** — hay más de un documento activo cuyo nombre empieza "
                             f"igual («{h[:44]}…»). **Comprueba la CITA antes de anotar**: en s331 una nota "
                             f"acabó en el documento equivocado por esto (DEC-261).")
                    break
            # separar propuesto de aplicado
            b2 = re.sub(r"^(      juez: )", r"      PROPUESTO por el juez (NO es lo aplicado) · ", b, flags=re.M)
            val = VALIDADAS.get(clave)
            reco = f"\n      {val}" if val else ""
            if pats:
                reco += "\n      🎯 **Recomendación afinada** (patrón que ya firmaste): " + \
                       " · ".join(f"[{k}] {r}" for k, _, r in pats)
            cuerpo.append(b2 + aviso + reco + "\n")

    cab = f"""# Packet E1 — adjudicación · **v3** (generado {utc})

> **Esta versión SUSTITUYE al v2 para trabajar.** El v2 queda como archivo: allí está la traza de
> las **125 filas ya resueltas** (con su recibo) y tus anotaciones originales. Aquí solo hay lo que
> sigue **VIVO: {vivas} filas**.
>
> **Qué cambia respecto al v2, y por qué** — los dos cambios nacen de errores REALES que tu repaso
> destapó, no de estética:
>
> 1. ⚠️ **Los documentos homónimos van marcados.** Tu nota «este archivo habla también de la ZX-A,
>    ZX-E…» acabó aplicada a la FAQ de la **DXc Connexion** en vez de a la de **«ZX y DX»** — se
>    diferencian en tres letras. Costó 6 atestaciones equivocadas (DEC-261). Ahora cada fila con
>    riesgo de confusión lleva un aviso y te pide comprobar la cita.
> 2. 🔍 **«PROPUESTO por el juez» ya no se confunde con lo aplicado.** Criticaste que el documento
>    «valiera para la ZXce, la ZXhe, ZX50» — y tenías razón, **pero esos ids nunca se aplicaron**:
>    eran propuesta del juez que la regla R1 descartó. El v2 los imprimía al lado de lo aplicado.
> 3. 🎯 **Cada fila viva lleva una recomendación afinada** con los patrones que TÚ ya firmaste, para
>    que la mayoría se resuelva en bloque:
>
> | patrón | qué es | filas | qué hacer |
> |---|---|---|---|
> | **P1** | el juez propone otra grafía y hay cita ✓ de portada | {cuenta['P1']} | seguir al juez (lo firmaste 9×) |
> | **P2** | fragmento PT/FR de 1 chunk con hermano ES | {cuenta['P2']} | baja del corpus (lo firmaste 3×) |
> | **P3** | artefacto con 0 menciones estrictas | {cuenta['P3']} | retirar |
> | **P4** | nombre real CON barra | {cuenta['P4']} | **tuya** — comprueba la grafía del fabricante |
> | **P5** | el nombre del fichero engaña sobre la familia | {cuenta['P5']} | R1': manda el contenido |
>
> **Cómo trabajar sobre este fichero**: escribe tu nota debajo de la fila, empezando por `Alberto:`
> (igual que en el v2). Si el fichero es tuyo en local, súbelo y lo proceso.
"""
    V3.write_text(cab + "\n---\n" + "\n".join(cuerpo), encoding="utf-8")
    print(f"{V3.name}: {vivas} filas vivas · patrones {dict(cuenta)}")
    for s, b in secciones.items():
        print(f"   {s[:56]:58} {len(b):3} vivas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
