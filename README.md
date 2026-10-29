# free-tv

A hand-picked M3U playlist of free, publicly available channels in English and Spanish, with an XMLTV
guide rebuilt every day. Made for [TV Hub](https://github.com/Gathin23/cleanyourtv/tree/main/addons/tv-hub),
but any player that reads M3U and XMLTV works.

| File | Address |
| :- | :- |
| Playlist | `https://alvaldes.github.io/free-tv/free.m3u` |
| Guide | `https://alvaldes.github.io/free-tv/guide.xml.gz` (named in the playlist header, so most players find it) |

## What is in it

Mexican public channels, English and Spanish news from the US, Spain and the rest of Europe, and movies,
series, documentaries, kids, music, travel and entertainment channels. Streams come from
[iptv-org](https://github.com/iptv-org/iptv), checked to answer when the list was built. Streams on bare IP
addresses, behind proxies, or on known restreaming hosts are left out on purpose. Kids, Travel & Lifestyle
and Music are trimmed to the channels listed in `scripts/build_list.py`.

The guide covers about 70% of the channels: Pluto TV's schedule from [i.mjh.nz](https://i.mjh.nz), renamed
to the playlist's `tvg-id`s, plus the [iptv-org grabber](https://github.com/iptv-org/epg) for the rest.

## How it updates

`.github/workflows/guide.yml` runs every day at 10:00 UTC, on every push to `main`, and by hand from the
Actions tab. It rebuilds the guide for the next 36 hours and publishes `free.m3u` and `guide.xml.gz` to
GitHub Pages. The playlist itself only changes when you rebuild it.

## Rebuilding the playlist

```sh
scripts/fetch_data.sh                                    # iptv-org API dumps, about 50 MB
python3 -I scripts/build_list.py data/iptv-data free.m3u https://alvaldes.github.io/free-tv/guide.xml.gz
git clone --depth 1 https://github.com/iptv-org/epg.git ../iptv-org-epg
python3 -I scripts/build_channels.py free.m3u ../iptv-org-epg/sites data/custom.channels.xml
```

`build_list.py` checks every stream, so it takes a minute or two and the result varies a little between
runs as free streams come and go. Channel numbers on the TV shift after each rebuild. Commit `free.m3u`
and `data/custom.channels.xml` together.

To build the guide locally: `(cd ../iptv-org-epg && npm ci --ignore-scripts)`, then
`EPG_REPO=../iptv-org-epg scripts/update_guide.sh`, which writes `site/`.
