# Physics studies, round 4: the plan for ten more

| Field | Value |
|---|---|
| Purpose | Plan ten physics studies that follow the twenty of rounds 2 and 3 ([round 2](physics-plan.md), [round 3](physics-plan-round3.md)): what each answers, how, with which inputs, checks and picture, and in what order. They cover triggering conditions (TCs) no study has touched yet, or only a Blender render has: the night, grades and curves, emergency vehicles, the driver's hands, the steering's torque, the radar's cover, and the traffic ahead changing lanes or braking hard |
| Status | Planned 2026-11-20; nothing built. AI-drafted (Claude, AI assistant; I0 under WP-M-02 §3.3); not reviewed |
| Credit | None. Every study is a design aid, synthetic (DSR-12), with no evidence credit (DQ-413, WP-V-02 §5.3, DQ-139). A result that would move an ODD limit or a requirement goes to the lead as a register question; the study itself does not move it |
| Lead decisions needed | **None to start.** Phases A and B run in existing environments. Phase C adds one tool, openpilot's own MPC solver (acados, from the `comma-deps-acados` wheel openpilot's `uv.lock` pins), as a new tool entry; that is a reversible technical choice. Inputs with no public source (raw torque scales, the radar cover's material) are T1 tasks, and the study gives a band until they come |

## 1. The ten at a glance

Numbered after the first twenty. Phase A reuses what is built with public data; phase B is statics and code
readings; phase C puts openpilot's longitudinal planner in the loop.

| # | Study | Question it answers | Safety item | Builds on | Phase | Effort |
|---|---|---|---|---|---|---|
| 21 | A stopped car beyond the headlights | At night on an unlit road, how far do low beams light a dark stopped car's rear, against the 149 m the item needs to stop from 110 km/h? | TC-08, TC-20, KS-05 | Study 11's pixel sizes; study 16's low beams and camera | A | 1 session |
| 22 | Grades and sag curves | Does a 6 % downhill eat into the item's −3.5 m/s² bound beyond the pitch compensation, and do the headlights light a stopped car at the bottom of a sag curve? | TC-16, TC-17 | Study 12's vertical curves; study 21's beams | A | 1 session |
| 23 | A lead hidden on the inside of a curve | On the ODD's tightest curve, where does a lead at the follow gap sit in the camera's frame, and how far does a barrier or cutting on the inside hide it? | TC-35, TC-14 | WP-C-02 §3.2 curve bound; camera intrinsics (`camera.py`) | A | ½ session |
| 24 | Emergency beacons at night | Do flashing beacons pump the camera's auto exposure, how much glare does each flash add, and how close does lane centring pass a car stopped on the shoulder? | TC-36, TC-02 | The ported auto exposure (study 10); study 9's veiling glare | A | 1 session |
| 25 | A weight on the steering wheel | How heavy a weight on the rim reads as the driver steering, and so as the driver engaged, and how far does the car drift while the controller fights it? | TC-25 | opendbc's Toyota threshold; `policy.py`; study 2's single-track car | B | 1 session |
| 26 | Steering torque for the ODD's curves | Does the EPS's command limit cover the aligning torque at the curve bound, with road crown and the crosswind case added? | GAP-04, TC-14, TC-15 | Study 5's crown; study 2's crosswind; opendbc's `STEER_MAX` | B | 1 session |
| 27 | Water, ice and slush on the radar cover | How much 77 GHz signal does a film on the bumper absorb, and what range does the radar lose? | TC-03, TC-04 | Study 11's radar equation | B | ½ session |
| 28 | A close cut-in | A car merges at a 0.5–1.5 s gap: what braking does openpilot's planner ask for, against the item's bound and the stock PCS? | TC-07 | openpilot's `long_mpc.py` | C | 1–2 sessions |
| 29 | A cut-out reveals a stopped car | The lead swerves round a stopped car at the follow gap: how much braking does the reveal need, and from which speeds is the item's bound enough? | TC-09, TC-08 | Study 28's planner | C | 1 session |
| 30 | A lead braking hard | A lead brakes at 6–9 m/s² while the item is held to 3.5: what gap is left, or at what speed does it hit, given the driver's reaction? | TC-33 | Study 28's planner; study 3's friction | C | 1 session |

**Order.** Phase A first: four studies on built models with published data. Phase B is statics and code readings
that pin the lines they read, as study 20 did. Phase C installs the planner's solver and runs it; if it will not
build, the three studies fall back to closed forms on the planner's own constants (§4) and say so. Each phase ends
with its CI checks green and a results page.

## 2. Phase A: reuse what is built

### 21. A stopped car beyond the headlights (TC-08, TC-20, KS-05)

- **Framing.** Study 11 found the model must take a stopped car at 149 m for the item to stop on its own. By day
  that is a size question; at night on an unlit road it is a light question too.
- **Method.** Low-beam intensity toward the lane ahead, from the regulation's test points, lights a car's rear;
  its luminance is the illuminance times a dark paint's reflectance, with its reflectors and unlit tail lights as a
  second case. Compare with the road's luminance in the same light, through study 16's camera and exposure, and
  read the contrast against distance. Repeat with high beams, and at 120 km/h for the over-speed case (TC-20).
- **Inputs.** UN R149 (formerly R112) low- and high-beam test points; published car-paint and retroreflector
  values; study 16's camera model and thresholds.
- **Checks.** Inverse square from the lamp by hand; with no lamp, no contrast; study 16's road luminance back on a
  dry road.
- **Picture.** Contrast of the stopped car against distance, low and high beam, with the 149 m stop and study 11's
  pixel sizes.
- **Feeds.** KS-05 night conditions; WP-C-02's lighting row. A gap at the ODD's speed goes to the lead.

### 22. Grades and sag curves (TC-16, TC-17)

- **Method.**
  - **Grade:** on the ODD's 6 % bound gravity adds about 0.59 m/s² along the road. Read the pitch compensation in
    `carcontroller.py` (±1.5 m/s²) and find what braking is left for the item downhill, and what the car does
    uphill at its acceleration bound.
  - **Sag:** a sag curve is built to AASHTO's headlight sight distance (lamp at 0.6 m, beam 1° up). Put the road
    camera and study 21's beams on it, and find where a stopped car at the bottom is lit and in view.
- **Inputs.** WP-C-02 §3.1 grade bound; `carcontroller.py`; AASHTO's sag K values and headlight model; study 3's
  friction.
- **Checks.** Gravity along a 6 % grade by hand; AASHTO's sag table back from the formula; on a flat road, study
  21's numbers.
- **Picture.** The sag in profile with the beam and the sight line; braking left against grade.
- **Feeds.** WP-C-02 OI-5 (grade to be confirmed); TC-16, TC-17.

### 23. A lead hidden on the inside of a curve (TC-35, TC-14)

- **Method.** On a curve at the ODD's bound (R = v²/2.5 m/s²) a lead at the follow gap sits off the camera's axis
  by about half the arc angle. Find that angle at each speed against the road camera's frame and the model's input
  crop. Then AASHTO's horizontal sight line offset gives how far a barrier or cutting on the inside, at a given
  offset from the lane, hides a lead or a stopped car.
- **Inputs.** WP-C-02 §3.2; the follow gaps in `long_mpc.py`; camera intrinsics; AASHTO's horizontal sight
  distance model.
- **Checks.** The chord angle by hand; AASHTO's own table back from the formula.
- **Picture.** A top-down curve with the lead, the frame's edges and the sight line past the barrier.
- **Feeds.** TC-35; KS test conditions for curves with barriers.

### 24. Emergency beacons at night (TC-36, TC-02)

- **Method.** A stopped emergency vehicle's LED beacons flash at 1–4 Hz. Run them through the ported auto exposure
  of study 10 and study 9's veiling glare, from 200 m to passing: does the exposure pump with the flashes, and how
  long is each frame washed out? Then the geometry of passing: lane centring keeps the car mid-lane, so the gap to a
  vehicle on a shoulder of a given width is fixed; compare with move-over guidance.
- **Inputs.** SAE J845 class 1 beacon intensities and flash rates; the exposure port; shoulder and lane widths.
- **Checks.** A steady lamp gives study 9's result; a flash slower than the exposure loop's time constant is
  followed, a faster one averaged.
- **Picture.** Exposure and glare against time while passing, with the flashes marked.
- **Feeds.** TC-36; KS night test conditions.

## 3. Phase B: statics and code readings

### 25. A weight on the steering wheel (TC-25)

- **Framing.** `policy.py` counts `steeringPressed` or `gasPressed` as the driver engaged, and in its wheel-touch
  policy that resets the alerts (with the distance bounds of TSR-634). Toyota sets `steeringPressed` when the
  driver's torque passes `STEER_THRESHOLD` (100, raw units).
- **Method.** A mass on the rim gives a torque of m·g·r·cos θ, where θ is the angle the hanging point makes with the horizontal. Sweep the mass and angle and find
  where it crosses the threshold. Then put that torque on study 2's single-track car and the plant's lane keeping:
  how far does the car drift, and does the controller's torque limit hold it? Pin the lines read, as study 20 did.
- **Inputs.** `opendbc_repo/opendbc/car/toyota/values.py`; `policy.py`; the rim's radius. The raw unit's scale to
  newton-metres has no public source: a band until a T1 measurement.
- **Checks.** No mass, no torque; the threshold crossing scales with 1/r.
- **Picture.** Torque against mass, with the threshold band; drift against time for the masses that cross it.
- **Feeds.** TC-25 (defeat devices); the DM's wheel-touch policy (WP-C-08 §5.4).

### 26. Steering torque for the ODD's curves (GAP-04, TC-14, TC-15)

- **Method.** The aligning torque at the rack is the front tyres' lateral force times their pneumatic trail plus
  the mechanical trail, from a brush tyre model. Add study 5's crown and study 2's crosswind case. Compare the
  steering torque needed with opendbc's `STEER_MAX` (1500, raw) and its rate limits, at each speed on the curve
  bound.
- **Inputs.** Corolla axle loads and steering geometry (vehicle spec); published trail and cornering stiffness
  values; opendbc's limits. The raw scale again needs a T1 measurement, so the result is a band.
- **Checks.** On a straight with no crown, no torque; the brush model's force against its linear limit by hand.
- **Picture.** Torque needed against speed on the curve bound, with and without crown and wind, against the limit
  band.
- **Feeds.** GAP-04 and AOU-01 (EPS torque authority); WP-C-02 §3.2's margin.

### 27. Water, ice and slush on the radar cover (TC-03, TC-04)

- **Method.** A film of water, ice or slush on the bumper cover is a lossy layer at 77 GHz. Its two-way loss
  follows from its permittivity (water from ITU-R P.527's double-Debye model, ice and wet snow from published
  values) and thickness, with the cover's reflection. Turn the loss into the radar's lost range with study 11's
  radar equation, and set it against where openpilot uses the radar (below 4 m/s within 25 m on its own, and in
  fusion with the model).
- **Inputs.** ITU-R P.527; published ice and wet-snow permittivity at 77 GHz; a band for the cover's material and
  thickness (T1).
- **Checks.** No film, no loss; the loss grows linearly with thickness in dB for a thick lossy film.
- **Picture.** Range lost against film thickness, water, slush and ice.
- **Feeds.** TC-03, TC-04; a note on where the radar's loss matters.

## 4. Phase C: openpilot's longitudinal planner in the loop

openpilot's longitudinal MPC (`long_mpc.py`) is generated with acados and casadi. openpilot's `uv.lock` pins acados
as the `comma-deps-acados` wheel, which downloads here. Phase C builds the solver from openpilot's own generator and
drives it with synthetic leads, behind a new tool entry. If the solver will not build, the three studies use the
planner's own constants instead (follow gaps 1.25, 1.45 and 1.75 s by personality; `COMFORT_BRAKE` 2.5 m/s²;
`STOP_DISTANCE` 6 m) and say so.

Every run clips the planner's output to the item's bounds and feeds a point-mass car with study 3's friction; the
stock PCS is a band of published AEB onset times, not a model.

### 28. A close cut-in (TC-07)

- **Method.** A car merges into the lane at a gap of 0.5–1.5 s and a speed 0–30 km/h below ours. The model's lead
  becomes valid after a latency band (the lead's probability crossing 0.5). Run the planner on the lead and read
  the braking it asks for, against the item's −3.5 m/s² and the PCS band.
- **Inputs.** `long_mpc.py`; latency band; published cut-in distributions for the gap and speed.
- **Checks.** A lead at the steady follow distance asks for no braking; the planner's stopping distance formula
  (`v²/(2·COMFORT_BRAKE)` plus the gap) back in steady state.
- **Picture.** The braking asked for over gap and speed difference, with the item's bound.
- **Feeds.** TC-07; KS cut-in conditions.

### 29. A cut-out reveals a stopped car (TC-09, TC-08)

- **Method.** The lead at the follow gap swerves out at a lateral rate from published lane-change data, revealing
  a stopped car. The model takes it after study 11's size band and the latency band. Run the planner and find the
  braking needed, and the speed at which the item's −3.5 m/s² stops being enough.
- **Inputs.** As study 28; study 11's detection range.
- **Checks.** A cut-out far ahead of the stopped car asks for the closed-form stop; at zero speed, nothing.
- **Picture.** Braking needed against speed, per personality, with the item's bound and the PCS band.
- **Feeds.** TC-09; the driver's role in the item's limits (WP-C-02 F-02).

### 30. A lead braking hard (TC-33)

- **Method.** A lead at the follow gap brakes at 6–9 m/s² (dry), or at study 3's wet limit. The item is held to
  −3.5 m/s². The driver takes over after a reaction time drawn from the DM's alert timing in `policy.py` and a
  published reaction band. Find the smallest gap, or the collision speed, for each personality.
- **Inputs.** As study 28; study 3's friction; DM timing from `policy.py` and WP-S-04.
- **Checks.** A lead braking at 3.5 m/s² or less leaves the steady gap; closed-form kinematics by hand for one case.
- **Picture.** The smallest gap or collision speed against lead braking, per personality.
- **Feeds.** TC-33; HE rows in the HARA for a hard-braking lead.

## 5. How the work is run

- **Where.** Studies 21–24 and 27 go in [`weather/`](weather/README.md) (pip, the `sim-weather` CI job). Studies 25
  and 26 go beside the plant (they use its car and lane keeping). Studies 28–30 go in a new `planner/` folder with
  their own lock file and CI step.
- **Every study** has a `params.yaml` entry with a source for each number, a results page (`results/*.md` and
  `.json`) that `--check` regenerates in CI, checks that fail the job, and figures as WebP under about 300 KB,
  marked "synthetic (DSR-12), no evidence credit".
- **Tool entries.** TL-53 and TL-54 grow to cover the new scripts. Phase C adds one entry for acados and casadi as
  openpilot's own solver.
- **Sources first.** A number with no source stays out. A study whose key input cannot be sourced says so and stops,
  as round 3's 13, 17's spray, 18 and 19 did.
- **What would come back to the lead.** Only results that suggest moving an ODD limit or a requirement, as register
  questions to the standard in CLAUDE.md. Most likely from studies 21 (night), 26 (torque authority) and 29
  (cut-outs).

## 6. Inputs from the car (T1 tasks)

Added to round 3's list ([`physics-plan-round3.md`](physics-plan-round3.md) §6):

| Input | Used by |
|---|---|
| The EPS's driver-torque and command scales: raw counts against newton-metres, on a bench or with a torque wrench | 25, 26 |
| The steering wheel's rim radius | 25 |
| The radar cover's material and thickness (the bumper emblem in front of the radar) | 27 |
| A night drive log on an unlit road with a parked car ahead, no uploads (DQ-084) | 21 |
