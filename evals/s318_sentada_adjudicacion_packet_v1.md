# s318 — Paquete de SENTADA ÚNICA de adjudicación (Alberto)

Tres decisiones, una sentada. Orden sugerido: la 1 es un sí/no de 2 minutos,
la 2 es la sentada B2 clásica (~30-45 min), la 3 es un sí/no viendo dos listas.
**El FULL fresco v3.2 (~$25) queda DETRÁS de esta sentada** (tu secuencia).

---

## 1. DP312x — marcar supersedida la revisión 202503 (censo s317, DEC-205)

**Qué es**: el censo de revisión encontró UN par supersedido activo en 1.069
docs: `MI_KIDDE_KE_DP312x_202503` vs `MI_KIDDE_KE_DP312x_202512` (misma familia,
la 202512 es 9 meses más nueva; ambas ACTIVAS y compitiendo en retrieval).

**Decisión**: ¿marco `status=superseded` en la 202503 con cadena
`superseded_by_id` → 202512? (Reversible; recibo con ambas filas antes/después.)

- [ ] SÍ, ejecuta · [ ] NO, déjalas convivir (di por qué para el registro)

---

## 2. Sentada B2 de gold-review — packet existente

**Doc**: `evals/s312_goldreview_b2_packet_v3.md` (9 ítems + 1 nuevo de s305).
Resuelve 4-5 de los 16 fallos del assessment vigente — son alcance de gold, no
ingeniería. Cada ítem lleva su evidencia y las opciones de etiqueta.

---

## 3. #71 — encender el frame `legal_disclaimer` (aparato protegido, DEC-148)

**Qué hace**: el apéndice de obligaciones deja de poder citar cláusulas de
exención de responsabilidad del fabricante como si fueran obligaciones técnicas
(el caso KGS «no se hará responsable en ningún caso…» que viste en #71).

**Evidencia (dúo r16 cerrado, Sol 5 + Fable 4, 0 FP, todo aplicado)**:
- Población: 105 docs ACTIVOS con boilerplate de responsabilidad.
- Sonda v2 por el CAMINO REAL con pregunta-oráculo
  (`evals/s318_disclaimer_probe_v2.json`): **83 obligaciones legales removidas
  (70 docs) · 0 obligaciones técnicas cambiadas** (invariante verificado).
- **28 «mixtas»** (exención que menciona instalar/usar/mantener «conforme al
  manual») — listadas VERBATIM en el recibo, sección `mixtas_detalle`: míralas
  antes de decidir; su contenido operativo es genérico (remiten al manual, sin
  payload numérico), pero la llamada es tuya.
- Precisión: «el módulo no es responsable de generar la alarma» (arquitectura
  real) NO se salta — guarda de contexto de exención en ES y EN, 24 tests.
- La clase GARANTÍA queda FUERA a conciencia («la garantía se anula si…» sí es
  contenido útil).

**Decisión**: ¿pongo `EC_LEGAL_DISCLAIMER_SKIP=on` en Railway?
(Flag reversible sin deploy; OFF = conducta de hoy byte-idéntica.)

- [ ] SÍ, enciende · [ ] NO / quiero cambios (¿cuáles?)

---

*Tras la sentada: ejecuto lo adjudicado con recibos + FULL fresco v3.2
(smoke primero) + estampo scoreboard y LEVER_DIGEST donde toque.*
