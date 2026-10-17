"""Daily job for the accuracy scorecard.

1. Saves today's wave forecast (Open-Meteo Marine, same source the site uses) to data/forecast-log.json.
2. Saves what the Torrey Pines buoy (NDBC 46225) actually measured, hour by hour, to data/observed.json.
The website compares the two in the browser. Only the Python standard library is used.
"""
import json, os, time, urllib.request
from datetime import datetime, timezone

UA = {"User-Agent": "waive (github.com/jakefeehan/waive)"}
KEEP_DAYS = 40
MARINE = ("https://marine-api.open-meteo.com/v1/marine?latitude=32.80&longitude=-117.28"
          "&hourly=wave_height,swell_wave_height,swell_wave_period,swell_wave_direction"
          "&timeformat=unixtime&timezone=GMT&forecast_days=4")
BUOY = "https://www.ndbc.noaa.gov/data/realtime2/46225.txt"


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return r.read().decode()


def load(path, default):
    try:
        return json.load(open(path))
    except Exception:
        return default


def save(path, obj):
    with open(path, "w") as f:
        json.dump(obj, f, separators=(",", ":"))


now = int(time.time())
cutoff = now - KEEP_DAYS * 86400

# 1. forecast snapshot: every 3 hours for the next 72 hours: [time, wave height m, swell height m, swell period s, swell direction deg]
h = json.loads(get(MARINE))["hourly"]
rows = []
for i, t in enumerate(h["time"]):
    if t < now or t > now + 72 * 3600 or (t // 3600) % 3:
        continue
    wave = h["wave_height"][i]
    if wave is None:
        continue
    rows.append([t, wave, h["swell_wave_height"][i], h["swell_wave_period"][i], h["swell_wave_direction"][i]])
day = datetime.fromtimestamp(now, timezone.utc).strftime("%Y-%m-%d")
log = load("data/forecast-log.json", {"snapshots": []})
snaps = [s for s in log["snapshots"] if s["day"] != day and s["issued"] >= cutoff]
if rows:
    snaps.append({"day": day, "issued": now, "hours": rows})
save("data/forecast-log.json", {"snapshots": snaps})

# 2. buoy observations, one per hour (the reading closest to the top of the hour)
best = {}
for line in get(BUOY).splitlines():
    if line.startswith("#") or not line.strip():
        continue
    c = line.split()
    if c[8] == "MM":
        continue
    t = int(datetime(int(c[0]), int(c[1]), int(c[2]), int(c[3]), int(c[4]), tzinfo=timezone.utc).timestamp())
    hour = round(t / 3600) * 3600
    n = lambda v: None if v == "MM" else float(v)
    if hour not in best or abs(t - hour) < best[hour][0]:
        best[hour] = (abs(t - hour), [hour, n(c[8]), n(c[9]), n(c[11])])
obs = {o[0]: o for o in load("data/observed.json", {"obs": []})["obs"] if o[0] >= cutoff}
for hour, (_, row) in best.items():
    obs[hour] = row
save("data/observed.json", {"obs": sorted(obs.values())})
print("snapshots:", len(snaps), "observations:", len(obs))
