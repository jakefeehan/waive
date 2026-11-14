"""One-off: save the live replies the site fetches in the browser, so a preview can run on real numbers."""
import json, time, urllib.request
UA = {"User-Agent": "waive (github.com/jakefeehan/waive)", "Accept": "application/geo+json"}
def get(u):
    with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60) as r:
        return json.loads(r.read().decode())
now = int(time.time()); out = {"made": now}
def ymd(s): return time.strftime("%Y%m%d", time.gmtime(s))
M = "https://marine-api.open-meteo.com/v1/marine?latitude=32.8&longitude=-117.28&hourly=wave_height,swell_wave_height,swell_wave_period,swell_wave_direction,secondary_swell_wave_height,secondary_swell_wave_period,secondary_swell_wave_direction,wind_wave_height,wind_wave_period,wind_wave_direction&timeformat=unixtime&timezone=GMT&forecast_days=4"
T = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?station=9410230&units=english&time_zone=gmt&format=json&application=waive"
jobs = {
 "marine": M, "marine2": M + "&models=ncep_gfswave016",
 "wind": "https://api.open-meteo.com/v1/forecast?latitude=32.8&longitude=-117.262&hourly=wind_speed_10m,wind_direction_10m,wind_gusts_10m,temperature_2m&wind_speed_unit=mph&temperature_unit=fahrenheit&timeformat=unixtime&timezone=GMT&forecast_days=4",
 "tideH": T + "&product=predictions&datum=MLLW&begin_date=%s&range=120&interval=h" % ymd(now - 86400),
 "tideHL": T + "&product=predictions&datum=MLLW&begin_date=%s&range=120&interval=hilo" % ymd(now - 86400),
 "pier": T + "&product=wind&date=recent",
}
for k, u in jobs.items():
    try: out[k] = get(u)
    except Exception as e: print("FAIL", k, e)
try:
    pt = get("https://api.weather.gov/points/32.8,-117.262")
    out["nwsHourly"] = get(pt["properties"]["forecastHourly"])
except Exception as e: print("FAIL nws", e)
json.dump(out, open("data/snapshot.json", "w"), separators=(",", ":"))
print({k: len(json.dumps(v)) for k, v in out.items()})
