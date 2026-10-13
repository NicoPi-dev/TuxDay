#!/usr/bin/env python3
"""Assemble les fichiers tools/src/*.txt en data/commands.json et contrôle la cohérence."""
import json
import re
import sys
from collections import Counter
from pathlib import Path

SRC = Path(__file__).parent / "src"
OUT = Path(__file__).parent.parent / "data" / "commands.json"

FIELDS = {"CMD", "TH", "FR", "EN", "INV", "IFR", "IEN", "REQ"}

# Outils absents de certaines distributions ou installations.
# Nom unique : une simple recherche suffit, sans risque de faux positif.
UNIQUE_TOOLS = [
    "nvidia-smi", "notify-send", "powerprofilesctl", "kreadconfig6", "firewall-cmd",
    "getenforce", "sestatus", "ausearch", "smartctl", "flatpak", "podman", "toolbox",
    "strace", "zstd", "tracepath", "resolvectl", "nmcli", "upower", "xdg-open",
    "xdg-mime", "xdg-settings", "xdg-user-dir", "ssh-keygen", "gpg", "openssl",
    "coredumpctl", "udevadm", "lspci", "lsusb", "crontab", "dnf", "rpm", "hexdump",
    "pstree", "zramctl", "whatis", "btrfs", "systemctl", "journalctl", "systemd-analyze",
    "systemd-run", "systemd-cgls", "systemd-cgtop", "systemd-detect-virt", "systemd-path",
    "loginctl", "timedatectl", "hostnamectl", "localectl", "busctl", "getfacl", "column",
    "parallel", "lsof", "taskset", "chrt", "ionice", "numfmt", "iconv", "csplit",
]
# Nom court : on ne le compte que là où une commande commence.
SHORT_TOOLS = ["ip", "ss", "git", "cal", "man", "bc", "ping", "curl", "perf", "script", "ssh", "sudo", "watch"]
CMD_START = r"(?:^|[|;&({]\s*|\$\(\s*|sudo\s+|-exec\s+|time\s+|nice\s+-n\s+\d+\s+|timeout\s+\d+\s+|stdbuf\s+\S+\s+)"
PY_LIST = r"[\[(]['\"]"
PATHS = {
    r"/sys/class/power_supply/BAT": "path:/sys/class/power_supply/BAT*",
    r"nvme0n1": "path:/dev/nvme0n1",
    r"thermal_zone": "path:/sys/class/thermal/thermal_zone0",
    r"/etc/fedora-release": "path:/etc/fedora-release",
    r"/etc/pki/": "path:/etc/pki/tls/certs/ca-bundle.crt",
    r"/usr/lib64/python3": "path:/usr/lib64/python3*",
    r"org\.kde\.konsole\.desktop": "path:/usr/share/applications/org.kde.konsole.desktop",
    r"kwinrc": "path:~/.config/kwinrc",
    r"sshd\.service|show sshd": "path:/usr/lib/systemd/system/sshd.service",
    r"security\.selinux|/sys/kernel/security": "path:/sys/fs/selinux",
    r"cpufreq": "path:/sys/devices/system/cpu/cpu0/cpufreq",
    r"/sys/class/dmi": "path:/sys/class/dmi/id",
    r"/sys/class/hwmon": "path:/sys/class/hwmon",
}
PY_MODULES = {"tkinter": "py:tkinter", "turtle": "py:tkinter"}


def detect_requires(*cmds):
    req = set()
    for c in cmds:
        for t in UNIQUE_TOOLS:
            if re.search(rf"(?<![\w./-]){re.escape(t)}(?![\w-])", c):
                req.add(t)
        for t in SHORT_TOOLS:
            if re.search(CMD_START + re.escape(t) + r"(?![\w.-])", c) or re.search(PY_LIST + re.escape(t) + r"['\"]", c):
                req.add(t)
        for pat, r in PATHS.items():
            if re.search(pat, c):
                req.add(r)
        for mod, r in PY_MODULES.items():
            if re.search(rf"import {mod}\b", c):
                req.add(r)
    req.discard("sudo")  # présent partout ; on garde sudo hors des prérequis
    return sorted(req)


def parse(path):
    level = typ = None
    entries, cur = [], None
    for n, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.rstrip()
        if not line:
            continue
        if line.startswith("@level"):
            level = int(line.split()[1]); continue
        if line.startswith("@type"):
            typ = line.split()[1]; continue
        key, _, val = line.partition(" ")
        if key not in FIELDS:
            sys.exit(f"{path.name}:{n}: champ inconnu {key!r}")
        if key == "CMD":
            cur = {"level": level, "type": typ, "src": f"{path.name}:{n}"}
            entries.append(cur)
        if cur is None:
            sys.exit(f"{path.name}:{n}: champ hors entrée")
        if key in cur:
            sys.exit(f"{path.name}:{n}: champ {key} en double")
        cur[key] = val.strip()
    return entries


def main():
    raw = []
    for p in sorted(SRC.glob("*.txt")):
        raw += parse(p)

    errors = []
    for e in raw:
        for k in ("CMD", "TH", "FR", "EN"):
            if not e.get(k):
                errors.append(f"{e['src']}: {k} manquant")
        has_inv = [k in e for k in ("INV", "IFR", "IEN")]
        if any(has_inv) and not all(has_inv):
            errors.append(f"{e['src']}: inverse incomplet")
        for k in ("FR", "EN", "IFR", "IEN"):
            if k in e and e[k].count("`") % 2:
                errors.append(f"{e['src']}: backtick impair dans {k}")

    dup = [c for c, n in Counter(e["CMD"] for e in raw).items() if n > 1]
    for c in dup:
        errors.append(f"commande en double : {c}")

    entries = []
    counters = Counter()
    for e in raw:
        key = (e["level"], e["type"])
        counters[key] += 1
        item = {
            "id": f"n{e['level']}-{'sh' if e['type'] == 'shell' else 'py'}-{counters[key]:03d}",
            "level": e["level"],
            "type": e["type"],
            "theme": e["TH"],
            "cmd": e["CMD"],
            "explain": {"fr": e["FR"], "en": e["EN"]},
        }
        if "INV" in e:
            item["inverse"] = {"cmd": e["INV"], "explain": {"fr": e["IFR"], "en": e["IEN"]}}
        req = set(detect_requires(e["CMD"], e.get("INV", "")))
        req |= set(e.get("REQ", "").split())
        if req:
            item["requires"] = sorted(req)
        entries.append(item)

    print("Répartition :")
    for lvl in (1, 2, 3, 4):
        sh, py = counters[(lvl, "shell")], counters[(lvl, "python")]
        print(f"  niveau {lvl} : {sh:3d} shell + {py:3d} python = {sh + py}")
    print(f"  total : {len(entries)}  (dont {sum('inverse' in e for e in entries)} paires)")

    if errors:
        print(f"\n{len(errors)} erreur(s) :")
        for err in errors:
            print("  -", err)
        sys.exit(1)

    data = {
        "version": 2,
        "name": "TuxDay",
        "license": "MIT",
        "langs": ["fr", "en"],
        "sandbox": "~/essai_linux",
        "levels": {
            "1": {"fr": "débutant", "en": "beginner"},
            "2": {"fr": "intermédiaire", "en": "intermediate"},
            "3": {"fr": "avancé", "en": "advanced"},
            "4": {"fr": "expert", "en": "expert"},
        },
        "entries": entries,
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nÉcrit : {OUT.name} ({OUT.stat().st_size // 1024} Ko)")


if __name__ == "__main__":
    main()
