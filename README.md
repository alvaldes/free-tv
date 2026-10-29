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
addresses, behind proxies, or on known restreaming hosts are left out on purpose.

The list is curated by hand: nothing joins it on its own. Channels taken out are recorded in
`data/rejected.json` with their name, group and date, so they are not offered again.

The guide covers about 70% of the channels: Pluto TV's schedule from [i.mjh.nz](https://i.mjh.nz), renamed
to the playlist's `tvg-id`s, plus the [iptv-org grabber](https://github.com/iptv-org/epg) for the rest.

## How it updates

`.github/workflows/guide.yml` runs every day at 10:00 UTC, on every push to `main`, and by hand from the
Actions tab. It rebuilds the guide for the next 36 hours and publishes `free.m3u` and `guide.xml.gz` to
GitHub Pages. The playlist itself only changes when you rebuild it.

## Adding and removing channels

Look for new channels:

```sh
scripts/fetch_data.sh                                    # iptv-org API dumps, about 25 MB
python3 -I scripts/build_list.py data/iptv-data candidates.m3u
python3 -I scripts/curate.py new candidates.m3u --out new.m3u
```

`build_list.py` keeps the streams that pass the automatic filters and answer right now, so it takes a
minute or two. `curate.py new` lists the candidates that are neither in `free.m3u` nor in
`data/rejected.json`; `new.m3u` holds just those, for a look on the TV before deciding.

Then approve or reject, by `tvg-id`:

```sh
python3 -I scripts/curate.py add candidates.m3u NewChannel.us OtherChannel.es
python3 -I scripts/curate.py reject --candidates candidates.m3u NotForUs.us   # never offer it again
python3 -I scripts/curate.py reject 13Realities.cl                            # take it out of free.m3u
```

Commit `free.m3u` and `data/rejected.json` together; the guide follows on the next run.

The grabber's sites are picked on every run by `scripts/build_channels.py`: every English or Spanish site
iptv-org has for a channel, one entry per site, and the guide takes each channel from the first of them
that returned programmes. Each site is grabbed in its own process, so a broken site only loses itself.

To build the guide locally:

```sh
git clone --depth 1 https://github.com/iptv-org/epg.git ../iptv-org-epg
(cd ../iptv-org-epg && npm ci --ignore-scripts)
EPG_REPO=../iptv-org-epg scripts/update_guide.sh        # writes site/
```
