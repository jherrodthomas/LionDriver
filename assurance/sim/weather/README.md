# Weather physics: sun in the road camera, hydroplaning and the cabin heat soak

> **Synthetic data (DSR-12). Design aid, no evidence credit (DQ-139).** Two small physics studies for the SOTIF
> triggering conditions of low sun (TC-01) and rain (TC-03). They answer *when* and *how fast*, not whether the item
> copes: that is for the logged drives and the known-scenario tests (KS-12, KS-15).

## 1. Sun in the road camera (TC-01, KS-12)

**Question.** On the corridor of the test sites (I-85, Atlanta – Greenville – Charlotte), when is the sun inside the
road camera's frame, and for how many hours a year?

**Method.** [`sun_glare.py`](sun_glare.py) takes the sun's position every 5 min of a year from the NREL Solar
Position Algorithm (pvlib 0.16.1, BSD-3; apparent elevation with refraction) and compares it with the road camera's
field of view, read from `openpilot/common/transformations/camera.py`: 1928 × 1208 px at a 2648 px focal length,
**40.0° × 25.7°**, assumed level. It counts every heading from 0° to 355° and the two corridor directions (63° and
243°). Results: [`results/sun-glare.md`](../results/sun-glare.md).

**Result.**
- **Northbound** the sun sits in the frame on April–August mornings, about 158 h a year, up to 75 min on one day.
- **Southbound** it sits there on October–March evenings, about 203 h a year, up to 80 min on one day.
- Within 10° of the frame, where the lens and windshield still flare, the hours double or more.

All of this is an upper bound, because terrain, trees, buildings and clouds are not modelled. The calendar gives the
clock times to schedule the KS-12 low-sun drives.

![Two calendars, day of the year across and clock time up, for I-85 northbound and southbound: orange marks when the sun is inside the road camera's frame; northbound a band from April to August around 6:30–8:00, southbound two bands, January to March and October to December, around 16:00–19:00](figures/fig-wx-1-sun-calendar.webp)

*Figure 1. When the sun is in the frame, by day and clock time.*

![Polar chart: hours a year with the sun in the frame for every heading, largest toward east and west, zero toward north; I-85 northbound 158 h and southbound 203 h marked](figures/fig-wx-2-sun-headings.webp)

*Figure 2. Every heading at the corridor.*

![Animation, looping: the road camera's frame on I-85 southbound on 1 January from mid-afternoon; the sun's path descends into the frame, which turns red with a "Sun in the frame" banner, until sunset](figures/fig-wx-3-sun-anim.webp)

*Figure 3. Driving southwest into the sunset (animated WebP).*

**For the Blender scenes.** The TC-01 preset of the hazard scenes ([`blender/library/conditions.yaml`](../blender/library/conditions.yaml),
owned by the scene session) draws the sun "ahead" at 5° elevation. The study gives corridor values such a scene can
take, for example southbound on 1 January at 16:20: 11° left of straight ahead, 11° up. This is a handover note; the
scene files are not changed here.

## 2. Hydroplaning (TC-03, KS-15)

**Question.** At what speed do the Corolla's tyres lose the road in rain, against the ODD's 110 km/h? The ODD
includes "light rain" and excludes heavier rain, but gives no number (WP-C-02 §3.1).

**Method.** [`hydroplaning.py`](hydroplaning.py) applies two published models:

| Model | What it gives | Source |
|---|---|---|
| Water film | Film depth above the texture from rain intensity, drainage path and slope (metric form: mm, m, mm/h, %) | Gallaway et al. 1979, FHWA-RD-79-31 |
| PAVDRN speed | Hydroplaning speed from the film depth and the texture: two fitted branches, meeting at 2.4 mm (0.095 in) | NCHRP PAVDRN (Anderson et al. 1998), from Gallaway 1979 and Huebner et al. 1986 |
| NASA | Full dynamic hydroplaning where water stands deeper than the tread: V = 10.35 √p mph, p the tyre pressure in psi | Horne and Dreher 1963, NASA TN D-2056 |

**Inputs.** The road is a crowned Interstate (2 % cross slope, 3.66 m lanes, 1–3 lanes draining across, 0–4 %
grade), with 0.8 mm mean texture depth, and tyre pressure 35 psi (assumed; the reference car's door placard
decides). Results: [`results/hydroplaning.md`](../results/hydroplaning.md).

**Result.**
- **Light rain** (below 2.5 mm/h): the texture drains the water on every road here, so there is no film.
- **Rain film**: the hydroplaning speed falls to 110 km/h only from about **25 mm/h** (three lanes draining) to
  **56 mm/h** (one lane). That is 3 to 7 times the top of moderate rain, so only in rain the ODD already excludes.
- **Standing water** deeper than the tread (ruts, puddles, a worn tyre) is the case that matters. NASA gives
  **98 km/h at 35 psi** (91–103 km/h at 30–38 psi), below the ODD's 110 km/h. Excluding heavier rain does not exclude
  water that stands on the road after the rain.

![Hydroplaning speed against rain intensity on a log scale for water draining across one, two and three lanes, with the light, moderate and heavy rain bands; no water film in light and moderate rain; the curves fall below the 110 km/h ODD bound only in heavy rain, from about 25 to 56 mm/h; a band at 91–103 km/h marks NASA's speed for water deeper than the tread](figures/fig-wx-4-hydro-speed.webp)

*Figure 4. Hydroplaning speed in rain against the ODD bound.*

![Animation, looping: a tyre on standing water as the speed rises from 50 to 130 km/h; water enters the footprint from the front, the share of the footprint on the road shrinks, and at 98 km/h a "Hydroplaning: no grip" banner appears](figures/fig-wx-5-hydro-anim.webp)

*Figure 5. The mechanism as a loop. The footprint bar follows the speed-squared law of lift and is a schematic, not a
measurement.*

**Limits.**
- All three are empirical fits from trough and track tests of the 1960s–80s, not tests of this car's tyres.
- PAVDRN's two branches meet at 0.095 in only where the texture-free term governs. With coarse texture the
  thick-film branch jumps, by up to about 4 mph at 1.3 mm texture. That is a property of the published fits.
- Tread depth enters only through NASA's condition (water deeper than the tread). A worn tyre lowers the water depth
  at which that condition is met.

## 3. Cabin heat soak (OI-3, TC-21)

**Question.** How hot does the air at the device mount get when the car is parked in the sun, and how fast does it
fall once the car drives? The device heat model ([`../thermal`](../thermal/README.md)) held the cabin at one
temperature for a whole drive. A real hot day starts hot and cools under the AC.

**Method.** [`cabin_soak.py`](cabin_soak.py) is a lumped heat model of the Corolla's cabin with five nodes: air,
windshield, dashboard, interior (seats and trim) and shell (roof, doors and the other glass).
- **Sun:** the sun on each glazed and opaque surface comes from pvlib's clear-sky model (Ineichen) on the tilted
  planes.
- **Outside:** the outside air follows a daily curve, coolest at 06:00 and warmest at 15:00.
- **Parked:** the car parks facing south at noon for two hours.
- **Driving:** it then drives southwest on I-85 at 100 km/h for an hour, with the AC on recirculation or the AC off
  (fan on fresh air).
- **Mount air:** the air at the mount is the cabin air plus 0.4 of the windshield's difference from it. That share is
  an assumption, and the logger at the mount (DQ-411) sets it.

Every cabin input is an estimate ([`params.yaml`](params.yaml), `cabin:`). Results:
[`results/cabin-soak.md`](../results/cabin-soak.md).

**Check against measured cars.** McLaren, Null and Quinn (2005, *Pediatrics* 116(1) e109) measured a dark sedan on
16 clear days at 22–36 °C ambient: the cabin air rose about 22 K in 60 min, at the same rate whatever the ambient.
The model gives 22.1 K at both 22 and 36 °C, with no tuning. It is slower early: 65 % of the rise in the first
30 min, against the 80 % measured. The model's interior holds more heat than a real car's, which the logger will
show.

**Result (hot 15 July, 35 °C afternoon, estimated inputs).**
- **Parked:** after two hours the cabin air is at 64 °C, the dashboard at 88 °C and the mount air at 59 °C.
- **Driving with the AC:** the mount air falls below the device model's worst-edge bound (43 °C) within 2 min and
  ends at 30 °C.
- **Driving without the AC:** it stays above that bound for 26 min and ends at 41 °C.

Fed into the device model ([`../thermal/cabin_drive.py`](../thermal/cabin_drive.py),
[`results/cabin-device.md`](../results/cabin-device.md)): parked with the device off, the SoC reaches 64 °C. While
driving it peaks at 77 °C with the AC on and 82 °C with it off, below the 96 °C limit in both. That comes from the
estimated inputs; T1 and the logger decide it.

![Two charts of a hot July day: parked in the sun from 12:00 to 14:00, the cabin air rises to 64 °C, the dashboard to 88 °C and the mount air to 59 °C, above the device model's 43–50 °C bound; then driving, with the AC on the mount air drops below the bound within minutes and ends at 30 °C, with the AC off it ends at 41 °C](figures/fig-wx-6-cabin.webp)

*Figure 6. The cabin through a hot day, with the AC on and off.*

![Animation, looping: a side view of the Corolla whose cabin, windshield and dashboard change colour with their temperatures from 12:00 to 15:00; parked in the sun the cabin turns orange and the mount air rises to 59 °C; from 14:00, driving with the AC on, it turns pale and the mount air falls to 30 °C; a chart below draws the mount-air curve against the device model's bound](figures/fig-wx-7-cabin-anim.webp)

*Figure 7. The same day as a loop.*

## 4. Checks

[`test_weather.py`](test_weather.py) runs in CI:

| Check | Catches |
|---|---|
| S1 pvlib's SPA against the published NREL reference case (zenith 50.11162°, azimuth 194.34024°) | a wrong solar library or call |
| S2 An independent NOAA algorithm, in numpy, against SPA over a year (within 0.05° elevation) | an error in either |
| S3 Field of view read from `camera.py` (40.0° × 25.7°); a sun 20° off-axis counted, 24° not | a wrong camera or frame test |
| S4 Solstice sunrise azimuth 58–64° at the corridor; heading north never sees the sun | a wrong site or time zone |
| W1 Metric film equation against the imperial one after unit conversion | a unit or coefficient error |
| W2 PAVDRN branches meet at 0.095 in where the texture-free term governs | a mistyped constant |
| W3 NASA formula (10.35 √p) | a wrong pressure or unit |
| W4 More rain, a longer path or a flatter slope never raises the speed | a sign or branch error |
| W5 The ODD bound read from WP-C-02 | a moved bound |
| C1 Cabin air rises 22 ± 5 K in 60 min of clear sun, the same at 22 and 36 °C ambient (McLaren et al. 2005) | a model far off measured cars |
| C2 No sun, no AC, constant outside: every node stays at the outside temperature; a clear night sky cools, not below the sky | heat from nowhere, a sign error |
| C3 Outside curve: minimum 06:00, maximum 15:00 | a wrong daily curve |

All three scripts' `--check` rerun the study and fail if any number moves by more than 0.05 from the committed JSON.

```sh
python3 -m pip install -r assurance/sim/weather/requirements.txt
python3 assurance/sim/weather/test_weather.py
python3 assurance/sim/weather/sun_glare.py --figures       # about 2 s, figures about 30 s
python3 assurance/sim/weather/hydroplaning.py --figures
python3 assurance/sim/weather/cabin_soak.py --figures      # reads results/thermal-pilot.json for the bound
```
