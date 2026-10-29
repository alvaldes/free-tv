"""Builds guide.xml.gz for free.m3u from Matt Huisman's Pluto TV guide, renaming Pluto channel ids
to the playlist's tvg-ids so favourites and merging keep working.
Usage: python3 -I build_epg.py <free.m3u> <pluto_all.xml.gz> <out guide.xml.gz> [grabbed.xml ...]"""
import gzip
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

M3U, PLUTO, OUT = sys.argv[1:4]
EXTRA = sys.argv[4:]
HORIZON = timedelta(hours=36)  # keep the file small for the TV

# One Pluto channel per tvg-id: a channel with two Pluto streams would otherwise get two overlapping schedules.
tvg_to_pluto = {}
tvg = None
for line in open(M3U, encoding="utf-8"):
    if line.startswith("#EXTINF"):
        tvg = re.search(r'tvg-id="([^"]+)"', line).group(1)
    else:
        m = re.search(r"jmp2\.uk/plu-(\w+)\.m3u8", line)
        if m and tvg:
            tvg_to_pluto.setdefault(tvg, m.group(1))
pluto_to_tvg = {}
for t, p in tvg_to_pluto.items():
    pluto_to_tvg.setdefault(p, t)
pluto_ids = set(pluto_to_tvg.values())


def start_of(p):
    return datetime.strptime(p.get("start")[:14], "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc) - offset(p.get("start"))


def offset(stamp):
    tz = stamp[15:].strip()
    if not tz:
        return timedelta(0)
    sign = 1 if tz[0] == "+" else -1
    return sign * timedelta(hours=int(tz[1:3]), minutes=int(tz[3:5]))


limit = datetime.now(timezone.utc) + HORIZON
channels = programmes = 0
seen = set()
with gzip.open(OUT, "wt", encoding="utf-8") as out:
    out.write('<?xml version="1.0" encoding="UTF-8"?>\n<tv generator-info-name="free.m3u guide (from i.mjh.nz)">\n')
    for _, el in ET.iterparse(gzip.open(PLUTO), events=("end",)):
        if el.tag == "channel":
            new = pluto_to_tvg.get(el.get("id"))
            if new and new not in seen:
                seen.add(new)
                el.set("id", new)
                out.write(ET.tostring(el, encoding="unicode"))
                channels += 1
            el.clear()
        elif el.tag == "programme":
            new = pluto_to_tvg.get(el.get("channel"))
            if new and start_of(el) < limit:
                el.set("channel", new)
                out.write(ET.tostring(el, encoding="unicode"))
                programmes += 1
            el.clear()
    # Guides from the iptv-org grabber already use the playlist's ids; Pluto's schedule wins on overlap.
    for extra in EXTRA:
        for _, el in ET.iterparse(extra, events=("end",)):
            target = el.get("id") if el.tag == "channel" else el.get("channel") if el.tag == "programme" else None
            if target and target not in pluto_ids:
                if el.tag == "channel" and target not in seen:
                    seen.add(target)
                    out.write(ET.tostring(el, encoding="unicode"))
                    channels += 1
                elif el.tag == "programme" and start_of(el) < limit:
                    out.write(ET.tostring(el, encoding="unicode"))
                    programmes += 1
            if el.tag in ("channel", "programme"):
                el.clear()
    out.write("</tv>\n")
print(f"channels {channels}, programmes {programmes}")
