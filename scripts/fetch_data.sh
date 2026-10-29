#!/usr/bin/env bash
# Downloads the iptv-org API dumps that build_list.py reads into data/iptv-data/.
set -euo pipefail

DATA="$(cd "$(dirname "$0")/.." && pwd)/data/iptv-data"
mkdir -p "$DATA"
for name in channels streams feeds logos blocklist categories; do
    curl -fsSL --retry 3 -o "$DATA/$name.json" "https://iptv-org.github.io/api/$name.json"
done
echo "saved to $DATA"
