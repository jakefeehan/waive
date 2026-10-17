# waive: Tourmaline prototype

## How to open it
Go to https://jakefeehan.github.io/waive on any phone or computer. It pulls live forecast data each time you open or refresh it.

## What's in it
- A 0 to 10 rating for Tourmaline, for right now or any hour you tap.
- Board picker (shortboard, fish, longboard, foamie) plus sliders to tune size, wind and tide for your board. Saved in your browser.
- Best time to go for each day (daylight only).
- 72-hour chart: rating bars, surf height, sets, tide with highs and lows, wind arrows.
- Animated side view of the waves to scale next to a 5'10" surfer, with set timing.
- Swell window compass showing which swell directions reach Tourmaline.
- A clickable map of the Pacific Beach breaks (Tourmaline, Law Street, Diamond Street, Crystal Pier, Pacific Beach Drive) with each break's rating and surf size for the selected hour.
- A table showing which data sources loaded.

## Free data sources
| Source | Used for | Notes |
|---|---|---|
| Open-Meteo Marine | Hourly swell height, period, direction | Free, no key. Free for non-commercial use; a paid plan is needed once waive makes money. |
| NWS api.weather.gov | Wind forecast (main), backup swell | Free, public domain. |
| Open-Meteo forecast | Wind gusts, backup wind | Same terms as above. |
| NOAA Tides and Currents (La Jolla 9410230) | Tide heights, high/low times | Free, public domain. |
| NDBC buoy 46225 Torrey Pines Outer | Measured waves right now, water temp; corrects the forecast | NDBC blocks direct browser requests, so a GitHub Action (`.github/workflows/buoy.yml`) copies the latest reading into `data/buoy.json` every hour. |

## Known limits
- Wave height at the beach is an estimate from offshore swell. The next accuracy step is comparing our estimates with real observations and tuning.
- The Claude preview link can't reach outside websites, so it shows sample conditions. The live site shows real data.
