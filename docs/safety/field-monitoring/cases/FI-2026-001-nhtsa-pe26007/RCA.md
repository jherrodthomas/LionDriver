# FI-2026-001 — Root Cause Analysis

**Method set:** Class A (PROCESS §5.5): timeline, barrier analysis, FTA, STPA, fishbone, 5-Why, SOTIF triggering conditions, escape-point analysis.

**Baselines analyzed:** LionDriver `8b8c6ae` (openpilot tree) and `opendbc_repo` `229dc70`.

**Short file names used below:**

| Short name | Full path |
|---|---|
| `radard.py` | `openpilot/selfdrive/controls/radard.py` |
| `long_mpc.py` | `openpilot/selfdrive/controls/lib/longitudinal_mpc_lib/long_mpc.py` |
| `longitudinal_planner.py` | `openpilot/selfdrive/controls/lib/longitudinal_planner.py` |
| `selfdrived.py` | `openpilot/selfdrive/selfdrived/selfdrived.py` |
| `policy.py` | `openpilot/selfdrive/monitoring/policy.py` |
| `interface.py`, `values.py`, `carcontroller.py`, `toyotacan.py` | `opendbc_repo/opendbc/car/toyota/…` |
| `toyota.h` | `opendbc_repo/opendbc/safety/modes/toyota.h` |

**Evidence limits:** crash logs are not available to us. Each claim below is tagged:

- **[Verified]**: read in code at the pinned commit, or computed from it.
- **[Supported]**: consistent with code and reporting, but not yet reproduced.
- **[Hypothesis]**: plausible and untested.

Nothing here claims to know what happened in a specific crash. The RCA asks a different question: *what in the design we inherit could allow this class of crash, and what would stop it on LionDriver?*

## 1. Problem statement

Vehicles running openpilot or openpilot-derived software, with the system engaged, collided with **stationary or slow vehicles in the ego lane**. This happened at least five times (3 fatalities, 11 injuries). The system did not slow the vehicle enough, the driver did not intervene in time, and any stock AEB present did not prevent the collision.

## 2. Sequence of events (generic — individual crash timelines unknown)

| Phase | What must go right | Notes |
|---|---|---|
| T-10…-5 s | Stopped vehicle visible ahead; often hidden behind a lead vehicle until that vehicle **cuts out** | Classic "reveal" scenario |
| T-5…-3 s | Driving model reports a lead with `lead_prob > 0.5`; `radard` matches it to a radar track or uses vision only | `radard.py:156-165` [Verified] |
| T-4…-2 s | MPC plans braking; FCW if predicted crash and `modelProb > 0.9` | `long_mpc.py:338-340`, `longitudinal_planner.py:121` [Verified] |
| T-3…0 s | Braking at most **-3.5 m/s²**; driver alerted by FCW; driver brakes or steers; stock AEB (if present) fires | `opendbc/car/toyota/values.py:43`, `safety/modes/toyota.h:208-209` [Verified] |
| 0 | Collision if every layer above fails or acts too late | |

## 3. Protection-layer (barrier) analysis

A collision needs **all three** independent layers to fail. Each layer has its own root cause.

| Layer | Intended function | Weakness found in our inherited baseline | Tag |
|---|---|---|---|
| **L1 — openpilot longitudinal control** | Detect the in-lane obstacle and brake in time | (a) At speed, stationary objects depend on the **vision model**. Radar tracks are only used when they match a vision lead (`match_vision_to_track`), or when ego speed < **4 m/s** (`V_EGO_STATIONARY`, `potential_low_speed_lead`). (b) Braking authority is capped at **-3.5 m/s²** by both the car port and the panda safety mode, so detection must come about **twice as early** as for full braking (see §3.1). (c) The system has no AEB function of its own. The PRE_COLLISION message is blocked unless all zeros. | `radard.py:24, 98-100, 113-134, 156-171`; `toyota.h:208-209, 250-256` [Verified] |
| **L2 — Driver** | Monitor the road and take over | (a) DM tolerates **5 s** of continuous visual distraction before the first alert, **8 s** before the second, **13 s** before the terminal alert. At 30 m/s that is 150 m / 240 m / 390 m travelled. (b) FCW only fires when the MPC predicts a crash with `modelProb > 0.9`, or when the model predicts hard braking. So the warning is tied to the same perception that missed or late-detected the obstacle (common cause with L1). (c) Over-trust from sustained good performance (automation complacency) is foreseeable misuse. | `policy.py:34-36, 196-198`; `long_mpc.py:338-340`; `selfdrived.py:442-445` [Verified]; complacency [Supported] |
| **L3 — Stock OEM AEB / PCS** | Independent last-resort braking | On **radar-ACC Toyotas** (incl. the 2022 RAV4) with alpha longitudinal on, openpilot **silences the radar ECU** with UDS CommunicationControl (disable TX). It then transmits `PCS_HUD` with `PCS_OFF = 1` and the comment *"PCS turned off"*. The independent L3 barrier is then **removed by design**. On camera-ACC TSS2 cars (our Corolla), openpilot leaves the radar ECU and PCS in place. | `interface.py:93-106, 126-131`; `carcontroller.py:294-295`; `toyotacan.py:101-110` [Verified code behavior]; effect on the vehicle's AEB [Supported — confirm on vehicle, CA-001] |

### 3.1 Braking-authority arithmetic [Verified, computed]

Stopping distance to a stationary target = latency distance + v²/(2a). Assumptions: 0.5 s end-to-end latency, constant deceleration once reached, jerk limits ignored. These are idealized and favorable to the system.

| Ego speed | Distance at -3.5 m/s² (openpilot cap) | Distance at -8 m/s² (≈ full braking) | Time to impact at constant speed from the -3.5 distance |
|---|---|---|---|
| 72 km/h (20 m/s) | 67 m | 35 m | 3.4 s |
| 90 km/h (25 m/s) | 102 m | 52 m | 4.1 s |
| 108 km/h (30 m/s) | 144 m | 71 m | 4.8 s |
| 126 km/h (35 m/s) | 193 m | 94 m | 5.5 s |

**Implication:** at highway speed, openpilot alone can only avoid a stopped vehicle if it is detected and confirmed (`lead_prob > 0.5`) at **≥ 140–190 m**. That is a demanding range for a single forward camera. A cut-out reveal often happens much closer. Any detection inside this range needs L2 or L3 to avoid the crash.

## 4. Fault tree (qualitative)

```text
TOP: Engaged vehicle collides with a stationary/slow in-lane vehicle
└── AND
    ├── G1: openpilot does not decelerate enough in time               (L1)
    │   └── OR
    │       ├── G1.1 Obstacle not detected / lead_prob ≤ 0.5 until too late
    │       │   └── OR
    │       │       ├── B1 Vision model insufficiency on stationary targets at range
    │       │       │      (emergency vehicles, lighting, glare, night, occlusion)       [Hypothesis]
    │       │       ├── B2 Cut-out reveal leaves too little distance                     [Supported]
    │       │       ├── B3 Radar track not used: no vision match, and v_ego ≥ 4 m/s      [Verified, SIL: CA-002]
    │       │       └── B4 Partially-in-lane object assigned to adjacent lane            [Hypothesis]
    │       ├── G1.2 Detected, but required decel > -3.5 m/s² cap                        [Verified design]
    │       └── G1.3 Configuration altered (fork parameters, aggressive follow profile,
    │                experimental/e2e mode, alpha long)                                  [Hypothesis]
    ├── G2: Driver does not intervene in time                           (L2)
    │   └── OR
    │       ├── B5 Distracted < DM alert threshold (≤ 5 s) at the critical moment       [Verified design]
    │       ├── B6 No FCW, or late FCW, because FCW shares perception with G1.1          [Verified design]
    │       └── B7 Over-trust / complacency; slow takeover                              [Supported]
    └── G3: Stock AEB/PCS does not prevent the collision                (L3)
        └── OR
            ├── B8 PCS disabled by openpilot (radar-ACC + alpha long)                    [Verified code]
            ├── B9 Stock AEB speed/scenario limits (high-speed stationary targets)       [Hypothesis]
            └── B10 Stock AEB intervention suppressed or mitigated only                  [Hypothesis]
```

**Minimal cut sets** (every one must be broken):

- {B1 or B2 or B3 or B4 or G1.2 or G1.3} **∧** {B5 or B6 or B7} **∧** {B8 or B9 or B10}
- **Common cause:** B6 (FCW) depends on the same perception as G1.1. **L1 and L2-warning are not independent.**

## 5. STPA — unsafe control actions

| Controller | Control action | Not provided | Provided unsafely | Wrong timing | Too short / too long |
|---|---|---|---|---|---|
| Longitudinal planner | Brake command | **UCA-1**: no braking when a stationary in-lane vehicle is ahead | — | **UCA-2**: braking starts after the point where -3.5 m/s² is sufficient | **UCA-3**: braking capped at -3.5 m/s² when more is needed |
| openpilot alerts | FCW | **UCA-4**: no FCW because perception missed the obstacle | — | **UCA-5**: FCW at TTC below driver reaction + braking time | — |
| DM | Distraction alert | **UCA-6**: no alert while the driver is looking away < 5 s at the critical moment | — | **UCA-7**: escalation (13 s to terminal) slower than the hazard develops | — |
| openpilot car interface | Radar ECU / PCS state | — | **UCA-8**: disables stock PCS (radar-ACC + alpha long) | — | — |
| Driver | Brake / steer | **UCA-9**: no takeover | — | **UCA-10**: takeover too late | — |

## 6. Fishbone

| Category | Candidate causes |
|---|---|
| Perception | Stationary-object recall at long range; emergency-vehicle appearance (flashing lights, odd shapes, angled parking); night/glare; low-contrast or partially occluded targets |
| Fusion & lead selection | Vision-gated radar use at speed; `lead_prob > 0.5` gate; sanity checks reject mismatched tracks; stationary radar returns treated as clutter |
| Planning & control | -3.5 m/s² hard cap; jerk-limited ramp-up; MPC follow-distance personality; experimental (e2e) mode behavior |
| Actuation & vehicle | Stock PCS silenced on radar-ACC Toyotas under alpha long; actuator delay; hybrid vs ICE brake response |
| Driver monitoring & HMI | 5/8/13 s vision-policy timings; FCW coupled to the same perception; wheel-touch fallback 5/15/25 s |
| Driver & use | Automation complacency; secondary tasks; using the system outside its stated limitations |
| Configuration & process | Forks change parameters with no safety analysis; no config identity in crash data; limitations only *documented*, not engineered |
| Environment & scenario | Emergency scenes on the shoulder or partly in the lane; queue tails on highways; cut-out reveals; curves/crests limiting sight distance |

## 7. 5-Why per root-cause branch

**Branch L1 — openpilot did not stop in time**
1. Why did it not stop? → It did not brake hard enough, early enough.
2. Why? → The obstacle was confirmed too late for -3.5 m/s² to be enough (§3.1).
3. Why too late? → At speed, stationary-target detection depends on vision confidence. Radar alone is not trusted above 4 m/s, to avoid phantom braking on stationary clutter (bridges, signs, parked cars).
4. Why is that acceptable upstream? → The design relies on the driver for stopped vehicles. `docs/LIMITATIONS.md:37-38` lists "vehicles in the same lane that are not moving" and "abrupt braking" as limitations.
5. **Root cause RC-02:** no requirement sets a minimum detection range or required braking performance for stationary in-lane targets. The hazard is handled only by information to the user (control tier 5).

**Branch L2 — driver did not intervene**
1. Why? → The driver was not looking or reacted late.
2. Why not caught? → DM allows up to 5 s of eyes-off before the first alert. FCW did not fire, or fired late.
3. Why did FCW not fire early? → FCW uses the same perception output (`modelProb > 0.9`) that missed or late-detected the obstacle.
4. Why is that accepted? → FCW was designed as a planner by-product, not an independent monitor. DM timings are tuned for nuisance rate, not linked to the time the hazard takes to develop.
5. **Root causes RC-03 and RC-04:** the warning channel is not independent of the primary perception, and DM thresholds are not derived from hazard timing (speed, scene).

**Branch L3 — stock AEB did not save it**
1. Why? → On a radar-ACC Toyota with alpha long, stock PCS is unavailable.
2. Why? → openpilot disables the radar ECU so it can own longitudinal control, and declares PCS off (`interface.py:126-131`, `toyotacan.py:103-107`).
3. Why allowed? → It is an opt-in "alpha" feature with a user warning. There is no interlock tying it to a replacement AEB.
4. Why can forks enable it more widely? → Forks can expose or default-on any toggle, and the panda safety mode does not stop the radar from being disabled.
5. **Root cause RC-01:** enabling openpilot longitudinal on some platforms removes an independent OEM safety mechanism, with no equivalent replacement and no configuration interlock.

**Branch process — why forks matter**
- **Root cause RC-05:** safety-relevant parameters (follow distance, braking limits, mode logic, alpha features) can be changed outside any assured configuration, and crash data does not reliably record which configuration was running.

## 8. SOTIF triggering conditions

| ID | Triggering condition | Performance limitation exposed | Known in a LionDriver SOTIF analysis? |
|---|---|---|---|
| TC-01 | Stationary vehicle in lane at ego speed ≥ 70 km/h | Detection range vs. -3.5 m/s² stopping distance | No — SOTIF analysis not yet started |
| TC-02 | Lead vehicle cuts out, revealing a stopped vehicle at < 100 m | Reaction distance; tracker re-acquisition | No |
| TC-03 | Emergency vehicle stopped on the shoulder or partly in the lane, flashing lights, night | Model recall on atypical appearance; glare | No |
| TC-04 | Queue tail on a highway after a curve or crest | Sight-distance limit | No |
| TC-05 | Slow-moving vehicle (≪ ego speed, e.g. farm equipment, crash-damaged car) | Closing-speed estimation | No |
| TC-06 | Partially-in-lane obstacle (lateral offset 0.5–1.5 m) | Lane assignment / `yRel` gating | No |

## 9. Root-cause register

| RC ID | Root cause | Category | Tag | Evidence | Confirmation test |
|---|---|---|---|---|---|
| RC-01 | Alpha longitudinal on radar-ACC Toyotas silences the stock radar and declares PCS off, removing the independent AEB barrier with no replacement or interlock | CFG, SYS | **Verified** (code); vehicle effect **Supported** | `interface.py:93-106, 126-131`; `carcontroller.py:294-295`; `toyotacan.py:101-110` @ 229dc70 | Bench/vehicle: confirm PCS is unavailable with DISABLE_RADAR set (CA-001) |
| RC-02 | No performance requirement for stationary/slow in-lane targets. Detection range plus the -3.5 m/s² cap can make avoidance impossible at highway speed; the hazard is handled only by documentation | PERF, ML, PROC | **Verified** (design); field contribution **Supported** | `radard.py:24, 98-100, 156-171`; `values.py:43`; `toyota.h:208-209`; `LIMITATIONS.md:37-38` | Stopped-vehicle scenario suite (CA-002) |
| RC-03 | FCW is not independent of the primary perception (common-cause failure with L1) | SYS | **Verified** (design) | `long_mpc.py:338-340`; `selfdrived.py:442-445` | Scenario suite: measure FCW TTC distribution (CA-002/CA-005) |
| RC-04 | DM escalation timings (5/8/13 s) are not derived from hazard timing; complacency is foreseeable | MISUSE, SYS | **Verified** (timings); complacency **Supported** | `policy.py:34-36` | DM timing analysis against closing scenarios (CA-006) |
| RC-05 | Safety-relevant configuration can drift (forks, toggles), and the active configuration is not reliably recorded | CFG, PROC | **Supported** | Press reports of a FrogPilot-equipped vehicle; NHTSA scope extends to forks | Config-identity logging review (CA-008) |
| RC-06 | Model recall on emergency vehicles and atypical stationary targets at range | ML, PERF | **Hypothesis** | Fatal case involved an emergency vehicle | Targeted replay / dataset evaluation (CA-003) |

> Per PROCESS §5.5, this RCA cannot close while RC-06 is a hypothesis. The corrective actions are therefore written to cover RC-06 whether or not it is confirmed (CA-002, CA-003, CA-004).

## 10. Escape-point analysis

| Lifecycle step | Should it have caught this? | Why not? | Preventive action |
|---|---|---|---|
| HARA | Yes — "collision with in-lane obstacle while ACC engaged" is a core hazardous event | LionDriver HARA not yet performed; upstream has none | PA-01: seed the HARA from `HAZARD-LOG.md` |
| SOTIF analysis | Yes — stationary targets are a textbook triggering condition | Not yet performed | PA-02: SOTIF triggering-condition catalog starting with TC-01…06 |
| Safety requirements | Yes — detection range / braking performance | None exist | CA-002, CA-004 create them |
| Design / architecture | Yes — independence of L1/L2/L3 | Upstream architecture uses the driver as the only independent layer | CA-001, CA-005 |
| Verification & validation | Yes — stopped-vehicle scenarios | Upstream regression is replay-based on typical drives; no stationary-target acceptance criteria | CA-002 |
| Configuration management | Yes — alpha features and forks | No assured configuration defined | CA-001, CA-008 |
| Field monitoring | Yes — fork incidents | No process existed | **This process (LD-SAF-PRC-001)** |

## 11. Feedback to analyses

| Finding | Hazard-log ID | Analysis to update |
|---|---|---|
| Collision with stationary/slow in-lane vehicle while longitudinal engaged | HZ-001 | HARA, SOTIF |
| Loss of stock AEB/PCS due to openpilot configuration | HZ-002 | HARA, FSC |
| Late or absent FCW from common-cause perception failure | HZ-003 | HARA, FSC |
| Driver unavailable at the critical moment (DM threshold / complacency) | HZ-004 | HARA (controllability), SOTIF (misuse) |
| Unassured configuration / fork parameter drift | HZ-005 | Safety plan, configuration management |
| Unintended / phantom hard braking (side effect of fixes to HZ-001) | HZ-006 | HARA, SOTIF |
| Rear-end collision by a following vehicle due to stronger braking | HZ-007 | HARA |

## 12. Proposed actions

See [`CORRECTIVE-ACTIONS.md`](CORRECTIVE-ACTIONS.md).

## 13. Review

| Role | Name | Date | Result |
|---|---|---|---|
| RCA lead | Project maintainer | 2026-10-10 | Draft |
| Independent reviewer | — | — | **Pending** |
| Safety manager | — | — | Pending |
