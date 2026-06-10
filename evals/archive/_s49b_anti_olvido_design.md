# s49b — Control anti-olvido de procedimientos canónicos — PARA REVISIÓN ADVERSARIAL

> Artefacto a atacar ANTES de cablear (Protocolo 3; toca esquema del ruler = zona de dolor +
> es proceso de alto impacto que gobierna TODA la autoría futura). Disparador: Alberto cazó 2×
> que declaré "procedimiento seguido" sin completarlo (autoría gold) y señaló el patrón general
> (contextual-retrieval: premisa no verificada 3 sesiones). Decisión de Alberto: activación +
> enforcement-puerta + barrido.

## 0. Diagnóstico (la raíz)
NO es falta de documentación (RULER_DESIGN §2 ya tiene el procedimiento). Es **activación en el
punto de uso**: solo `CLAUDE.md` se carga SIEMPRE; el resto (RULER_DESIGN, el código, el estado
real) solo si me acuerdo de leerlo/verificarlo. Los 2 fallos de Alberto son el MISMO patrón:
"no traje al contexto / no verifiqué lo ya establecido ANTES de actuar". Es una laguna del
Protocolo 1 (verifica antes de declarar éxito) que no lista los PROCEDIMIENTOS a verificar.

## 1. Inventario del barrido (DEC-001..023 + D1-D11) — procedimientos/contratos RECURRENTES
(Filtrados: los que se aplican en un GATILLO, no decisiones puntuales.)
- **Autoría de gold** — RULER_DESIGN §2 (D3 loc exhaustiva · D4 render · doble-señal AND · render±1 · predicado completo). [el que fallé]
- **Verificar código/estado/premisa ANTES de teorizar** — DEC-022 (contextual-retrieval), feedback_my_bias #20. [el que citó Alberto]
- **gold ancla en la FUENTE, NUNCA en chunks_v2 (circular)** — RULER_DESIGN §0/§2, D7. [reforzado hoy]
- **Embargo held-out** (no inspeccionar/tunear) — DEC-023.
- **Juez único GPT-5.5 + K-mayoría** (no single-pass; árbitro ruidoso) — DEC-015/021 §D.
- **A/B con 2 ejes** (completitud↑ SIN invención↑) — DEC-001.
- **gate-first / medir-barato-primero** (no pre-suponer el lever) — DEC-018/019; medir delta, no proxies — DEC-005.
- **gold_store = puerta única, no editar a mano** — D10.
- **Conducta del gold desde principios+corpus, no del prompt** — D2. **Clarify = candidatos del catálogo** — D6.
- (Ya en CLAUDE.md: Protocolos 1/2/3, eval-driven, dúo en zona de dolor, cierre de sesión.)

## 2. Pieza 1 — `CLAUDE.md`: "Registro de procedimientos canónicos (gatillo → acción)"
Sección nueva (lo único cargado siempre). Regla rectora + tabla de triggers de 1 línea → doc canónico.

**Regla rectora:** *Antes de declarar que seguiste un procedimiento o que algo está "hecho/completo/
verificado", re-lee su checklist canónico y verifícalo punto por punto. La ausencia de verificación
punto-por-punto ES la señal de que no lo hiciste. (Protocolo 1 extendido a procedimientos.)*

| GATILLO | ACCIÓN OBLIGATORIA | Canónico |
|---|---|---|
| Autorar/editar un gold | Checklist completo §2; ancla en la FUENTE **nunca** chunks_v2; vía `gold_store` | RULER_DESIGN §2; D3/D4/D7/D10 |
| Tocar retrieval/generación/premisa/"cimiento" | Verificar el **código y estado real PRIMERO**; no teorizar sobre premisas no verificadas | DEC-022; bias #20 |
| Correr eval / medir un lever | Held-out **embargado**; juez GPT-5.5 + **K-mayoría**; 2 ejes (completitud↑ sin invención↑); freeze-contract | DEC-023/015/001/021§F |
| Proponer/elegir un lever | **Gate/audit primero** (no pre-suponer); medir **delta en eval**, no proxies | DEC-019/005 |

## 3. Pieza 2 — `RULER_DESIGN §2`: checklist explícito al inicio (de prosa a lista tildea-ble)
```
[ ] 1. Localización EXHAUSTIVA: barrido de TODOS los manuales del producto (ES+EN) → _provenance.manuales_buscados
[ ] 2. Render del píxel de la fuente (no texto-solo)
[ ] 3. Render ±1 vecina (cazar off-by-one)
[ ] 4. Doble-señal AND por hecho CORE: cross-model render (Claude+GPT) Y/O match determinista en texto
[ ] 5. Predicado completo (valor + parámetro + contexto, no solo el número)
[ ] 6. Hechos atómicos (core/supp) + conducta derivada de principios+corpus (no del prompt)
[ ] 7. El gold se ancla en la FUENTE; chunks_v2 = nota diagnóstica POST-hoc, jamás criterio (circular)
[ ] 8. Escritura vía gold_store.upsert (puerta única)
```

## 4. Pieza 3 — `gold_store` enforcement-puerta (el control inevitable)
Para `estado=verificado`, `validate_entry` EXIGE evidencia del procedimiento (promueve de warning a ERROR):
- `_provenance.localizacion.manuales_buscados` (lista no vacía) — evidencia de loc exhaustiva.
- `_provenance.localizacion.metodo` (str no vacío) — evidencia de render + render±1 + doble-señal.
- `_provenance.verificado_por` (str no vacío) — evidencia de quién (2 modelos para doble-señal).

**Grandfathering (dato real: `metodo` solo lo tiene cat008; `manuales_buscados` falta en hp011/hp017):**
sin grandfather, el enforcement rompe los 22 legacy. → marcar los 22 con `_provenance.legacy_verificado: true`
(retrofit one-off); el enforcement exime a `legacy_verificado` de metodo/manuales_buscados. Los NUEVOS
(cat008 ya cumple; bulk futuro) deben cumplir. CI sigue verde.

**Límite honesto (declarado):** el esquema verifica que DOCUMENTÉ los pasos, NO que los EJECUTÉ. Convierte
"olvido" en omisión-visible (validate falla) o en mentira-consciente (texto falso) — un control real,
no infalible. El dúo P3 sobre golds en zona de dolor sigue siendo la capa de ejecución.

## 5. Por qué BP + estructural + escalable
- Quita el control de la mano de Alberto (norma feedback_my_bias) y de mi memoria → al sistema.
- 3 capas: activación (CLAUDE.md siempre cargado) + checklist (la lista) + enforcement (la puerta, inevitable).
- Mismo principio validado en s49 (embargo en la puerta). Escala: registro extensible.

## 6. Alternativas descartadas
- Solo documentar mejor → ya está; el fallo es activación.
- Hook en settings.json → frágil (ejecuta comandos, no cambia razonamiento; autoría vía script, no Edit).
- Inventar un `metodo` retroactivo para los 22 legacy → deshonesto (no documentamos ese proceso); el flag legacy es honesto.

## 7. Dónde quiero bite (no rubber-stamp)
1. ¿El enforcement-puerta (documenta≠ejecuta) es control REAL o teatro/ritual? ¿Mejor un campo estructurado por-paso vs `metodo` libre?
2. ¿El grandfathering por flag `legacy_verificado` es correcto, o debería ser por `schema_version`/fecha? ¿Riesgo de que los nuevos hereden el flag por copia y se salten el control?
3. ¿El registro en CLAUDE.md es proporcionado o lo infla? ¿Sobra/falta algún trigger del inventario §1?
4. ¿Estoy over-engineering (mi sesgo) — basta la capa 1+2 (activación+checklist) y el enforcement-puerta es burocracia? ¿O es justo el control inevitable que pidió Alberto?
5. ¿Algún procedimiento canónico del barrido §1 que NO debería ser trigger (ruido), o alguno CLAVE que me dejé?
