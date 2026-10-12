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

## Injury-risk curve for SH-06 and SH-03

`risk_curve.py` covers the case the ratio cannot: SH-06, a rear-end into slow or stationary traffic with no braking before impact (WP-V-02 §3.5 item 3).
- **Δv:** from the closing speed by conservation of momentum, with a small restitution.
- **Driver risk:** the Joksch (1993) rule of thumb, p = (Δv / 71 mph)⁴.
- **Crash risk:** bounded over all occupants of both vehicles with the union bound. The curve is per driver, but FARS counts a crash as fatal if anyone dies.

```bash
tools/severity/risk_curve.py              # ODD speed bounds: 120 km/h (ODD-H), 90 km/h (ODD-A)
tools/severity/risk_curve.py --speed 60   # another closing speed
```

At both ODD speed bounds the worst credible lead gives P(fatal crash) = 1. That lead is a stationary heavy truck, which the ODD includes. The Corolla's Δv is then almost the full closing speed. Even car-to-car at 120 km/h reaches 1 once all occupants are counted. So SH-06 earns no severity credit, and its target rests on P(E-situation), P(not controlled) and the lead-detection requirements (AIR-03, AIR-04). SH-03 approaching slower traffic (OS-07) is at least as severe and is also 1. SH-03 following at a short gap (OS-05) accelerates at +2.0 m/s² over the planner's following gap. That gives impacts of about 50 km/h and bounds of 0.33 in ODD-H and 0.20 in ODD-A, the only severity credit the curve gives. There is no injury curve: at these Δv an injury is near certain, so for an injury-crash budget the value is 1.

The curve constant (71 mph), its scope (impact directions, which occupants), the masses, the occupancies and the restitution are written from memory or assumed. Check them before the result is recorded as evidence.

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
