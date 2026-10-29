#!/usr/bin/env bash
# Builds site/ for GitHub Pages: free.m3u plus guide.xml.gz, made from Pluto TV's guide on i.mjh.nz and
# the iptv-org grabber for the channels in data/custom.channels.xml.
# Usage: EPG_REPO=<iptv-org/epg checkout with npm deps> scripts/update_guide.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
EPG_REPO="${EPG_REPO:?set EPG_REPO to an iptv-org/epg checkout}"
SITE="$ROOT/site"

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
mkdir -p "$SITE"

echo "== $(date -u '+%F %T') UTC start"
curl -fsSL --retry 3 -o "$WORK/pluto_all.xml.gz" https://i.mjh.nz/PlutoTV/all.xml.gz

# A failed grab still leaves the Pluto part worth publishing.
(cd "$EPG_REPO" && npm run grab --- --channels="$ROOT/data/custom.channels.xml" \
    --output="$WORK/grabbed.xml" --days=2 --maxConnections=5) || echo "grabber failed; publishing Pluto only"

extra=()
[[ -s "$WORK/grabbed.xml" ]] && extra=("$WORK/grabbed.xml")
python3 -I "$ROOT/scripts/build_epg.py" "$ROOT/free.m3u" "$WORK/pluto_all.xml.gz" "$SITE/guide.xml.gz" "${extra[@]}"
cp "$ROOT/free.m3u" "$SITE/free.m3u"
echo "== $(date -u '+%F %T') UTC done"
