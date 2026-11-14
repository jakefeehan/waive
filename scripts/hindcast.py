"""One-off: pull the CDIP nowcast for the last 40 days at each break, to compare with the old size formula."""
import json, sys, time
sys.path.insert(0, "scripts")
import fetch_feeds as F
meta = F.mop_meta("D0400")
out = {}
for key, site in F.SITES.items():
    n = F.mop_len(site, "nowcast")
    d = F.parse_ascii(F.get(F.MOP + "%s_nowcast.nc.ascii?waveTime[%d:1:%d]" % (site, n - 3, n - 1)))
    print(key, site, n, d["waveTime"])
    rows = F.mop_rows(site, "nowcast", "[%d:1:%d]" % (n - 40 * 24, n - 1), meta)
    out[key] = rows
    print(key, len(rows), rows[0], rows[-1])
json.dump(out, open("data/hindcast.json", "w"), separators=(",", ":"))
