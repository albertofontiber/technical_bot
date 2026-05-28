#!/usr/bin/env python3
"""Verificación de citación determinista — capa 1 del judge v2 (faithfulness).

Para cada caso del eval log: extrae cada afirmación citada [F<n>] de la respuesta
del bot, extrae sus DATOS DUROS (números+unidad, normas, switches, secciones), y
verifica de forma determinista si cada dato está en el chunk citado / en otro
chunk / en ninguno.

Opera sobre los chunks COMPLETOS del eval log — inmune al truncado del .md.
Reproducible y auditable. No usa LLM.
"""
import sys
import json
import re

sys.stdout.reconfigure(encoding="utf-8")

LOG = "logs/eval_20260502T152857Z.json"

# --- Extracción de datos duros ---
UNIT = r"(?:V\s?(?:DC|CC|CA|AC)?|mA|kΩ|Ω|ohmios?|ohm|µF|μF|uF|nF|mm²|mm2|mm|cm|km|°C|%|W\b|Hz|kHz|baudios?)"
PATTERNS = [
    re.compile(rf"\b\d+[.,]?\d*\s?{UNIT}", re.IGNORECASE),          # 24V, 6,8 kΩ, 40 Ω, 0,5 µF
    re.compile(r"\bEN\s?\d{2,5}(?:[-‑]\d+)?(?:\s?\d+\.\d+)?", re.IGNORECASE),  # EN54-2, EN 54-20
    re.compile(r"\bUNE[-\s]?(?:EN\s?)?\d{3,6}(?:[-\d]+)?", re.IGNORECASE),
    re.compile(r"\bNFPA\s?\d{1,4}", re.IGNORECASE),
    re.compile(r"\bIEC\s?\d{3,5}", re.IGNORECASE),
    re.compile(r"\bIP\s?\d{2}\b", re.IGNORECASE),
    re.compile(r"\bSW\s?\d+\s?[-‑]?\s?\d*", re.IGNORECASE),          # SW3-6, SW1-7
    re.compile(r"\bTB\s?\d+(?:[-‑]\d+)?", re.IGNORECASE),            # TB1-1
    re.compile(r"\bJP\s?\d+", re.IGNORECASE),
    re.compile(r"\b\d+\.\d+(?:\.\d+){1,3}\b"),                       # secciones 5.3.4.8
]


def norm(s):
    """Normaliza para comparación: minúsculas, sin espacios, coma->punto."""
    return re.sub(r"\s+", "", s.lower()).replace(",", ".")


def hard_tokens(text):
    out = []
    for pat in PATTERNS:
        for m in pat.finditer(text):
            tok = m.group(0).strip()
            if tok and tok not in out:
                out.append(tok)
    return out


def claims_with_citations(answer):
    """Devuelve [(claim_text, [fnums])] — afirmación + fragmentos citados."""
    out = []
    # localizar grupos de marcadores [F1][F2]...
    for m in re.finditer(r"(?:\[F\d+\])+", answer):
        fnums = [int(x) for x in re.findall(r"F(\d+)", m.group(0))]
        # claim = texto desde el delimitador anterior hasta el marcador
        start = m.start()
        prev = max(answer.rfind(c, 0, start) for c in ".\n;:!•")
        claim = answer[prev + 1:start].strip()
        if claim:
            out.append((claim, fnums))
    return out


def main():
    log = json.load(open(LOG, encoding="utf-8"))
    results = log["results"]

    tot_tokens = tot_supported = tot_miscited = tot_missing = 0
    cases_with_missing = []

    for r in results:
        qid = r["question"]["id"]
        answer = r["result"].get("answer", "")
        chunks = r["result"].get("chunks_full") or []
        chunk_norm = [norm(c.get("content", "")) for c in chunks]

        claims = claims_with_citations(answer)
        case_tokens = case_sup = case_mis = case_mis_list = 0
        missing = []
        miscited = []

        for claim, fnums in claims:
            for tok in hard_tokens(claim):
                tn = norm(tok)
                if len(tn) < 2:
                    continue
                case_tokens += 1
                tot_tokens += 1
                in_cited = any(
                    0 <= fn - 1 < len(chunk_norm) and tn in chunk_norm[fn - 1]
                    for fn in fnums
                )
                in_any = any(tn in cn for cn in chunk_norm)
                if in_cited:
                    case_sup += 1
                    tot_supported += 1
                elif in_any:
                    case_mis += 1
                    tot_miscited += 1
                    miscited.append(f"'{tok}' citado a F{fnums} pero está en otro F")
                else:
                    tot_missing += 1
                    missing.append(f"'{tok}' (claim: …{claim[-70:]})")

        flag = ""
        if missing:
            flag = f"  ⚠ {len(missing)} dato(s) sin soporte en NINGÚN chunk"
            cases_with_missing.append((qid, missing, miscited))
        print(f"{qid:7s} judge={r['score'].get('judge',{}).get('overall_pass')!s:5s} "
              f"| {len(claims):2d} claims citadas | {case_tokens:2d} datos duros | "
              f"sup={case_sup:2d} miscit={case_mis:2d} sin_soporte={len(missing)}{flag}")

    print("\n" + "=" * 70)
    print(f"TOTAL datos duros citados: {tot_tokens}")
    print(f"  soportados en el F citado:     {tot_supported} ({100*tot_supported//max(tot_tokens,1)}%)")
    print(f"  miscitados (en otro F):        {tot_miscited}")
    print(f"  SIN SOPORTE en ningún chunk:   {tot_missing}  <- candidatos a invención")
    print("\n--- Detalle de casos con datos sin soporte ---")
    for qid, missing, miscited in cases_with_missing:
        print(f"\n[{qid}]")
        for m in missing[:8]:
            print(f"   SIN SOPORTE: {m}")
        for m in miscited[:4]:
            print(f"   miscitado:   {m}")


if __name__ == "__main__":
    main()
