# s329 — El enlace de invitación debe ser de copiar y pegar (pedido de Alberto, 20-ago)

SÍNTOMA: el panel emitía `https://t.me/<NOMBRE_DEL_BOT>?start=...` + aviso «falta
TELEGRAM_BOT_USERNAME», porque la variable no existe en el entorno de Vercel (ni en
Railway — censo s329 por API: en producción no está en NINGÚN sitio; solo los tests
y la ayuda del CLI conocen el valor).

DECISIÓN (impacto MEDIO): default en código. `src/bot/access.py` gana
`BOT_USERNAME_DEFECTO = "PCI_Soporte_tecnico_bot"` — VERIFICADO contra getMe de
Telegram con el token vivo del worker de Railway (username=@PCI_Soporte_tecnico_bot,
nombre='Soporte tecnico PCI IA', id=8710961901) — y `bot_username_publico(explicito=None)`
que resuelve explícito > env TELEGRAM_BOT_USERNAME > default y nunca devuelve vacío.
El panel (`dashboard/gestion.py`) y el CLI (`scripts/s324e_invitaciones.py`) comparten
la resolución; las ramas placeholder/OJO quedan inalcanzables y se eliminan.

ALTERNATIVAS DESCARTADAS:
(a) Poner la var en Vercel: acción manual de dashboard que Alberto pidió evitar; deja
    viva la clase «var ausente → placeholder» en cada entorno/preview nuevo; sin acceso
    programático a la config de Vercel desde esta sesión.
(b) getMe en runtime desde el panel: exigiría llevar TELEGRAM_BOT_TOKEN al entorno del
    panel = ampliar la superficie de secreto expuesta a internet, contra el diseño del
    panel (CSP default-src 'none', sin JS, mínimo secreto).
(c) El worker estampa su username en una tabla y el panel lo lee: migración + lectura
    extra + pieza móvil nueva para una constante pública que cambia ~nunca.

GAPS DECLARADOS:
- Renombrado del @username en BotFather → default obsoleto (enlace a username liberado).
  Mitigación: checklist ampliado en DG_DEPLOYMENT.md + el override por env var. No hay
  oráculo offline posible.
- El fix llega a producción al mergear a main (auto-deploy de Vercel); la invitación ya
  emitida con placeholder sigue válida (editable a mano o anular + re-emitir).
- Acopla identidad-de-deployment al repo; se acepta porque el username es identidad
  PÚBLICA del producto (viaja en cada enlace compartido) y el override existe.

TESTS: tests/test_s329_username_bot.py nuevo (resolución + integración panel sin var);
suites afectadas verdes: 214 passed (s324e allowlist, s324f rutas, s329).
