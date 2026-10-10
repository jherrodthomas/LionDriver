# WP-C-02 ODD and Intended Functionality Specification

| Field | Value |
|---|---|
| Work product | WP-C-02 ODD and intended functionality specification |
| Standard reference | ISO 21448:2022 §5 (specification of the functionality); ISO 26262-3:2018 §5 (item definition input); ISO/PAS 8800:2024 (input space definition); ASPICE 4.0 SYS.1; SAE J3016 and ISO 34503 (ODD taxonomy, informative) |
| Version | 0.1 |
| Status | Draft |
| ASIL / scope | SOTIF; input to HARA exposure ratings |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1) |
| Approver | Safety manager |
| Baseline | `8b8c6ae` |

## 1. Purpose

This document specifies, for the reference configuration (2020 Toyota Corolla LE, US, `TOYOTA_COROLLA_TSS2`, openpilot longitudinal; see [WP-C-01](WP-C-01-item-definition.md)):

1. the operational design domain (ODD) in which LD-SDA is intended to be used and for which claims are made;
2. the intended functionality: the nominal behaviour of each function F-01…F-07, the driver's role and the system limits;
3. what happens when the vehicle leaves the ODD;
4. a recommendation on Experimental Mode (GAP-18, [WP-C-01](WP-C-01-item-definition.md) OI-8, [WP-M-01](../01-management/WP-M-01-assurance-strategy.md) D-08).

The ODD is the scope of every SOTIF analysis ([WP-C-05](WP-C-05-sotif-hazard-identification.md), [WP-C-06](WP-C-06-sotif-insufficiencies-triggering-conditions.md)) and of validation ([WP-V-02](../06-validation/WP-V-02-sotif-vv-strategy.md)). The HARA situation catalogue ([WP-C-03](WP-C-03-hara.md) §3) is rated against it.

**Important:** today the system itself enforces almost none of the ODD bounds below (§6). The ODD is enforced mostly by the driver, through user information ([WP-O-03](../09-production-operation/WP-O-03-user-information-safety-warnings.md)). The functional modifications that add system-side enforcement are in [WP-C-07](WP-C-07-sotif-functional-modifications.md).

## 2. Sources

| Source | Use |
|---|---|
| `docs/LIMITATIONS.md` | Upstream limitations for ALC/LDW (lines 8-19), ACC/FCW (lines 27-43), DM (lines 51-56) |
| `opendbc_repo/opendbc/car/interfaces.py:23-26` | `V_CRUISE_MAX = 145` km/h; `MAX_CTRL_SPEED = (145 + 4)` km/h ≈ 41.4 m/s; `ACCEL_MAX/MIN = +2.0/−3.5` m/s² |
| `openpilot/selfdrive/controls/lib/drive_helpers.py:9-14` | `MAX_CURVATURE = 0.2` 1/m; `MAX_LATERAL_ACCEL_NO_ROLL = 3.0` m/s²; lateral jerk 5 m/s³ |
| `opendbc_repo/opendbc/car/lateral.py:10` | `ISO_LATERAL_ACCEL = 3.0` m/s² |
| `openpilot/selfdrive/controls/lib/ldw.py:7, 21` | `LDW_MIN_SPEED = 31 mph` (13.9 m/s) |
| `openpilot/selfdrive/controls/lib/desire_helper.py:8-9` | Lane change assist ≥ 20 mph, max 10 s |
| `openpilot/selfdrive/monitoring/policy.py:29` | DM alerts only above 2.8 m/s (10 km/h) |
| `opendbc_repo/opendbc/car/toyota/interface.py:52, 115` | TSS2 → stop-and-go; `minEnableSpeed = -1` (engage from standstill) |
| `openpilot/selfdrive/controls/lib/longitudinal_planner.py:19-22` | Chill cruise acceleration 1.6→0.6 m/s² with speed, cruise decel −1.2 m/s² |

## 3. Reference ODD (proposed)

The reference ODD has two parts. **ODD-H** (limited-access highway) is the core use case. **ODD-A** (arterial and rural roads) is included because the HARA exposure ratings for OS-03 and OS-04 assume it. Anything not listed as included is excluded.

### 3.1 ODD taxonomy

| Category | Attribute | Included (ODD-H) | Included (ODD-A) | Excluded | Basis |
|---|---|---|---|---|---|
| Road type | Functional class | Limited-access divided highway (Interstate, freeway, expressway) incl. merge/weave lanes | Divided and undivided multi-lane arterials; two-lane rural highways with paved shoulders | Residential streets, parking lots, private roads, unpaved roads, on/off ramps with tight curvature, roundabouts, school zones | `LIMITATIONS.md:14, 19, 34`; HARA OS-01…OS-04 |
| Road type | Intersections | None (grade-separated) | Signalised and stop-controlled intersections **traversed with the driver controlling all stops and turns** | Turning at intersections under system control; unprotected turns; railway level crossings | `LIMITATIONS.md:35`; Chill mode does not stop for signals |
| Geometry | Horizontal curve radius | R ≥ v²/2.5 m/s² at the travel speed (table §3.2) | same | Tighter curves; ramps; hairpins | Controller limit 3.0 m/s² (`drive_helpers.py:14`) minus 0.5 m/s² margin; torque authority not yet characterised (GAP-04) |
| Geometry | Longitudinal grade | ≤ 6 % | ≤ 6 % | Steeper grades; "hills" per `LIMITATIONS.md:19, 40` | Pitch compensation in `carcontroller.py` (±1.5 m/s²); to be validated |
| Geometry | Vertical curves | Crests with stopping sight distance per design standards | same | Blind crests below design sight distance | Camera/radar range at crests (WP-C-06 TC-17) |
| Geometry | Cross-slope / banking | ≤ 6 % | ≤ 6 % | "Highly banked roads" | `LIMITATIONS.md:16`; roll compensation `drive_helpers.py:37-38` |
| Geometry | Lane width | 3.0–3.9 m | 2.9–3.9 m | Narrow lanes < 2.9 m; lane shifts in work zones | `LIMITATIONS.md:19` ("narrow") |
| Lane markings | Presence | Visible longitudinal markings on at least one side, US MUTCD style | same | Unmarked roads; faded or missing markings over long sections; conflicting old/new markings | End-to-end model; markings not strictly required but needed for validated performance |
| Speed | Ego speed | 0 – 120 km/h (75 mph), not above the posted limit | 0 – 90 km/h (55 mph), not above the posted limit | > 120 km/h. Note: the system allows engagement up to 149 km/h (`MAX_CTRL_SPEED`) | HARA OS-01 rated to 120 km/h; `LIMITATIONS.md:36` (speed limits not detected) |
| Speed | Stop-and-go | Following a lead to standstill and auto-resume | same | Starting from standstill with no lead in front (e.g. at a stop line) | `interface.py:52, 107`; HE-03.2 |
| Weather | Precipitation | None or light rain | same | Moderate/heavy rain, snow, sleet, hail, freezing rain | `LIMITATIONS.md:10, 29` |
| Weather | Visibility | ≥ 200 m | ≥ 150 m | Fog, smoke, dust, spray reducing visibility below the bound | `LIMITATIONS.md:10` |
| Weather | Wind | Normal | Normal | Strong cross-wind (warnings issued or gusts noticeable) | `LIMITATIONS.md:16` |
| Weather | Ambient temperature | Within the device operating range (to be specified from device data, OI-3) | same | "Extremely hot or cold"; device overheat (`events.py:800`) | `LIMITATIONS.md:17, 41` |
| Lighting | Illumination | Day; dusk/dawn; night with headlights (with or without street lighting) | same | Low sun directly in the camera field of view; oncoming high-beam glare; tunnels (not validated) | `LIMITATIONS.md:18, 42, 53-54` |
| Road surface | Type and condition | Paved asphalt or concrete; dry or wet | same | Snow, ice, standing water, gravel, oil, metal plates, bridge expansion joints with surface change, toll plazas | `LIMITATIONS.md:33`; HARA OS-11 (wet in ODD) |
| Traffic | Motor vehicles | Mixed traffic incl. trucks; lead vehicles; cut-ins from adjacent lanes | same + oncoming traffic on undivided roads | Emergency-vehicle scenes, police stops, crash scenes | `LIMITATIONS.md:37, 39` |
| Traffic | Stationary objects in lane | Not handled reliably; driver must act | same | — (driver responsibility, see §5) | `LIMITATIONS.md:37` |
| VRUs | Pedestrians, cyclists | Rare (shoulder only) | Present at road edge and crossings; **system does not respond to VRUs reliably; driver must act** | Shared spaces, dense urban pedestrian areas | `LIMITATIONS.md:34`; HE-01.3 |
| Geography | Region | Continental US, right-hand traffic, US MUTCD signs and markings | same | Other countries; left-hand traffic | Reference configuration (WP-M-01 §3.1) |
| Infrastructure | Special zones | — | — | Construction / work zones, restricted lanes, toll booths, border crossings, ferries, car washes | `LIMITATIONS.md:15, 33` |
| Connectivity | Network | Not required | Not required | — | AOU-11: no safety function depends on network |
| Vehicle state | Reference vehicle | Maintained, unmodified, no active DTCs, VSC on, device mounted and calibrated | same | Towing a trailer; roof loads affecting cross-wind; spare tyre fitted; snow chains | AOU-08, AOU-09, AOU-10 |
| Driver state | Driver | Licensed, briefed, attentive, face visible to the driver camera, hands near the wheel | same | Driver not visible to DM; impaired, drowsy or distracted driver | AOU-06; `LIMITATIONS.md:53-56` |

### 3.2 Minimum curve radius versus speed

R_ctrl = v² / 3.0 m/s² is the curve the controller can command at its lateral acceleration limit (`drive_helpers.py:14`). R_ODD = v² / 2.5 m/s² is the proposed ODD bound (0.5 m/s² margin for controller error, road crown and wind). Both assume the EPS torque authority suffices; that is not yet characterised (GAP-04, AOU-01).

| Speed (km/h) | Speed (m/s) | R_ctrl (m) | R_ODD (m) |
|---|---|---|---|
| 40 | 11.1 | 41 | 49 |
| 60 | 16.7 | 93 | 111 |
| 80 | 22.2 | 165 | 198 |
| 100 | 27.8 | 257 | 309 |
| 120 | 33.3 | 370 | 444 |

The planner in Chill mode does not reduce speed ahead of curves; it only limits acceleration in turns (`longitudinal_planner.py:37-50`). Entering a curve tighter than R_ODD at the current speed is therefore a driver task.

## 4. Intended functionality

### 4.1 Nominal behaviour per function

| Function | Nominal behaviour inside the ODD | Not intended / not provided |
|---|---|---|
| F-01 Lateral control | Keeps the vehicle near the centre of the lane by commanding steering torque from the driving model's desired curvature; lateral acceleration ≤ 3.0 m/s², jerk ≤ 5 m/s³. Assisted lane change when the driver signals and nudges the wheel, above 20 mph, within 10 s (`desire_helper.py:8-9`) | Blind-spot checking (the Corolla LE reference vehicle has no BSM input expected; the driver checks), turning at intersections, evasive steering, steering at standstill |
| F-02 Longitudinal control (Chill mode) | Holds the set speed; follows the lead vehicle (radar track fused with vision, `radard.py:153-165`) at the selected personality gap; stops behind a stopping lead and resumes when it moves; acceleration −3.5…+2.0 m/s², cruise acceleration 1.6→0.6 m/s² by speed | Stopping for traffic lights, stop signs, pedestrians, stationary vehicles not previously tracked as lead; detecting speed limits (`LIMITATIONS.md:35-37`); emergency braking (stock PCS remains responsible) |
| F-03 Engagement and modes | Engages only through the stock cruise controls; the envelope grants authority on the PCM cruise rising edge. Driver brake or cancel disengages; gas overrides longitudinal (does not disengage, `DisengageOnAccelerator` default `0`, `common/params_keys.h:35`); steering input overrides lateral | Engagement without driver action; staying engaged after brake |
| F-04 Driver monitoring | Above 2.8 m/s, monitors driver attention by camera; escalating alerts 5/8/13 s (vision) or 5/15/25 s (wheel-touch fallback); force deceleration and lockout on no response (`policy.py:29-44`) | Exact alertness measurement (`LIMITATIONS.md:49`); monitoring below 10 km/h |
| F-05 Driver information | Shows engagement state, alerts (warning, soft disable, immediate disable, no entry) on the device with sounds; cluster LKAS HUD | Explaining every limitation in real time |
| F-06 FCW | Visual + acoustic "BRAKE!" alert when the model predicts hard braking or the planner predicts a collision (`selfdrived.py:441-445`, `events.py:493`) | Braking; the stock PCS remains responsible for AEB |
| F-07 LDW | When not laterally engaged, above 31 mph and no turn signal in the last 5 s, warns when the vehicle drifts towards a visible lane line (`ldw.py:7-35`) | Steering correction |

### 4.2 Driver role

The driver:

1. is responsible for the driving task at all times (SAE Level 2);
2. decides whether the current situation is inside the ODD, and engages only inside it;
3. supervises continuously with eyes on the road and hands near the wheel, and intervenes immediately when the system does not handle a situation;
4. handles all items listed as "not intended" in §4.1: traffic signals, stop signs, VRUs, stationary obstacles, intersections, blind-spot checks, speed limits, curves tighter than R_ODD;
5. disengages before leaving the ODD (§6) and responds to every take-over request;
6. keeps the vehicle and device in the state required by AOU-08…AOU-10.

### 4.3 System limits (as inherited)

| Limit | Value | Source |
|---|---|---|
| Max steering torque request | 1500 raw (physical value TBD) | `opendbc_repo/opendbc/safety/modes/toyota.h:173` |
| Lateral acceleration command | ≤ 3.0 m/s² (roll-compensated) | `drive_helpers.py:14, 37-38` |
| Max curvature | 0.2 1/m | `drive_helpers.py:9` |
| Acceleration command | −3.5 … +2.0 m/s² | `toyota.h:208-209`, `interfaces.py:25-26` |
| Engagement speed | From standstill | `toyota/interface.py:115` |
| Max control speed | ≈149 km/h: warning + no-entry only | `interfaces.py:24`, `selfdrive/car/car_events.py:126`, `events.py:989-996` |
| LDW active | > 31 mph, not laterally engaged | `ldw.py:7, 21` |
| DM active | > 2.8 m/s | `policy.py:29` |

## 5. Behaviour at the ODD boundary

### 5.1 Principle

LD-SDA has **no ODD monitor**. The driver detects ODD exit and disengages. The system detects only a few exit conditions, mostly indirectly through component diagnostics.

### 5.2 Exit conditions and current reaction

| ODD exit | Detected by system? | Current reaction | Gap / proposal |
|---|---|---|---|
| Speed > 120 km/h (reference bound) | No | None | FM-07 in WP-C-07 (speed bound enforcement) |
| Speed > 149 km/h | Yes, `speedTooHigh` (`car_events.py:126`) | Warning + no-entry; **stays engaged** (`events.py:989-996`) | GAP-19; FM-07 |
| Curve tighter than R_ODD | Partly: `steerSaturated` warning when the controller saturates (`events.py:619`) | Warning only | Driver task |
| Missing/faded markings, construction zone, road type change, intersection | No | None | Driver task; FM-08 (map/road-type, if feasible) |
| Heavy rain, fog, glare, camera blocked | Not directly; possible model degradation without gating | None specific (GAP-22) | FM-09 (uncertainty monitor) |
| Snow / ice | No | None | Driver task |
| Device mis-calibration | Yes, `calibrationInvalid` (`events.py:816`) | Soft disable | Implemented |
| Device overheat | Yes, `overheat` (`events.py:800`) | Soft disable | Implemented |
| Driver not visible to DM | Yes (no face / high uncertainty) | Wheel-touch fallback (`policy.py:77-78`) | GAP-21 |
| Vehicle state (VSC off, door, seatbelt, gear) | Yes (`espDisabled`, `doorOpen`, `seatbeltNotLatched`, `wrongGear`) | Soft disable / no entry | Implemented |

### 5.3 Required behaviour at ODD exit

- If the system detects an exit: it shall give a take-over request and shall not remain engaged indefinitely (see FM-07). Engagement outside the ODD shall be prevented where the system can detect it (no-entry).
- If the system does not detect an exit: the driver disengages. User information (WP-O-03) must state the ODD in terms the driver can recognise (road type, weather, speed).

## 6. Experimental Mode recommendation (GAP-18, D-08, WP-C-01 OI-8)

### 6.1 Facts

- Upstream commit `f21bfc3` makes `ExperimentalMode` default `"1"` without user confirmation (`openpilot/common/params_keys.h:43`).
- In Experimental Mode the driving model's desired acceleration joins the planner's candidates and the minimum is used (`longitudinal_planner.py:132-149`). The model can therefore only make the vehicle slower or brake harder than the Chill plan, except that the cruise acceleration limit is raised to `ACCEL_MAX` (2.0 m/s²) instead of the speed-scheduled 1.6→0.6 m/s² (`longitudinal_planner.py:37-38`), and AccelBoost can add up to +0.2 m/s² after gas overrides.
- The UI states: "openpilot will drive as it thinks a human would, including stopping for red lights and stop signs … Mistakes should be expected" (`selfdrive/ui/layouts/settings/toggles.py:155-158`).
- `docs/LIMITATIONS.md:35` says traffic signs and lights are not detected. The two statements contradict each other.
- The HARA has not rated Experimental Mode specific events (WP-C-03 OI-5).

### 6.2 Hazards it introduces or changes

| Effect | Hazard link |
|---|---|
| False stops or unexpected braking for misread signals, shadows or objects | H-04 / SH-04 |
| Driver over-trust that the car stops at red lights and stop signs; when it does not, the vehicle enters the intersection | SH-09 (WP-C-05) |
| Higher cruise acceleration (2.0 m/s²) | H-03 / SH-03 |
| Mode confusion between Chill and Experimental behaviour | WP-C-08 MC-09 |

### 6.3 Options

| Option | Description | Assessment |
|---|---|---|
| A | Exclude Experimental Mode from the reference ODD: default `"0"` and toggle locked or hidden in reference builds; Chill mode only | Removes SH-09 and the e2e-specific part of SH-03/SH-04 from the claimed scope. Low effort (FM-01 in WP-C-07) |
| B | Include it after HARA re-rating (OI-5), SOTIF analysis of traffic-control handling and validation against WP-V-02 targets | Large validation effort; ML longitudinal behaviour without uncertainty gating (GAP-22) |
| C | Keep the upstream default | Not consistent with WP-M-01 §3.2 claim G0 or with `LIMITATIONS.md`; no hazard assessment exists |

### 6.4 Recommendation for the maintainer's decision

**Recommendation: Option A.** Experimental Mode is outside the reference ODD (Chill mode only) until it has been analysed and validated. The default should be reverted for reference-configuration builds and the toggle disabled. If the project later wants Experimental Mode, it enters the scope through option B with an impact analysis ([WP-M-12](../01-management/WP-M-12-impact-analysis.md)).

Decision record: **pending** — maintainer decision under D-08 / WP-C-01 OI-8.

## 7. Open items

| ID | Item | Owner | Needed by |
|---|---|---|---|
| OI-1 | Maintainer decision on Experimental Mode (§6.4) | Maintainer | G1 |
| OI-2 | Characterise EPS torque authority and confirm R_ODD (§3.2); adjust if lateral capability < 2.5 m/s² at some speeds | Safety engineer | G2 |
| OI-3 | Obtain the device operating temperature range and set the ambient temperature bound | HW lead | G1 |
| OI-4 | Confirm ODD-A inclusion with the HARA owner (OS-03/OS-04 exposure depends on it); if ODD-A is dropped, re-rate exposure | HARA owner | G1 |
| OI-5 | Confirm grade and banking bounds (6 %) by vehicle test | Safety engineer | G2 |
| OI-6 | Specify the training-data ODD of the driving model (not available from upstream; GAP-22) and compare with this ODD ([WP-C-11](WP-C-11-ai-system-definition-and-safety-requirements.md)) | ML lead | G2 |
| OI-7 | Feed the ODD in driver-recognisable terms into WP-O-03 user information | Maintainer | G5 |
