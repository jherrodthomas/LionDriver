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

## Before the first run

The variable names and codes in `CODES` and `DESIGN` were written from memory of the FARS and CRSS analytical user's manuals. They have **not** been checked against a release. Check each one against the manual of the year you load and correct the script where it differs. Record the check with the result (WP-V-02 §3.5 item 4).

| Item | Used as | Check in the manual |
|---|---|---|
| `MAN_COLL` codes | 1 rear-end, 2 head-on, 6 angle, 7 sideswipe same direction, 8 sideswipe opposite | Manner of collision codes for the year |
| `HARM_EV` codes | 8 pedestrian, 9 pedalcyclist, with `MAN_COLL` 0 | First harmful event codes |
| `ROUTE` (FARS), `INT_HWY` (CRSS) | 1 = Interstate | Route signing / Interstate flag; the two must define the same road class |
| `MAX_SEV` (CRSS) | 1–5 injury, 4 fatal; 6 excluded | Maximum injury severity in crash |
| `VSPD_LIM` | Posted limit in mph per vehicle; 0, 98 and 99 unknown | Speed limit codes; the crash takes the highest known limit |
| `WEIGHT`, `PSUSTRAT`, `PSU_VAR` | Case weight, variance stratum, variance PSU | Variance estimation section |

## Limits

- **Barrier impacts are not separated.** SH-01 and SH-02 include barrier impacts (HE-01.2), but the script groups only collisions with a motor vehicle in transport, plus pedestrians and cyclists. A barrier class needs the fixed-object harmful-event codes. Until it has them, the SH-01 and SH-02 values cover sideswipe and head-on only.
- **Average crash, not the LD-SDA crash.** The ratio is valid only where the LD-SDA collision is argued to be no more severe than the average crash of that type and band (WP-V-02 §3.5 item 3). SH-06 with no braking before impact is not; it needs an injury-risk curve at the impact speed.
- **Same year for both.** FARS and CRSS of different years must not be mixed.
- **Upper bounds use a normal approximation** (`--z`, default 1.645 for 95 % one-sided).
