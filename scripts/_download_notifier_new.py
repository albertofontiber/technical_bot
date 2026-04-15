"""One-shot downloader for the 357 new Notifier PDFs (see _to_download.json)."""
import sys
import io
import json
import re
import os
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import httpx
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(".env")

OUTDIR = Path("Manuales_Notifier_Privado")
OUTDIR.mkdir(exist_ok=True)
items = json.loads((OUTDIR / "_to_download.json").read_text(encoding="utf-8"))
print(f"To download: {len(items)}")

USER = os.getenv("NOTIFIER_USER")
PASS = os.getenv("NOTIFIER_PASSWORD")

c = httpx.Client(follow_redirects=True, timeout=120.0, headers={"User-Agent": "Mozilla/5.0"})
r = c.get("https://www.notifier.es/index.php/acceso-clientes")
csrf = re.search(r'name="([a-f0-9]{32})"\s+value="1"', r.text).group(1)
ret = re.search(r'name="return"\s+value="([^"]+)"', r.text).group(1)
c.post(
    "https://www.notifier.es/index.php/acceso-clientes?task=user.login",
    data={"username": USER, "password": PASS, "remember": "yes", "return": ret, csrf: "1"},
)
assert c.cookies.get("joomla_user_state") == "logged_in"
print("Login OK")


def sanitize(fn: str) -> str:
    return fn.replace("/", "_").replace("\\", "_")


ok = 0
skip = 0
fail = []
for i, it in enumerate(items, 1):
    fn = sanitize(it["filename"])
    dest = OUTDIR / fn
    if dest.exists() and dest.stat().st_size > 1024:
        skip += 1
        continue
    try:
        resp = c.get(it["url"])
        resp.raise_for_status()
        if resp.content[:4] != b"%PDF":
            fail.append((fn, f"not-pdf ct={resp.headers.get('content-type', '')}"))
            continue
        dest.write_bytes(resp.content)
        ok += 1
        if i % 25 == 0 or i == len(items):
            total_mb = sum(p.stat().st_size for p in OUTDIR.glob("*.pdf")) / 1024 / 1024
            print(f"  {i}/{len(items)}  ok={ok} skip={skip} fail={len(fail)}  disk={total_mb:.0f}MB")
    except Exception as e:
        fail.append((fn, str(e)[:120]))
    time.sleep(1.0)

print(f"\nDONE  ok={ok} skip={skip} fail={len(fail)}")
if fail:
    print("Failures:")
    for fn, err in fail[:30]:
        print(f"  {fn[:80]}: {err}")
    (OUTDIR / "_download_failures.json").write_text(
        json.dumps([{"filename": f, "error": e} for f, e in fail], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
