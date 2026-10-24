# Cyber simulation: design note

| Field | Value |
|---|---|
| Scope | Design of a simulation that plays the [WP-C-09](../../02-concept/WP-C-09-tara.md) attack paths through LionDriver's topology ([WP-S-07](../../03-system/WP-S-07-cybersecurity-requirements-architecture.md) §3.1–3.2), shows where each path meets a control and how far that control is built, and, where a path reaches the car, hands the last step to the layer-1 plant ([`../plant/`](../plant/)), which runs the real panda safety code |
| Version | 0.1 (first draft: model, mapping, outputs, limits, and the prototype proposal for TS-06 and TS-14; nothing built; 2026-10-24) |
| Status | Draft. AI-drafted (Claude, AI assistant; I0 under WP-M-02 §3.3); not reviewed. Design only: no code, no result |
| Feeds | Review figures and dashboards for [WP-C-09](../../02-concept/WP-C-09-tara.md), [WP-C-10](../../02-concept/WP-C-10-cybersecurity-goals-and-concept.md) and [WP-S-07](../../03-system/WP-S-07-cybersecurity-requirements-architecture.md); previews cases for [WP-V-06](../../06-validation/WP-V-06-cybersecurity-validation.md). **Never evidence** (§5) |
| Reviewer(s) | TBD (I1) |
| Approver | Project maintainer (acting cybersecurity manager) |

> Defensive engineering document, at the abstraction of WP-C-09 §5: entry point → stage → control → asset → damage.
> It contains, and the simulation will contain, no exploit or signature names, payloads, commands, keys or procedures.
> Every output is synthetic data (DSR-12) and earns no evidence credit.

## 1. What it is for

The TARA and the goal cards say, path by path, which control should stop an attack and whether that control exists.
They do not show the path as a sequence: where it enters, which boundaries it crosses, which control it meets at each,
what the item itself would notice, and what happens to the car if it gets through. This simulation does that, in three
parts:

1. **Path model** (new, standard-library Python): plays each attack path through the zones and trust boundaries of
   WP-S-07 as a sequence of stages, with each control drawn as a gate whose state is read from the CSR statuses.
2. **Hand-off to layer 1** (existing plant): where a path reaches the actuation, the last step becomes a layer-1 fault
   kind, run with the real panda safety code, so the physical consequence and the HARA hazard come from the same plant
   the safety work uses.
3. **Views**: ground truth against what the item's own monitors see, a dashboard by stage and by asset, and one
   Blender review scene.

It borrows three ideas. From Kuhl et al. (WSC 2007): a network of elements, a stage graph that says which stage may
follow which, seeded attacker parameters, and a ground-truth file set against the alerts each sensor would raise. From
breach-and-attack-simulation dashboards: results by attack stage and by asset. From cyber-physical testbeds: attacks
enter at a layer (applications, communications, protection and control) and their effect is seen in a physical
simulation underneath. LionDriver already has that layering: the SoC applications over msgq and SPI over the panda
envelope over CAN over the vehicle and EPS plant.

## 2. The model

### 2.1 Topology

The elements are the zones of WP-S-07 §3.1 and the boundaries of §3.2, read from that document, not copied.

| Element (Kuhl's term) | LionDriver | Source |
|---|---|---|
| Machines | Z1 safety MCU, Z2 safety-relevant host, Z3 network-facing host, Z5 vehicle ECUs, Z7 the device at rest | WP-S-07 §3.1 |
| Subnets | Z4 external network and back end, Z6 release environment | WP-S-07 §3.1 |
| Connectors | TB-1 command channel, TB-2 boot lines, TB-3 network, TB-4 local params, IPC and files, TB-5 vehicle CAN, TB-6 signed artefacts, TB-7 physical | WP-S-07 §3.2 |
| Sensors on connectors | The item's own monitors only (§2.5); there is no intrusion-detection system and the model does not invent one | WP-S-07 §4, plant |

Each zone is also tagged with its testbed layer: **applications** (Z3, Z2 user space), **communications** (TB-1, TB-4,
TB-5), **protection and control** (Z1, the envelope), **physical** (the plant: vehicle, EPS, road, driver model).

### 2.2 Stage graph

Kuhl's stages (recon, intrusion as a user, escalation, root, goal; external machines, then internal) become stages
over LionDriver's trust order. A path is a walk through this graph; every edge crosses a WP-S-07 boundary.

| Stage | Meaning | Reached across | Note |
|---|---|---|---|
| S0 Knowledge | The attacker knows the design | none | Always reached: the source is public (WP-C-09 §6, KoI "public" for every path) |
| S1 Foothold | Control of an input the item accepts: update source, network position, physical access, upstream code | Z4, Z5, Z6 or Z7 | Outside the item; reached by assumption (WP-C-10 CA-01…CA-05) |
| S2 Network-facing code | Code or data accepted by a Z3 handler | TB-3 or TB-6 | Updater, remote access, SSH, model store |
| S3 Safety-relevant host | Root-equivalent effect on Z2: params, IPC, processes | TB-4 | WP-S-07 assumes Z2 compromisable |
| S4 Envelope | Effect on Z1: its configuration, its firmware, or the frame stream it filters | TB-1 or TB-2 | The last line for every safety goal (WP-S-07 §3.2 principle) |
| S5 Vehicle | A frame reaches the car's actuation, or the stock PCS path | TB-5 | Hand-off to the plant (§3) |
| G Goal | A WP-C-09 damage scenario | none | DS-nn, and the HARA hazard it links to |

Allowed edges: S0→S1; S1→S2; S1→S5 (physical bus, TS-01); S1→G (device at rest, TS-11); S2→S3; S2→G (privacy
paths, TS-07); S3→S4; S3→S5 (in-envelope commands, TS-04, TS-12); S3→G (DM and HMI paths, DS-13, DS-14); S4→S5;
S5→G. The graph is data
(`stages.yaml`, prototype §6) and the build fails if a path uses an edge it does not list.

### 2.3 Gates (controls)

A gate sits on an edge and names the CSR-nnn of WP-S-07 §4 that implement it. Its state is read from the
"Evidence at baseline" column and its dated notes, with the patterns `fig_c10_goals.py` already uses, so the two
figures cannot disagree:

| State | Drawn as (same convention as Figures 9-2 and 7-1) | Meaning |
|---|---|---|
| open | no barrier | Not implemented, not met |
| partial | dashed amber | Part built, or built in one build only |
| unverified | dashed blue | Implemented, not verified |
| verified | solid green | Implemented and verified (none today) |

Every path is run under two **lenses**, so the figures never credit an unverified control:

- **Credited**: only a verified gate stops the path. Today no gate is verified, so every path reaches its goal; the
  lens shows that plainly.
- **As built**: a gate stops the part of the path its implementation covers, in the build where it exists. For gates
  in the panda, this is not a judgment: the plant runs the code (§3) and the frame is accepted or refused.

### 2.4 Attacker parameters

Kuhl's efficiency, stealth and skill become the WP-C-09 §6 attack-potential factors of the path being played
(elapsed time, expertise, window of opportunity, equipment), read from the TARA. They set the **timeline** of the
ground truth (when each stage happens) and the **stealth** choice (whether the attacker avoids actions that trip a
monitor, where the path offers a choice). They do **not** set a probability that a step succeeds: such a number would
be an invented pass rate. Whether a step passes is decided by the gate state (path model) or by the panda code
(plant), never by a draw.

Seeded randomness is used only where the plant already uses it: the driving situation at the hand-off (speed, road,
driver reaction), drawn from the layer-4 families ([`../search/families.yaml`](../search/families.yaml)) with a fixed
seed. An attacker can choose the moment, so the hand-off is run at the worst in-ODD case the layer-4 catalogue holds,
not at a random exposure.

### 2.5 Monitors (the detector view)

The "sensors" are what the item already observes. Each is listed with the CSR or TSR it comes from and its own build
state, so a monitor that does not exist yet is shown as absent, not as silent.

| Monitor | Where | Source | Build state |
|---|---|---|---|
| Rejected configuration requests counted in the health packet | Z1 | CSR-012 | partial (reference build) |
| TX frame refused by the envelope (allow-list, limits, rate) | Z1 | CSR-092, TSR-518, TSR-705 | partial (reference build) |
| Authority revoked, siren | Z1 | plant (panda code) | as the plant runs it |
| Mode or firmware mismatch seen by pandad | Z2 | CSR-016, CSR-053 | open; partial |
| Update signature or origin refused | Z3 | CSR-121, CSR-122 | open |
| Developer-mode or second-publisher alarm | Z2 | CSR-063, CSR-073 | open |

Background events (benign refusals, update checks) can be added as a Poisson process with a stated, synthetic rate
that defaults to zero; the prototype does not need them.

## 3. From attack path to the car

The attack's last step is handed to the plant as a fault kind of [`../faults.yaml`](../faults.yaml). Kinds marked
*new* do not exist yet; they would feed frames into the real TX hook, so the panda code, not the model, decides.

| TS | Entry layer | Stage walk | Gates met on the way (CSR) | Layer-1 kind at S5 | DS → HARA |
|---|---|---|---|---|---|
| **TS-06** malicious update | applications (updater) | S0→S1→S2→S3→S4→S5 | 124 updates off, 122 fixed origin, 121 signed manifest, 123 anti-rollback; then as TS-04 and TS-14; if the update carries panda firmware, 031…034, 051…054 | in-envelope worst commands: `hardover` (F-01b), `accel_max` (L-01), `decel_min` (L-03), `soc_stall` (F-04b); plus the TS-14 kinds | DS-01, DS-03, DS-04, DS-02; DS-11 (fleet) → H-01…H-06 |
| **TS-14** SoC frames through the panda | communications (TB-1 TX stream) | S3→S4→S5 | 092 TX allow-list (TSR-705), TX rate per ID (TSR-518) | *new* `tx_pcs_spoof`: a PCS-type frame offered to the TX hook; *new* `tx_flood`: in-limit steering frames far above their nominal rate | DS-04 → H-04, DS-07 → H-08; DS-01 → H-01, DS-03 → H-03 |
| TS-04 params / IPC | applications, communications (TB-4) | S3→S5 or S3→G | 061…064, 071…073 | `hardover`, `accel_max`, `decel_min`, `decel_lost`, `dm_stop` | DS-01…06 → H-01…H-06; DS-13, DS-14 → H-07, H-09 (not in the plant) |
| TS-12 denial of service | applications | S3→S5 | 061 (envelope independence) | `soc_stall`, `heartbeat`, `frozen`, `decel_lost` | DS-02, DS-06 → H-02, H-06 |
| TS-08, TS-09, TS-10 | applications | S1/S2→S3 | 101…104; 081…083; 131…135 | as TS-04 and TS-14 | as TS-04 |
| TS-02 safety configuration | communications (TB-1) | S3→S4 | 011…016 | wrong configuration, then `overlimit` (F-01a) passes | DS-01…07 |
| TS-01 physical CAN | communications (TB-5) | S1→S5 | 091…093 | *new* forged plausibility input; relay check (093) | DS-01…07 |
| TS-03, TS-05 firmware replaced | protection and control | S3→S4 | 021…024, 031…034, 041…043, 051…054 | **beyond the plant**: no envelope is left to run; shown as "outcome not bounded by the item" | DS-01…07 |
| TS-07, TS-11, TS-13 | applications; physical device | S1→S2→G (TS-07, TS-13); S1→G (TS-11) | 111…117; 141…152 | none: privacy goals, no path to the car | DS-08…10, DS-12 |

Two limits follow from the table. The plant is one car, so DS-11 (fleet) is drawn as a multiplier, not simulated. And
the plant has no HMI or attention model, so DS-13 and DS-14 end at the goal, not in a plant run.

## 4. Outputs

| Output | Form | Content |
|---|---|---|
| Ground truth | `results/cyber-<case>.jsonl`, generated | One record per step: time, stage, zone, boundary, gate and its state, lens, outcome (passed, stopped, handed off) |
| Detector view | same file, `monitor` records | What each §2.5 monitor reports at each step, or "absent" |
| Results page | `results/cyber-prototype.md`, generated | Per path and lens: where it stops or what reaches the car; for hand-offs, the plant outcome (panda decisions, times, lane margin or gap) and the HARA hazard |
| Path strip | SVG, one per path | The stage walk left to right with each gate drawn by state, and the plant outcome at the end |
| Dashboard | SVG, one page | Stage × threat-scenario grid with gate states; assets and zones at risk; per stage, which monitors exist; counts of paths that reach the car under each lens. Every number is a count of documented statuses or of runs, labelled synthetic |
| Review scene | one Blender dashboard via the existing `scene.json` pipeline ([`../blender/`](../blender/README.md)) | TS-14 rate flood: the same steering run with the envelope as built and without the reference-build checks, side by side |

Figures follow the house rules: 640 px wide, 13–16 px text, colour tokens with a dark variant, `<title>` and `<desc>`,
a still for any loop longer than 5 s, and a red "synthetic, no evidence credit" band.

## 5. What it can and cannot claim

It **can** show:

- for each modelled path, which documented controls lie between the entry and the goal, and how far each is built,
  as WP-S-07 records it on the date of the run;
- for a panda gate, what the pinned panda code does with the frames the path offers, in the plant (accepted, refused,
  authority revoked, after how long);
- for what gets through, the physical consequence in the layer-1 plant and the HARA hazard it falls under, under the
  plant's stated assumptions.

It **cannot**:

- rate feasibility, risk or CAL, or re-rate any threat scenario (WP-C-09 OI-5 is a TARA iteration, not a sim run);
- verify any CSR: that is WP-W-11 and WP-V-06 work on real builds and hardware;
- say anything about how likely an attacker is to succeed, or about real attackers;
- represent firmware replacement, fleet effects, or the driver's view of a spoofed HMI;
- stand for the shipped baseline: the plant builds the pinned panda with and without the reference-build flag, which
  is not the as-shipped commit WP-C-09 rates.

Until the plant is validated against Corolla logs, its outcomes rank and illustrate only (sim [README](../README.md)
§4). The whole track is DSR-12 synthetic data.

## 6. Prototype proposal: TS-06 and TS-14, end to end

The smallest version that exercises every part: two paths, both lenses, one real-code hand-off, one plant-only
hand-off, one dashboard and one scene.

| Piece | What | New or reused |
|---|---|---|
| `stages.yaml`, `paths.yaml` | §2.2 graph; the TS-06 and TS-14 walks with gates as CSR IDs, entry layer, hand-off kinds | new, data |
| `cyber.py` | Reads WP-C-09 (§5 paths, §6 factors, §8 risk) and WP-S-07 (§3 zones and boundaries, §4 statuses); walks each path under both lenses; writes ground truth and detector records. Fails if an ID or status pattern is missing | new, standard library |
| plant kinds `tx_pcs_spoof`, `tx_flood` | In `../plant/simulate.py`, offering frames to the real TX hook; run with the reference build and without it | new, small |
| TS-06 hand-off | The existing `hardover`, `accel_max`, `decel_min` and `soc_stall` cases, referenced, not re-run | reused |
| `report.py --check`, tests | Results page and the two SVGs; `--check` fails if stale; tests check every fact against its source | new; added to the CI "trace and link checks" job |
| Scene | TS-14 rate flood, as built against without the reference checks | Blender pipeline, reused |

What the prototype is expected to show, to be confirmed by the runs, not assumed: TS-06 meets four update gates, none
built (updates are off by procedure only, CSR-124), and reaches the car with whatever the attacker's software
commands, bounded by the envelope as built. TS-14's PCS frames are refused and its rate flood revoked in the reference
build; without the reference-build checks the flood lets a hard-over build up faster than the per-frame rate limit
intends.

### 6.1 Technical choices made here (reversible; change them by editing this note)

1. **No success probabilities.** Gates decide by state, the panda by its code; attacker parameters set timing only
   (§2.4). Avoids invented pass rates.
2. **Two lenses**, credited and as built (§2.3), so no figure credits an unverified control.
3. **Worst in-ODD situation at the hand-off**, from the layer-4 catalogue, because an attacker picks the moment.
4. **Firmware replacement is not simulated**; it is drawn as beyond the plant rather than as a plant without an
   envelope, which would be a model of no code at all.
5. **The dashboard shows the HARA hazard and the TARA safety impact, not an ASIL**, since the HARA's exposure rating
   assumes random occurrence.
6. **Standard-library Python** for the path model; the plant keeps its own dependencies.

### 6.2 For the project lead

One question is recorded in the [decision register](../../01-management/decisions/register.yaml) as queued, not
asked, because the prototype does not wait on it: whether the HARA and HATARA should record attacker-triggered
hazardous events, whose exposure is chosen rather than random (choice 5 above works either way). Nothing else here
needs the lead.
