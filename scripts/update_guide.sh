#!/usr/bin/env bash
# Builds site/ for GitHub Pages: free.m3u plus guide.xml.gz, made from Pluto TV's guide on i.mjh.nz and
# the iptv-org grabber for the playlist's other channels (sites picked by scripts/build_channels.py).
# Usage: EPG_REPO=<iptv-org/epg checkout with npm deps> scripts/update_guide.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
EPG_REPO="${EPG_REPO:?set EPG_REPO to an iptv-org/epg checkout}"
SITE="$ROOT/site"

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
mkdir -p "$SITE" "$WORK/grabbed"

echo "== $(date -u '+%F %T') UTC start"
curl -fsSL --retry 3 -o "$WORK/pluto_all.xml.gz" https://i.mjh.nz/PlutoTV/all.xml.gz

# The grabber's channel list is rebuilt each run from the checkout's current site configs.
python3 -I "$ROOT/scripts/build_channels.py" "$ROOT/free.m3u" "$EPG_REPO/sites" "$WORK/channels.xml" "$WORK/sites"

# One grabber process per site: a site config that throws takes down only its own process, and the
# rest of the guide still gets published. Four sites run at a time.
grab_site() {
    local site; site="$(basename "$1" .channels.xml)"
    (cd "$EPG_REPO" && npm run --silent grab --- --channels="$1" --output="$2/$site.xml" \
        --days=2 --maxConnections=3 > "$2/$site.log" 2>&1) || echo "grabber failed for $site"
}
export -f grab_site
export EPG_REPO
find "$WORK/sites" -name '*.channels.xml' -print0 | xargs -0 -P 4 -I{} bash -c 'grab_site "$1" "$2"' _ {} "$WORK/grabbed"
rm -f "$WORK"/grabbed/*.log

python3 -I "$ROOT/scripts/build_epg.py" "$ROOT/free.m3u" "$WORK/pluto_all.xml.gz" "$SITE/guide.xml.gz" \
    "$WORK/channels.xml" "$WORK/grabbed"
cp "$ROOT/free.m3u" "$SITE/free.m3u"
echo "== $(date -u '+%F %T') UTC done"
