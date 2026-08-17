# -*- coding: utf-8 -*-
"""`dashboard/` — el panel de control del bot (s324f, DEC-231).

QUÉ ES. Un servicio web APARTE del bot, en este mismo repo, que sirve dos cosas
a quien administra el piloto: la **gestión de acceso** (emitir, listar y anular
invitaciones; ver y revocar la allowlist) y las **métricas** que ya existen en
Supabase (las 7 vistas de DEC-183 + los errores agregados). Sólo lectura salvo
en gestión de acceso.

POR QUÉ VIVE AQUÍ Y NO EN `src/`. Tres motivos, y ninguno es estético:

  1. **`src/` es el árbol del BOT.** Su matriz de imports
     (`tests/test_import_contract.py`) describe un producto —ingesta, RAG,
     orquestador, transporte— y su censo de módulos es un trinquete
     anti-acreción deliberado. El panel es una SEGUNDA aplicación sobre los
     mismos datos, no un módulo nuevo del bot: meterlo en `src/` mezclaría dos
     grafos de dependencias que no comparten runtime.
  2. **DEC-231 §2 exige que no compartan proceso**: «si el panel cae, el bot
     sigue». Que sean dos raíces distintas hace esa frontera visible en el
     árbol, no sólo en la configuración de Railway.
  3. **La flecha de dependencia apunta en un solo sentido**: el panel importa
     de `src/`, `src/` NUNCA importa del panel. Eso no se deja a la disciplina —
     `dashboard` está en `RAICES_PROHIBIDAS` del contrato de imports, así que un
     `import dashboard` dentro de `src/` pone el CI en rojo.

QUÉ REUTILIZA (y qué NO reimplementa). El canje de una invitación, la puerta de
acceso y la taxonomía de errores **ya existen y están probados**; el panel es
otra cara sobre ellos:

  · `src.bot.access` — vocabulario del token (`token_nuevo`, `hash_token`,
    `enlace_invitacion`), las cotas de caducidad y el estado derivado de una
    invitación (`estado_invitacion`). El panel es un EMISOR más, exactamente
    como el CLI: por eso la regla vive en la hoja pura y no aquí;
  · `scripts.s324e_bot_errores_insights.agregar` — la agregación de errores,
    tal cual, sin una segunda copia;
  · las 7 vistas SQL de DEC-183 — el panel las lee, no las recalcula.

  El **canje** (`logging_db.canjear_invitacion`) no aparece por ningún lado: lo
  hace el bot cuando el invitado pulsa el enlace, y el panel no tiene por qué
  poder canjear nada.

LA FRONTERA DE SEGURIDAD, en una línea: **la clave de servicio de Supabase no
sale de este proceso**. Todo el acceso a datos es server-side, el HTML se
renderiza aquí y el navegador recibe texto ya cocinado. No hay JavaScript, no
hay ficheros estáticos y no hay ninguna ruta que responda sin sesión salvo la
propia pantalla de entrada.
"""

VERSION = "s324f-v1"
