"""¿Coge el clasificador una pregunta SIN signos de interrogación?

PUNTO DE ALBERTO (20-ago, al pasar el gate de acuerdo de la v8): «si alguien
pregunta "qué productos Detnov tienes", sin los signos de interrogación, también
debería considerarse pregunta».

POR QUÉ ESTO ES UNA SONDA Y NO UN TEST. La regla determinista NO coge ese caso
—solo mira el signo FINAL, que es la adjudicación literal de Alberto—, así que
la decisión la toma el LLM con el sesgo «ante la duda, pregunta». Es decir: la
conducta que Alberto quiere **depende del prompt**, no del código. Un test con un
LLM de mentira no probaría nada; hace falta llamar al modelo de verdad, y eso
cuesta (céntimos) y no puede vivir en la suite.

POR QUÉ NO SE AMPLIÓ LA REGLA en su lugar. Medido abajo: el LLM acierta 8/8 sin
un solo falso positivo en los controles. Una regla de aperturas interrogativas
(«qué/cómo/cuántos/dime/necesito…») no añadiría precisión hoy y sí superficie —
y sobre todo TAPARÍA la señal: si un cambio de prompt rompiera esto, la regla lo
escondería en vez de dejar que esta sonda lo cace.

CUÁNDO RE-CORRERLA A MANO: casi nunca, desde s328e. Los mismos casos son ahora
**pre-vuelo del job de clasificación** (`scripts/clasificar_preguntas.py`), que
los mide antes de escribir nada y ABORTA si el eje ha regresado — el gatillo
dejó de depender de que alguien se acuerde. Este script sigue existiendo para
mirar el detalle caso a caso (imprime qué decidió cada eje y qué categoría),
que el pre-vuelo no enseña. Los casos congelados viven en `src/clasificacion.py`
(`SONDA_EJE_PREGUNTAS` / `SONDA_EJE_NO_PREGUNTAS`), no aquí: dos copias de una
lista congelada divergen.

Uso:  python -m scripts.s328c_sonda_pregunta_sin_signos
"""
import os, sys
sys.path.insert(0, "/home/user/technical_bot")
from src.clasificacion import (Catalogo, cargar_taxonomia, construir_llm,
                               construir_prompt, indice_de_marcas,
                               parsear_respuesta, termina_en_interrogacion,
                               MODELO_LLM)

SIN_SIGNOS_PERO_PREGUNTAN = [
    "qué productos Detnov tienes",                       # el ejemplo de Alberto
    "que centrales de 4 lazos teneis",
    "cuantos lazos tiene la CAD-250",
    "como se rearma la ID3000 tras una alarma",
    "dime las especificaciones del DGD-600",
    "necesito el esquema de conexión del CAD-250",
    "me puedes pasar el manual de la NFS2-3030",
    "cual es la resistencia de fin de línea de la AFP-200E",
]
NO_PREGUNTAN = [                                          # control en el otro sentido
    "ok, entendido",
    "Programación principalmente.",
    "estoy trabajando con la ZX1e",
    "gracias, me vale",
]

taxonomia = cargar_taxonomia()
catalogo = Catalogo(nombres=["Detnov", "Notifier", "Morley", "Kidde"],
                    marca_de_modelo=lambda m: None, resolver_alias=lambda a: None)
indice = indice_de_marcas(catalogo.nombres)
llm = construir_llm(os.environ["ANTHROPIC_API_KEY"], MODELO_LLM)

def decidir(texto):
    dura = termina_en_interrogacion(texto)
    prompt = construir_prompt(taxonomia, texto)
    parseado = parsear_respuesta(llm(prompt), taxonomia.ids)
    if parseado is None:
        return dura, None, "PARSER-RECHAZA"
    cat, marcas, es_pregunta = parseado
    return dura, es_pregunta, cat

print(f"taxonomía v{taxonomia.version} · modelo {MODELO_LLM}\n")
print("DEBERÍAN SER PREGUNTA (sin ningún signo de interrogación):")
fallos = []
for t in SIN_SIGNOS_PERO_PREGUNTAN:
    dura, es_preg, cat = decidir(t)
    marca = "OK " if es_preg else "FALLA"
    if not es_preg: fallos.append(t)
    print(f"  {marca}  regla={'sí' if dura else 'no':<3} llm={'pregunta' if es_preg else 'NO-pregunta':<12} {cat:<26} «{t}»")

print("\nNO deberían ser pregunta (control):")
fp = []
for t in NO_PREGUNTAN:
    dura, es_preg, cat = decidir(t)
    marca = "OK " if not es_preg else "FALLA"
    if es_preg: fp.append(t)
    print(f"  {marca}  regla={'sí' if dura else 'no':<3} llm={'pregunta' if es_preg else 'NO-pregunta':<12} {cat:<26} «{t}»")

print(f"\nRESULTADO: {len(SIN_SIGNOS_PERO_PREGUNTAN)-len(fallos)}/{len(SIN_SIGNOS_PERO_PREGUNTAN)} "
      f"preguntas sin signos reconocidas · {len(NO_PREGUNTAN)-len(fp)}/{len(NO_PREGUNTAN)} controles limpios")
if fallos: print("  NO reconocidas:", fallos)
if fp: print("  falsos positivos:", fp)
