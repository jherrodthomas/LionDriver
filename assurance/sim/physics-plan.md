# Physics studies, round 2: the plan for ten more

| Field | Value |
|---|---|
| Purpose | Plan ten physics studies that follow the four already built (sun, hydroplaning, cabin heat soak, crosswind; [weather README](weather/README.md)): what each one answers, how, with which inputs, checks and picture, and in what order |
| Status | Phase A built 2026-10-21 (studies 1, 3, 4, 5; §2); phase B built 2026-10-25 (studies 2, 9, 10; §3); phase C built 2026-10-25 (studies 6, 7, 8; §4). AI-drafted (Claude, AI assistant; I0 under WP-M-02 §3.3); not reviewed |
| Credit | None. Every study is a design aid, synthetic (DSR-12), with no evidence credit (DQ-413, WP-V-02 §5.3, DQ-139). A result that would move an ODD limit goes to the lead as a register question; the study itself does not move it |
| Lead decisions needed | **None to start.** Phase A raised one: whether the ODD should ask for more tyre tread than the legal minimum (register, from study 3). The one new tool (ngspice, study 8) is a reversible technical choice: Claude decided it and logged it in the register (DQ-420) when phase C started. Measurements on the car are tasks for T1 ([TE-04](../07-supporting/tool-evaluations/TE-04-physics-field-model.md) §5), not decisions |

## 1. The ten at a glance

| # | Study | Question it answers | Safety item | Builds on | Phase | Effort |
|---|---|---|---|---|---|---|
| 1 | Fog and dew on the windshield | How many hours a year the glass in front of the camera is below dew point, and how long the defroster takes to clear it | TC-19, KS-16 | Cabin heat soak (glass node) | A | 1 session |
| 4 | MCU temperature next to the SoC | How hot the safety MCU runs when the SoC heats the enclosure, against its rating and TSR-509 | DFI-04, TSR-509 | Device heat model (the MCU source is already in it) | A | ½ session |
| 5 | Road crown and bank, engaged | The lateral push left over after openpilot's roll compensation, and how a roll-estimate error adds to the crosswind | TC-15, KS-02 | Crosswind push; plant `straight_drift.py` | A | ½ session |
| 3 | Stopping on a wet road | Whether the item's −3.5 m/s² braking bound and the stock PCS have the friction they need in rain and on standing water | TC-03, TC-33 | Hydroplaning water film | A | 1 session |
| 2 | A gust through the car and controller | Peak lateral drift when a gust hits (open road, passing a truck, leaving a bridge), against the lane margin | TC-15, KS-02, DQ-415 | Crosswind force from the silhouette; plant with EPS lag | B | 1–2 sessions |
| 10 | Tunnel entry and exit | How long the road camera is over- or under-exposed at the tunnel portal, driven by openpilot's own auto-exposure code | TC-18, KS-12 | Real `camerad` exposure loop | B | 1–2 sessions |
| 9 | Oncoming headlights at night | How bright an oncoming low beam is at the camera against distance, and what the exposure loop does with it | TC-02, KS-12 | Study 10's exposure loop | B | 1 session |
| 6 | Sun on the device through the car | When the roof and pillars shade the device, by ray-casting the sun through the 3D mesh, as a better sun input to the heat model | TC-21, DFI-04 | Sun position, 3D mesh, heat model | C | 1–2 sessions |
| 7 | Mount vibration modes | The mount's natural frequencies against road and engine excitation, and the camera's angular jitter | TC-19, KS-16, WP-H-07 | FEniCSx (elasticity; SLEPc is already in the lock) | C | 2 sessions |
| 8 | 12 V dips when the engine cranks | Whether the MCU's supply stays in range through a cranking dip, or a brown-out reset follows | TSR-505 | New tool: ngspice | C | 2 sessions |

**Order.** Phase A first: four small studies, each reusing a built model, with no new inputs. Phase B reuses real code
(the plant and `camerad`). Phase C needs a new physics type or a new tool, and it gets better with T1's
measurements of the device and mount. Each phase ends with its CI checks green and a results page.

## 2. Phase A: reuse what is built

**Built 2026-10-21.** Results, synthetic and on estimated inputs:

| # | Study | Finding | Results |
|---|---|---|---|
| 1 | Fog on the windshield | Dew about 680 h and frost about 71 h a year on a car parked outside. The camera's view clears last under the defroster, about 8 min after a humid night. Recirculation without air conditioning fogs the inside in the cold months | [`windshield-fog.md`](results/windshield-fog.md), [weather §5](weather/README.md#5-fog-dew-and-frost-on-the-windshield-tc-19-ks-16) |
| 4 | MCU next to the SoC | The SoC's heat lifts the MCU about 12 K. When the SoC reaches its limit, the MCU's junction is at 79–97 °C, below 125 °C. Candidate TSR-509 trip: a DTS reading of 117 °C or below, 35 K from the hottest ODD drive | [`mcu-heat.md`](results/mcu-heat.md), [thermal §2.2](thermal/README.md#22-the-safety-mcu-next-to-the-soc-dfi-04-tsr-509) |
| 5 | Road crown | Compensated while the roll estimate is valid. The device's mount roll costs 0.17 m/s² per degree until torqued learns it. With roll invalid, a 6 % bank's 0.59 m/s² comes back | [`road-crown.md`](results/road-crown.md), [weather §6](weather/README.md#6-road-crown-and-bank-while-engaged-tc-15-ks-02) |
| 3 | Wet braking | New tyres give 5.6 m/s² on a wet road at 110 km/h; tyres at the legal minimum give about 2.0, below the item's 3.5 (put to the lead) | [`wet-braking.md`](results/wet-braking.md), [weather §7](weather/README.md#7-stopping-on-a-wet-road-tc-03-tc-33) |

Changes from the plan below:
- **Study 1** answers TC-19 and KS-16. TC-04 is weather fog, outside the ODD.
- **Study 3** uses a handbook friction table, not NASA and PIARC curves.
- **Study 5** found the mount roll term, which the plan did not foresee.

### 1. Fog and dew on the windshield (TC-19, KS-16)

- **Method.** The cabin model already gives the windshield's temperature hour by hour. Add moisture: outdoor
  relative humidity, plus the occupants' breath with recirculation on or off. Fog forms on the inside when the
  glass's inner face drops below the cabin dew point (Magnus formula). Dew or frost forms on the outside after a
  clear night, when the glass radiates to a cold sky.
- **Inputs.** A typical-year hourly climate for the reference site (34.85 N, 82.40 W; pvlib can fetch PVGIS's
  typical year, and only derived numbers are committed). Breath moisture about 40 g/h per person (ASHRAE). Defroster
  airflow, an estimate with a stated band.
- **Checks.** Magnus against ASHRAE dew-point tables. The glass energy balance closes. With a dry cabin the
  defroster run clears the glass in about the FMVSS 103 time.
- **Picture.** A month × hour heat map of fog risk, and an animated windshield that clears from the defroster vents up.
- **Feeds.** KS-16 test conditions (when fog is likely on the test corridor); an INS or user-information line on
  waiting for clear glass before engaging.

### 4. MCU temperature next to the SoC (DFI-04, TSR-509)

- **Method.** The device model already carries the MCU as a 0.4 W source next to the SoC. Read its peak out of the
  runs already made (pilot, hot July drive) and sweep the coupling.
- **Inputs.** The MCU's operating range from its datasheet; the TSR-509 threshold, which has not yet been set
  (HWSR-509).
- **Checks.** The existing V1–V7. Add one: the MCU node's energy balance with only the SoC on.
- **Picture.** A section through the device, with the heat spreading from the SoC to the MCU, and the MCU's curve
  against its limit.
- **Feeds.** WP-A-03 DFI-04 (do the SoC and MCU go out of range together?) and a candidate TSR-509 threshold for the
  HWSR-509 owner.

### 5. Road crown and bank while engaged (TC-15, KS-02)

- **Method.** A cross-slope pushes the car downhill by g·sin θ. openpilot's torque controller subtracts
  `params.roll · g` (`latcontrol_torque.py:67`), so only the error in the roll estimate is left over. Sweep crown
  1.5–2 % (US highway practice) and KS-02's bank 2–6 % against the roll-estimate error. Add the crosswind push from
  the same side.
- **Inputs.** The roll-estimate error, from `locationd` or `paramsd` logs when available, an estimate until then.
- **Checks.** With a perfect estimate the remainder is zero. Without compensation it equals the plant's
  `straight_drift.py` push.
- **Picture.** Crown + wind push against the WP-C-02 §3.2 margin, as a stacked bar.
- **Feeds.** WP-C-02 §3.2 margin text, which names road crown; KS-02.

### 3. Stopping on a wet road (TC-03, TC-33)

- **Method.** The friction available falls with water film depth and speed. Take the film from the hydroplaning
  model and the friction drop toward the hydroplaning speed from NASA and PIARC wet-friction data. Compare that with
  what the item asks for (−3.5 m/s², opendbc `ACCEL_MIN`) and what the stock PCS asks for.
- **Inputs.** Wet-friction curves (published, with their scatter); the tyre state from the hydroplaning study.
- **Checks.** Dry friction and stopping distance against the published Corolla stopping distances. With a thin
  film the friction curve's speed dependence agrees with the source data.
- **Picture.** Stopping distance against speed, dry, wet and standing water, with the 3.5 m/s² line across it.
- **Feeds.** DQ-414 rain bound (is the item's braking bound always available inside the ODD?), TC-33.

## 3. Phase B: real code in the loop

**Built 2026-10-25.** Results, synthetic:

| # | Study | Finding | Results |
|---|---|---|---|
| 2 | Gust | Gusts of 0.5–8 s move the car at most 26 cm with ideal steering. A step into a 30 km/h wind at the upper load band leaves the lane even so: the steady push takes 89 % of the Corolla's steering | [`gust.md`](results/gust.md), [weather §8](weather/README.md#8-a-gust-through-the-car-and-its-lane-keeping-tc-15-ks-02) |
| 10 | Tunnel | openpilot's auto exposure (ported from camerad): about 0.25 s of dark frames at the entry and 1–1.25 s of bright ones at the exit | [`tunnel.md`](results/tunnel.md), [weather §9](weather/README.md#9-tunnel-entry-and-exit-tc-18-ks-12) |
| 9 | Headlights | The lamps' own pixels do not move the median-based exposure. Veiling glare does: low beams leave at least 88 % of the road's contrast, and an undipped high beam across an 8 m median leaves 20 % with a dirty windshield | [`headlights.md`](results/headlights.md), [weather §10](weather/README.md#10-oncoming-headlights-at-night-tc-02-ks-12) |

Changes from the plan below:
- **Gust:** the truck bow wave is left out for want of a source. The steering is taken from the plant's law and
  opendbc's limiter, with an ideal-steering bound added.
- **Tunnel:** the exposure loop is ported line by line rather than run as C++; a check pins every line it follows.
- **Headlights:** these use UN R112's bounds only, as the US limits were not confirmed. The ODD's divided highways
  are the main case, with the undivided road as a reference.

### 2. A gust through the car and controller (TC-15, KS-02, DQ-415)

- **Method.** The crosswind study gave a steady push. Here the wind changes with time: a one-minus-cosine gust in
  open country, the bow wave of a truck being passed, and the step when leaving a bridge or cutting. The side force
  and yaw moment come from the silhouette and drive the plant's single-track model. A perfect-perception controller
  steers through the EPS lag (`steerActuatorDelay`).
- **Inputs.** The gust shapes and amplitudes from published crosswind work, with stated sources. The crosswind
  study's force band.
- **Checks.** A slow gust settles at the steady push. The open-loop response agrees with the analytic single-track
  transfer function.
- **Picture.** A top-down lane view of the car drifting and recovering, with the peak deviation against the margin.
- **Feeds.** WP-C-02 §3.2 and OI-10 (what the windy-day log should look for); KS-02.

### 10. Tunnel entry and exit (TC-18, KS-12)

- **Method.** At the portal the road ahead's brightness drops by a factor of tens to hundreds (daylight
  against the tunnel lighting levels of CIE 88). The camera's exposure loop is openpilot's own `set_camera_exposure`
  (`system/camerad/cameras/camera_qcom2.cc:116`). It is run unchanged against a synthetic brightness trace at 110 km/h,
  with the sensor's exposure and gain limits from `sensors/ox03c10.cc`.
- **Inputs.** Luminance outside and inside (CIE 88 levels for the zones); the portal's approach geometry.
- **Checks.** The loop's step response matches its own time constant in the code. Brightness that stays steady
  leaves exposure steady.
- **Picture.** An exposure timeline through entry and exit, with the frames outside the target grey band shaded.
- **Feeds.** TC-18 is excluded until validated. This gives the length of the dark and bright windows that a
  validation would have to cover. Nothing about how the driving model copes with those frames.

### 9. Oncoming headlights at night (TC-02, KS-12)

- **Method.** The illuminance at the camera from an oncoming low beam, for each distance and lateral offset on an
  undivided road, uses the published low-beam intensity points toward an oncoming driver (FMVSS 108 / UN R112). Feed
  it to study 10's exposure loop and see how far the scene darkens around the glare.
- **Inputs.** Published headlamp intensity points; sensor dynamic range. **The weakest of the ten:** lens flare and
  veiling glare need camera data that we don't have, so the result is a band, not a line.
- **Checks.** Inverse-square fall-off; the exposure loop as in study 10.
- **Picture.** Glare-to-road brightness against distance, with the exposure loop's response.
- **Feeds.** KS-12 test conditions.

## 4. Phase C: new physics or a new tool

**Built 2026-10-25.** Results, synthetic and on estimated inputs:

| # | Study | Finding | Results |
|---|---|---|---|
| 6 | Sun on the device | The car never shades the device's windshield side: every direction in front of it is windshield. Its angle limits the sun. Into the whole box at most 2.32 W, in winter, the heat model's 2.30 W; in June–August at most 1.89 W, so the hot-day bound has margin on the sun | [`device-sun.md`](results/device-sun.md), [weather §11](weather/README.md#11-sun-on-the-device-through-the-car-tc-21-dfi-04) |
| 7 | Mount vibration | First mode about 91 Hz (56–117 Hz over the pad's band), the device nodding on its pad: clear of the wheel and idle orders, but near the engine's second order at cruise. The road's own jitter is 0.03–0.06 px RMS | [`mount-modes.md`](results/mount-modes.md), [thermal §2.3](thermal/README.md#23-the-mounts-vibration-modes-tc-19-ks-16-wp-h-07-qe-08) |
| 8 | Cranking dip | ISO 16750-2 level I rides through; level II locks out the nominal converter and the device resets. On the way down the MCU's rail is out of range without a reset for a fraction of a millisecond, which a BOR closes. The input dips to 4.3–7.5 V, which an HWSR-505b threshold has to allow | [`crank-dip.md`](results/crank-dip.md), [supply README](supply/README.md) |

Changes from the plan below:
- **Study 6** found the shading the plan expected does not happen on the windshield side. It computes every face and
  the glass each ray crosses, and runs in the weather job (pvlib), not the thermal one. The ray cast runs only where
  the mesh is; its table is committed.
- **Study 7** models the pad, the mount and the device as blocks square to the glass, and drives them with ISO 8608
  roads through a quarter-car. The engine's shaking is compared by frequency only, for want of an amplitude. The
  modes are drawn as still shapes, not animated.
- **Study 8** uses ISO 16750-2 levels I, II and IV as TI reproduces them; the ripple and level III are not given
  there. Whether the reference car has engine stop-start stays a T1 task.

### 6. Sun on the device through the car (TC-21, DFI-04)

- **Method.** Cast the sun vector from the sun-position model through the licensed mesh to the device's mount point.
  The roof, A-pillars and windshield frit shade it for part of the day. The sunlit fraction scales the heat model's
  sun flux hour by hour, replacing the full-sun estimate. The mesh stays out of git; only the shading table is
  committed.
- **Inputs.** The mount position: an estimate from the installation guide until T1 measures it. Whether the
  reference car has a glass roof (open with T1).
- **Checks.** The ray caster against an analytic shadow of a box. Sun straight down the windshield normal gives no
  shading.
- **Picture.** The device's view up through the windshield over a day, sunlit or shaded.
- **Feeds.** The heat model's sun input (TE-04 T1). A tighter band on the device bound.

### 7. Mount vibration modes (TC-19, KS-16, WP-H-07)

- **Method.** Linear elasticity in FEniCSx with the eigenvalue solver SLEPc (already in the lock, so no new
  environment) on the mount and device as two bodies. Compare the first modes with road excitation (ISO 8608
  classes A–B at highway speed) and engine idle. Compute the camera's angular jitter as a fraction of a pixel.
- **Inputs.** Mount dimensions and material (T1 measures them; estimates until then); the adhesive pad's stiffness,
  an estimate with a wide band.
- **Checks.** A cantilever beam against its Euler–Bernoulli frequencies; mesh convergence of the first mode.
- **Picture.** The first three mode shapes, animated, and jitter in pixels against frequency.
- **Feeds.** KS-16 and calibration drift; WP-H-07 vibration qualification (where the margin is thin).

### 8. 12 V dips when the engine cranks (TSR-505)

- **Method.** A circuit model in ngspice: battery and harness, the device's input stage with its hold-up capacitance,
  the regulator's under-voltage lockout, and the MCU's rail. Drive it with published starting profiles (deep and
  shallow dips). Does the MCU rail stay above its brown-out level? Brown-out reset is not configured today (TSR-505).
  Engaged cranking happens only with engine stop-start, so the study first checks whether the reference car has it.
- **Inputs.** The device's power path is not published, so the model is generic with stated bands until a
  schematic or a bench measurement replaces it.
- **Checks.** RC hold-up discharge against the closed-form result; regulator dropout against its datasheet curve.
- **Picture.** Rail voltages through the dip, against the brown-out and reset levels.
- **Feeds.** TSR-505 and HWSR-505…505b (whether a brown-out threshold matters in practice).
- **Tool.** ngspice (BSD-3), pinned from conda-forge in its own lock; a new TL entry in WP-P-07 at TCL1.

## 5. How the work is run

- **Where.** Studies 1, 2, 3, 5, 9 and 10 go in [`weather/`](weather/README.md) (pip, the `sim-weather` CI job).
  Studies 4, 6 and 7 go in [`thermal/`](thermal/README.md) (conda lock, the `sim-thermal` job). Study 8 gets its own
  folder and job.
- **Every study** has a `params.yaml` entry with a source for each number, a results page (`results/*.md` and
  `.json`) that `--check` regenerates in CI, checks that fail the job, and figures as WebP under about 300 KB, marked
  "synthetic (DSR-12), no evidence credit".
- **Tool entries.** TL-53 and TL-54 grow to cover the new scripts; TL-58 for ngspice (TL-55 was taken).
- **What would come back to the lead.** Only results that suggest moving an ODD limit, as register questions to the
  standard in CLAUDE.md. Most likely from studies 1, 3 and 2.

## 6. Inputs from the car (T1 tasks)

One visit with a tape measure and a phone covers all of these:

| Input | Used by |
|---|---|
| Device mount position on the windshield (photo with a scale) | 6, 7, 1 |
| Mount and pad dimensions | 7 |
| Glass roof, yes or no | 6, 1 |
| Windshield rake angle | 1, 6 (the mesh gives 25.8° today) |
| Engine stop-start, yes or no | 8 |
| The device's roll on the windshield, with a level against the car (calibration takes it as zero) | 5 |
| The panda MCU's marking (temperature grade suffix) and package | 4 |
| Tyre tread depth on all four tyres | 3 |
| A few local drive logs with roll and exposure (`liveParameters`, camera exposure; no uploads, DQ-084) | 5, 10 |
