# -*- coding: utf-8 -*-
"""s331 — Anota en el packet E1 v2 el ESTADO del residuo que se cerró en esta sesión.

Alberto delegó las 3 preguntas ⏳ (MADT015_01, MNDT600, MNDT701), pidió atacar los no-bloqueantes
(VSN2-PLUS, OCR TI-007) y preguntó por §1.A. Este script marca fila a fila lo que ya NO requiere su
decisión, con el recibo de cada cosa, y deja explícito lo poco que sigue siendo suyo.

Idempotente: borra y reescribe SU bloque (`<!-- s331-estado:* -->`) y SUS marcas (`↳ **s331:**`).
No toca el bloque ni las marcas de s324, ni las anotaciones de Alberto.

Uso:  python scripts/s331_packets_estado.py
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
E1 = ROOT / "evals/s320_e1_packet_adjudicacion_v2.md"
INI, FIN = "<!-- s331-estado:inicio -->", "<!-- s331-estado:fin -->"
S324_FIN = "<!-- s324-estado:fin -->"
MARCA = "      ↳ **s331:** "


def bloque(texto: str, cuerpo: str) -> str:
    """Inserta el bloque de estado s331 DESPUÉS del de s324 (o tras el titular si no existe)."""
    texto = re.sub(re.escape(INI) + r".*?" + re.escape(FIN) + r"\n?", "", texto, flags=re.S)
    nuevo = INI + "\n" + cuerpo.strip() + "\n" + FIN + "\n"
    if S324_FIN in texto:
        cabeza, resto = texto.split(S324_FIN, 1)
        return cabeza + S324_FIN + "\n\n" + nuevo + resto.lstrip("\n")
    partes = texto.split("\n", 1)
    return partes[0] + "\n\n" + nuevo + (partes[1] if len(partes) > 1 else "")


def marcar(texto: str, estados: dict[str, str]) -> tuple[str, int]:
    """Añade una línea `↳ **s331:**` bajo cada casilla `- [ ] \\`<clave>\\`` cuya clave esté en `estados`."""
    texto = re.sub(r"\n" + re.escape(MARCA) + r"[^\n]*", "", texto)   # idempotencia
    n = 0

    def rep(m):
        nonlocal n
        clave = m.group(2)
        est = estados.get(clave) or estados.get(clave.lower())
        if not est:
            return m.group(0)
        n += 1
        return m.group(0) + "\n" + MARCA + est

    texto = re.sub(r"(^- \[ \] `)([^`]+)(`[^\n]*)", rep, texto, flags=re.M)
    return texto, n


def ultimo(patron: str) -> str | None:
    hits = sorted((ROOT / "evals").glob(patron))
    return hits[-1].name if hits else None


def main() -> int:
    rec_lote = ultimo("s331_residuo_aplicar_*.json") or ultimo("s331_residuo_v1_aplicar_*.json")
    rec_baja = ultimo("s331_retirar_docs_aplicar_*.json")
    if not rec_lote or not rec_baja:
        print("AVISO: falta algún recibo de aplicación — se marca igualmente con lo que hay",
              f"(lote={rec_lote}, baja={rec_baja})", file=sys.stderr)
    utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%MZ")
    ref_lote = f"`{rec_lote}`" if rec_lote else "(recibo pendiente)"
    ref_baja = f"`{rec_baja}`" if rec_baja else "(recibo pendiente)"

    estados = {
        # §0.D — las 3 preguntas que Alberto delegó ("son para ti")
        "notifier:madt-015": (
            f"✅ RESUELTO (delegado por ti, s331) → **NFS 2-8**, no la serie FS. Comparé los dos PDF: el manual "
            f"`FS2-1` (que SÍ existe, con `notifier:fs-1/2/4` en catálogo — mi «no existe» de s324 era falso, lo cazó "
            f"el dúo) es de centrales de **1/2/4 zonas**, con EFL solo resistivo, sin entradas digitales ni retardos; "
            f"la guía MADT015_01 tiene **8 zonas**, EFL resistencia **o** condensador, 2 entradas digitales y retardos "
            f"— y su árbol de configuración es idéntico al del anexo MADT015_03 («Anexo al manual de instalación de la "
            f"central **NFS 2-8**, ref.: MI-DT-015»). Aplicado: retag pm + doc_map `notifier:nfs-2-8` · recibo {ref_lote}"),
        "notifier:mndt-600": (
            f"✅ RESUELTO (delegado por ti, s331) → pm **`unknown`**, sin doc_map. El texto es genérico (calibración/"
            f"mantenimiento de detectores de gas) y no nombra ni un modelo: los únicos códigos son las células "
            f"«S1096/2096… S1097.2097…». **Tu pregunta contestada con censo corpus-wide** (1.054 activos): el doc del "
            f"**SMART3 GD2 NO está en el corpus** con ninguna grafía (los 6 hits de «GD2/GD3» son «P**GD-2**00», el "
            f"programador Detnov); el **GD3 = `SMART3G-D3`** sí está atestado (doc MTEX4805 Zona 2). El paraguas "
            f"«SMART 3» sería decisión tuya aparte — no hace falta para limpiar este artefacto · recibo {ref_lote}"),
        "notifier:mndt-701": (
            f"✅ RESUELTO (delegado por ti, s331) → pm **`unknown`**. Confirmado en el PDF: es la guía del software "
            f"del detector **Triple IR / IR3** (SPECTRONIX; la portada es un SharpEye™), pero el software no tiene "
            f"nombre en el texto y solo se habla de «detectores IR3» en bus RS-485. El doc_map queda DIFERIDO al ítem 3 "
            f"de tu lista («nombres con barra»): en cuanto firmes 20/20MI y 20/20R nace la familia y se atesta ahí "
            f"(grafía verbatim del corpus: «S20/20MI») · recibo {ref_lote}"),
        # §1.A — las dos filas que quedaban
        "996-130-000-3 manuel d'utilisation zx_hlsi": (
            f"✅ BAJA APLICADA (tu «baja del corpus» de este packet) · `status=retired`, chunks intactos (reversible) · "
            f"recibo {ref_baja}"),
        "hlsi-ti-007_vsn-4rel": (
            f"✅ CERRADO (s331): la re-ingesta de s324d ya trajo el texto (2 chunks, 3.600 chars — la causa NO era OCR "
            f"sino markdown degenerado, #87), pero los chunks nuevos volvieron con pm artefacto `TI-007`. Hoy: retag a "
            f"**VSN-4REL** + doc_map `notifier:vsn-4rel` con cita full-text «Instalación del módulo VSN-4REL» — "
            f"la atestación que dejaste pendiente · recibo {ref_lote}"),
        # §0.C — las dos preguntas que quedaban
        "aritech:2x-a": (
            "⏳ SIGUE SIENDO TUYA, pero ya con la MEDIDA hecha (s331, sonda `evals/s331_2xa_sonda_plan_v1.json`): crear "
            "el paraguas «2X-A» **no pierde ninguna gold** y hace GANAR 2 golds (12 fuentes cada una, entre ellas «¿El "
            "detector KE-DP3020W vale para la central 2X-A?»). Lo único que dispara es la sonda de tokens sintética "
            "«2 x a» del gate — **0 disparos en las 111 consultas reales**. Lo que necesito de ti es UNA frase: "
            "«2X-A sí, con los táctiles» (38 modelos, incluidos los 11 2X-AT) o «2X-A sí, sin táctiles» (27; los "
            "táctiles ya tienen su propio paraguas 2X-AT). Con eso lo aplico con recibo."),
        "notifier:stratos": (
            "✅ CONFIRMADO por ti (s331: «OK a Stratos… parece de verdad que es una familia», con el enlace de "
            "sensetek). Ya estaba aplicado en s324b como paraguas de familia (LaserStar-HSSD-2 = Stratos HSSD-2, "
            "MINILÁSER25 = Stratos Micra 25, MINILASER 100 = Stratos Micra 100); tu OK cierra la fila."),
    }

    cuerpo = f"""> ## 🟢 ESTADO s331 ({utc}) — el residuo de este fichero, CERRADO salvo una frase tuya
> Encargo tuyo de hoy: «las 3 preguntas son para ti» + atacar los no-bloqueantes + ¿queda algo en §1.A?
>
> **Hecho y aplicado** (dúo r38 Sol+Fable ANTES de escribir; dry-run PASS: detector +0/−0 términos,
> 0 gold perdidas, findability 4/4; recibos {ref_lote} y {ref_baja}):
> - **MADT015_01 → NFS 2-8** (retag + doc_map). Tu hipótesis FS se comprobó al píxel contra el manual
>   `FS2-1` y NO cuadra (1/2/4 zonas, sin condensador EFL, sin entradas digitales ni retardos).
> - **MNDT600 → `unknown`** + tu pregunta contestada: el **SMART3 GD2 no está en el corpus**; el GD3
>   (`SMART3G-D3`) sí, por el doc MTEX4805.
> - **MNDT701 → `unknown`**, con el doc_map diferido al ítem 3 (20/20MI, 20/20R).
> - **TI-007**: retag a VSN-4REL + doc_map con cita full-text → la atestación pendiente de #87, cerrada.
> - **§1.A: COMPLETA.** De sus 13 filas, 11 ya estaban resueltas; hoy caen las 2 últimas (la baja del
>   fragmento FR `996-130` que firmaste, y TI-007).
> - **VSN2-PLUS**: censado (18 grafías en ~20 docs Supra/UCIP) y DIFERIDO a la sentada E1b a propósito —
>   es rebrand multi-marca (NFS Supra ↔ VSN-2Plus/Vision Plus2 ↔ ESS-2Plus): `evals/s331_vsn2plus_censo_v1.md`.
> - **STRATOS**: tu OK cierra la fila (ya estaba aplicado como paraguas en s324b).
>
> **LO ÚNICO QUE SIGUE SIENDO TUYO en este fichero:**
> 1. **2X-A**: una frase — «con táctiles» (38) o «sin táctiles» (27). La medida ya está hecha: 0 gold
>    perdidas, +2 golds ganan fuentes, 0 disparos en 111 consultas reales (solo salta la sonda
>    sintética «2 x a»). Ver la fila marcada de `aritech:2x-a`.
> 2. **Nombres reales con barra (10)**: DOA FJ/CPD, EFS/EM 8, CONV232/485, PUL-D/EXT, PUL-P/EXT,
>    STS/CKD+, 20/20MI, 20/20R, NX2/R/R, NX5/R/R — un «sí» y se dan de alta (y con 20/20MI + 20/20R se
>    desbloquea la atestación de MNDT701).
> 3. **VSN2-PLUS / «Plus2»**: no bloquea; se adjudica dentro de la sentada E1b.
>
> **Deuda declarada nueva**: `TECH_DEBT #95` — los retags de `product_model` NO sobreviven a una
> re-ingesta (el pipeline re-deriva el pm del filename). Hoy no afecta al serving; el arreglo BP es que
> `detect_document_metadata` consulte el doc_map antes de derivar.
>
> Marcas fila a fila: `↳ **s331:**` bajo cada casilla tocada hoy."""

    texto = E1.read_text(encoding="utf-8")
    texto = bloque(texto, cuerpo)
    texto, n = marcar(texto, estados)
    E1.write_text(texto, encoding="utf-8")
    print(f"E1 actualizado: bloque s331 + {n} filas marcadas (esperadas {len(estados)})")
    faltan = [k for k in estados if MARCA + estados[k][:30] not in texto and estados[k][:30] not in texto]
    if faltan:
        print("AVISO: sin marcar →", faltan, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
