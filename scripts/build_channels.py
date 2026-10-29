"""Writes the iptv-org grabber's channel list for the playlist's channels that have no Pluto TV stream
(Pluto's guide comes from i.mjh.nz instead), English sites first, then Spanish. With a split dir it also
writes one <site>.channels.xml per site there, so each site can be grabbed in its own process.
Usage: python3 -I build_channels.py <free.m3u> <iptv-org/epg sites dir> <out.channels.xml> [<split dir>]"""
import glob
import re
import sys
from pathlib import Path
from xml.sax.saxutils import quoteattr

M3U, SITES, OUT = sys.argv[1:4]
SPLIT = Path(sys.argv[4]) if len(sys.argv) > 4 else None

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
found = {}
for path in sorted(glob.glob(f"{SITES}/*/*.channels.xml")):
    for m in CHANNEL.finditer(open(path, encoding="utf-8").read()):
        a = dict(ATTR.findall(m.group(1)))
        base = a.get("xmltv_id", "").split("@")[0]
        if base in need:
            found.setdefault(base, {})[(a["site"], a["site_id"])] = (RANK.get(a.get("lang", ""), 2), a, m.group(2))

# Every English or Spanish site for a channel (any language when it has neither), in order of preference:
# sites go down often, so build_epg.py takes each channel from the first site in this order whose guide
# came back with programmes. One entry per site: the grabber files every entry of a site under the same
# xmltv_id, so two feeds of one site (Plex regions, CNN International's regional feeds) would mix schedules.
HEAD, TAIL = '<?xml version="1.0" encoding="UTF-8"?>\n<channels>\n', "</channels>\n"
lines, by_site = [], {}
for base, cands in sorted(found.items()):
    top = min(rank for rank, _, _ in cands.values())
    sites = set()
    for rank, a, name in sorted(cands.values(), key=lambda c: (c[0], c[1]["site"], c[1]["site_id"])):
        if rank <= max(top, 1) and a["site"] not in sites:
            sites.add(a["site"])
            line = (f'  <channel site={quoteattr(a["site"])} lang={quoteattr(a.get("lang", "en"))} '
                    f'xmltv_id={quoteattr(base)} site_id={quoteattr(a["site_id"])}>{name}</channel>\n')
            lines.append(line)
            by_site.setdefault(a["site"], []).append(line)
open(OUT, "w", encoding="utf-8").write(HEAD + "".join(lines) + TAIL)
if SPLIT:
    SPLIT.mkdir(parents=True, exist_ok=True)
    for site, site_lines in by_site.items():
        (SPLIT / f"{site}.channels.xml").write_text(HEAD + "".join(site_lines) + TAIL, encoding="utf-8")
print(f"channels without Pluto {len(need)}, with a grabber {len(found)}, entries {len(lines)}, sites {len(by_site)}")
