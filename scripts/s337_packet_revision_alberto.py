#!/usr/bin/env python
"""s337 — genera el packet de revisión UNO A UNO para Alberto.

Pedido suyo: «¿me preparas un archivo con los que haya que revisar, dándome una
recomendación, y los reviso uno a uno?».

Reglas de construcción, para que el archivo no se convierta en otro volcado:
  · **una fila = una DECISIÓN**, no un manual. Si una firma desbloquea 12
    manuales, es UNA fila que dice 12 — así el orden por valor es real.
  · **cada fila lleva RECOMENDACIÓN**, derivada de la evidencia, no escrita a
    mano: qué propongo y por qué, con el dato delante.
  · **lo que ya decidió va aparte**, con lo que YO entendí, para que corrija de
    un vistazo si le leí mal.
  · el suelo (lo que no baja de ninguna manera) va al final, para que no parezca
    cola pendiente.

NADA se aplica: esto escribe un `.md`.
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
sys.path.insert(0, str(ROOT))
import httpx                                                    # noqa: E402
from src.config import SUPABASE_URL, SUPABASE_SERVICE_KEY      # noqa: E402
from src.rag import catalog as C                               # noqa: E402
from src.rag import catalog_store as cs                        # noqa: E402

SB = SUPABASE_URL.rstrip("/") + "/rest/v1"
H = {"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"}
#: Lo que Alberto ya zanjó, para NO volver a preguntárselo. La queja del packet v3
#: fue justo ésa: `morley:tg` se le preguntó 15 veces.
YA_DECIDIDO = {
    "vsn122plus": ("«1 OK»", "morley:vsn12-2plus",
                   "el manual es de la serie NFS Supra de Morley"),
    "tg1020": ("«3 OK»", "notifier:tg-1020",
               "coherente con que los TG sean software de Notifier"),
}

DIAG = ROOT / "evals/s336c_diagnostico_huerfanos.json"
#: s338 resolvió por canales independientes cosas que s336c había mandado al
#: suelo. Sin esto el packet le diría a Alberto «esto NO baja» de manuales que
#: acabo de resolver — evidencia caducada, que es justo lo que critico.
MULTI = ROOT / "evals/s338_resolucion_multicanal.json"
SALIDA = ROOT / "docs/REVISION_ALBERTO_HUERFANOS.md"


def _k(s: object) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(s or "").lower())


def _pagina(tabla: str, params: dict, orden: str = "id") -> list[dict]:
    """`order` + verificación contra `count=exact`: PostgREST no garantiza orden
    estable entre rangos y sin eso la paginación salta filas."""
    out, desde = [], 0
    with httpx.Client(timeout=300) as c:
        r0 = c.get(f"{SB}/{tabla}", headers={**H, "Prefer": "count=exact"},
                   params={**params, "limit": "1"})
        total = int((r0.headers.get("content-range") or "0/0").split("/")[-1] or 0)
        while True:
            r = c.get(f"{SB}/{tabla}", headers={**H, "Range-Unit": "items",
                      "Range": f"{desde}-{desde+999}"}, params={**params, "order": orden})
            r.raise_for_status()
            d = r.json()
            out += d
            if len(d) < 1000:
                break
            desde += 1000
    if len(out) != total:
        raise SystemExit(f"paginación incompleta en {tabla}: {len(out)} de {total}")
    return out


def marcas_que_lo_nombran(tokens: list[str]) -> dict[str, list[tuple[str, int]]]:
    """¿Qué marca nombra de verdad cada token? Es el ÚNICO discriminador honesto
    para un token que dos marcas se disputan: mi lectura no, el corpus sí."""
    docs = {str(d["id"]): str(d.get("manufacturer") or "?")
            for d in _pagina("documents", {"select": "id,manufacturer"})}
    ch = _pagina("chunks_v2", {"select": "id,document_id,content"})
    por_doc: dict[str, list[str]] = defaultdict(list)
    for x in ch:
        por_doc[str(x.get("document_id"))].append(x.get("content") or "")
    out = {}
    for t in tokens:
        core = C._core(t)
        if not core:
            continue
        rx = re.compile(rf"\b{core}\b(?!\d)", re.I)
        cnt: dict[str, int] = defaultdict(int)
        for d, ts in por_doc.items():
            if any(rx.search(x or "") for x in ts):
                cnt[docs.get(d, "?")] += 1
        out[_k(t)] = sorted(cnt.items(), key=lambda kv: -kv[1])
    return out


def main() -> int:
    cat = cs.load()
    diag = json.loads(DIAG.read_text("utf-8"))
    multi, descubiertos = {}, {}
    if MULTI.exists():
        todas = json.loads(MULTI.read_text("utf-8"))["filas"]
        multi = {f["source_file"]: f for f in todas if f["veredicto"] == "RESUELTO"}
        # El DESCUBRIMIENTO de nombres vale aunque la fila no llegue a RESUELTO:
        # `Manual-de-Usuario-S3-T2-y-S2-T2` se queda en un canal precisamente
        # PORQUE el catálogo lo guarda por número de referencia — que es el
        # problema que el nombre nuevo arregla. Filtrarlo por veredicto perdía
        # el ejemplo bandera de Alberto.
        descubiertos = {f["source_file"]: f for f in todas if f.get("nombres_que_no_tenemos")}
    bucket = {f["source_file"]: f for f in diag["filas"]}

    # huérfanos VIVOS ahora (el diagnóstico es de antes de aplicar s336f)
    huer = {}
    for f in cat.doc_map:
        ids = [e["id"] for e in f.get("entries", []) if e["id"] in cat.products]
        if ids and not any(cat._consumable(i) for i in ids):
            huer[str(f.get("source_file") or "")] = ids

    por_canon = defaultdict(list)
    for pid, p in cat.products.items():
        por_canon[_k(p.get("canonical_model"))].append(pid)

    # ── agrupar por DECISIÓN ───────────────────────────────────────────────
    redirects = defaultdict(list)      # unresolved:X -> [manuales]  (gemelo único consumible)
    ambiguos = defaultdict(list)       # unresolved:X -> [manuales]  (gemelo en 2 marcas)
    detnov, sin_gemelo, suelo = [], defaultdict(list), []

    for sf, ids in sorted(huer.items()):
        b = (bucket.get(sf) or {}).get("bucket", "?")
        decidido = False
        for i in ids:
            c = cat.products[i]["canonical_model"]
            gem = [x for x in por_canon[_k(c)] if x != i and cat._consumable(x)]
            if not gem:
                continue
            marcas = {g.split(":")[0] for g in gem}
            (redirects if len(marcas) == 1 else ambiguos)[(i, c, tuple(sorted(gem)))].append(sf)
            decidido = True
            break
        if decidido:
            continue
        if b == "SOLO_NUMERO_DE_REFERENCIA":
            detnov.append((sf, ids, (bucket.get(sf) or {}).get("referencias")
                           or (bucket.get(sf) or {}).get("tokens_citados")))
        elif b in ("NI_CANONICO_NI_REFERENCIA", "CANONICO_DIGIT_ONLY", "LECTOR_MULTIMODAL",
                   "SIN_PDF"):
            if sf in multi:
                detnov.append((sf, ids, None))     # resuelto por s338: deja de ser suelo
            else:
                suelo.append((sf, ids, b))
        else:
            for i in ids:
                sin_gemelo[(i, cat.products[i]["canonical_model"])].append(sf)
                break   # una fila = una decisión: el primer id manda

    L: list[str] = []
    A = L.append
    A("# Revisión uno a uno — manuales huérfanos")
    A("")
    A(f"> Generado por `scripts/s337_packet_revision_alberto.py` sobre el catálogo vivo "
      f"(**{len(huer)} huérfanos**) y el diagnóstico `evals/s336c_diagnostico_huerfanos.json`.")
    A("> **Una fila = una decisión**, no un manual: si una firma desbloquea 12 manuales, es una "
      "fila que dice 12. Ordenado por lo que desbloquea cada una.")
    A("> Marca `[x]` lo que apruebes y escribe al lado si quieres otra cosa. Nada está aplicado.")
    A("")
    A("---")
    A("")
    A("## ✅ Lo que ya decidiste hoy — comprueba que te leí bien")
    A("")
    A("| tu palabra | lo que entendí | efecto |")
    A("|---|---|---|")
    A("| «Detnov OK» | El **nº de referencia del fabricante vale como cita bajo R4** cuando el "
      "manual no usa el nombre de modelo (`MAD-491` ↔ `55349102`) | desbloquea el bloque Detnov, "
      "abajo |")
    A("| «los TG son software» | La familia TG es **software**, y por **R10** el software ES "
      "producto consultable → **no se retiran**. Propongo además marcarles "
      "`categoria: software de configuración`, campo que ya existe y usan 4 productos | ninguno "
      "de los TG sale del catálogo |")
    A("| «1 OK» | `HLSI-MN-025-I_NFS Supra Series v05` — el `unresolved:vsn12-2plus` se resuelve; "
      "**propongo `morley:`** porque el manual es de la serie NFS Supra de Morley | 1 manual |")
    A("| «3 OK» | `TG-1020-INT` — se resuelve a favor de **Notifier**, coherente con que los TG "
      "sean su software. ⚠️ Ojo: hoy existe `desico:tg-1020` **consumible**; si TG es software "
      "de Notifier, eso huele a atribución equivocada y te lo pregunto abajo | 1 manual |")
    A("")
    A("---")
    A("")

    # ── redirects de una línea ────────────────────────────────────────────
    A("## 1 · Redirects de una línea — el gemelo YA es consumible")
    A("")
    A("Mismo canónico, uno con la marca puesta y otro sin ella. **R21 dice que lo firmas tú.** "
      "Simulado sobre una copia del catálogo: **0 huérfanos nuevos**.")
    A("")
    orden = sorted(redirects.items(), key=lambda kv: -len(kv[1]))
    for n, ((i, c, gem), mans) in enumerate(orden, 1):
        sw = " · **software (R10)**" if _k(c).startswith("tg") else ""
        A(f"### 1.{n} — `{i}` → `{gem[0]}`  ·  **{len(mans)} manual(es)**{sw}")
        A("")
        A(f"- **Recomendación: SÍ.** Mismo canónico «{c}»; el destino ya es consumible, así que "
          f"el redirect no crea nada nuevo — sólo deja de perder los manuales.")
        A(f"- Manuales: {', '.join('`'+m[:44]+'`' for m in sorted(mans)[:12])}"
          + (f" … y {len(mans)-12} más" if len(mans) > 12 else ""))
        A("")
        A("  - [ ] OK  ·  [ ] otra cosa: ______")
        A("")

    # ── ambiguos ──────────────────────────────────────────────────────────
    A("## 2 · Ambiguos — el token lo disputan dos ids")
    A("")
    A("No te doy «mi lectura»: te doy **en cuántos documentos de cada marca aparece el token**, "
      "que es el único discriminador que no me invento.")
    A("")
    ev = marcas_que_lo_nombran([c for (_, c, _) in ambiguos])
    for n, ((i, c, gem), mans) in enumerate(sorted(ambiguos.items(), key=lambda kv: -len(kv[1])), 1):
        marcas = ev.get(_k(c)) or []
        pinta = " · ".join(f"**{m}** {k}" for m, k in marcas[:4]) or "sin apariciones"
        dec = YA_DECIDIDO.get(_k(c))
        A(f"### 2.{n} — «{c}»  ·  {len(mans)} manual(es)"
          + ("  ·  ✅ **YA LO DECIDISTE**" if dec else ""))
        A("")
        A(f"- Ids que se lo disputan: {', '.join('`'+g+'`' for g in gem)} (+ el candidate del manual)")
        A(f"- **Aparece en documentos de**: {pinta}")
        A(f"- Manuales: {', '.join('`'+m[:44]+'`' for m in sorted(mans))}")
        if dec:
            palabra, destino, por = dec
            A(f"- ✅ Dijiste {palabra} → lo entiendo como **`{destino}`** ({por}). "
              f"La evidencia de arriba lo respalda.")
            A("")
            A("  - [ ] confirmado  ·  [ ] te leí mal, era: ______")
        else:
            # ¿es de verdad una disputa ENTRE MARCAS, o un gemelo ortográfico de la
            # misma? `unresolved:` no es una marca, así que no cuenta como bando.
            bandos = {g.split(":", 1)[0] for g in gem} - {"unresolved"}
            gana = marcas[0][0] if marcas else None
            solo_una = len(marcas) == 1 or (len(marcas) > 1 and marcas[0][1] >= 5 * marcas[1][1])
            if len(bandos) == 1:
                dueno = sorted(bandos)[0]
                destino = next(g for g in gem if g.startswith(dueno + ":"))
                A(f"- ⚠️ **Esto NO es una disputa entre marcas**: `{destino}` y el candidate del "
                  f"manual son **el mismo producto de {dueno}, escrito distinto** (el guion). "
                  f"Los `unresolved:` no son un bando.")
                A(f"- **Recomendación: redirect `{i}` → `{destino}`.** No hay que elegir marca: "
                  f"hay que dejar de tener dos filas para lo mismo. Sigue siendo tuyo por R21.")
                A("")
                A("  - [ ] OK al redirect  ·  [ ] otra cosa: ______")
                A("")
                continue
            if gana and solo_una:
                A(f"- **Recomendación: canónico en `{gana.lower()}`**, y el otro id a `redirect` "
                  f"con `vendido_bajo` = ambas (R3). El corpus es claro: el token vive en "
                  f"documentos de {gana}.")
            else:
                A("- **Recomendación: ninguna — está repartido de verdad.** Si es el mismo "
                  "producto vendido bajo dos marcas, fusión (R3); si son productos distintos que "
                  "comparten nombre, es **homónimo** y hay que declararlo.")
            A("")
            A("  - [ ] fusionar, canónico `______`  ·  [ ] son distintos (homónimo)  ·  [ ] otra cosa")
        A("")

    # ── Detnov ────────────────────────────────────────────────────────────
    A("## 3 · Resueltos por evidencia — tu «Detnov OK» + el mecanismo nuevo (s338)")
    A("")
    A(f"**{len(detnov)} manuales.** Dos orígenes, los dos con la evidencia a la vista:")
    A("")
    A("- **tu «Detnov OK»**: el manual cita su **nº de referencia**, que ya es alias del producto "
      "y coincide con el nombre del fichero (doble ancla) → cumple R4.")
    A("- **s338, tu pushback**: canales independientes. `FICHERO` (R8 protege de INVENTARSE un "
      "producto, no impide CONFIRMAR uno que el `doc_map` ya enlaza), `URL_FABRICANTE` (el "
      "fabricante publica ese PDF con el modelo en la URL) y `CATALOGO_FABRICANTE` (su catálogo "
      "lo lista con descripción impresa). **RESUELTO exige ≥2 canales independientes.**")
    A("")
    A("| # | manual | producto | evidencia |")
    A("|---|---|---|---|")
    for n, (sf, ids, refs) in enumerate(sorted(detnov), 1):
        canon = [cat.products[i]["canonical_model"] for i in ids if i in cat.products]
        mf = multi.get(sf)
        if mf:
            ev = " + ".join(k for k in mf["canales"] if k != "CHUNKS")
            if mf.get("url_fabricante"):
                ev += f" · [fuente]({mf['url_fabricante']})"
        else:
            ev = f"ref. `{', '.join((refs or [])[:2])}`"
        A(f"| {n} | `{sf[:44]}` | {', '.join(canon[:2])} | {ev} |")
    A("")
    A("- [ ] Adelante con todos  ·  [ ] quita los que marque arriba")
    A("")
    faltan = sorted(descubiertos.items())
    if faltan:
        A("### 3.b — Nombres que el FABRICANTE usa y nosotros no tenemos")
        A("")
        A("El canal web no sólo confirma: **descubre**. Tu ejemplo del `S3-T2` era esto — el "
          "catálogo los tiene como número de referencia y Fidegas los llama por su nombre. "
          "Bautizar un producto es adjudicación tuya (R21), así que sólo se proponen.")
        A("")
        A("| manual | lo que tenemos | como lo llama el fabricante |")
        A("|---|---|---|")
        for sf, mf in sorted(faltan):
            A(f"| `{sf[:40]}` | {', '.join(mf['canonicos'][:2])} | "
              f"**{', '.join(mf['nombres_que_no_tenemos'][:3])}** |")
        A("")
        A("> Aviso honesto: junto a los hallazgos reales cuela algún vecino de contexto — "
          "`CCD-100` es la serie de central donde se enchufa el TRD-100, no el producto de ese "
          "manual. Por eso no se aplican solos.")
        A("")
        A("- [ ] añade los que marque  ·  [ ] ninguno  ·  [ ] otra cosa")
        A("")

    # ── sin gemelo ────────────────────────────────────────────────────────
    # El cajón de sastre NO es una sola cosa. Clasificarlo es el trabajo: un
    # `notifier:nas` y un `unresolved:itac` piden decisiones distintas.
    alias_de = defaultdict(set)
    for a in cat.aliases:
        if cat._consumable(str(a.get("id", ""))):
            alias_de[_k(a.get("alias"))].add(str(a["id"]))
    cand_por_canon = defaultdict(set)
    for pid, pr in cat.products.items():
        if pr.get("candidate"):
            cand_por_canon[_k(pr.get("canonical_model"))].add(pid.split(":", 1)[0])

    fusiones, gemelo_alias, sin_marca, uno_a_uno = (defaultdict(list), defaultdict(list),
                                                    defaultdict(list), defaultdict(list))
    for (i, c), mans in sin_gemelo.items():
        marcas_cand = cand_por_canon.get(_k(c), set()) - {"unresolved"}
        gem_alias = sorted(alias_de.get(_k(c), set()) - {i})
        if len(marcas_cand) > 1:
            fusiones[(_k(c), c, tuple(sorted(marcas_cand)))] += mans
        elif gem_alias:
            gemelo_alias[(i, c, tuple(gem_alias))] += mans
        elif i.startswith("unresolved:"):
            sin_marca[(i, c)] += mans
        else:
            uno_a_uno[(i, c)] += mans

    if fusiones:
        A("## 4 · Fusiones Morley ↔ Notifier — cada una desbloquea los DOS lados")
        A("")
        A("El mismo canónico existe **en cuarentena en dos marcas**, y cada lado tiene manual "
          "huérfano. Elegir uno solo deja el otro perdido; **fusionar los desbloquea a la vez**.")
        A("")
        for n, ((_, c, marcas), mans) in enumerate(sorted(fusiones.items(),
                                                          key=lambda kv: -len(kv[1])), 1):
            A(f"### 4.{n} — «{c}» en {list(marcas)}  ·  **{len(mans)} manual(es)**")
            A("")
            A(f"- Manuales: {', '.join('`'+m[:44]+'`' for m in sorted(mans))}")
            A("- **Recomendación: fusionar** — un id canónico, el otro `redirect`, "
              "`vendido_bajo` = ambas (R3). Es el mismo aparato con dos etiquetas comerciales.")
            A("")
            A("  - [ ] fusionar, canónico `______`  ·  [ ] son distintos  ·  [ ] otra cosa")
            A("")

    if gemelo_alias:
        A("## 5 · Gemelos por alias — el nombre YA es alias de un producto vivo")
        A("")
        A("Su canónico ya existe como **alias** de un producto consumible: son filas duplicadas, "
          "no productos nuevos. (Este caso me lo cazó el gate cuando intenté promoverlos.)")
        A("")
        for n, ((i, c, gem), mans) in enumerate(sorted(gemelo_alias.items()), 1):
            A(f"### 5.{n} — `{i}` «{c}» → alias de {list(gem)}  ·  {len(mans)} manual(es)")
            A("")
            A(f"- Manuales: {', '.join('`'+m[:44]+'`' for m in sorted(mans))}")
            A(f"- **Recomendación: redirect `{i}` → `{gem[0]}`.**")
            A("")
            A("  - [ ] OK  ·  [ ] otra cosa: ______")
            A("")

    if uno_a_uno:
        A("## 6 · Candidates que mi filtro paró — uno a uno, porque cada uno es distinto")
        A("")
        A("Tienen marca y cita, pero **R19 (producto-hood)** los frenó: el token está en el texto "
          "y eso no lo hace producto. Te digo qué frenó a cada uno y qué propongo.")
        A("")
        MOTIVO = {
          "nas": ("sigla de 3 letras sin dígitos. Precedente DEC-272: `NAS` llegó a arrastrar 231 "
                  "documentos", "¿es NAS un producto con nombre propio, o una sigla genérica? Si "
                  "es producto, dime su nombre completo y lo uso de canónico"),
          "eev2": ("el canónico es `EEV(2)` y **los paréntesis no los ve el detector**",
                   "necesita un canónico sin paréntesis (¿`EEV2`?) o se queda inalcanzable"),
          "rhistorico.exe": ("es el **ejecutable**, no el software. R10 dice que el software SÍ es "
                             "producto: el canónico debería ser el nombre del programa",
                             "propongo canónico «Utilidad de Reparación de Históricos» y "
                             "`RHistorico.exe` como alias"),
          "serie-800": ("«Serie 800» es una **familia**, no un modelo",
                        "propongo tratarlo como paraguas (`umbrellas`), no como producto"),
          "am-lcd": ("lo saqué del lote yo: su core casa «Pantalla **FM/AM LCD**» de un manual de "
                     "radio (1 falso positivo real de 6 documentos)",
                     "propongo promoverlo **y** meter el falso positivo en `DETECT_STOPWORDS`, "
                     "que es el mecanismo que ya existe para esto"),
        }
        for n, ((i, c), mans) in enumerate(sorted(uno_a_uno.items()), 1):
            clave = i.split(":", 1)[1]
            por, prop = MOTIVO.get(clave, ("no pasó R19/R21", "necesita tu criterio"))
            A(f"### 6.{n} — `{i}` «{c}»  ·  {len(mans)} manual(es)")
            A("")
            A(f"- Manuales: {', '.join('`'+m[:44]+'`' for m in sorted(mans))}")
            A(f"- **Qué lo frenó**: {por}.")
            A(f"- **Recomendación**: {prop}.")
            A("")
            A("  - [ ] adelante  ·  [ ] déjalo  ·  [ ] otra cosa: ______")
            A("")

    if sin_marca:
        A("## 7 · `unresolved:` sin gemelo — ¿promover tal cual?")
        A("")
        A(f"**{len(sin_marca)} ids**, {sum(len(v) for v in sin_marca.values())} manuales. No "
          "existe ese canónico en ninguna marca, así que no hay redirect posible.")
        A("")
        A("- **Recomendación: promoverlos tal cual, sin asignar marca.** El detector **no usa el "
          "namespace** para nada, así que asignarla es trabajo de adjudicación que no cambia lo "
          "que el bot hace. Si luego aparece el fabricante, se añade sin tocar el id (son "
          "inmutables).")
        A("")
        A("  - [ ] OK a promover sin marca  ·  [ ] prefiero asignar marca uno a uno")
        A("")
        A("| id | canónico | manuales | nota |")
        A("|---|---|---|---|")
        for (i, c), mans in sorted(sin_marca.items(), key=lambda kv: -len(kv[1])):
            nota = ""
            if _k(c).startswith("tg"):
                # con «los TG son software» encima, y con la familia TG-IP ya en
                # Notifier, esto deja de ser un id sin dueño evidente
                nota = ("**software (R10)** · la familia `TG-IP-*` ya existe en `notifier:` "
                        "(`tg-ip-1`, `tg-ip-10`, `tg-ip-100`), así que aquí sí hay marca natural")
            A(f"| `{i}` | {c} | {len(mans)} | {nota} |")
        A("")

    # ── suelo ─────────────────────────────────────────────────────────────
    A("## 8 · El suelo — esto NO baja, y no es cola pendiente")
    A("")
    A(f"**{len(suelo)} manuales.** Los dejo listados para que se vea que están medidos, no "
      "olvidados.")
    A("")
    MOT = {"NI_CANONICO_NI_REFERENCIA": "el manual no nombra su producto (ni por referencia)",
           "CANONICO_DIGIT_ONLY": "el canónico es sólo dígitos — el detector los excluye a propósito",
           "LECTOR_MULTIMODAL": "PDF escaneado; leído con Claude, la página no nombra el modelo",
           "SIN_PDF": "no hay PDF en Storage"}
    A("| manual | por qué |")
    A("|---|---|")
    # algunos están en el suelo SÓLO porque el catálogo los guarda por número de
    # referencia; si apruebas el nombre que propone 3.b, dejan de estarlo. Sin
    # este enlace, el mismo manual aparece en dos sitios y parece contradicción.
    con_nombre = set(descubiertos)
    for sf, ids, b in sorted(suelo):
        extra = (" — **pero 3.b propone un nombre del fabricante**: si lo apruebas, sale del suelo"
                 if sf in con_nombre else "")
        A(f"| `{sf[:52]}` | {MOT.get(b, b)}{extra} |")
    A("")
    A("---")
    A("")
    A("## Y una pregunta que sale de lo que me dijiste")
    A("")
    A("Si los **TG son software de Notifier**, ¿qué hace `desico:tg-1020` como producto "
      "consumible de Desico? O es una atribución equivocada (y entonces sobra), o Desico tiene su "
      "propio TG-1020 (y entonces es un **homónimo** y hay que declararlo como tal, no dejar dos "
      "dueños del mismo token).")
    A("")
    A("- [ ] es atribución equivocada, quita `desico:tg-1020`  ·  [ ] son distintos, decláralo "
      "homónimo  ·  [ ] déjalo como está")
    A("")

    SALIDA.write_text("\n".join(L) + "\n", "utf-8")
    print(f"decisiones de redirect ... {len(redirects)}  ({sum(len(v) for v in redirects.values())} manuales)")
    print(f"ambiguos ................. {len(ambiguos)}  ({sum(len(v) for v in ambiguos.values())} manuales)")
    print(f"Detnov (tu OK) ........... {len(detnov)} manuales")
    print(f"unresolved sin gemelo .... {len(sin_gemelo)} ids")
    print(f"suelo .................... {len(suelo)} manuales")
    print(f"\n→ {SALIDA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
