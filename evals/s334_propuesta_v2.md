# s334 · Fuzzy acotado + R8 — v2 VINCULANTE (post-dúo, 21-ago-2026)

> Sustituye a la v1. Ronda emparejada ts=2026-08-21T13:41:30: **Sol 5 + Fable 5, 10/10 con
> sustancia, 0 FP** (adjudicación en §6). Fable: «núcleo sólido y bien anclado en incidentes
> reales; NO ship-ready tal cual» — las tres condiciones quedan cerradas aquí.

## 1 · Reframing honesto del fuzzy (Sol-1 CRÍTICO + Fable-3)

**El fuzzy es una APUESTA ANTICIPATORIA, no un rescate medido**: todas las corrupciones
observadas hoy están ya tabuladas (BQide/KIDE/ITIDE/death-knob) o a distancia >1 con fila
aviso (ID) — mi propio fix inmediato (#331) consumió la evidencia viva. La autoridad del
desbloqueo es **el GO explícito de Alberto** con su argumento de escala (usuarios nuevos ⇒
typos nuevos; cada uno = una conversación mala ANTES de que exista su fila), no una
distinción metodológica contra DEC-233 — que fue un mandato de disciplina («solo lo
observado»), no un experimento con métrica (Fable-3, verificado: 1 solo hit de «fuzzy» en
DECISIONS y es de s29). Consecuencias operativas:
- GA1-fuzzy se mide con **typos sintéticos NO tabulados** (p.ej. «morlei»→Morley,
  «kiddi»→Kidde) — y la verificación post-flip usa un typo no tabulado.
- El solape de capas queda DECLARADO y pre-registrado (Fable-2): con `ASR_AVISOS=on` la
  TABLA gana antes de la rama de corrección (orden: tabla > plantilla > fuzzy+clasificador);
  GA1 corre la **matriz `ASR_AVISOS`×vía** (on/off × voz/escrito) para que el gate no pueda
  «pasar» sin ejercitar el mecanismo nuevo.

## 2 · Fuzzy v2 (flag `F1_CORRECCION_FUZZY`)

- **Conjunto objetivo = fabricantes GOBERNADOS del catálogo** (36 en ARCHITECTURE) ∪
  `BRAND_TOKENS`, normalizado a token-primario — NO solo los 25 de `BRAND_TOKENS` (Sol-3:
  seed+10-yaml es un subconjunto reconocido; basar el fuzzy ahí perpetúa el mismatch y no
  cumple 30+).
- **Invariante como GUARD-TEST, no auditoría puntual** (Fable-1 + Sol-4): test en CI que
  reconstruye el conjunto VIVO y asserta (a) cero pares internos a distancia ≤1 y (b) cero
  VECINOS-d1 COMPARTIDOS entre dos objetivos (dos marcas a d=2 pueden compartir un token
  intermedio a d=1 de ambas — la resolución sería ambigua). Un yaml nuevo que rompa la
  invariante revienta CI, no la producción.
- Población y resolución: como v1 §1 (solo rama de corrección activa + cue presente +
  `matched_brands` vacío + UN candidato a d≤1 de UNA marca objetivo) — con
  `Asuncion(kind="marca_fuzzy")` (enum + trace allowlist extendidos) y disclosure OBLIGATORIO.
- **GA2 con negativos REALES** (Sol-4): palabras castellanas/en-dominio a distancia 1 de una
  marca objetivo (enumeradas al construir la cohorte-mini desde un lexicón; si el barrido
  demuestra que no existe ninguna, ESE resultado se estampa como evidencia de seguridad) +
  distancia-2 + dos-candidatos + sin-cue.

## 3 · R8 v2 (flag `F1_ESTADO_ATAJOS`)

- **Alcance = TODAS las rutas terminales de atajo CON CONTENIDO** (Sol-2, verificado en el
  dispatcher): `inventario`, `fabricantes`, `catalogo`, `mismatch`, `marca_no_servida` — la
  v1 decía «solo inventario» y era falso que fuera la única; dejar las otras fuera
  incumpliría el lifecycle «CLEAR en todas las rutas de salida» (conversation_policy:187-194).
  Cortesías (saludo/gracias) FUERA (no cambian de tema; Fable lo confirma).
- **Mecánica compositiva fijada** (Fable-5, sin disyuntiva): la rama-de-RESPUESTA de
  `advance_working_state` se extrae a un helper compartido
  (`_estado_tras_respuesta(query, excerpt, now, avail, models=())`) y
  `advance_after_shortcut` DELEGA en él — divergencia imposible por construcción, no por
  test. Escritura única vía `_aplicar_estado` en cada ruta terminal, gateada por el flag.
- Semántica: `models=()` (el atajo no bindea), `last_query=query`, excerpt, `last_turn_at=now`,
  **pending consumido** (cierra el hueco «ciclo máximo 1» a través de atajos). S99 intacto.

## 4 · Gates PRE-REGISTRADOS (v2)

- **GA0** (flags off): replay 5-turnos de hoy byte-conducta + suite + MT 52/52.
- **GA1 matriz**: (a) fuzzy: typo NO tabulado («quería decir de morlei») × `ASR_AVISOS`
  on/off × escrito/voz-normalizada ⇒ con tabla-silente el fuzzy resuelve Morley + disclosure;
  (b) R8: atajo (cada una de las 5 rutas con contenido; al menos inventario+mismatch
  ejercitadas e2e) → «Ahora quiero Morley» ⇒ el clasificador recibe `last_query` FRESCA —
  **su veredicto con estado fresco es HIPÓTESIS a medir aquí** (Sol-5: «ahora quiero X» no
  es un P13/P14 adjudicado; si sale NUEVO se lee, se estampa y se adjudica con Alberto);
  (c) pending vivo se limpia tras atajo (dirigido).
- **GA2**: cohorte-mini fuzzy determinista ($0) según §2.
- Ship: PR → merge → `F1_CORRECCION_FUZZY=on` + `F1_ESTADO_ATAJOS=on` → verificación por
  voz con typo NO tabulado.

## 5 · Alternativas y riesgos

v1 §4 vigente (fonético/d≥2 no; fuzzy-en-todo-turno no; transición duplicada en bot no;
cortesías no) + riesgos v1 §5 con R2 CERRADO por construcción (§3) y R1 medido en GA2.
La cita colgante «§2.A» de v1 queda retirada (Fable-4): la auditoría vive en el guard-test.

## 6 · Traza y adjudicación (ts=2026-08-21T13:41:30, emparejada, 10/10 · 0 FP)

| # | hallazgo | adjudicación |
|---|---|---|
| Sol-1 crítico | KIDE ya tabulado ⇒ el fuzzy no tiene rescate vivo aislado; apuesta anticipatoria vendida como medida | §1: reframe honesto; gates y verificación con typos NO tabulados |
| Sol-2 medio | «inventario única ruta con contenido» FALSO — fabricantes/catalogo/mismatch/marca_no_servida también retornan antes de la política | §3: alcance = las 5 rutas terminales con contenido |
| Sol-3 medio | BRAND_TOKENS (seed+yaml, 25) no es la fuente canónica; catálogo tiene 36 | §2: objetivo = gobernados del catálogo ∪ tokens |
| Sol-4 medio | cero-pares-d1 no excluye vecinos-d1 compartidos entre marcas a d2; GA2 con negativos triviales | §2: guard-test de vecindarios + negativos reales |
| Sol-5 menor | «Ahora quiero Morley» = P13/P14 es hipótesis, no hecho adjudicado | §4 GA1(b): se mide y se lee; adjudicación si NUEVO |
| Fable-1 medio | invariante d1 es hecho PUNTUAL — BRAND_TOKENS dinámico puede romperla en silencio | §2: guard-test en CI sobre el conjunto VIVO |
| Fable-2 medio | solape tabla/fuzzy no declarado; GA1(a) podía «pasar» sin ejercitar el fuzzy | §1/§4: orden de capas declarado + matriz pre-registrada |
| Fable-3 medio | caracterización de DEC-233 como «experimento medido» sin ancla | §1: la autoridad es el GO del owner; DEC-233 = mandato de disciplina |
| Fable-4 menor | cita colgante «§2.A» | §5: retirada; evidencia = guard-test |
| Fable-5 menor | R2 disyuntiva vaga | §3: delegación compositiva fijada |

## 7 · Checklist de build (B1-B7)

B1 guard-test de invariante (conjunto vivo, pares d≤1 + vecinos compartidos) ·
B2 conjunto objetivo gobernado + resolver fuzzy + rama en corrección + `marca_fuzzy` en
enum/trace + disclosure · B3 helper compartido `_estado_tras_respuesta` +
`advance_after_shortcut` + escrituras en las 5 rutas (flag) + limpieza de pending ·
B4 flags + inventario P1 (2 vars) · B5 runners GA0-GA2 + RUN con recibos ·
B6 suite + MT + push · B7 docs (DEC, digest, PLAN, HISTORY) + PR + mergeabilidad verificada.
