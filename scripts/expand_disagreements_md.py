#!/usr/bin/env python3
"""Expande el contenido truncado a 1500 chars en gate_validation_disagreements.md
hasta el cap real de los jueces (4000 chars = MAX_CHUNK_CHARS), preservando
todas las decisiones humanas (`**Tu decisión:**`) y comentarios.

Fix del bug: cross_validate_relevance.py:311 truncaba el render a 1500 mientras
que Sonnet/Opus juzgaban sobre 4000. La revisión humana quedaba con menos info
que los LLMs — gap silencioso.

Uso: python scripts/expand_disagreements_md.py
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
sys.stdout.reconfigure(encoding="utf-8")

from src.ingestion.supabase_client import SupabaseHTTP

MD_PATH = Path("evals/gate_validation_disagreements.md")
JSON_PATH = Path("evals/gate_validation_results.json")
TARGET_CHARS = 4000  # = MAX_CHUNK_CHARS de identify_relevant_chunks.py


def main():
    md = MD_PATH.read_text(encoding="utf-8")
    results = json.loads(JSON_PATH.read_text(encoding="utf-8"))

    # Mapa short_id (12 chars) → full chunk_id
    short_to_full = {v["chunk_id"][:12]: v["chunk_id"]
                     for v in results["validations"]}
    print(f"Mapped {len(short_to_full)} unique chunk_ids from JSON")

    # Encontrar todos los chunk_ids cortos referenciados en el .md
    short_ids = re.findall(r"## \w+ · chunk `([0-9a-f]{8}-[0-9a-f]{3})`", md)
    unique_shorts = list(dict.fromkeys(short_ids))  # preserva orden
    print(f"Found {len(short_ids)} chunk refs in .md ({len(unique_shorts)} unique)")

    # Resolver a full ids
    missing = [s for s in unique_shorts if s not in short_to_full]
    if missing:
        print(f"WARN: {len(missing)} short_ids without mapping: {missing[:5]}")
    full_ids = [short_to_full[s] for s in unique_shorts if s in short_to_full]

    # Fetch full content en lotes (chunks_v2)
    db = SupabaseHTTP()
    content_by_id = {}
    BATCH = 50
    for i in range(0, len(full_ids), BATCH):
        batch = full_ids[i:i+BATCH]
        # PostgREST: id=in.(uuid1,uuid2,...)
        filt = {"id": f"in.({','.join(batch)})"}
        rows = db.fetch_rows("chunks_v2", select="id,content",
                             filters=filt, limit=BATCH * 2)
        for r in rows:
            content_by_id[r["id"]] = r["content"] or ""
        print(f"  Fetched {i+len(batch)}/{len(full_ids)}")

    print(f"Got content for {len(content_by_id)} chunks")

    # Reemplazar cada bloque ```...``` que sigue al header del chunk
    # Estrategia: split por chunk header y procesar cada bloque
    def replace_content(match):
        header = match.group(0)  # "## hp001 · chunk `xxxxx`"
        short = match.group(1)
        full = short_to_full.get(short)
        if not full or full not in content_by_id:
            return header  # no tocamos si no tenemos el chunk
        return header + f"__FULL_ID:{full}__"

    # Insertar marker temporal con el full_id al lado del header
    md_marked = re.sub(r"## \w+ · chunk `([0-9a-f]{8}-[0-9a-f]{3})`",
                       replace_content, md)

    # Ahora para cada bloque, buscar el patrón:
    # __FULL_ID:xxx__ ... ```\n<content>\n``` y reemplazar <content>
    def expand_block(match):
        full_id = match.group(1)
        prefix = match.group(2)
        # No nos importa el viejo content, lo reemplazamos
        new_content = content_by_id.get(full_id, "")
        if new_content:
            new_content = new_content[:TARGET_CHARS]
        return f"{prefix}```\n{new_content}\n```"

    pattern = re.compile(
        r"__FULL_ID:([0-9a-f-]+)__"          # marker
        r"(.*?\*\*Chunk\*\*[^\n]+\n\n)"      # prefix hasta el opening ```
        r"```\n.*?\n```",                     # bloque ``` viejo
        re.DOTALL,
    )
    md_new = pattern.sub(expand_block, md_marked)

    # Limpiar markers residuales
    md_new = re.sub(r"__FULL_ID:[0-9a-f-]+__", "", md_new)

    # Verificar que no hemos perdido las decisiones
    decisions_before = re.findall(r"\*\*Tu decisión:\*\*", md)
    decisions_after = re.findall(r"\*\*Tu decisión:\*\*", md_new)
    print(f"Decisions preserved: {len(decisions_before)} → {len(decisions_after)}")
    assert len(decisions_before) == len(decisions_after), "DECISIONES PERDIDAS"

    comments_before = md.count("**Comentarios:**") + md.count("** Comentarios:**") + md.count("**comentarios:**")
    comments_after = md_new.count("**Comentarios:**") + md_new.count("** Comentarios:**") + md_new.count("**comentarios:**")
    print(f"Comments preserved: {comments_before} → {comments_after}")
    assert comments_before == comments_after, "COMENTARIOS PERDIDOS"

    # Métricas de cambio
    old_lens = [len(m.group(1)) for m in re.finditer(r"```\n(.*?)\n```", md, re.DOTALL)]
    new_lens = [len(m.group(1)) for m in re.finditer(r"```\n(.*?)\n```", md_new, re.DOTALL)]
    print(f"Chunk lengths — before: min={min(old_lens)} med={sorted(old_lens)[len(old_lens)//2]} max={max(old_lens)}")
    print(f"Chunk lengths — after:  min={min(new_lens)} med={sorted(new_lens)[len(new_lens)//2]} max={max(new_lens)}")

    # Backup y escribir
    backup = MD_PATH.with_suffix(".md.bak")
    backup.write_text(md, encoding="utf-8")
    MD_PATH.write_text(md_new, encoding="utf-8")
    print(f"Done. Backup en {backup}")


if __name__ == "__main__":
    main()
