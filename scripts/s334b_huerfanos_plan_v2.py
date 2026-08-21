#!/usr/bin/env python3
"""s334b — plan COMPLETO del segundo asalto a los manuales huérfanos.

POR QUÉ HAY UN SEGUNDO ASALTO. Alberto no dio por buenos los 193 que dejó el
primero («deberías atacarlo hasta que queden 10 como máximo»), y tenía razón por
dos motivos distintos, los dos míos:

  1. **59 nunca fueron huérfanos.** Mi definición no seguía los `redirect`, y el
     resolver SÍ los sigue (`catalog_resolver.py:187` llama `follow_redirect`
     ANTES de indexar el documento; `catalog_store._consumable` lo sigue por
     diseño, «fix dúo s90»). Contar con una definición propia en vez de con la
     del consumidor se inventa un problema. Huérfanos REALES: 134.
  2. **Descarté por prior lo que un instrumento sabía medir.** Aparté los
     `unresolved:` diciendo «asignar fabricante es adjudicación»: cierto, e
     irrelevante — promover no exige asignarlo. El detector se construye con
     `canonical_model` y el índice con `norm_token(canonical_model)`: **el
     namespace no interviene**. Igual con los acrónimos cortos y con los que no
     tenían cita: eran precauciones, no medidas.

LOS TRES MECANISMOS, cada uno verificado antes de entrar aquí:

  **(A) PROMOVER** — el candidate pasa a consumible. Verificado por la sonda G4
  fila a fila y aislada: `resolve_query(canónico)` pasa de no traer su manual a
  traerlo.

  **(B) PROMOVER + DOC_MAP** — para los que ESTRECHAN. Promover puede quitar el
  paraguas de `models` bajo `replace` y dejar la consulta con menos fuentes que
  antes (mecanismo hp009/DEC-091b, lo cazó Fable en r42). No es un muro: es una
  señal de que al plan le falta su acompañamiento. Se añaden al `doc_map` del
  producto, como `secondary`, las fuentes que perdería. Medido sobre el caso
  peor (`notifier:tg-6000`): de 4 fuentes → 1 con sólo promover, y **4 → 5 con el
  doc_map**, o sea 0 perdidas y 1 ganada. `secondary` es literalmente lo que son:
  «lo menciona y sirve como fuente, sin reclamarlo».

  **(C) PROMOVER + ALIAS DE MARCA** — para los bloqueados por un homónimo
  abierto. El token desnudo (`SP-200` en Morley y en Notifier) tiene que seguir
  fallando abierto: ES ambiguo, y resolverlo es adjudicar un rebrand (R8). Pero
  el manual no tiene por qué seguir perdido: con el alias `Morley SP-200` se
  alcanza. Medido: 3 de 4 casos lo alcanzan; el que no (`aritech:apic`) es un
  acrónimo SIN dígitos, y el detector sólo admite alias `nombre-largo` con dígito
  (`catalog_resolver._add`) — se queda fuera y se declara.

LO QUE NO ENTRA, y por qué NO es pereza:
  · **digit-only** (`020-590`, `34110400`, `00051`): el detector excluye los
    tokens sin letras A PROPÓSITO. Promoverlos es inerte — la sonda los marca
    `NI_DETECTA`. Su manual sólo se alcanza si otro id de su fila lo alcanza.
  · **`EEV(2)`**: los paréntesis parten el token; `detect()` devuelve vacío.

NO escribe: produce el plan que consume `s324_lote_firmado_writer.py`.

Uso:  python scripts/s334b_huerfanos_plan_v2.py [--salida X]
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")
os.environ["IDENTITY_RESOLVE"] = "on"
os.environ["IDENTITY_RESOLVE_POLICY"] = "replace"          # el brazo de producción

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)
sys.path.insert(0, str(ROOT))
from src.rag import catalog_store as cs                      # noqa: E402
from src.rag import catalog_resolver as R                    # noqa: E402
from src.rag.catalog_store import CATALOG_DIR, FILES, norm_token  # noqa: E402

VERIF = ROOT / "evals/s334_huerfanos_verificacion_v1.json"
EVID = ROOT / "evals/s334_huerfanos_evidencia_v1.json"
DESTINO = ROOT / "evals/s334b_huerfanos_plan.json"

#: LO QUE YA SE DECIDIÓ EN LA RONDA 1 Y SIGUE VALIENDO. Se arrastra a propósito:
#: un generador nuevo que no hereda las exclusiones del anterior las DESHACE en
#: silencio (aquí volvió a colarse `RHistorico.exe`, que el dúo r42 había sacado).
#: Sólo se heredan las que son de PRODUCTO, no las de mecanismo: `tg-6000`,
#: `8100e-faast` y `m710-cz` salieron por ESTRECHAR, y eso este plan ya lo
#: resuelve con `doc_map_altas`, así que vuelven a entrar.
HEREDADAS = {
    "notifier:eia-485": "R19/R14' — EIA-485 es el bus serie RS-485, no un producto (dúo r42).",
    "notifier:ad-pe": "R19/R2 — «Versión Exd (AD-PE)» es un sufijo de variante (dúo r42).",
    "notifier:rhistorico.exe": "R19 — el producto se llama «Reparación de Históricos»; "
                               "`RHistorico.exe` es su ejecutable (dúo r42).",
    "notifier:am-lcd": "PREFIJO: en su propia cita aparece como «AM-LCD-SPA».",
    "notifier:notifier-inspire-e10": "PREFIJO: aparece como «Notifier INSPIRE E10/E15».",
    "notifier:cfp-ze4": "PREFIJO: aparece como «CFP-ZE4/CFP».",
    "notifier:smart-3-cc": "PREFIJO: aparece como «SMART 3 CC-CD».",
    "notifier:lpx-751": "R2 — huele a etiqueta de serie, no a modelo.",
    "notifier:serie-800": "R2 — «Serie 800» es literalmente una etiqueta de serie.",
    "fidegas:cs4-analgica": "R2 — etiqueta de gama, no modelo.",
    "fidegas:cs4-digital": "R2 — etiqueta de gama, no modelo.",
}

#: PALABRAS, no nombres. MEDIDO, no supuesto: se contó en cuántos `source_file`
#: distintos aparece cada token de riesgo **con frontera de palabra**, que es como
#: lo busca el detector. `VIEW` sale en 331 documentos y `INDICATOR` en 260 — se
#: reparten por todo el corpus porque son palabras inglesas. La primera pasada usé
#: `ilike *X*` (SUBSTRING) y habría excluido además `ITAC` (270→11 al poner la
#: frontera: casaba dentro de «capacitación») y `NAS` (231→11): dos productos
#: legítimos perdidos por medir con un operador distinto del que usa el consumidor.
PALABRAS = {"VIEW": 331, "INDICATOR": 260}

#: Marca legible para el alias cualificado, por namespace.
MARCA = {"morley": "Morley", "notifier": "Notifier", "sensitron": "Sensitron",
         "systemsensor": "System Sensor", "aritech": "Aritech", "fidegas": "Fidegas",
         "xtralis": "Xtralis", "detnov": "Detnov", "zareba": "Zareba",
         "spectrex": "Spectrex", "sense-ware": "Sense-Ware", "desico": "Desico"}


def _copia(promover: set[str]) -> Path:
    d = Path(tempfile.mkdtemp())
    for _, fn in FILES.items():
        if (CATALOG_DIR / fn).exists():
            shutil.copy(CATALOG_DIR / fn, d / fn)
    ruta = d / FILES["products"]
    filas = [json.loads(l) for l in ruta.read_text("utf-8").splitlines() if l.strip()]
    for p in filas:
        if p["id"] in promover:
            p["candidate"] = False
    ruta.write_text("".join(json.dumps(p, ensure_ascii=False) + "\n" for p in filas), "utf-8")
    return d


def _fuentes(catalog_dir: Path, q: str) -> set[str]:
    orig = cs.load
    try:
        cs.load = lambda *a, **k: orig(catalog_dir)
        R._loaded = False
        R._pattern = None
        R._build()
        return set(R.resolve_query(q)["allowed_sources"])
    finally:
        cs.load = orig
        R._loaded = False
        R._pattern = None


def main() -> int:
    destino = (Path(sys.argv[sys.argv.index("--salida") + 1])
               if "--salida" in sys.argv else DESTINO)
    verif = json.loads(VERIF.read_text("utf-8"))
    evid = json.loads(EVID.read_text("utf-8"))
    cita_de = {it["id"]: it for l in evid["lotes"].values() for it in l["ids"]}

    rango = {"DESBLOQUEA": 0, "DESBLOQUEA_PERO_ESTRECHA": 1, "YA_ALCANZABLE": 2,
             "DETECTA_SIN_FUENTE": 3, "NI_DETECTA": 4}
    mejor: dict[str, dict] = {}
    for d in verif["detalle"]:
        if d["id"] not in mejor or rango[d["veredicto"]] < rango[mejor[d["id"]]["veredicto"]]:
            mejor[d["id"]] = d
    # el PEOR caso manda para el estrechamiento (un id que estrecha en uno de sus
    # manuales sigue estrechando aunque desbloquee limpio en otro)
    for d in verif["detalle"]:
        if d["veredicto"] == "DESBLOQUEA_PERO_ESTRECHA":
            mejor[d["id"]] = d

    dm = [json.loads(l) for l in (ROOT / "data/catalog/doc_map.jsonl")
          .read_text("utf-8").splitlines() if l.strip()]
    docid_de_sf = {str(r.get("source_file") or ""): str(r.get("document_id") or "") for r in dm}

    # ── COLISIONES DE CANÓNICO ────────────────────────────────────────────
    # El validador prohíbe dos productos ACTIVOS y no-candidate con el mismo
    # canónico normalizado: `_by_canonical` sería last-wins silencioso. Al
    # promover en bloque aparecen 13, y no todas son el mismo problema:
    #
    #   · `unresolved:X` vs `<marca>:X` → **no es una colisión, es un DUPLICADO**.
    #     La operación correcta no es promover los dos: es REDIRIGIR el
    #     `unresolved:` al que tiene marca. `follow_redirect` hace que la fila del
    #     `doc_map` apunte al producto con marca, así que el manual se alcanza
    #     igual, **sin añadir un término al detector** (riesgo léxico cero) y
    #     arreglando de paso la atribución de marca. Estrictamente mejor.
    #   · `<marca1>:X` vs `<marca2>:X` → homónimo de verdad. Decidir si es un
    #     rebrand es adjudicación (R8): los dos fuera.
    prod = {}
    for l in (ROOT / "data/catalog/products.jsonl").read_text("utf-8").splitlines():
        if l.strip():
            q = json.loads(l)
            prod[q["id"]] = q
    canon_activo = {}
    for q in prod.values():
        if q.get("estado") == "activo":
            canon_activo.setdefault(norm_token(q["canonical_model"]), []).append(q["id"])

    def _consumible(pid: str) -> bool:
        visto: set[str] = set()
        q = prod.get(pid)
        while q and q.get("estado") == "redirect" and q.get("redirect_to") and pid not in visto:
            visto.add(pid)
            pid = q["redirect_to"]
            q = prod.get(pid)
        return bool(q) and q.get("estado") == "activo" and not q.get("candidate")

    dm_pre = [json.loads(l) for l in (ROOT / "data/catalog/doc_map.jsonl")
              .read_text("utf-8").splitlines() if l.strip()]
    huerfano_de: set[str] = set()
    for fila in dm_pre:
        ids_f = [e["id"] for e in fila.get("entries", []) if e["id"] in prod]
        if ids_f and not any(_consumible(i) for i in ids_f):
            huerfano_de.update(ids_f)

    redirects, colisiona = [], {}
    for nk, grupo in canon_activo.items():
        if len(grupo) < 2:
            continue
        sin_marca = [i for i in grupo if i.startswith("unresolved:")]
        con_marca = [i for i in grupo if not i.startswith("unresolved:")]
        if sin_marca and len(con_marca) == 1:
            destino_id = con_marca[0]
            for i in sin_marca:
                redirects.append({
                    "id": i, "redirect_to": destino_id,
                    "motivo": (f"DUPLICADO sin marca: mismo canónico que «{destino_id}». "
                               f"Redirigir alcanza su manual por `follow_redirect` SIN meter "
                               f"un término nuevo en el detector, y le pone marca")})
                colisiona[i] = "redirigido"
        elif len(con_marca) > 1 and any(_consumible(i) for i in con_marca):
            # Uno de los dos YA es consumible: el otro no puede promoverse, pero si
            # son la MISMA MARCA es una variante de grafía del mismo producto y
            # redirigir es mecánico (`notifier:id-3000` → `notifier:id3000`).
            vivo = next(i for i in con_marca if _consumible(i))
            for i in grupo:
                if i == vivo:
                    continue
                if i.split(":", 1)[0] == vivo.split(":", 1)[0]:
                    redirects.append({
                        "id": i, "redirect_to": vivo,
                        "motivo": (f"MISMA MARCA, grafía distinta del mismo canónico que «{vivo}», "
                                   f"que ya es consumible. Redirigir alcanza su manual sin añadir "
                                   f"término al detector; promoverlo rompería el validador")})
                    colisiona[i] = "redirigido"
                else:
                    colisiona[i] = (f"COLISIÓN con «{vivo}», que ya es consumible y es de OTRA "
                                    f"marca: no se puede promover ni redirigir sin decidir si son "
                                    f"el mismo producto — adjudicación de Alberto (R8).")
        else:
            # Colisión entre marcas con TODOS en cuarentena: el validador sólo
            # prohíbe DOS consumibles con el mismo canónico, así que promover
            # exactamente UNO es legal. Y cuál no es arbitrario: **el que tiene el
            # manual huérfano**. Si sólo un lado tiene documento perdido, ése es el
            # que hace falta; si los dos lo tienen, elegir sí es adjudicar (y el
            # arreglo bueno es fusionarlos, que desbloquea LOS DOS).
            con_huerfano = [i for i in grupo if i in huerfano_de]
            if len(con_huerfano) == 1:
                elegido = con_huerfano[0]
                for i in grupo:
                    if i != elegido:
                        colisiona[i] = (f"COLISIÓN de canónico con «{elegido}», que es el que tiene "
                                        f"el manual huérfano; sólo uno de los dos puede ser "
                                        f"consumible, así que este se queda en cuarentena.")
            else:
                for i in grupo:
                    colisiona[i] = (f"COLISIÓN DE CANÓNICO entre marcas ({', '.join(grupo)}) y LOS "
                                    f"DOS tienen manual huérfano: elegir uno deja el otro perdido. "
                                    f"El arreglo que desbloquea los dos es fusionarlos, y eso es "
                                    f"adjudicación de Alberto (R8).")

    alias_filas = [json.loads(l) for l in (ROOT / "data/catalog/aliases.jsonl")
                   .read_text("utf-8").splitlines() if l.strip()]
    alias_existentes = {norm_token(a["alias"]) for a in alias_filas}
    canon_existentes = {norm_token(q["canonical_model"]) for q in prod.values()}

    # GEMELO DETECTADO POR ALIAS. El mismo duplicado que arriba, pero escondido:
    # `notifier:notifier-inspire-e10` tiene por canónico «Notifier INSPIRE E10»,
    # que YA existe como ALIAS de `notifier:inspire-e10` — y ése ya es consumible.
    # Promover el primero rompe el validador («exact pisaría el alias»); redirigirlo
    # al que el alias señala alcanza su manual y deja de haber dos filas para un
    # mismo producto. Se exige que el destino sea consumible: redirigir a otro
    # candidate no desbloquea nada.
    destino_de_alias = {norm_token(a["alias"]): a["id"] for a in alias_filas
                        if not a.get("candidate")}
    for q in prod.values():
        if not (q.get("candidate") and q.get("estado") == "activo"):
            continue
        destino_id = destino_de_alias.get(norm_token(q["canonical_model"]))
        if (destino_id and destino_id != q["id"] and q["id"] not in colisiona
                and _consumible(destino_id)):
            redirects.append({
                "id": q["id"], "redirect_to": destino_id,
                "motivo": (f"DUPLICADO: su canónico «{q['canonical_model']}» ya es un ALIAS de "
                           f"«{destino_id}», que es consumible. Redirigir alcanza su manual y "
                           f"quita la fila repetida; promoverlo rompería el validador")})
            colisiona[q["id"]] = "redirigido"

    confirmar, docmap_altas, alias_altas, fuera = [], [], [], {}
    estrechan = [i for i, d in mejor.items() if d["veredicto"] == "DESBLOQUEA_PERO_ESTRECHA"]
    print(f"ids con veredicto: {len(mejor)}  ·  de ellos estrechan: {len(estrechan)}")

    # (B) para cada uno que estrecha, se MIDE aislado qué fuentes perdería
    perdidas_de: dict[str, list[str]] = {}
    if estrechan:
        print("midiendo, uno a uno y AISLADO, qué fuentes perdería cada uno…")
        antes_cache: dict[str, set[str]] = {}
        for i, pid in enumerate(estrechan, 1):
            q = mejor[pid]["canonico"]
            if q not in antes_cache:
                antes_cache[q] = _fuentes(CATALOG_DIR, q)
            d = _copia({pid})
            try:
                perdidas_de[pid] = sorted(antes_cache[q] - _fuentes(d, q))
            finally:
                shutil.rmtree(d, ignore_errors=True)
            if i % 5 == 0:
                print(f"  …{i}/{len(estrechan)}", flush=True)

    for pid, d in sorted(mejor.items()):
        v = d["veredicto"]
        it = cita_de.get(pid, {})
        cita = (it.get("cita") or "").replace("\n", " ")[:150]
        if pid in HEREDADAS:
            fuera[pid] = f"HEREDADO de la ronda 1: {HEREDADAS[pid]}"
            continue
        if d["canonico"] in PALABRAS:
            fuera[pid] = (f"PALABRA, no nombre: «{d['canonico']}» aparece con frontera de palabra "
                          f"en {PALABRAS[d['canonico']]} documentos del corpus — se reparte por "
                          f"todo él porque es una palabra inglesa. Meterlo en el detector "
                          f"secuestraría consultas de cualquier producto.")
            continue
        if colisiona.get(pid) == "redirigido":
            fuera[pid] = ("DUPLICADO de un producto con marca: entra como `products_redirect`, "
                          "no como promoción — alcanza su manual sin tocar el detector.")
            continue
        if pid in colisiona:
            fuera[pid] = colisiona[pid]
            continue
        if v == "NI_DETECTA":
            fuera[pid] = ("NO DETECTABLE: el token no tiene letras (o lleva paréntesis) y el "
                          "detector los excluye a propósito — promover es inerte.")
            continue
        base = {"id": pid, "canonical_model": d["canonico"],
                "provenance_add": (f"s334b huérfano-desbloqueado ({v}). Cita en su propio "
                                   f"doc: «{cita}»" if cita else
                                   f"s334b huérfano-desbloqueado ({v}); sin cita literal en su "
                                   f"propio documento (la extracción no conservó el nombre): la "
                                   f"evidencia es su fila de doc_map")}
        if v == "DESBLOQUEA_PERO_ESTRECHA":
            perd = perdidas_de.get(pid, [])
            recuperables = [(docid_de_sf[s], s) for s in perd if s in docid_de_sf]
            if len(recuperables) < len(perd):
                fuera[pid] = (f"ESTRECHA y no todas sus pérdidas son recuperables por doc_map "
                              f"({len(recuperables)}/{len(perd)}): sin eso el saldo es negativo.")
                continue
            base["provenance_add"] += (f" | ESTRECHABA: se le añaden al doc_map, como "
                                       f"`secondary`, las {len(perd)} fuentes que perdería")
            for did, sf in recuperables:
                docmap_altas.append({
                    "document_id": did, "source_file": sf,
                    "entries": [{"id": pid, "role": "secondary", "scope": "doc",
                                 "provenance": ("s334b: fuente que la promoción de este producto "
                                                "perdería (paraguas dropeado bajo `replace`); se "
                                                "re-ata como secondary — el manual lo menciona y "
                                                "sirve como fuente, sin reclamarlo")}]})
        elif v == "DETECTA_SIN_FUENTE":
            marca = MARCA.get(pid.split(":", 1)[0])
            tok = d["canonico"]
            if not marca or not any(c.isdigit() for c in tok):
                fuera[pid] = ("HOMÓNIMO/GEMELO abierto y su token no admite alias de marca "
                              "detectable (el detector sólo acepta alias `nombre-largo` CON "
                              "dígito, `catalog_resolver._add`) — adjudicación de Alberto.")
                continue
            base["provenance_add"] += (f" | HOMÓNIMO abierto: el token desnudo sigue fallando "
                                       f"abierto a propósito (es ambiguo, R8); se alcanza por el "
                                       f"alias «{marca} {tok}»")
            nk_alias = norm_token(f"{marca} {tok}")
            if nk_alias in alias_existentes or nk_alias in canon_existentes:
                fuera[pid] = ("HOMÓNIMO abierto y el alias de marca que lo alcanzaría YA existe "
                              "como alias o como canónico de otro producto — el validador lo "
                              "rechaza (`exact` pisaría el alias).")
                continue
            alias_existentes.add(nk_alias)
            alias_altas.append({
                "alias": f"{marca} {tok}", "id": pid, "tipo": "nombre-largo",
                "added_by": "s334b",
                "provenance": ("s334b: alias cualificado por marca. El token desnudo es un "
                               "homónimo abierto entre dos marcas y DEBE seguir fallando abierto "
                               "hasta que Alberto adjudique el rebrand; esto no lo toca, sólo "
                               "da una vía inequívoca al manual")})
        confirmar.append(base)

    # Un redirect a un producto que SIGUE en cuarentena no desbloquea nada: el
    # `follow_redirect` llega a una fila `candidate` y `_consumable` dice que no.
    # Se promueve también el destino. Su canónico es el MISMO que el del origen
    # —por eso colisionaban—, así que la evidencia G4 del origen vale igual para
    # él: el término que entra en el detector es exactamente el mismo.
    ya = {c["id"] for c in confirmar}
    for rd in redirects:
        destino_id = rd["redirect_to"]
        if destino_id in ya or _consumible(destino_id):
            continue
        confirmar.append({
            "id": destino_id,
            "canonical_model": prod[destino_id]["canonical_model"],
            "provenance_add": (f"s334b: promovido como DESTINO del redirect de «{rd['id']}» — un "
                               f"redirect a una fila en cuarentena no desbloquea nada. Mismo "
                               f"canónico que el origen, así que el término del detector es el "
                               f"mismo que ya verificó la sonda G4")})
        ya.add(destino_id)

    plan = {
        "que_es": ("s334b — segundo asalto a los manuales huérfanos, con la definición de "
                   "huérfano CORREGIDA (sigue redirects, como el resolver) y sin los descartes "
                   "por prior del primero. Tres mecanismos: promover · promover+doc_map (para "
                   "los que estrecharían) · promover+alias de marca (para los homónimos)."),
        "pedido": "Alberto, 21-ago: «deberías atacarlo hasta que queden 10 como máximo».",
        "products_altas": [], "products_confirmar": confirmar, "products_retirar": [],
        "products_redirect": redirects, "aliases_altas": alias_altas, "aliases_quitar": [],
        "umbrellas_altas": [], "doc_map_altas": docmap_altas, "doc_map_modificaciones": [],
        "retags_db": [], "no_aplicar": [], "gaps": [],
        "perdidas_de_fuente_adjudicadas": [],
        "fuera_con_motivo": fuera,
    }
    destino.write_text(json.dumps(plan, ensure_ascii=False, indent=1), "utf-8")
    print(f"\n  products_confirmar ... {len(confirmar)}")
    print(f"  products_redirect .... {len(redirects)}")
    print(f"  doc_map_altas ........ {len(docmap_altas)}")
    print(f"  aliases_altas ........ {len(alias_altas)}")
    print(f"  fuera con motivo ..... {len(fuera)}")
    print(f"\n→ {destino}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
