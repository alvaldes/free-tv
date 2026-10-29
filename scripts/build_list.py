"""Writes candidates.m3u from the iptv-org API dumps in DATA_DIR: Mexican public channels, English/Spanish
news from the US and Europe, and English/Spanish entertainment channels from anywhere, with only the
streams that answer from this network. These are candidates, not the playlist: free.m3u is curated by hand
with scripts/curate.py, which also skips the channels in data/rejected.json.
Usage: python3 -I build_list.py <data dir> <out candidates.m3u>"""
import ipaddress
import json
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlparse

DATA = Path(sys.argv[1])
OUT = Path(sys.argv[2])
EUROPE = set("AD AL AT BA BE BG BY CH CY CZ DE DK EE ES FI FO FR GB GI GR HR HU IE IS IT LI LT LU LV MC MD ME MK MT NL NO PL PT RO RS RU SE SI SK SM UA VA XK".split())
MX_CATS = {"public", "legislative", "education", "culture"}
LANGS = {"eng", "spa"}
MX_PUBLIC = {"Canal 22 Nacional", "Canal Once", "Ingenio TV", "Canal 44", "RTQ Queretaro", "SICOM Television",
             "Sistema Michoacano de TV", "Telemax", "Tele Yucatan", "Tlaxcala TV", "XHGV-TDT", "SQCS Canal 4"}
# Unlicensed restreams of cable channels; kept out on purpose.
DENY_HOSTS = ("aynaott.com", "usnlive.com", "onnethn.com", "thestream.cyou", "j00r.us", "ddns.net",
              "aynascope.net", "mangora1.cfd", "skygo.mn", "gpcdn.net", "boldmss.com", "mjunoon.tv", "anixa.tv",
              "freem3u.xyz", "workers.dev", "githubusercontent.com", "vtrplay.com")
# Checked in order: a channel lands in the first group whose categories it has.
EXTRA_GROUPS = [
    ("Movies", {"movies", "classic"}),
    ("Series", {"series", "comedy"}),
    ("Documentary & Science", {"documentary", "science"}),
    ("Kids", {"kids", "animation"}),
    ("Music", {"music"}),
    ("Travel & Lifestyle", {"travel", "lifestyle", "outdoor"}),
    ("Entertainment", {"entertainment"}),
]
SKIP_CATS = {"religious", "shop", "xxx"}
PER_CHANNEL = 2  # keep a fallback stream when one exists


def load(name):
    return json.loads((DATA / f"{name}.json").read_text())


channels = {c["id"]: c for c in load("channels")}
feeds = {(f["channel"], f["id"]): f for f in load("feeds")}
logos = {}
for l in load("logos"):
    logos.setdefault(l["channel"], l["url"])
blocked = {b["channel"] for b in load("blocklist")}


def group_for(ch, feed):
    langs = set(feed["languages"]) if feed else set()
    cats = set(ch["categories"])
    if ch["country"] == "MX" and (cats & MX_CATS or ch["name"] in MX_PUBLIC):
        return "Mexico Public"
    if not (langs & LANGS) or cats & SKIP_CATS:
        return None
    if "news" not in cats:
        return next((name for name, want in EXTRA_GROUPS if cats & want), None)
    if ch["country"] == "US":
        return "News US"
    if ch["country"] == "ES":
        return "News Spain"
    if ch["country"] in EUROPE:
        return "News Europe"
    return None


def bare_ip(url):
    try:
        ipaddress.ip_address(urlparse(url).hostname or "")
        return True
    except ValueError:
        return False


candidates = []
for s in load("streams"):
    ch = channels.get(s["channel"])
    if not ch or ch["is_nsfw"] or ch["closed"] or ch["id"] in blocked:
        continue
    if ("Geo-blocked" in s["labels"] and ch["country"] != "MX") or bare_ip(s["url"]):
        continue
    # Proxies that wrap another stream's address hide where it really comes from.
    if (urlparse(s["url"]).hostname or "").endswith(DENY_HOSTS) or "url=http" in s["url"]:
        continue
    if not s["url"].startswith(("http://", "https://")):
        continue
    feed = feeds.get((ch["id"], s["feed"])) or next((f for (c, _), f in feeds.items() if c == ch["id"] and f["is_main"]), None)
    group = group_for(ch, feed)
    if group:
        candidates.append((group, ch, feed, s))


def alive(item):
    # Free streams drop requests now and then; one retry keeps them from flickering in and out.
    return probe(item) or probe(item)


def probe(item):
    s = item[3]
    headers = {"User-Agent": s["user_agent"] or "Mozilla/5.0"}
    if s["referrer"]:
        headers["Referer"] = s["referrer"]
    try:
        with urllib.request.urlopen(urllib.request.Request(s["url"], headers=headers), timeout=8) as r:
            return r.status == 200 and r.read(512).lstrip().startswith(b"#EXTM3U")
    except Exception:
        return False


with ThreadPoolExecutor(16) as pool:
    ok = [c for c, good in zip(candidates, pool.map(alive, candidates)) if good]

ORDER = ["Mexico Public", "News US", "News Spain", "News Europe"] + [name for name, _ in EXTRA_GROUPS]
ok.sort(key=lambda x: (ORDER.index(x[0]), x[1]["name"].lower()))
kept, lines = {}, ["#EXTM3U"]
for group, ch, feed, s in ok:
    if kept.get(ch["id"], 0) >= PER_CHANNEL:
        continue
    kept[ch["id"]] = kept.get(ch["id"], 0) + 1
    attrs = f'tvg-id="{ch["id"]}" tvg-name="{ch["name"]}" group-title="{group}"'
    if ch["id"] in logos:
        attrs += f' tvg-logo="{logos[ch["id"]]}"'
    lines.append(f'#EXTINF:-1 {attrs},{s["title"]}')
    if s["user_agent"]:
        lines.append(f'#EXTVLCOPT:http-user-agent={s["user_agent"]}')
    if s["referrer"]:
        lines.append(f'#EXTVLCOPT:http-referrer={s["referrer"]}')
    lines.append(s["url"])
OUT.write_text("\n".join(lines) + "\n")

print(f"candidates {len(candidates)}, alive {len(ok)}, channels {len(kept)}")
for g in ORDER:
    names = sorted({ch["name"] for grp, ch, _, _ in ok if grp == g and ch["id"] in kept})
    print(f"\n{g} ({len(names)}): " + ", ".join(names[:25]) + (" ..." if len(names) > 25 else ""))
