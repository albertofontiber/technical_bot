# S131 — enmienda v3 de acceso al retrieval shadow

Contrato normativo compuesto por:

- `evals/s131_chunks_v3_shadow_binding_design_v2.md`, SHA-256
  `acdd1f560fe8dc0ad92c9f31aad3c33d34b86a5698a10907ed09df077afc099f`;
- esta sustitución puntual de la ruta de acceso definida en V2.7 y de sus
  pruebas M0b relacionadas.

V3 no cambia manifests, identidades, taxonomía, conteos, particiones, tabla de
verdad, gates, orden development→held-out, coste ni autorizaciones.

## Sustitución normativa

La vista `chunks_v3_shadow_retrieval_eligible_v2` conserva
`WITH (security_invoker=true)`, pero no se concede directamente al runner ni a
ningún rol de API.

Se crean tres roles `NOLOGIN` separados:

1. `technical_bot_chunks_v3_shadow_loader`: carga y transiciones shadow
   estrechas, sin retrieval;
2. `technical_bot_chunks_v3_shadow_rpc_owner`: owner interno de las RPC shadow,
   con el mínimo `SELECT` necesario sobre vista/tablas y sin login, creación de
   roles, bypass RLS ni autoridad de publicación productiva;
3. `technical_bot_chunks_v3_shadow_runner`: recibe únicamente `EXECUTE` sobre
   las firmas RPC shadow enumeradas y ningún `SELECT` sobre vista o tablas.

Las RPC shadow son `SECURITY DEFINER`, propiedad exclusiva del rol interno,
`SET search_path=''` y usan nombres totalmente cualificados. Exigen sin defaults
`materialization_id`, `evaluation_partition`, query/filtros y límite; validan
materialización `validated`, manifest experimental exacto y partición antes de
consultar. No aceptan fallback, generación `active`, partición distinta,
funciones dinámicas ni SQL construido desde inputs.

Se revoca `EXECUTE` a `PUBLIC`, `anon`, `authenticated` y `service_role`; solo
`technical_bot_chunks_v3_shadow_runner` puede ejecutarlas. El runner no puede
asumir el rol owner.

M0b debe demostrar simultáneamente:

- la RPC autorizada funciona al ejecutar como runner;
- `SELECT` directo del runner sobre vista y cada tabla subyacente falla;
- el runner no puede ejecutar RPC con otra materialización o partición;
- el owner no tiene login, membresías elevadas ni privilegios fuera de los
  objetos exactos del shadow;
- roles API y `service_role` no pueden usar vista, tablas ni RPC;
- `search_path`, owner, grants, RLS y nombres cualificados coinciden con el
  contrato.

Tras GO adversarial, la salida permitida continúa siendo exclusivamente
`GO_TO_IMPLEMENT_BINDING_MANIFEST_AND_STATIC_SQL_V2`.
