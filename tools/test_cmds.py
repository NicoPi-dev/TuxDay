#!/usr/bin/env python3
"""Exécute chaque commande de data/commands.json dans un HOME isolé et signale les échecs.

Les commandes interactives ou longues sont sautées. Pour une paire, on lance la
commande puis son inverse, et on vérifie que ~/essai_linux est revenu vide.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

LIB = Path(__file__).parent.parent / "data" / "commands.json"

SKIP = re.compile(
    r"^(man |less |watch |xdg-open|python3$|sudo |top|htop|journalctl -f|tail -f|ssh )"
    r"|input\(|read -p|cat > |http\.server|help\(|antigravity|ping |curl |nmcli device wifi"
    r"|nc -l|ncat -l|timeout 0|openssl s_client|sleep [0-9]{2}|vim? |nano "
)


def run(cmd, home):
    env = dict(os.environ, HOME=str(home), USER=os.environ.get("USER", "tux"))
    try:
        r = subprocess.run(["bash", "-c", cmd], cwd=home, env=env, stdin=subprocess.DEVNULL,
                           capture_output=True, text=True, timeout=15)
        return r.returncode, (r.stderr or r.stdout).strip().splitlines()[-1:]
    except subprocess.TimeoutExpired:
        return "timeout", []


def main(levels):
    data = json.loads(LIB.read_text())
    fails, skipped, ok = [], 0, 0
    for e in data["entries"]:
        if levels and e["level"] not in levels:
            continue
        cmds = [e["cmd"]] + ([e["inverse"]["cmd"]] if "inverse" in e else [])
        if any(SKIP.search(c) for c in cmds):
            skipped += 1
            continue
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / "essai_linux").mkdir()
            bad = None
            for c in cmds:
                code, msg = run(c, home)
                if code not in (0,) and not c.startswith(("false", "ls /inexistant;")):
                    bad = (c, code, msg)
                    break
            if not bad and "inverse" in e:
                left = list((home / "essai_linux").iterdir())
                if left:
                    bad = (e["inverse"]["cmd"], "reste", [str(p.name) for p in left])
            if bad:
                fails.append((e["id"], *bad))
            else:
                ok += 1
    print(f"OK : {ok}  sautées : {skipped}  échecs : {len(fails)}")
    for f in fails:
        print(f"- {f[0]} [{f[2]}] {f[1]}\n    {f[3]}")


if __name__ == "__main__":
    main({int(a) for a in sys.argv[1:]})
