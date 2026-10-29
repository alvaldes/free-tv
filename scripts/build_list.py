"""Builds free.m3u from the iptv-org API dumps in DATA_DIR: Mexican public channels plus
English/Spanish news from the US and Europe, plus English/Spanish
entertainment channels from anywhere. Only streams that answer from this network are kept.
Usage: python3 -I build_list.py <data dir> <out.m3u> [guide url]"""
import ipaddress
import json
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlparse

DATA = Path(sys.argv[1])
OUT = Path(sys.argv[2])
GUIDE = sys.argv[3] if len(sys.argv) > 3 else None
EUROPE = set("AD AL AT BA BE BG BY CH CY CZ DE DK EE ES FI FO FR GB GI GR HR HU IE IS IT LI LT LU LV MC MD ME MK MT NL NO PL PT RO RS RU SE SI SK SM UA VA XK".split())
MX_CATS = {"public", "legislative", "education", "culture"}
LANGS = {"eng", "spa"}
MX_PUBLIC = {"Canal 22 Nacional", "Canal Once", "Ingenio TV", "Canal 44", "RTQ Queretaro", "SICOM Television",
             "Sistema Michoacano de TV", "Telemax", "Tele Yucatan", "Tlaxcala TV", "XHGV-TDT", "SQCS Canal 4"}
MX_SKIP = {"Presumiendo Mexico", "GikTVMX"}
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
# Kids is trimmed to these name prefixes (picked by hand on the TV).
KIDS_KEEP = ("ABC Entertains", "Avatar", "Forever Kids", "Las Tortugas Ninja", "Nickelodeon", "Pluto TV", "Smurf TV",
             "Tom And Jerry", "Toonami", "Tortues Ninja", "Totally Turtles")
# Travel & Lifestyle is trimmed to these channel ids (picked by hand on the TV).
TRAVEL_KEEP = {
    "AKCTVPuppies.us", "AntiquesRoadTrip.us", "ArubaTV.aw", "AspireTVLife.us", "BeachTVFloridaAlabama.us",
    "BeachTVKeyWestFloridaKeys.us", "BeachTVMyrtleBeachTheGrandStrand.us", "BetterHealthTV.us", "BizTV.us",
    "DroneTV.us", "DuckHuntingTV.us", "ElMueble.es", "FashionLifeStyle.ru", "FashionTV.ua", "FashionTVSecrets.fr",
    "FunRoads.us", "HGTV.au", "HGTV.be", "HGTV.ca", "HGTV.cz", "HGTV.de", "HGTV.hu", "HGTV.ie", "HGTV.it",
    "HGTV.nl", "HGTV.nz", "HGTV.pl", "HGTV.ru", "HGTV.tw", "HGTV.uk", "HGTV.us", "HobbyMaker.uk",
    "HorseCountryTV.uk", "INFAST.nl", "INTRAVEL.nl", "InTrouble.nl", "KNOVCD411.us", "KaloopyTV.us", "Localish.us",
    "LoveNature.ca", "LuxembourgGlobalRadioTV.lu", "MonsterJam.us", "MyDestinationTV.us", "NBCLX.us",
    "NBCLXHome.us", "Okhotairybalka.ru", "OutdoorAmerica.us", "OutdoorChannel.us", "OutsideTV.us",
    "PalmBeachesTV.us", "PeerTVSouthTyrol.it", "PlousTV.ve", "PlutoTVDiseno.de", "PlutoTVEstilodeVida.us",
    "PoconoTelevisionNetwork.us", "PursuitUP.us", "RedBullTV.at", "SpaceLivepoweredbysen.uk", "SpikeOutdoors.us",
    "SuperyachtTV.mc", "TVSTravelNetwork.us", "Teletur.do", "TheDesignNetwork.us", "TheJamieOliverChannel.us",
    "TravelPlusAdventure.ru", "WaypointTV.us", "YachtingTV.cz"
}
# Music is trimmed to these channel ids (picked by hand on the TV).
MUSIC_KEEP = {
    "ActivaTV.es", "AfrobeatTVEntertainment.uk", "BTATV.ve", "BestofDanceTV.ee", "CKNOFM.ca",
    "CMCUSACountryMusicChannel.us", "ClubbingTV.us", "ConcertChannel.us", "DanceFM.cl", "DanceTVAlgorhythm.ee",
    "DanceTVDeepHouseDistrict.ee", "DanceTVHouseFloor.ee", "DanceTVTechnoWarehouse.ee", "DeluxeDance.de",
    "DeluxeRap.de", "HappyRadioTV.ua", "HeartRadioAruba.aw", "MTVBiggestPop.us", "MTVClassic.us",
    "MTVFlowLatino.us", "MTVSpankinNew.us", "MezzoLive.fr", "MovieMusicbyStingray.ca", "Now70s.uk", "Now80s.uk",
    "Now90s00s.uk", "POPWorldTV.es", "RadioRumbaTV.pe", "RetromusicaTelevision.cl", "SpektraTV.es",
    "StingrayCityscapes.ca", "StingrayClassicRock.ca", "StingrayClassica.ca", "StingrayCozyCafe.ca",
    "StingrayDJAZZ.ca", "StingrayEasyListening.ca", "StingrayEverything80s.ca", "StingrayFlashback70s.ca",
    "StingrayGreatestHits.ca", "StingrayGreatestHolidayHits.us", "StingrayHitList.ca", "StingrayHolidayHits.ca",
    "StingrayHolidayscapes.ca", "StingrayHotCountry.ca", "StingrayJukeboxOldies.ca", "StingrayKaraoke.ca",
    "StingrayNaturescape.ca", "StingrayNothinBut90s.ca", "StingrayPopAdult.ca", "StingrayRememberthe80s.ca",
    "StingrayRockAlternative.ca", "StingrayRomanceLatino.ca", "StingraySmoothJazz.ca", "StingraySoulStorm.ca",
    "StingrayTheSpa.ca", "StingrayTikTokRadio.ca", "StingrayTodaysLatinPop.ca", "StingrayiConcerts.ca",
    "Thats70s.uk", "Thats80s.uk", "TheCountryNetwork.us", "Totalmusic.uk", "Totalmusic2000s.uk", "Totalmusic80s.uk",
    "V2BEATTV.uk", "Vevo2K.us", "Vevo70s.us", "Vevo80s.us", "Vevo90s.us", "VevoCountry.us", "VevoHipHop.us",
    "VevoLatino.us", "VevoPop.us", "VevoRB.us", "VevoRetroRock.us", "VevoTrueSchoolHipHop.us",
    "XITE90sThrowback.us", "XITEHits.nl", "XITEJustChill.nl", "YoMTV.us"
}
# Channels removed by hand, by channel id; they stay out of every group.
EXCLUDE = {
    "13Realities.cl", "13T.cl", "1KZNTV.za", "30AGeorgiaHollywoodReview.us", "30ALionelNation.us",
    "30ALoomeredTV.us", "30ARidiculousTV.us", "30ASidewalks.us", "30ATVClassicMovies.us", "30ATelevisionChannel.us",
    "88Stereo.cr", "ABCNewsLive1.us", "ABCNewsLive10.us", "ABCNewsLive2.us", "ABCNewsLive3.us", "ABCNewsLive4.us",
    "ABCNewsLive5.us", "ABCNewsLive6.us", "ABCNewsLive7.us", "ABCNewsLive8.us", "ABCNewsLive9.us",
    "ANCTelevision.co", "AbejalesTV.ve", "AlloCine.cm", "Anaylos7.us", "AsianCrush.us", "Backstage.us", "WPLG101.us"
}
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
    if ch["country"] == "MX" and ch["name"] not in MX_SKIP and (cats & MX_CATS or ch["name"] in MX_PUBLIC):
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
    if not ch or ch["is_nsfw"] or ch["closed"] or ch["id"] in blocked or ch["id"] in EXCLUDE:
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
    if group == "Kids" and not ch["name"].startswith(KIDS_KEEP):
        continue
    if group == "Travel & Lifestyle" and ch["id"] not in TRAVEL_KEEP:
        continue
    if group == "Music" and ch["id"] not in MUSIC_KEEP:
        continue
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
kept, lines = {}, [f'#EXTM3U x-tvg-url="{GUIDE}"' if GUIDE else "#EXTM3U"]
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
