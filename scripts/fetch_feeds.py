"""Hourly job: gathers the free measurements and nearshore wave predictions the site can't fetch from a browser.

Writes data/feeds.json with:
  buoys - latest reading from three CDIP/NDBC buoys, with the swell and wind-wave parts NDBC separates out
  cdip  - CDIP's MOP nearshore wave model (UC San Diego / Scripps), one point in 10 m of water off each break:
          the last measured-driven "nowcast" and the forecast, split into groundswell, windswell and chop
Each part is fetched on its own, and if one fails the last good copy of that part is kept.
Only the Python standard library is used.
"""
import json, math, re, sys, time, urllib.request

UA = {"User-Agent": "waive (github.com/jakefeehan/waive)"}
OUT = "data/feeds.json"
BUOYS = {"46254": "Scripps Nearshore", "46225": "Torrey Pines Outer", "46258": "Mission Bay West"}
# CDIP MOP points (about every 100 m along the coast, in 10 m of water). Picked by latitude to sit straight off each break.
SITES = {"tourmaline": "D0424", "law": "D0422", "diamond": "D0413", "crystal": "D0408", "pbdrive": "D0400"}
MOP = "https://thredds.cdip.ucsd.edu/thredds/dodsC/cdip/model/MOP_alongshore/"
# Wave-period bands: groundswell 12 s and longer, windswell 7 to 12 s, chop shorter than 7 s.
F_GROUND, F_CHOP = 0.0825, 0.145
COMPASS = {n: i * 22.5 for i, n in enumerate("N NNE NE ENE E ESE SE SSE S SSW SW WSW W WNW NW NNW".split())}


def get(url, timeout=60):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def parse_ascii(text):
    """Parse an OPeNDAP .ascii reply into {name: list} (2-D arrays become a list of rows)."""
    out, name, rows, two_d = {}, None, [], False
    body = text.split("---------------------------------------------", 1)[-1]
    for line in body.splitlines():
        line = line.strip()
        m = re.match(r"^([\w.]+?)(\[\d+\])+$", line)
        if m:
            name, two_d = m.group(1), line.count("[") > 1
            out[name] = rows = []
        elif line and name:
            if two_d:
                rows.append([float(v) for v in line.split(",")[1:]])
            else:
                rows.extend(float(v) for v in line.split(","))
    return out


def bands(freq, bw, energy):
    """Split one spectrum into groundswell, windswell and chop: height (m) of each and the peak period of the two swells."""
    g = w = c = 0.0
    gp = wp = None
    gmax = wmax = 0.0
    for f, b, e in zip(freq, bw, energy):
        if e < 0:
            continue
        if f <= F_GROUND:
            g += e * b
            if e > gmax:
                gmax, gp = e, 1 / f
        elif f <= F_CHOP:
            w += e * b
            if e > wmax:
                wmax, wp = e, 1 / f
        else:
            c += e * b
    r = lambda v: round(4 * math.sqrt(v), 3)
    return [r(g), round(gp, 1) if gp else None, r(w), round(wp, 1) if wp else None, r(c)]


def clean(v, nd=3):
    return None if v is None or v < -900 else round(v, nd)


def mop_rows(site, kind, sel, meta):
    """Rows [time, hs, tp, dp, ground hs, ground period, windswell hs, windswell period, chop hs] for one MOP point."""
    q = "waveTime%s,waveHs%s,waveTp%s,waveDp%s,waveEnergyDensity%s" % (sel, sel, sel, sel, sel)
    d = parse_ascii(get(MOP + "%s_%s.nc.ascii?%s" % (site, kind, q)))
    rows = []
    for i, t in enumerate(d["waveTime"]):
        hs = clean(d["waveHs"][i])
        if hs is None:
            continue
        rows.append([int(t), hs, clean(d["waveTp"][i], 1), clean(d["waveDp"][i], 0)] + bands(meta["f"], meta["bw"], d["waveEnergyDensity.waveEnergyDensity"][i]))
    return rows


def mop_meta(site):
    d = parse_ascii(get(MOP + site + "_forecast.nc.ascii?waveFrequency,waveBandwidth"))
    return {"f": d["waveFrequency"], "bw": d["waveBandwidth"]}


def mop_len(site, kind):
    return int(re.search(r"waveTime = (\d+)", get(MOP + "%s_%s.nc.dds" % (site, kind))).group(1))


def fetch_cdip(now):
    meta = mop_meta(next(iter(SITES.values())))
    spots = {}
    for key, site in SITES.items():
        n = mop_len(site, "nowcast")
        nowc = mop_rows(site, "nowcast", "[%d:1:%d]" % (n - 6, n - 1), meta)
        fc = [r for r in mop_rows(site, "forecast", "", meta) if r[0] >= now - 4 * 3600]
        spots[key] = {"site": site, "now": nowc[-1] if nowc else None, "fc": fc}
    return {"made": now, "cols": ["t", "hs", "tp", "dp", "ground", "groundP", "wind", "windP", "chop"], "spots": spots}


def fetch_buoy(bid):
    num = lambda v: None if v == "MM" else float(v)
    out = {"name": BUOYS[bid]}
    for line in get("https://www.ndbc.noaa.gov/data/realtime2/%s.txt" % bid).splitlines():
        c = line.split()
        if line.startswith("#") or len(c) < 15:
            continue
        stamp = "%s-%s-%sT%s:%s:00Z" % tuple(c[:5])
        if "t" not in out and c[8] != "MM":
            out.update({"t": stamp, "hs": num(c[8]), "dpd": num(c[9]), "mwd": num(c[11])})
        if "wtmpT" not in out and c[14] != "MM":
            out.update({"wtmpC": num(c[14]), "wtmpT": stamp})
        if "t" in out and "wtmpT" in out:
            break
    try:
        for line in get("https://www.ndbc.noaa.gov/data/realtime2/%s.spec" % bid).splitlines():
            c = line.split()
            if line.startswith("#") or len(c) < 15 or c[6] == "MM":
                continue
            out["parts"] = {"t": "%s-%s-%sT%s:%s:00Z" % tuple(c[:5]), "swH": num(c[6]), "swP": num(c[7]), "wwH": num(c[8]), "wwP": num(c[9]),
                            "swD": COMPASS.get(c[10]), "wwD": COMPASS.get(c[11])}
            break
    except Exception as e:
        print("spec failed", bid, e)
    if "t" not in out:
        raise ValueError("no rows")
    return out


def main():
    now = int(time.time())
    try:
        feeds = json.load(open(OUT))
    except Exception:
        feeds = {}
    feeds.setdefault("buoys", {})
    for bid in BUOYS:
        try:
            feeds["buoys"][bid] = fetch_buoy(bid)
        except Exception as e:
            print("buoy failed", bid, e)
    try:
        feeds["cdip"] = fetch_cdip(now)
    except Exception as e:
        print("cdip failed", e)
    feeds["made"] = now
    with open(OUT, "w") as f:
        json.dump(feeds, f, separators=(",", ":"))
    print("buoys", list(feeds["buoys"]), "cdip", {k: len(v["fc"]) for k, v in feeds.get("cdip", {}).get("spots", {}).items()})


if __name__ == "__main__":
    main()
