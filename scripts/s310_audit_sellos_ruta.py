#!/usr/bin/env python3
"""s310 — PRE-FLIGHT de cualquier movimiento de ficheros: ¿qué pina el ecosistema de sellos?

Nace del NO-GO de L2a: el blueprint contaba ARISTAS DE IMPORT (censo s300) y enumeró 2
módulos anclados + un puñado de tests; la realidad medida al ejecutar el traslado fue que
**29 de los 33 módulos de la isla están referenciados POR RUTA** desde recibos congelados
(preregs/permisos con {path, sha256}) o desde los 380 ficheros de código que esos recibos
pinan por sha. Mover un fichero así = o romper sellos o una cirugía de traducciones que no
compensa la legibilidad que compraba (la garantía ESTRUCTURAL ya la da la cuarentena
lógica del contrato L0).

REGLA NUEVA (DEC-189): antes de proponer mover CUALQUIER fichero, correr este audit.
Un fichero con referencias-por-ruta desde sellos NO se mueve — se ancla y se declara
(el patrón de los 2 anclados del blueprint, que resultó ser la regla y no la excepción).

Uso:  python scripts/s310_audit_sellos_ruta.py            # la isla del contrato
"""
import json
import yaml
from pathlib import Path

import ast
_contrato = ast.parse(Path('tests/test_import_contract.py').read_text(encoding='utf-8'))
for _n in ast.walk(_contrato):
    if isinstance(_n, ast.Assign) and getattr(_n.targets[0], 'id', '') == 'ISLA':
        MOVIDOS = {x.split('.')[-1] for x in ast.literal_eval(_n.value.args[0])}
assert len(MOVIDOS) >= 30, 'ISLA no encontrada en el contrato'

refs = {m: set() for m in MOVIDOS}
pineados_files = set()

for f in list(Path('evals').glob('*.yaml')) + list(Path('evals').glob('*.json')):
    try:
        d = (yaml.safe_load if f.suffix == '.yaml' else json.loads)(
            f.read_text(encoding='utf-8'))
    except Exception:
        continue

    def walk(x):
        if isinstance(x, dict):
            p = x.get('path')
            if isinstance(p, str):
                q = Path(p)
                posix = q.as_posix()
                if q.stem in MOVIDOS and posix.startswith('src/'):
                    refs[q.stem].add('recibo:' + f.name)
                if posix.endswith('.py') and 'sha256' in x:
                    pineados_files.add(posix)
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(d)

for pf in pineados_files:
    q = Path(pf)
    if not q.exists():
        continue
    t = q.read_text(encoding='utf-8', errors='ignore')
    for m in MOVIDOS:
        if f'src/rag/{m}.py' in t or f'src/reingest/{m}.py' in t:
            refs[m].add('congelado:' + q.name)

anclar = {m: v for m, v in refs.items() if v}
print(f"ficheros pineados totales: {len(pineados_files)}")
print(f"módulos con referencia POR RUTA desde sellos: {len(anclar)}/{len(MOVIDOS)}")
for m in sorted(anclar):
    extras = '...' if len(anclar[m]) > 3 else ''
    print(f"  {m}: {sorted(anclar[m])[:3]}{extras}")
print(f"\nLIBRES: {len(MOVIDOS) - len(anclar)}")
for m in sorted(MOVIDOS - set(anclar)):
    print(' ', m)
