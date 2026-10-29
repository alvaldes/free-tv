"""Writes the iptv-org grabber's channel list for the playlist's channels that have no Pluto TV stream
(Pluto's guide comes from i.mjh.nz instead). One site per channel, English first, then Spanish.
Usage: python3 -I build_channels.py <free.m3u> <iptv-org/epg sites dir> <out.channels.xml>"""
import glob
import re
import sys
from xml.sax.saxutils import quoteattr

M3U, SITES, OUT = sys.argv[1:4]

need, pluto, tvg = set(), set(), None
for line in open(M3U, encoding="utf-8"):
    if line.startswith("#EXTINF"):
        tvg = re.search(r'tvg-id="([^"]+)"', line).group(1)
    elif "jmp2.uk/plu-" in line:
        pluto.add(tvg)
    elif line.startswith("http"):
        need.add(tvg)
need -= pluto

RANK = {"en": 0, "es": 1}
CHANNEL = re.compile(r"<channel\s+([^>]*)>([^<]*)</channel>")
ATTR = re.compile(r'(\w+)="([^"]*)"')
best = {}
for path in sorted(glob.glob(f"{SITES}/*/*.channels.xml")):
    for m in CHANNEL.finditer(open(path, encoding="utf-8").read()):
        a = dict(ATTR.findall(m.group(1)))
        base = a.get("xmltv_id", "").split("@")[0]
        if base in need:
            rank = RANK.get(a.get("lang", ""), 2)
            if base not in best or rank < best[base][0]:
                best[base] = (rank, a, m.group(2))

lines = ['<?xml version="1.0" encoding="UTF-8"?>', "<channels>"]
for base, (_, a, name) in sorted(best.items()):
    lines.append(f'  <channel site={quoteattr(a["site"])} lang={quoteattr(a.get("lang", "en"))} '
                 f'xmltv_id={quoteattr(base)} site_id={quoteattr(a["site_id"])}>{name}</channel>')
lines.append("</channels>")
open(OUT, "w", encoding="utf-8").write("\n".join(lines) + "\n")
print(f"channels without Pluto {len(need)}, with a grabber {len(best)}")
