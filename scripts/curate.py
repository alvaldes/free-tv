"""Curates free.m3u by hand. Channels you take out go to data/rejected.json so they never come back as new.

Usage:
  python3 -I curate.py new <candidates.m3u> [--out new.m3u]   candidates neither approved nor rejected
  python3 -I curate.py add <candidates.m3u> <tvg-id>...       approve: append the channels' streams to free.m3u
  python3 -I curate.py reject [--note TEXT] [--candidates <candidates.m3u>] <tvg-id>...
                                                              take channels out of free.m3u (if there) and record them
candidates.m3u comes from build_list.py."""
import json
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLAYLIST = ROOT / "free.m3u"
REJECTED = ROOT / "data" / "rejected.json"
ATTR = re.compile(r'([\w-]+)="([^"]*)"')


def read_m3u(path):
    """Returns the header line and {tvg-id: [entry lines]}, in file order; an entry runs from #EXTINF to its URL."""
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    header, entries, block = lines[0], {}, []
    for line in lines[1:]:
        if not line.strip():
            continue
        block.append(line)
        if not line.startswith("#"):
            tvg = dict(ATTR.findall(block[0]))["tvg-id"]
            entries.setdefault(tvg, []).extend(block)
            block = []
    return header, entries


def info(lines):
    attrs = dict(ATTR.findall(lines[0]))
    return attrs.get("tvg-name") or lines[0].rsplit(",", 1)[1], attrs.get("group-title")


def write_m3u(path, header, entries):
    Path(path).write_text("\n".join([header] + [l for block in entries.values() for l in block]) + "\n", encoding="utf-8")


def load_rejected():
    return json.loads(REJECTED.read_text(encoding="utf-8")) if REJECTED.exists() else {}


def take(args, flag):
    if flag in args:
        i = args.index(flag)
        value = args[i + 1]
        del args[i:i + 2]
        return value
    return None


def new(args):
    out = take(args, "--out")
    _, candidates = read_m3u(args[0])
    _, approved = read_m3u(PLAYLIST)
    rejected = load_rejected()
    fresh = {k: v for k, v in candidates.items() if k not in approved and k not in rejected}
    by_group = {}
    for tvg, lines in fresh.items():
        name, group = info(lines)
        by_group.setdefault(group, []).append((name, tvg))
    for group, items in by_group.items():
        print(f"\n{group} ({len(items)})")
        for name, tvg in sorted(items, key=lambda x: x[0].lower()):
            print(f"  {tvg:40} {name}")
    print(f"\n{len(fresh)} new of {len(candidates)} candidates")
    if out:
        write_m3u(out, "#EXTM3U", fresh)


def add(args):
    if len(args) < 2:
        sys.exit(__doc__)
    _, candidates = read_m3u(args[0])
    header, approved = read_m3u(PLAYLIST)
    rejected = load_rejected()
    for tvg in args[1:]:
        if tvg not in candidates:
            sys.exit(f"{tvg}: not in {args[0]}")
        if tvg in rejected:
            sys.exit(f"{tvg}: rejected on {rejected[tvg]['date']}; remove it from {REJECTED.name} first")
        if tvg in approved:
            sys.exit(f"{tvg}: already in {PLAYLIST.name}")
        approved[tvg] = candidates[tvg]
    write_m3u(PLAYLIST, header, approved)
    print(f"added {len(args) - 1}; {PLAYLIST.name} has {len(approved)} channels")


def reject(args):
    note = take(args, "--note") or "removed by hand"
    path = take(args, "--candidates")
    if not args:
        sys.exit(__doc__)
    candidates = read_m3u(path)[1] if path else {}
    header, approved = read_m3u(PLAYLIST)
    rejected = load_rejected()
    for tvg in args:
        lines = approved.pop(tvg, None) or candidates.get(tvg)
        if lines is None:
            sys.exit(f"{tvg}: not in {PLAYLIST.name}" + (f" or {path}" if path else "; pass --candidates to reject a candidate"))
        name, group = info(lines)
        rejected[tvg] = {"name": name, "group": group, "date": date.today().isoformat(), "note": note}
    write_m3u(PLAYLIST, header, approved)
    REJECTED.write_text(json.dumps(dict(sorted(rejected.items())), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"rejected {len(args)}; {PLAYLIST.name} has {len(approved)} channels, {REJECTED.name} has {len(rejected)}")


COMMANDS = {"new": new, "add": add, "reject": reject}
if len(sys.argv) < 3 or sys.argv[1] not in COMMANDS:
    sys.exit(__doc__)
args = sys.argv[2:]
COMMANDS[sys.argv[1]](args)
