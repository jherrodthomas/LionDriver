# Physics studies, round 3: the plan for ten more

| Field | Value |
|---|---|
| Purpose | Plan ten physics studies that follow the fourteen already built ([weather README](weather/README.md), [thermal README](thermal/README.md), [supply README](supply/README.md), [round 2](physics-plan.md)): what each answers, how, with which inputs, checks and picture, and in what order. They cover triggering conditions (TCs) the first two rounds left out: what the sensors can see, the vehicle at its limits, the driver camera and the device |
| Status | Phase A built 2026-10-25 (studies 11, 12, 14, 15; §2); study 13 stopped for want of a source; phases B and C planned. AI-drafted (Claude, AI assistant; I0 under WP-M-02 §3.3); not reviewed |
| Credit | None. Every study is a design aid, synthetic (DSR-12), with no evidence credit (DQ-413, WP-V-02 §5.3, DQ-139). A result that would move an ODD limit goes to the lead as a register question; the study itself does not move it |
| Lead decisions needed | **None to start.** No new tool: every study runs in an existing environment. Inputs that have no public source yet (the radar's beam, the driver camera's light) are tasks, and the study that needs them waits in phase B |

## 1. The ten at a glance

Numbered after the first fourteen. Phase A reuses what is built; phase B needs published optical or radio data;
phase C puts openpilot's own localizer in the loop.

| # | Study | Question it answers | Safety item | Builds on | Phase | Effort |
|---|---|---|---|---|---|---|
| 11 | A stopped car ahead | At 110 km/h, how far away does a stopped car become trackable by the radar and big enough for the camera, and how much time does that leave the driver? | TC-08, KS-05 | Camera intrinsics (`camera.py`); stopping distances of study 3 | A | 1 session |
| 12 | Hill crests | On a crest built to the design standard, does the camera's and the radar's line of sight over the top cover the stopping distance, dry and wet? | TC-17, KS-27 | Study 3's friction; study 11's detection ranges | A | 1 session |
| 13 | Passing a truck in a narrow lane | How far does the air a truck pushes sideways move the car in a 3.3 m lane? | TC-32, KS-06 | Study 2's gust model and opendbc's torque limiter | A | 1 session |
| 14 | Curves on a wet road | Does the ODD's curve bound leave tyre grip on a wet road with 3 mm of tread, alone and while braking in the curve? | TC-14, TC-03, KS-01 | WP-C-02 §3.2 curve bound; study 3's friction table | A | ½ session |
| 15 | Dust in the fan | How do the device and the MCU's margin move as the fan slowly clogs, between as-built and stalled? | TC-21, HWSR-509a | The heat model and study 4 | A | ½ session |
| 16 | Lane markings at night in rain | How much line-to-road contrast does the road camera get on a wet road at night, worn paint included, with and without oncoming glare? | TC-05, TC-03, KS-03, KS-15 | Study 9's headlights; the ported auto exposure (study 10) | B | 1 session |
| 17 | Fog and truck spray | How far does the camera see in fog, and how long does a truck's spray blind it as we pass? | TC-04, TC-03 | Study 9's veiling glare; study 13's truck | B | 1 session |
| 18 | Radar under bridges | Does the ground bounce make a car ahead fade at some ranges, and can a bridge deck look like a stopped car? | TC-10, KS-10 | Study 11's radar equation | B | 1–2 sessions |
| 19 | Driver camera through sunglasses | Does enough of the driver camera's infrared light pass common lenses, polarised ones included, for the eyes to show? | TC-24, KS-17 | The driver camera's sensor (`os04c10.cc`) | B | 1 session |
| 20 | Losing GPS in a tunnel | How far does the position estimate drift in a long tunnel, and does anything engaged depend on it? | TC-18 | openpilot's `locationd` | C | 1 session |

**Order.** Phase A first: five studies on built models, with no new inputs. Phase B needs published optical and
radio data, each with a source before it starts; 18 and 19 also need a fact about the hardware that may not be
public. Phase C runs openpilot's own localizer. Each phase ends with its CI checks green and a results page.

## 2. Phase A: reuse what is built

**Built 2026-10-25.** Results, synthetic and on estimated inputs:

| # | Study | Finding | Results |
|---|---|---|---|
| 11 | A stopped car ahead | At highway speed openpilot takes a lead only from the driving model (radard, read from the code). For the item to stop on its own the model must take the stopped car at 149 m, where it is 11 px wide in its input; it reaches 32 px only at 51 m | [`stopped-car.md`](results/stopped-car.md), [weather §14](weather/README.md#14-a-stopped-car-ahead-tc-08-ks-05) |
| 12 | Hill crests | Over a crest built for 110 km/h the camera sees a stopped car at 228 m and the radar, lowest, at 172 m; both cover the item's stop and a driver's wet stop. Crests built for 100 km/h cut that to 191 and 144 m | [`crest.md`](results/crest.md), [weather §13](weather/README.md#13-hill-crests-tc-17-ks-27) |
| 13 | Passing a truck | **Not built.** No source holds up: the car–truck measurements (Howell et al. 2014, Noger and Van Grevenynghe 2011) are not openly available, and the open simulation found (Uystepruyst and Krajnović, arXiv 1511.06220) is two car-like bodies with its numbers only in plots. A windy-day log passing trucks (WP-C-02 OI-10) or one of those papers would unblock it | — |
| 14 | Wet curves | With the ODD's 3 mm of tread, cornering at the curve bound and braking at the item's rate on a straight each hold in light rain; both at once fall just short at MIRA's end of the measured band (3.4 m/s² left instead of 3.5 at 110 km/h). A note for the curve bound's rationale, not a register question | [`wet-curves.md`](results/wet-curves.md), [weather §12](weather/README.md#12-curves-on-a-wet-road-tc-14-tc-03-ks-01) |
| 15 | Dust in the fan | Clean to stalled costs 18 K of cabin air, most of it in the last fifth of the fan's cooling; the host still stops before the MCU leaves its range at every step | [`fan-dust.md`](results/fan-dust.md), [thermal §2.4](thermal/README.md#24-dust-in-the-fan-tc-21-hwsr-509a) |

Changes from the plan below:
- **Study 11** found that the radar does not make a stopped car a lead at highway speed (radard needs the model), so
  it sizes the car in the model's input rather than computing a radar range.
- **Study 14** first interpolated 3 mm between the table's rows, which put 3 mm below the item's braking even on a
  straight. Two measured tread-depth tests (Continental, MIRA) replaced it and give a band.
- **Study 13** stopped, as §5 said it would without a source.

### 11. A stopped car ahead (TC-08, KS-05)

- **Framing.** The item does not brake for a stationary vehicle it has not tracked as a lead (WP-C-02 F-02); the
  stock PCS stays responsible. So the question is how early the scene shows a stopped car, and how much time that
  leaves the driver before the stock PCS or a crash.
- **Method.**
  - **Camera:** the pixels a car's rear (1.8 m × 1.5 m) covers against distance, from the road camera's intrinsics
    in `camera.py`. Mark where it reaches a size an object detector typically needs (a band, about 10–20 px).
  - **Radar:** the radar equation with a published radar cross-section for a car's rear and the stock radar's
    published range. The Corolla's radar tracks reach openpilot (`radard.py`).
  - **Time:** each range against the driver's take-over at the item's −3.5 m/s² and at the stock PCS's harder
    braking; reaction time from WP-S-04.
  - A straight road, and a stopped car just round a curve at the ODD's tightest radius (it leaves the beam and the
    frame).
- **Inputs.** Radar cross-section and the radar's range from published sources; the 1.5 s driver reaction of
  WP-S-04 if it has one, else a band.
- **Checks.** Pixel size against the pinhole formula by hand; a radar range that scales with the fourth root of the
  cross-section.
- **Picture.** A road strip with the car's image size and the radar's range against distance, and the stopping
  distances under it.
- **Feeds.** KS-05 test distances; the driver-warning budget (WP-S-04).

### 12. Hill crests (TC-17, KS-27)

- **Method.** A crest is a parabolic vertical curve with a length chosen for the design speed (AASHTO's stopping
  sight distance model: eye 1.08 m, object 0.60 m). Put the road camera at 1.2 m and the radar at its mounting
  height. Find the line of sight over the top to a stopped car's rear, and to a car's tail lights. Compare the
  sight distance with the stopping distance on a dry and a wet road (study 3), with the item's −3.5 m/s² and with
  full braking.
- **Inputs.** AASHTO's sight-distance model and design speeds, as published; study 3's friction.
- **Checks.** The sight-distance formula against AASHTO's own table; the camera at the design eye height gives
  AASHTO's numbers back.
- **Picture.** The crest in profile with the sight lines, and the margin against speed.
- **Feeds.** WP-C-02 §3.1 geometry row (crests at the design standard), TC-17, KS-27.

### 13. Passing a truck in a narrow lane (TC-32, KS-06)

- **Method.** The side force and yaw moment on a car passing a truck at a given gap, from published measurements
  or a sourced model (scaled to the Corolla's side area). Run it as a time series through study 2's
  single-track car, the plant's lane keeping and opendbc's torque limiter. Lanes 3.3 and 3.7 m; truck at 90 km/h,
  ours at 110 km/h.
- **Inputs.** Published passing-truck forces (wind tunnel or road measurements), with a stated source. If none
  holds up, the study stops and says so.
- **Checks.** No truck, no movement; a slow pass settles at the steady push of the same force; the force falls
  off with the gap as the source says.
- **Picture.** The top-down lane view of study 2 with the truck going by, and the peak sideways movement against
  the lane margin.
- **Feeds.** KS-06 and the gust picture of study 2 (the bow wave it left out).

### 14. Curves on a wet road (TC-14, TC-03, KS-01)

- **Method.** On the ODD's curve bound the car corners at 2.5 m/s². Add the item's −3.5 m/s² braking in the curve:
  the tyres then need about 4.3 m/s², a friction of 0.44. Set that against study 3's wet friction at each speed,
  for new tyres and for the 3 mm tread the ODD now asks for (DQ-416 A), with the friction circle as the limit.
- **Inputs.** WP-C-02 §3.2; study 3's table.
- **Checks.** Pure cornering needs 2.5/9.81 = 0.25; the friction circle by hand; study 3's numbers back at zero
  lateral acceleration.
- **Picture.** Friction needed against friction available, against speed, dry and wet.
- **Feeds.** WP-C-02 §3.2's margin. A shortfall goes to the lead as a register question.

### 15. Dust in the fan (TC-21, HWSR-509a)

- **Method.** The heat model with the fan's conductance swept from 100 % (as built) to 0 (stalled), steady at the
  ODD's hottest cabin air. Read the SoC's peak, the MCU's junction and its margin to the candidate TSR-509 trip of
  study 4.
- **Inputs.** None new.
- **Checks.** The 100 % and 0 % ends equal study 4's as-built and stalled results; the temperatures rise
  monotonically as the fan clogs.
- **Picture.** SoC and MCU temperatures against the fan's remaining cooling, with the limits.
- **Feeds.** HWSR-509a (how much a partly clogged fan costs before it stalls); a maintenance note for WP-O-03.

## 3. Phase B: published optical and radio data

### 16. Lane markings at night in rain (TC-05, TC-03, KS-03, KS-15)

- **Method.** The car's low beams light the line and the road. Their brightness at the camera is the light times
  each surface's retroreflection, dry and wet: new paint, worn paint at the US minimum and the bare road. The
  ported auto exposure sets the image; the contrast left between line and road is the answer. Add study 9's
  oncoming glare across a median.
- **Inputs.** The FHWA minimum retroreflectivity for longitudinal markings; published wet against dry values for
  paint and asphalt; UN R112 low-beam intensities toward the road.
- **Checks.** No light, no contrast; dry new paint against its published value; the exposure loop as in study 10.
- **Picture.** Line-to-road contrast against distance ahead, dry and wet, new and worn.
- **Feeds.** KS-03 and KS-15 test conditions.

### 17. Fog and truck spray (TC-04, TC-03)

- **Method.**
  - **Fog:** Koschmieder's law gives the contrast left at each distance for a meteorological visibility; the camera
    sees a car when its contrast is above a threshold (a band, about 2–5 %).
  - **Spray:** a truck's spray plume as an extinction that grows with speed and rain rate, from published spray
    measurements. Passing it, the camera looks through it for a time set by the speeds.
- **Inputs.** Koschmieder's law and visibility classes; published truck-spray data, with a source.
- **Checks.** Koschmieder against its own definition (2 % contrast at the visibility); no spray, no loss.
- **Picture.** Seeing distance against visibility, and the blind time against the passing speed.
- **Feeds.** The fog boundary of the ODD (excluded today); KS-15 rain with trucks.

### 18. Radar under bridges (TC-10, KS-10)

- **Method.** A two-ray model at 77 GHz: the direct path to a car ahead and the path bounced off the road, which
  add or cancel with range. A bridge deck or gantry above the road is a flat reflector in the beam's upper edge:
  how strong does its return look against a stopped car's at the same range?
- **Inputs.** The radar's mounting height and elevation beam width, which need a source (a teardown, an FCC filing
  or a measurement); the road's reflection at 77 GHz from published data.
- **Checks.** Free space gives the radar equation's 1/R⁴; with the ground the nulls fall where the path difference
  is half a wavelength.
- **Picture.** Received power against range, with and without the ground, and the bridge's return against the
  stopped car's.
- **Feeds.** KS-10 test conditions. Waits for the beam width: without it the study does not start.

### 19. Driver camera through sunglasses (TC-24, KS-17)

- **Method.** The driver camera lights the face with infrared. The eye's signal is the light out, through the
  lens, off the eye region and back through the lens to the sensor: lens transmission at that wavelength, squared.
  Compare clear glasses, tinted, polarised and mirrored lenses.
- **Inputs.** The illuminator's wavelength and power (needs a source: comma's documentation, the part's marking or
  a measurement); published infrared transmission of sunglass lenses; the sensor's sensitivity from `os04c10.cc`
  and its datasheet.
- **Checks.** No lens, no loss; transmission squared for the round trip.
- **Picture.** The eye signal left for each lens type, against the sensor's noise floor.
- **Feeds.** KS-17 test glasses. Waits for the wavelength.

## 4. Phase C: openpilot's localizer in the loop

### 20. Losing GPS in a tunnel (TC-18)

- **Method.** Drive `locationd`'s filter, read from the code, with synthetic inertial and wheel-speed data along a
  2 km tunnel with no GPS. The sensor errors (bias and noise) are bands from published consumer IMU data. Read
  how far the position and heading estimates drift, then trace in the code which engaged functions read them.
- **Inputs.** `openpilot/selfdrive/locationd/`; IMU error bands.
- **Checks.** No errors, no drift; a constant gyro bias gives the heading drift its integral says.
- **Picture.** The estimated position against the true one through the tunnel.
- **Feeds.** TC-18's second half (GNSS loss) in WP-C-06. The likely answer, that lateral control does not use the
  global position, is worth stating with the code reference.

## 5. How the work is run

- **Where.** Studies 11–14 and 16–18 go in [`weather/`](weather/README.md) (pip, the `sim-weather` CI job). Study 15
  goes in [`thermal/`](thermal/README.md). Study 19 goes in `weather/` too (optics, no new tool). Study 20 needs
  openpilot's Python environment and goes beside the plant, with its own CI step.
- **Every study** has a `params.yaml` entry with a source for each number, a results page (`results/*.md` and
  `.json`) that `--check` regenerates in CI, checks that fail the job, and figures as WebP under about 300 KB, marked
  "synthetic (DSR-12), no evidence credit".
- **Tool entries.** TL-53 and TL-54 grow to cover the new scripts. No new tool.
- **Sources first.** A number with no source stays out: a study whose key input cannot be sourced (13, 17, 18, 19)
  says so and stops, rather than guessing.
- **What would come back to the lead.** Only results that suggest moving an ODD limit, as register questions to the
  standard in CLAUDE.md. Most likely from studies 12 (crests), 14 (wet curves) and 11 (the driver's time).

## 6. Inputs from the car (T1 tasks)

Added to round 2's list ([`physics-plan.md`](physics-plan.md) §6):

| Input | Used by |
|---|---|
| The radar's mounting height, measured to the ground | 18, 12 |
| The driver camera's illuminator: a photo of the part or the device's documentation | 19 |
| A local drive log through a long tunnel (`liveLocationKalman`), no uploads (DQ-084) | 20 |
