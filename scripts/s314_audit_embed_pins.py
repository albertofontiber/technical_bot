#!/usr/bin/env python3
"""Pre-flight puntual L3 (equivalente DEC-189 para embed.py, no la isla).

1. ¿Algun recibo evals/*.yaml|json pina {path: src/reingest/embed.py, sha256: ...}?
2. ¿Algun fichero PINEADO por sha256 (congelado) referencia src/reingest/embed
   o src.reingest.embed?
Distingue: pins VIVOS (bloquean el mv) vs fingerprints del assessment (via
sancionada L1: pipe_sha cambia -> smoke + fila).
"""
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(r'C:\dev\technical_bot')
TARGET_PATHS = {'src/reingest/embed.py'}
TARGET_STRINGS = ('src/reingest/embed', 'src.reingest.embed')

direct_pins = []       # recibos que pinan embed.py con sha256
path_mentions = []     # recibos que mencionan la ruta en un campo path SIN sha256
pineados_files = set() # todos los .py pineados por sha256 en algun recibo
pin_sources = {}       # fichero pineado -> recibos que lo pinan

for f in list((ROOT / 'evals').glob('*.yaml')) + list((ROOT / 'evals').glob('*.json')):
    try:
        d = (yaml.safe_load if f.suffix == '.yaml' else json.loads)(
            f.read_text(encoding='utf-8'))
    except Exception:
        continue

    def walk(x):
        if isinstance(x, dict):
            p = x.get('path')
            if isinstance(p, str):
                posix = Path(p).as_posix()
                if posix in TARGET_PATHS:
                    if 'sha256' in x:
                        direct_pins.append((f.name, x.get('sha256')))
                    else:
                        path_mentions.append(f.name)
                if posix.endswith('.py') and 'sha256' in x:
                    pineados_files.add(posix)
                    pin_sources.setdefault(posix, set()).add(f.name)
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)

    walk(d)

frozen_refs = []
for pf in sorted(pineados_files):
    q = ROOT / pf
    if not q.exists():
        continue
    t = q.read_text(encoding='utf-8', errors='ignore')
    if any(s in t for s in TARGET_STRINGS):
        frozen_refs.append((pf, sorted(pin_sources[pf])[:3]))

print(f"recibos evals escaneados: yaml+json de evals/")
print(f"ficheros .py pineados por sha256 en recibos: {len(pineados_files)}")
print(f"\n[1] PINS DIRECTOS {{path: src/reingest/embed.py, sha256}}: {len(direct_pins)}")
for name, sha in direct_pins:
    print(f"    {name}  sha256={str(sha)[:16]}...")
print(f"\n[2] menciones de la ruta en campo path SIN sha256: {len(path_mentions)}")
for name in sorted(set(path_mentions)):
    print(f"    {name}")
print(f"\n[3] ficheros CONGELADOS (pineados) que referencian src[./]reingest[./]embed: {len(frozen_refs)}")
for pf, srcs in frozen_refs:
    print(f"    {pf}  <- pineado por {srcs}")

blocking = bool(direct_pins) or bool(frozen_refs)
print(f"\nVEREDICTO: {'BLOQUEA - hay pins vivos' if blocking else 'OK - 0 referencias bloqueantes desde congelados'}")
sys.exit(1 if blocking else 0)
