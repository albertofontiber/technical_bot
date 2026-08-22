# s336 · Lote de clasificación del catálogo (Notifier) — v2 VINCULANTE (post-ronda, 21-ago-2026)

> Sustituye a la v1. Ronda ts=2026-08-21T18:51:18: **Sol 5 (2 críticos) + Fable 5 = 10/10
> con sustancia, 0 FP** — adjudicación completa en §5. **DECLARACIÓN de integridad**: el
> emparejamiento formal de esa ronda se ROMPIÓ por mis dos commits de higiene mid-ronda
> (el gate pinna `repo_head`+`repo_view_sha256`; la regla «cero git en ronda» protegía
> exactamente esto — lección registrada). La review de Fable quedó guardada sin emparejar
> (`evals/adversarial_reviews/2026-08-21T18-53-47_claude-fable-5_*.md`); su sustancia se
> adjudica aquí y **esta v2 va a una ronda emparejada LIMPIA como ronda de registro**
> antes del build.

## 0 · Objetivo y MÉTRICA (cifras reconciliadas — Fable-1/2/3)

- Fila real `a9ba756a` (15:53Z): «3 clasificados / 448 ciegos» = el JOIN de la VISTA
  pre-#332 (451 propios − 3). **La población de este lote se define por ESE join** (el
  que paga el efecto): `_productos_marca(cat, "notifier")` HOY = **505 propios · 3
  clasificados · 502 sin clasificar · 484 con docs en doc_map (270 con 1 doc) · 18 sin
  docs**. La vista incluye miembros `vendido_bajo` de otros namespaces (firelite 14,
  systemsensor 12, spectrex 10, …): clasificarlos paga la vista Notifier Y la suya; las
  tranches posteriores DEDUPLICAN por id (cada id se clasifica una vez).
- Los `unresolved:*` (45) están FUERA de esta diana (no aparecen en la vista Notifier);
  pertenecen al backlog global y quedan excluidos de TODAS las tranches hasta que
  Alberto resuelva su namespace.
- **La barra heredada del método es 29/29 = 100%** (gate FINAL congelado en
  `evals/s322_76_packet_adjudicacion_v1.md`, tras la repesca v3); el «19/19» de la v1
  era el gate INTERMEDIO estampado en provenance de filas — G1 aplicado: cifra
  re-anclada al recibo canónico.

**Gates pre-registrados de ESTE lote:**
1. **Método**: precisión de la alta-confianza vs mini-GT nueva (30, congelada con SHA
   antes de la pasada) **≥95%**, n≥10 — y las citas de TODO lo escrito verificadas a
   **TEXTO COMPLETO** contra su doc atribuido (no prefijo; ver §1.4).
2. **Efecto (G6)**: replay de `a9ba756a` sirve listado gobernado con **≥15 centrales**
   Notifier; before/after de clasificados/ciegos estampado.
3. **Utilidad honesta (Sol-4)**: si lo ESCRITO (alta verificada) queda **<60% de la
   diana-con-docs (484)**, el veredicto del lote es **PARCIAL** (declarado así en recibo,
   DEC y digest — jamás «PASS» con el catálogo mayormente ciego) y el residuo va a
   packet §1 con su distribución de confianzas.
4. **No-regresión**: 168+3 filas clasificadas existentes byte-idénticas; inventario
   sin-filtro byte-igual; suite + MT.

## 1 · El método: la versión CERRADA de s322b, entera (Sol-2/3 + Fable-4)

No la primera pasada — el protocolo completo que cerró Detnov+Kidde al 100%:

1. **Censo diana** desde el JOIN real de la vista (no namespace), con docs por doc_map.
2. **Pasada fable-5** (prompt/esquema/degradación de `s322_76_poblacion.py`): muestra
   real de SUS docs, veredicto con cita VERBATIM por campo, cita-en-muestra o degrada.
   Smoke de 10 PRIMERO (coste real estampado) → pasada completa (~484 llamadas).
3. **REPESCA dirigida heredada** (TECH_DEBT s322b: la ventana inicial perdió 22/22 que
   la repesca v3 a TABLAS DE MODELOS recuperó): los media/baja por «muestra sin sección
   de enumeración» pasan por la repesca (ventana dirigida a R9: «Descripción general» /
   tabla de modelos / ordering information) ANTES de caer al packet. Su coste entra en
   el presupuesto (§3).
4. **Verificación FULL-TEXT pre-escritura (Sol-2, crítico)**: TODA cita almacenada se
   verifica ENTERA (no `[:50]`) contra el TEXTO COMPLETO de su doc atribuido — espejo de
   `s322_76_verifica_citas_v1.py` (el que cazó 1 invención en s322b). Sin full-text
   verificada NO se escribe: degrada a packet. Derivadas (no-verbatim) se declaran como
   en s322b, jamás se cuelan como verbatim.
5. **#76b — gatillo DURO cumplido ANTES de poblar (Sol-1, crítico)**: Notifier es
   multi-mercado (clase AFP1010: 2 lazos ES / 4 US). Forma BP de TECH_DEBT #76b:
   (a) la entrada de atributo gana marcador **`alcance`** adjudicable (mercado/idioma
   del doc, derivado del doc atribuido y declarado como derivación);
   (b) el gate de población **FLAGEA divergencia de max entre docs → packet de
   adjudicación, jamás write-fusión** (el writer se niega a escribir lazos/zonas
   divergentes sin adjudicación);
   (c) el display del inventario **distingue** capacidad ampliable (base→max de un
   mismo alcance, se sirve «hasta max») de divergencia de alcance (se sirve POR
   FUENTE, nunca el max fusionado). (c) toca `telegram_bot._casa` — cambio de conducta
   SERVIDA solo para entradas con `alcance` divergente (hoy 0 filas ⇒ byte-idéntico
   hasta que el lote escriba la primera); test dirigido con la clase AFP1010.
   TECH_DEBT #76b se marca CERRADO por este lote si (a)-(c) pasan sus tests.
6. **Escritura ATÓMICA (Sol-5)**: `write_jsonl` escribe el fichero VIVO y valida
   después — el writer del lote construye el products.jsonl candidato en TEMPORAL,
   `validate()` sobre la copia, **backup timestamped del vivo, swap atómico
   (`os.replace`) y rollback verificado** (test: validación que falla ⇒ el vivo queda
   byte-idéntico). Solo alta+cita-full-text; provenance «s336 método s322b …» por fila.
7. **GT**: 30 productos de la diana, estratos por nº de docs (objetivo) y por familia
   APARENTE **declarada como proxy de muestreo, no como estrato verificado** (Fable-5;
   el nombre engaña por principio rector — la etiqueta GT se decide leyendo docs, jamás
   por el nombre). Etiquetado a mano ANTES de la pasada; límites `duda` fuera del gate.
8. **Enum CERRADO** sin cambios; fuera-de-enum → packet con propuesta de valor
   (¿EVAC/audio en Notifier?) — ampliar el enum es adjudicación de Alberto.

## 2 · Alternativas y descartes (sin cambios de la v1)

Nombre/patrón sin docs (viola principio rector + R19) · web del fabricante como fuente
masiva (R18 es validación puntual) · tacada única de 1.019 (gate por marca detecta
deriva de estilo documental) · LLM en el turno (dato estático, coste por consulta).

## 3 · Coste y presupuesto (Fable-3/4 reconciliado)

~484 llamadas de pasada + repesca dirigida (s322b: dimensión ~10-20% de la diana) +
smoke 10. Estimación ~$12-25 y ~1,5-2 h; el smoke calibra ANTES de comprometer y el
recibo estampa el coste real. Población exacta del censo la fija B1 desde el join real.

## 4 · Colas declaradas (mismo protocolo, cada una con su GT y su gate)

Vistas de marca restantes tras dedupe por id (morley, systemsensor, xtralis, kidde,
securiton, kac, …) + los 18 sin-docs de esta vista (packet «sin evidencia») + los 45
`unresolved:*` (esperan adjudicación de namespace).

## 5 · Adjudicación de la ronda ts=2026-08-21T18:51:18 (10/10, 0 FP)

| # | hallazgo | adjudicación |
|---|---|---|
| Sol-1 crít | #76b es gatillo DURO omitido; el consumidor sirve max fusionado | §1.5 (a)(b)(c) — el lote lo CIERRA |
| Sol-2 crít | verificación de cita = prefijo 50 chars; ya dejó pasar una invención | §1.4 full-text pre-escritura obligatoria |
| Sol-3 med | «mismo método» era la versión PRE-repesca | §1.3 repesca dirigida heredada + presupuesto |
| Sol-4 med | gates permitían éxito vacío | §0.3 veredicto PARCIAL declarado bajo 60% |
| Sol-5 med | «validate/backup/swap» no existe en write_jsonl | §1.6 writer atómico con rollback verificado |
| Fable-1 med | «19/19» ≠ recibo congelado (29/29) | §0 barra re-anclada (G1) |
| Fable-2 med | 448 (vista) vs 480 (namespace) sin reconciliar | §0 población = JOIN real; ambos números declarados (G3) |
| Fable-3 med | aritmética unresolved/478 no cierra | §0 unresolved FUERA de la diana; censo por vista |
| Fable-4 men | s322-76 no fue pasada única (2 repescas + rescate) | §1.3 + §3 protocolo y coste heredados |
| Fable-5 men | estratos GT por «familia aparente» = proxy no declarado | §1.7 proxy declarado; etiqueta solo leyendo docs |

## 6 · Build (B1-B7, tras la ronda limpia sobre ESTA v2)

B1 censo diana por el join real + freeze · B2 mini-GT 30 (a mano, antes de la pasada,
SHA) · B3 esquema `alcance` + gate de divergencia + display por-fuente + writer atómico
(con sus tests, incluido rollback y AFP1010 dirigido) · B4 smoke 10 → pasada → repesca →
full-text → gate ≥95% · B5 escritura atómica + efecto before/after (≥15 centrales) +
veredicto PASS/PARCIAL honesto + suite/MT · B6 packet §1 + recibos + DEC + digest/PLAN/
HISTORY (TECH_DEBT #76b cerrado si procede) · B7 PR + mergeabilidad verificada.
