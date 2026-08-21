"""Huella de detección en el CORPUS de los 3 términos nuevos.

Fable: «0 disparos en 36 negativos + 137 reales es una base fina para un término
letters-only», con el precedente DEC-272 (NAS: 231→11 documentos). La respuesta
no es discutir el flag: es la misma medida que zanjó aquello — ¿en cuántos
documentos del corpus dispararía cada término, y son SUYOS?
"""
import json, re, sys, unicodedata
from collections import defaultdict
sys.path.insert(0, "/home/user/technical_bot")
from dotenv import load_dotenv; load_dotenv("/home/user/technical_bot/.env")
from src.config import SUPABASE_URL, SUPABASE_SERVICE_KEY
from src.rag import catalog_store as cs
import httpx
SB = SUPABASE_URL.rstrip("/") + "/rest/v1"
H = {"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"}

CORES = {  # tal cual los emite el censo del gate
 "AM-LCD":      r"am[-\s/.+]*lcd",
 "SDX-751-TEM": r"sdx[-\s/.+]*751[-\s/.+]*tem",
 "LPX-751":     r"lpx[-\s/.+]*751",
}
SUYO = {"AM-LCD": "notifier:am-lcd", "SDX-751-TEM": "notifier:sdx-751-tem",
        "LPX-751": "notifier:lpx-751"}

def pag(t, params, orden="id"):
    """Paginar SIN `order` es un bug: PostgREST no garantiza orden estable entre
    rangos, así que la paginación salta y duplica filas. Lo vi porque dos pases
    idénticos dieron AM-LCD=2 y AM-LCD=6. Con `order` explícito es determinista;
    y se comprueba contra el total que devuelve `count=exact`."""
    out, d0 = [], 0
    with httpx.Client(timeout=300) as c:
        r0 = c.get(f"{SB}/{t}", headers={**H, "Prefer": "count=exact"},
                   params={**params, "limit": "1"})
        total = int((r0.headers.get("content-range") or "0/0").split("/")[-1] or 0)
        while True:
            r = c.get(f"{SB}/{t}", headers={**H, "Range-Unit": "items",
                      "Range": f"{d0}-{d0+999}"}, params={**params, "order": orden})
            r.raise_for_status()
            d = r.json()
            out += d
            if len(d) < 1000:
                break
            d0 += 1000
    if len(out) != total:
        raise SystemExit(f"paginación incompleta en {t}: {len(out)} de {total} filas")
    return out

cat = cs.load()
fuentes = defaultdict(set)          # id -> documentos que el doc_map le asigna
for f in cat.doc_map:
    for e in f.get("entries", []):
        fuentes[str(e.get("id"))].add(str(f.get("document_id")))

print("bajando chunks_v2 …", flush=True)
ch = pag("chunks_v2", {"select": "document_id,content"})
por_doc = defaultdict(list)
for x in ch: por_doc[str(x.get("document_id"))].append(x.get("content") or "")
print(f"  {len(ch)} chunks en {len(por_doc)} documentos\n")

filas = []
print("=== HUELLA POR TÉRMINO (documentos donde dispararía) ===")
for term, core in CORES.items():
    rx = re.compile(rf"(?<![a-z0-9]){core}(?![a-z0-9])", re.I)
    hits = {d for d, ts in por_doc.items() if any(rx.search(t or "") for t in ts)}
    suyos = fuentes.get(SUYO[term], set())
    ajenos = hits - suyos
    print(f"\n  {term:14s} dispara en {len(hits):4d} documentos · suyos {len(hits & suyos)} · "
          f"AJENOS {len(ajenos)}")
    filas.append({"termino": term, "documentos": len(hits), "suyos": len(hits & suyos),
                  "ajenos": len(ajenos), "contextos_ajenos": []})
    for d in sorted(ajenos):
        ej = next((t for t in por_doc[d] if rx.search(t or "")), "")
        m = rx.search(ej); ctx = ej[max(0, m.start()-52):m.end()+52].replace("\n", " ") if m else ""
        filas[-1]["contextos_ajenos"].append({"document_id": d, "contexto": ctx.strip()[:160]})
        print(f"      … «{ctx.strip()[:104]}»")


json.dump({
 "que_es": ("s336g · huella de detección en el corpus de los 3 términos que promueve s336f. "
            "Responde al hallazgo de Fable en el dúo de s336f: el censo del gate flagea `AM-LCD` "
            "con [sin_digitos, acronimo_corto] —la clase con la que R19 mata `NAS`— y 137 "
            "consultas reales son base fina para un término letters-only. La medida es la misma "
            "que zanjó DEC-272 (NAS: 231→11 documentos): ¿en cuántos documentos dispara, y son "
            "suyos o ajenos? Y para los ajenos, ¿la aparición es legítima?"),
 "corpus": {"chunks": len(ch), "documentos": len(por_doc)},
 "nota_paginacion": ("el paginador de este script lleva `order` explícito + verificación contra "
                     "`count=exact`. Sin `order`, dos pases idénticos daban AM-LCD=2 y AM-LCD=6 "
                     "y el corpus salía con 954 documentos en vez de 1.080: PostgREST no "
                     "garantiza orden estable entre rangos."),
 "filas": filas,
}, open("/home/user/technical_bot/evals/s336g_huella_deteccion.json", "w"),
   ensure_ascii=False, indent=1)
print("\n→ evals/s336g_huella_deteccion.json")
