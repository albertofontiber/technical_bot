# -*- coding: utf-8 -*-
"""s324b — CONSOLIDA en el packet canónico (evals/s320_e1_packet_adjudicacion_v2.md) las notas que
Alberto escribió en dos copias (`…_v2_AS.md` sobre la versión de las 11:46Z y `…_v2_AS2.md` sobre la
de las 18:50Z), para que revise SIEMPRE la última versión. Idempotente: no duplica notas ya presentes
y sustituye la nota parcial «ALBERTO: aquí » que quedó en el fichero canónico por la completa de AS.
Bajo cada nota deja la respuesta/acción del autor (línea `↳ s324b:`), que él puede matizar.
"""
from __future__ import annotations
import re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
V2 = ROOT / "evals/s320_e1_packet_adjudicacion_v2.md"
COPIAS = [ROOT / "evals/s320_e1_packet_adjudicacion_v2_AS.md", ROOT / "evals/s320_e1_packet_adjudicacion_v2_AS2.md"]

# respuesta del autor a cada nota (clave = inicio de la nota de Alberto)
RESPUESTAS = {
    "aplica a todos los modelos de la serie 2x-A":
        "de acuerdo: NO se crea el producto `aritech:2x-a`; «2X-A» pasa a ser el PARAGUAS de familia (miembros = centrales y repetidores de la serie, derivados por regla; hoy 38). El gate léxico lo había frenado por un negativo SINTÉTICO («2 x a»); medido sobre el tráfico REAL (`query_logs`, 96 consultas): 0 disparos → entra en el lote §0.C con esa medida en el recibo.",
    "¿este no es el mismo doc que la fila anterior?":
        "sí: es la MISMA fila duplicada en el draft (mismo id `kidde:ke-dm3110r-kit`, mismo doc `DS_KIDDE_KE_DM3110R_KIT_f3b7.pdf`, dos fuentes de extracción). Se aplica UNA sola alta.",
    "aquí aplicará a todos los modelos de la familia dxc-connexion":
        "de acuerdo: NO se crea el producto `morley:dxc-connexion` (es la familia; el paraguas «DXc»/«DX Connexion» ya existe, gt s90). La FAQ pasa al doc_map → `morley:dxc1`, `dxc2`, `dxc4` (regla serie × central, como las demás FAQ DXc).",
    "no estoy seguro, creo que eliminaría este doc.":
        "el doc es una hoja de «tarjetas de idiomas» de la Vision Supra (30012012, rev A). Lo dejo ⏳ como BAJA PROPUESTA (no atesto ni doy de alta `morley:vision-supra` desde él). Si confirmas «baja», lo retiro con recibo; si no, lo dejo fuera del lote sin tocar.",
    "Doc en PT, eliminaría si hay documento similar en ES":
        "hecho: `4188-1124-PT` ya está RETIRADO esta mañana (fragmento PT, 6 chunks; el ES `4188-1124-ES issue 6` tiene 116). Esta fila queda sin alta desde ese doc; «CLSS Configuration Tool» es software y se trata como el caso ID²net de abajo (alta desde el doc ES si verifica).",
    "Doc en PT, eliminaría porque el doc \"MADT190_01\" es la versión en español":
        "de acuerdo — misma clase que los 6 PT retirados esta mañana (se me escapó por el nombre `MADT190P_01_C`). Se RETIRA con recibo tras verificar que `MADT190_01` (ES) está activo y con más chunks; sin alta desde el PT.",
    "ojo que no es un modelo, es un software":
        "el software SÍ entra en el catálogo como producto con `clasificacion.categoria = software` (precedente: `morley:mk-vsn`/`mk-zx`/`mk50`/`mkdx`, `notifier:opc-rp1r`, `spectrex:winhost`). ID²NET se da de alta como SOFTWARE (no como modelo de hardware), con cita del doc ES `MADT190_01`. Si prefieres otra categoría (p. ej. «pasarela»/red), dilo.",
    "Modelo S40-40M i.e. con la \"S\"":
        "de acuerdo: canonical `S40/40M` (como lo escribe el doc: «S40/40M XXXXX…») + alias `40/40M` (variante tipográfica; es la forma de las etiquetas del corpus y de los golds «SharpEye 40/40»). Se verifica el token en `MNDT725` antes de escribir.",
    "Modelo S40-40R i.e. con la \"S\"":
        "de acuerdo: canonical `S40/40R` («MODELO S40/40R») + alias `40/40R`. Se verifica el token en `MNDT724`.",
    "Ojo que son dos modelos, el S40-40U y S40-40UB":
        "de acuerdo: DOS altas — `S40/40U` y `S40/40UB` (BIT = prueba incorporada), cada una con su cita verificada en `MNDT723`; alias `40/40U`/`40/40UB`. La fila del draft (`spectrex:40-40u`) no se crea tal cual.",
}


def notas_de(copia: Path) -> list[tuple[str, str]]:
    """[(fila_ancla, nota)] — la fila ancla es la línea `- [ ] …` anterior a la nota (sin marcas ↳ s324)."""
    if not copia.exists():
        return []
    L = copia.read_text(encoding="utf-8").splitlines()
    out = []
    for i, l in enumerate(L):
        if l.strip().startswith("ALBERTO:") and i > 200:
            j = i
            while j > 0 and not L[j].startswith("- [ ]") and not L[j].startswith("- [x]"):
                j -= 1
            nota = l.strip()
            if nota == "ALBERTO: aquí" or nota == "ALBERTO: aquí ":
                continue                                    # la parcial: se sustituye por la de AS
            out.append((L[j], nota))
    return out


def main() -> None:
    v2 = V2.read_text(encoding="utf-8").splitlines()
    # 1) quitar la nota parcial que quedó en el canónico
    v2 = [l for l in v2 if l.strip() not in ("ALBERTO: aquí", "ALBERTO: aquí ")]
    notas: list[tuple[str, str]] = []
    for c in COPIAS:
        for fila, nota in notas_de(c):
            if (fila, nota) not in notas:
                notas.append((fila, nota))
    insertadas, ya, sin_ancla = 0, 0, []
    for fila, nota in notas:
        # localizar la fila ancla en v2 (texto exacto de la casilla)
        idx = [k for k, l in enumerate(v2) if l == fila]
        if not idx:
            sin_ancla.append((fila[:80], nota[:60])); continue
        # si la misma fila aparece 2 veces (draft duplicado), anclar en la que aún no tiene esta nota
        k = None
        for cand in idx:
            fin = cand + 1
            while fin < len(v2) and v2[fin].startswith("      "):
                fin += 1
            bloque = v2[cand:fin]
            if any(l.strip() == nota for l in bloque):
                k = None; ya += 1; break
            k = cand
            break
        if k is None:
            continue
        fin = k + 1
        while fin < len(v2) and v2[fin].startswith("      "):
            fin += 1
        resp = next((r for pref, r in RESPUESTAS.items() if nota.startswith("ALBERTO: " + pref)), None)
        nuevas = ["      " + nota] + (["      ↳ **s324b:** " + resp] if resp else [])
        v2[fin:fin] = nuevas
        insertadas += 1
    V2.write_text("\n".join(v2) + "\n", encoding="utf-8")
    print(f"notas consolidadas: {insertadas} insertadas · {ya} ya presentes · sin ancla: {sin_ancla}")


if __name__ == "__main__":
    main()
