# Severity ratios from FARS and CRSS

`severity_ratio.py` computes P(severity class) for the SOTIF validation targets ([WP-V-02 §3.5](../../assurance/06-validation/WP-V-02-sotif-vv-strategy.md#35-evidence-for-pseverity-class), open item OI-8). For each collision type, road class (Interstate or not) and posted speed-limit band it reports:

- **P(fatal | crash):** FARS fatal crashes divided by the CRSS estimate of police-reported crashes. FARS is a census, so the one-sided upper bound uses only the lower bound of the CRSS total.
- **P(injury | crash):** the CRSS share of crashes with an injury (KABCO K, A, B, C or injured with unknown severity). Its upper bound uses the Taylor-linearised standard error of a ratio.

CRSS standard errors come from its stratified cluster design: PSUs within strata, treated as sampled with replacement. A cell falls back to a bound of 1, as WP-V-02 §3.5 requires, when any of these holds:
- it has fewer than 30 CRSS cases;
- a stratum in it has a single PSU;
- it has no CRSS crash at all.

It then summarises per SOTIF hazard. The per-SH value is the largest upper bound over the hazard's collision types and the speed bands of each ODD part. A band with no data counts as 1.

## Use

Download the national CSV releases of the **same year** from NHTSA, unzip them, and point the script at the two directories:

```bash
tools/severity/severity_ratio.py --fars FARS2022NationalCSV/ --crss CRSS2022CSV/ --json severity-2022.json
```

It prints two Markdown tables, per cell and per SH, and `--json` writes both together with the codes and design variables used.

## Injury-risk curves for SH-06, SH-03, SH-04, SH-11 and the SH-01/02 head-on

`risk_curve.py` covers the case the ratio cannot: SH-06, a rear-end into slow or stationary traffic with no braking before impact (WP-V-02 §3.5 item 3).
- **Δv:** from the closing speed by conservation of momentum, with a small restitution.
- **Driver risk:** the Joksch (1993) rule of thumb, p = (Δv / 71 mph)⁴.
- **Crash risk:** bounded over all occupants of both vehicles with the union bound. The curve is per driver, but FARS counts a crash as fatal if anyone dies.

```bash
tools/severity/risk_curve.py              # ODD speed bounds: 120 km/h (ODD-H), 90 km/h (ODD-A)
tools/severity/risk_curve.py --speed 60   # another closing speed
```

At both ODD speed bounds the worst credible lead gives P(fatal crash) = 1. That lead is a stationary heavy truck, which the ODD includes. The Corolla's Δv is then almost the full closing speed. Even car-to-car at 120 km/h reaches 1 once all occupants are counted. So SH-06 earns no severity credit, and its target rests on P(E-situation), P(not controlled) and the lead-detection requirements (AIR-03, AIR-04). SH-03 approaching slower traffic (OS-07) is at least as severe and is also 1. SH-03 following at a short gap (OS-05) accelerates at +2.0 m/s² over the planner's following gap. That gives impacts of about 50 km/h and bounds of 0.33 in ODD-H and 0.20 in ODD-A.

SH-04 (struck from behind after phantom braking, OS-08) is simulated:
- **Ego:** brakes at the envelope minimum (−3.5 m/s²) to a stop.
- **Follower:** at a time gap of 0.5, 1.0 or 1.5 s, holds its speed for 2.0 s, then brakes at 3.0 m/s². Those are the assumed worst credible reaction time and deceleration.
- **Impact:** at 27–35 km/h relative speed.
- **Bound:** 0.043 in ODD-H and 0.032 in ODD-A, with a heavy truck behind.

`--sensitivity` prints the impact speed over reaction times of 1.0–2.0 s and follower braking of 3–6 m/s². A follower that never brakes before impact is outside this bound.

SH-11 (no reaction to a pedestrian or cyclist) uses the pedestrian fatality curve of Tefft (2011, AAA Foundation report): 10/25/50/75/90 % at 23/32/42/50/58 mph, interpolated linearly, and 1 above 58 mph. There is no braking before impact. The result is 0.38 at the OS-04 bound (60 km/h) and 0.05 after a launch from a queue (OS-06, 18 km/h). Its pedestrian and pedalcyclist ratio cells are still printed by `severity_ratio.py`, but no per-SH value is taken from them. The anchor points, the use for cyclists and the linear risk below 23 mph are checked (see below). `--low-speed` prints the linear segment next to a logistic fit to the Tefft anchors and the Hussain et al. (2019) meta-analysis; the linear risk is the highest of the three from 2 to 23 mph. `--age` prints the SH-11 cases with the curve shifted for ages 50, 70 and 80.

SH-01 and SH-02 are split. The ODD-A head-on (drift into the oncoming lane, no reaction, 90 + 90 km/h closing) is on the curve and gives 1. SH-02 departs in a curve, so `--sh02` checks its barrier angle. With θ = √(2d/R), the controller's 3.0 m/s² limit and a barrier 4 m off the path, the angle is 9–14° at 70–110 km/h. That is below the 25° crash-test angle (MASH TL-3), so the barrier ratio still applies. `--sh01` gives the same check for an SH-01 departure on a straight road, 8.4° at 120 km/h. The SH-01 barrier impact stays on the ratio rather than a curve, for the same reason as SH-10: its first impact is a glancing one, and its harm comes from what follows. Sideswipe and barrier impacts from a drift happen at a shallow angle, no worse than the average crash of their type, so they stay on the sideswipe-same-direction and barrier ratios of `severity_ratio.py`.

SH-10 (lane change into an occupied lane) is not on a curve. Its primary contact is a sideswipe with a Δv of a few km/h, so a curve would credit almost all of its risk away. Its S3 rating comes from the loss of control and secondary impacts that follow, which the curve does not model. It uses the sideswipe-same-direction ratio of `severity_ratio.py`, whose crashes are typically lane changes and include those secondary outcomes. There is no injury curve: at these Δv an injury is near certain, so for an injury-crash budget the value is 1. `--sh10` checks that its contact belongs to the sideswipe class. At the controller's 3.0 m/s² lateral limit, the lateral closing speed is at most 13 km/h (about 7 km/h of Δv per car). The angle is 6–12° at 60–120 km/h and 22° at the 20 mph lane-change minimum. The same bound covers an SH-01/02 drift into an adjacent vehicle, which also stays on the sideswipe ratio.

The curve constant (71 mph), its scope (impact directions, which occupants), the masses, the occupancies and the restitution are written from memory or assumed. Check them before the result is recorded as evidence.

## Curve-constant check

Checked on 2026-10-12 against search summaries; the full texts were not reachable from the cloud environment.

| Source | Confirmed | Open |
|---|---|---|
| Joksch (1993), *AAP* 25(1) 103–104 | Citation; car-car collisions; risk of occupant death; fourth power. One secondary source gives 31.74 m/s, which is 71.0 mph | One other source quotes the constant garbled (reads like 61.54); the impact directions in the data. Rear-struck occupants (SH-04 ego, SH-06/SH-03 lead): checked, conservative, since rear impacts are less injurious at the same Δv (MAIS3+ at 30 mph: 19.9 % rear against 38.9 % frontal, PMC3217552); no credit taken; rear-seat intrusion from a heavy follower not covered. Directions not named in any summary; `--curve richards` uses the Richards (2010) frontal fit (3/17/60 % at 30/40/50 mph Δv), above Joksch from about 33 mph: SH-03 following 0.45 in ODD-H, inside the 61.54 sensitivity. Richards side (belted, struck side, 25/85 % at 30/40 mph; half of deaths at ≤ 24 mph): `--sh10` and `--sh02` print it at the primary-contact lateral Δv, 7 and about 19 km/h, giving 0.0002 and 0.002, which is why those collisions stay on the ratio. Sensitivity: `--joksch-mph 61.54` raises SH-03 following to 0.59 and SH-04 to 0.076 |
| Tefft (2011), AAA Foundation report | Anchors 10/25/50/75/90 % at 23/32/42/50/58 mph; pedestrians struck by forward-moving cars and light trucks, 1994–1998 | Cyclists not covered by Tefft. Cyclist curves put the risk at or below the pedestrian's at the same speed (Nie, Li and Yang 2015: 50 % at 67.6 km/h for cyclists, 65.4 km/h for pedestrians; Lubbe, Wu and Jeppsson 2022: 10 % serious injury at 44 and 29 km/h), so using Tefft for cyclists is conservative. The journal version (*AAP* 50, 871–878, 2013) gives 10 % near 24 mph and 50 % near 41 mph |
| Richards (2010), DfT Road Safety Web Publication 16, section 3 (full text reached) | Frontal 3/17/60 % at 30/40/50 mph Δv, side 25/85 % at 30/40 mph, read off the fitted curves; fits here go through them within 0.005. Belted drivers, one impact with another car, no rollover; OTS 2000–09 and CCIS 1983–2010; 620 frontal (66 fatal), 118 side (21 fatal); weighted to STATS19, likely to overestimate the risk (report). Momentum Δv as used here. Median Δv of the deaths: 34 mph frontal, 24 mph side | Coefficients not published; confidence bands only drawn; UK fleet, not US |
| Richards (2010), section 2 and table 4.1 (pedestrians, ages 15+) | 30/40 mph: Ashton and Mackay (GB 1970s) 14/60 %, OTS (GB 2000–09) 9/33 %, GIDAS (DE 1999–2007) 7/25 %. `--pedestrian-compare`: at SH-11 OS-04, Tefft 0.38 against 0.45/0.24/0.18; at OS-06, 0.05 against ≤ 0.005. Tefft is above both recent datasets | Two-point logistic fits; extrapolated at 18 km/h. Only the 1970s data exceed Tefft |
| Richards (2010), section 2.2.1.2 (Ashton and Mackay, by age) | 30 mph: 47 % for 60+, 5 % for 15–59, 14 % for 15+; odds ratio 60+ against 15+ 5.45. `--age` applies it to the Tefft average: OS-04 0.77 (age-70 shift 0.72, upper CI 0.80); OS-06 0.21 on the linear segment, 0.11 on the logistic fit (shift 0.10). Elderly ranges reported: 0.72–0.80 and 0.10–0.21 | 1970s data; one point per age group; ratio assumed constant over speed; 60+ mean age not given |
| Hussain et al. (2019), *AAP* 129, 241–249 | Pedestrian fatality meta-analysis of 20 studies: odds ratio 1.11 per km/h, 5 % at 30 km/h, 50 % at 59 km/h. With a logistic fit to the Tefft anchors (logit p = −5.108 + 0.1246 · mph) it checks the linear segment below 23 mph: linear ≥ both from 2 to 23 mph; OS-06 (18 km/h) is 0.048 linear, 0.023 Tefft fit, 0.013 Hussain | Below 2 mph the linear risk is up to 0.006 under the Tefft fit (logistic artefact) |
| Tefft (2013), *AAP* 50, 871–878 (age) | A 70-year-old struck at any speed has about the death risk of a 30-year-old struck 11.8 mph faster (2011 report: 10.4 mph for death, 95 % CI 5.4–15.4; `--age-offset-mph` sets it, and 15.4 gives 0.80 in OS-04 at 70). A secondary source quotes the report: 20 % died at 30 mph, against 0.22 from the curve. `--age` shifts the curve by 0.295 mph per year over 30: SH-11 OS-04 0.38 average, ≤ 0.72 at 70; OS-06 0.05, ≤ 0.10 at 70 | Sample mean age 45 (422 PCDS pedestrians aged 15+, 1994–1998); `--age` also prints the central estimate shifted from 45 (OS-04 0.58 at 70). Open: the mean age of the 2007–2009 standardisation population (GES person file), and the age-by-speed tables (every copy blocked); age 80 is extrapolated. The average stays the P(severity class) value (WP-V-02 §3.5) |

## Before the first run

The variable names and codes in `CODES` and `DESIGN` were written from memory of the FARS and CRSS analytical user's manuals. They have **not** been checked against a release. Check each one against the manual of the year you load and correct the script where it differs. Record the check with the result (WP-V-02 §3.5 item 4).

| Item | Used as | Check in the manual |
|---|---|---|
| `MAN_COLL` codes | 1 rear-end, 2 head-on, 6 angle, 7 sideswipe same direction, 8 sideswipe opposite | Manner of collision codes for the year |
| `HARM_EV` codes | 8 pedestrian, 9 pedalcyclist; barrier 20 impact attenuator, 23 bridge rail, 24 guardrail face, 25 concrete traffic barrier, 26 other traffic barrier, 52 guardrail end, 57 cable barrier; all with `MAN_COLL` 0 | First harmful event codes; the barrier list must hold every barrier type of the year's code list and nothing else |
| `ROUTE` (FARS), `INT_HWY` (CRSS) | 1 = Interstate | Route signing / Interstate flag; the two must define the same road class |
| `MAX_SEV` (CRSS) | 1–5 injury, 4 fatal; 6 excluded | Maximum injury severity in crash |
| `VSPD_LIM` | Posted limit in mph per vehicle; 0, 98 and 99 unknown | Speed limit codes; the crash takes the highest known limit |
| `WEIGHT`, `PSUSTRAT`, `PSU_VAR` | Case weight, variance stratum, variance PSU | Variance estimation section |

## Limits

- **Barrier by first harmful event.** A crash is a barrier crash when its first harmful event is a barrier (lane departure into it, HE-01.2). A crash that starts with another vehicle and then hits a barrier counts under its first event. A departure that first strikes something else, such as a curb, a ditch or a tree, is not in the barrier class. Those objects are not among the SH-01/SH-02 collisions of WP-V-02 §3.5 item 2. If the HARA adds them, extend the class.
- **Average crash, not the LD-SDA crash.** The ratio is valid only where the LD-SDA collision is argued to be no more severe than the average crash of that type and band (WP-V-02 §3.5 item 3). SH-06 with no braking before impact is not; it needs an injury-risk curve at the impact speed.
- **Same year for both.** FARS and CRSS of different years must not be mixed.
- **Upper bounds use a normal approximation** (`--z`, default 1.645 for 95 % one-sided).
