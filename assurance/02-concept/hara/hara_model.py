#!/usr/bin/env python3
"""LionDriver HARA model: the source of truth for the Cartesian HARA (WP-C-03).

The workbook is generated with the hara-builder method (function x malfunction guide word x
operational situation x weather). This file holds every analyst input as readable data:

- functions F-01...F-09 from WP-C-01 §2.1 (plus F-02X, Experimental Mode, for the scope variant);
- the SC / NSC / NA classification of every function x guide-word pair, with rationale;
- the operational situations (from the WP-C-02 ODD) and weather / surface conditions;
- the S and C rating rules per hazard and situation, with rationale.

Running it writes the generator inputs (`hara_input*.json`) and the count summary
(`hara-cartesian-summary.md`). `--check` fails if the committed outputs are stale.
`--postprocess <xlsx>` applies the LionDriver corrections to a generated workbook (see POSTPROCESS).

Usage:
    python3 hara_model.py                 # write inputs and summary
    python3 hara_model.py --check         # verify committed inputs and summary are current
    python3 hara_model.py --postprocess WP-C-03-hara-cartesian.xlsx
"""
# ruff: noqa: E501  (analyst data tables: one rating rule or rationale per line)
from __future__ import annotations

import csv
import io
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent

MALFUNCTIONS = [
  ("M01", "No Function"), ("M02", "Stops Functioning"), ("M03", "Unrequested Function"),
  ("M04", "Function Stuck"), ("M05", "Excessive Function"), ("M06", "Partial Function"),
  ("M07", "Functions Early"), ("M08", "Functions Late"), ("M09", "Function Applies Too Short"),
  ("M10", "Function Applies Too Long"), ("M11", "Function is Delayed"), ("M12", "Inverse Function"),
  ("M13", "Erratic or Intermittent"), ("M14", "Function is Uneven"),
]

HAZARDS = {
  "H-01": "Unintended or excessive lateral motion",
  "H-02": "Unannounced loss or degradation of lateral control",
  "H-03": "Unintended acceleration",
  "H-04": "Unintended or excessive deceleration",
  "H-05": "Driver unable to override or disengage",
  "H-06": "Unannounced loss of longitudinal deceleration",
  "H-07": "Displayed system state differs from actual state (mode confusion)",
  "H-08": "Suppression of the vehicle's stock pre-collision braking",
  "H-09": "Automated control continues with a driver who is not supervising or not responding",
  "H-10": "Vehicle does not stop for a traffic signal or stop sign it is expected to stop for",
}

# ---------------------------------------------------------------------------------------------
# Functions (WP-C-01 §2.1). kinetic_authority follows the hara-builder classes.
# ---------------------------------------------------------------------------------------------
FUNCTIONS = [
  ("F-01", "Lateral control (lane centring)", "high",
   "Computes desired curvature from the driving model and commands LKA steering torque (0x2E4). Driver-initiated assisted lane change."),
  ("F-02", "Longitudinal control (ACC, Chill mode)", "high",
   "Holds set speed or follows a lead; commands acceleration/deceleration through ACC_CONTROL (0x343), incl. standstill and cancel."),
  ("F-03", "Engagement and mode management", "medium",
   "Engages on the PCM cruise rising edge; disengages on brake, cancel or faults; supports driver override (gas, steering)."),
  ("F-04", "Driver monitoring", "medium",
   "Driver camera + DM model; escalating warnings, forced deceleration on no response, lockout."),
  ("F-05", "Driver information and warnings", "low",
   "Device display and sounds, cluster LKAS HUD (0x412); engagement state and alerts."),
  ("F-06", "Forward collision warning", "low",
   "Visual and acoustic warning from model hard-brake prediction or planner crash estimate. Does not brake."),
  ("F-07", "Lane departure warning", "low",
   "Warning when not laterally engaged, above 31 mph, no recent turn signal."),
  ("F-08", "Safety envelope and camera-message forwarding", "medium",
   "Panda MCU: TX whitelist, actuation limits, engagement gating, RX checks, heartbeat; harness relay and forwarding of camera messages (incl. stock PCS) to the car."),
  ("F-09", "Logging, upload, remote access, software update", "none",
   "Non-driving functions (loggerd, uploader, athena, SSH, updated)."),
]
EXPERIMENTAL_FUNCTION = ("F-02X", "Longitudinal control, Experimental Mode (end-to-end)", "high",
   "Driving-model desired acceleration joins the planner (minimum used); intended to stop for traffic lights and stop signs; cruise acceleration up to 2.0 m/s². Only in scope if D-08 option B is chosen.")

# ---------------------------------------------------------------------------------------------
# Function x guide word classification: (class, hazard or "", subsumed_by or "", rationale)
# ---------------------------------------------------------------------------------------------
SC, NSC, NA = "SC", "NSC", "NA"
FM: dict[str, dict[str, tuple[str, str, str, str]]] = {
  "F-01": {
    "M01": (SC, "H-02", "", "Lateral control shown as active but no torque delivered; the vehicle is not steered."),
    "M02": (SC, "H-02", "", "Torque stops mid-curve or mid-manoeuvre while still commanded, without a take-over warning."),
    "M03": (SC, "H-01", "", "Torque applied while not engaged or after disengagement (HE-01.4)."),
    "M04": (SC, "H-02", "", "Torque request frozen at its last value; steering bias continues while the road changes (HE-02.3). Bounded by the envelope and EPS authority."),
    "M05": (SC, "H-01", "", "Torque magnitude or rate above the intended value."),
    "M06": (SC, "H-02", "", "Torque below the intended value: the vehicle understeers in a curve."),
    "M07": (SC, "H-01", "", "Assisted lane change starts before the driver confirms (nudge) or before the target lane is clear."),
    "M08": (SC, "H-02", "M11", "Correction arrives after the lane geometry required it; same vehicle response as delayed function."),
    "M09": (SC, "H-02", "M02", "Torque held for less time than commanded; same vehicle response as stops functioning."),
    "M10": (SC, "H-01", "M03", "Torque continues after the command ends (after lane change or disengagement); same as unrequested torque."),
    "M11": (SC, "H-02", "", "Lateral response latency beyond specification; lane departure in curves."),
    "M12": (SC, "H-01", "", "Torque in the opposite direction to the command."),
    "M13": (SC, "H-01", "", "Oscillating or chattering torque; weaving within or out of the lane."),
    "M14": (SC, "H-01", "M05", "Asymmetric authority left vs right; the excess side behaves as excessive function."),
  },
  "F-02": {
    "M01": (SC, "H-06", "", "No deceleration delivered when following a lead that slows, without warning."),
    "M02": (SC, "H-06", "", "Deceleration stops while still needed (e.g. stale plan holds zero acceleration, HE-06.1)."),
    "M03": (SC, "H-04", "", "Braking with no reason (phantom braking), incl. a stop from speed. Unrequested acceleration has the same root but a different effect and is rated under M05."),
    "M04": (SC, "H-03", "", "Acceleration request frozen at a positive value while the lead slows or stops."),
    "M05": (SC, "H-03", "", "Acceleration above intended, or acceleration from standstill when not intended (HE-03.x). Also acceleration while not engaged, including just after a brake press has cancelled engagement (OS-13, HE-03.7, DQ-364)."),
    "M06": (SC, "H-06", "", "Deceleration below the required value when closing on a lead."),
    "M07": (SC, "H-04", "M03", "Braking before there is a reason; same response as unrequested braking."),
    "M08": (SC, "H-06", "M11", "Braking starts after it was needed; same as delayed."),
    "M09": (SC, "H-06", "M02", "Braking released before the vehicle has slowed enough; same as stops functioning."),
    "M10": (SC, "H-04", "", "Braking continues after the reason has gone; vehicle slows or stops unexpectedly in traffic."),
    "M11": (SC, "H-06", "", "Longitudinal response latency beyond specification when the lead slows."),
    "M12": (SC, "H-03", "", "Acceleration when deceleration is commanded (e.g. sign error), HE-03.3."),
    "M13": (SC, "H-04", "", "Oscillating acceleration and braking (surging); unexpected decelerations for following traffic."),
    "M14": (NA, "", "", "Longitudinal output is a single scalar request to the PCM; no left/right or per-axle asymmetry exists at this interface."),
  },
  "F-03": {
    "M01": (SC, "H-05", "", "Disengagement on brake, cancel or override does not happen (HE-05.x). Engagement failing to happen is safe (driver drives)."),
    "M02": (SC, "H-02", "", "System disengages while the driver relies on it, without adequate warning (lateral and longitudinal lost)."),
    "M03": (SC, "H-01", "", "Engagement without a driver request (the envelope gates on the PCM cruise rising edge); unexpected steering and acceleration. Lateral is the worst case and is rated here; the acceleration of a false engagement is rated as F-02 M05 in OS-13 (HE-03.7, DQ-364)."),
    "M04": (SC, "H-05", "M01", "Engagement state stuck at 'engaged'; same as disengagement not happening."),
    "M05": (NA, "", "", "Engagement is a discrete state; no magnitude."),
    "M06": (SC, "H-05", "", "Partial disengagement: one axis released, the other still actuating after brake or cancel."),
    "M07": (NSC, "", "", "Early disengagement equals an announced disengagement; rated under M02 if unannounced."),
    "M08": (SC, "H-05", "M11", "Disengagement after the driver input has passed; same as delayed."),
    "M09": (NA, "", "", "Engagement has no commanded duration."),
    "M10": (SC, "H-05", "M01", "Engagement continues after the driver ends it; same as no disengagement."),
    "M11": (SC, "H-05", "", "Release delayed beyond the specified time after brake or cancel (SG-05 FTTI 0.2 s)."),
    "M12": (SC, "H-01", "M03", "Engages when the driver cancels; same as unrequested engagement."),
    "M13": (SC, "H-02", "M02", "Repeated engage/disengage toggling; each drop behaves as an unannounced disengagement."),
    "M14": (NA, "", "", "No asymmetric profile for a discrete state."),
  },
  "F-04": {
    "M01": (SC, "H-09", "", "Inattention or unresponsiveness not detected, or no escalation to the no-response reaction (forced deceleration, lockout): the item keeps controlling the vehicle with nobody supervising (H-09, DQ-205). While the driver supervises it is latent (S0 rows): it removes a measure the controllability of H-02/H-06 relies on."),
    "M02": (SC, "H-09", "M01", "Monitoring stops during the drive; same as no function."),
    "M03": (SC, "H-04", "", "DM escalates to forced deceleration although the driver is attentive."),
    "M04": (SC, "H-09", "M01", "Attention estimate stuck: stuck 'attentive' is the same as no function; stuck 'distracted' is rated as M03."),
    "M05": (SC, "H-04", "M03", "Over-sensitive DM: escalation and forced deceleration too often; same response as unrequested intervention."),
    "M06": (SC, "H-09", "M01", "Under-sensitive DM: a non-supervising driver is not detected; same as no function."),
    "M07": (SC, "H-04", "M03", "Escalation steps reached too early; ends in unrequested forced deceleration."),
    "M08": (SC, "H-09", "M01", "Escalation too late: the item keeps driving unsupervised for longer; same as no function."),
    "M09": (NA, "", "", "Alerts have no safety-relevant commanded duration."),
    "M10": (NSC, "", "", "Alert or lockout lasts longer than needed: availability only."),
    "M11": (SC, "H-09", "M01", "Delayed detection; same as no function."),
    "M12": (NA, "", "", "No direction."),
    "M13": (NSC, "", "", "Intermittent false alerts: nuisance; repeated forced decelerations rated under M03."),
    "M14": (NA, "", "", "No asymmetric profile."),
  },
  "F-05": {
    "M01": (SC, "H-07", "", "Take-over request or disengagement alert not given; the driver believes the system is still in control."),
    "M02": (SC, "H-07", "M01", "Display or sound stops during operation; same effect as no alert."),
    "M03": (NSC, "", "", "Spurious alert: driver checks the situation; nuisance (HMI / SOTIF, WP-C-08)."),
    "M04": (SC, "H-07", "", "Engagement indication frozen (shows engaged after disengagement)."),
    "M05": (NA, "", "", "No magnitude beyond loudness; covered by HMI requirements."),
    "M06": (SC, "H-07", "M01", "Alert partly given (visual without sound); driver may miss it."),
    "M07": (NSC, "", "", "Alert shown before the event: no hazard."),
    "M08": (SC, "H-07", "M01", "Alert shown after the driver needed it; same as missing."),
    "M09": (SC, "H-07", "M01", "Alert too short to be noticed; same as missing."),
    "M10": (NSC, "", "", "Alert persists: nuisance."),
    "M11": (SC, "H-07", "M01", "Delayed alert; same as missing at the moment it matters."),
    "M12": (SC, "H-07", "M04", "Shows engaged when disengaged or the reverse; same as frozen indication."),
    "M13": (NSC, "", "", "Flickering indication: nuisance."),
    "M14": (NA, "", "", "No asymmetric profile."),
  },
  "F-06": {
    "M01": (NSC, "", "", "Missing FCW: the warning supplements driver supervision; the stock PCS gives its own warning (subject to H-08). QM in the draft HARA (§5.8)."),
    "M02": (NSC, "", "M01", "Same as no function."),
    "M03": (SC, "H-04", "", "False FCW may provoke reflex braking by the driver (rated as unintended deceleration, driver-actuated)."),
    "M04": (NA, "", "", "Discrete alert."),
    "M05": (NA, "", "", "Discrete alert."),
    "M06": (NA, "", "", "Discrete alert."),
    "M07": (NSC, "", "M03", "Early warning for a real event: helpful or same as false warning."),
    "M08": (NSC, "", "M01", "Late warning: same as missing."),
    "M09": (NA, "", "", "No safety-relevant duration."),
    "M10": (NA, "", "", "No safety-relevant duration."),
    "M11": (NSC, "", "M01", "Delayed: same as missing."),
    "M12": (NA, "", "", "No direction."),
    "M13": (NSC, "", "M03", "Repeated false alerts: same as false warning."),
    "M14": (NA, "", "", "No asymmetric profile."),
  },
  "F-07": {
    "M01": (NSC, "", "", "Missing LDW during manual driving: driver in full control (draft §5.8)."),
    "M02": (NSC, "", "M01", "Same as no function."),
    "M03": (NSC, "", "", "False LDW: no actuation; nuisance."),
    "M04": (NA, "", "", "Discrete alert."),
    "M05": (NA, "", "", "Discrete alert."),
    "M06": (NA, "", "", "Discrete alert."),
    "M07": (NSC, "", "", "Early warning: no hazard."),
    "M08": (NSC, "", "M01", "Late: same as missing."),
    "M09": (NA, "", "", "No safety-relevant duration."),
    "M10": (NA, "", "", "No safety-relevant duration."),
    "M11": (NSC, "", "M01", "Delayed: same as missing."),
    "M12": (NA, "", "", "No direction."),
    "M13": (NSC, "", "M03", "Repeated false alerts: nuisance."),
    "M14": (NA, "", "", "No asymmetric profile."),
  },
  "F-08": {
    "M01": (NSC, "", "", "Limits, gating or checks not enforced: latent fault of a safety mechanism; hazardous only together with an F-01/F-02/F-03 malfunction (dual-point). Handled in the FSC/TSC and the HW metrics, not as a separate hazardous event. Forwarding failure is M03."),
    "M02": (NSC, "", "M01", "Same as no function (latent)."),
    "M03": (SC, "H-08", "", "Relay or forwarding blocks, delays or alters camera PCS/AEB messages, or the item transmits on PCS IDs (GAP-42)."),
    "M04": (SC, "H-02", "", "Envelope stuck in a blocking state (e.g. controls_allowed stuck false, relay stuck) while the SoC shows engaged: lateral and longitudinal silently dropped."),
    "M05": (SC, "H-02", "M04", "Over-limiting: valid commands rejected; same as stuck blocking (unannounced loss of control)."),
    "M06": (NSC, "", "M01", "Under-limiting: latent."),
    "M07": (NSC, "", "", "Disengagement by envelope before needed: announced via the SoC fault path; availability."),
    "M08": (NSC, "", "M01", "Late limit enforcement: latent (covered by FTTI budget, WP-S-04)."),
    "M09": (NA, "", "", "No commanded duration."),
    "M10": (NSC, "", "M01", "Gate stays open after disengagement: latent, dual-point with F-01 M03."),
    "M11": (NSC, "", "M01", "Delayed detection: latent (GAP-06)."),
    "M12": (NA, "", "", "No direction."),
    "M13": (SC, "H-02", "M04", "Intermittent blocking: each block behaves as stuck blocking."),
    "M14": (NA, "", "", "No asymmetric profile."),
  },
  "F-09": {m: (NSC, "", "", "No kinetic authority. Logging, upload, remote access and update malfunctions do not act on vehicle motion directly; cyber-induced effects are in the TARA (WP-C-09) and map to H-01…H-08.")
           for m, _ in MALFUNCTIONS},
  "F-02X": {
    "M01": (SC, "H-10", "", "Does not stop for a red light or stop sign that Experimental Mode is presented as handling."),
    "M02": (SC, "H-10", "M01", "Starts stopping, then releases before the stop line; same as not stopping."),
    "M03": (SC, "H-04", "", "Stops for a signal, sign, shadow or object that is not there (false stop)."),
    "M04": (NSC, "", "", "Stuck model acceleration: the planner takes the minimum of model and MPC, so a stuck model value can only hold or reduce speed; rated as M03 if it brakes."),
    "M05": (SC, "H-04", "M03", "Excessive model deceleration; same as false stop."),
    "M06": (SC, "H-10", "M01", "Insufficient braking for the stop line; overshoot into the intersection."),
    "M07": (SC, "H-04", "M03", "Stops early (far before the line); same as false stop for following traffic."),
    "M08": (SC, "H-10", "M01", "Stops late (past the line); same as not stopping."),
    "M09": (SC, "H-10", "M01", "Releases the stop too early (creeps into a red light)."),
    "M10": (SC, "H-04", "M03", "Stays stopped after green: following traffic; same as false stop."),
    "M11": (SC, "H-10", "M01", "Delayed reaction to a signal; same as not stopping in time."),
    "M12": (NA, "", "", "The minimum selection prevents the model from producing more acceleration than the Chill plan, apart from the raised cruise limit, which is intended behaviour."),
    "M13": (SC, "H-04", "M03", "Stop-go oscillation at signals; same as false stop."),
    "M14": (NA, "", "", "Scalar request."),
  },
}

# ---------------------------------------------------------------------------------------------
# Operational situations (WP-C-02 ODD; IDs continue the draft OS catalogue, OS-11 wet road is
# now the weather dimension) and weather / surface.
# E follows ISO 26262-3:2018 Table B.2 (duration): E2 < 1 %, E3 1-10 %, E4 > 10 % of operating time.
# OS-07 is the exception: rated by frequency (Table B.3, E4), decision register DQ-036.
# Highway only (DQ-023 B): OS-03, OS-04, OS-15 and OS-16 are outside the ODD and rated as foreseeable misuse,
# like OS-14; since v0.6 at E3, because upstream owners engage off the highway routinely (RR-2026-011, DQ-213 A).
# OS-19 (roundabout), OS-20 (road works) and OS-21 (no lane markings) are added from the same audit. OS-17 and OS-18 are the driver-state misuse situations of H-STPA-1 (DQ-003, DQ-205).
# Engaged situations end at 110 km/h, the ODD bound (DQ-260); manual driving (OS-13) and the stock PCS (OS-09) keep 120.
# ---------------------------------------------------------------------------------------------
SITUATIONS = [
  ("OS-01", "Limited-access highway, free flow, adjacent traffic", 90, 110, "E4", "Majority of engaged time (ODD-H)"),
  ("OS-02", "Highway curve near R_ODD with barrier or adjacent traffic", 70, 110, "E3", "Curves of this radius at speed: 1–10 % of time"),
  ("OS-03", "Engaged on an undivided rural or arterial road, oncoming traffic: outside the ODD, foreseeable misuse", 60, 90, "E3", "Outside the highway-only ODD (DQ-023); engagement is not prevented off-highway. RR-2026-011: upstream owners engage openpilot off the highway routinely, so the share is rated 1–10 % (DQ-213 A) (A-ODD)"),
  ("OS-04", "Engaged on an urban arterial, pedestrians and cyclists near the lane edge: outside the ODD, foreseeable misuse", 30, 60, "E3", "Outside the highway-only ODD (DQ-023). RR-2026-011: upstream owners engage openpilot off the highway routinely, so the share is rated 1–10 % (DQ-213 A) (A-ODD)"),
  ("OS-05", "Following a lead vehicle at a short gap, dense traffic", 30, 110, "E4", "Most engaged time has a lead vehicle"),
  ("OS-06", "Stop-and-go queue or standstill behind a lead; pedestrians may cross", 0, 30, "E3", "Congestion share of driving"),
  ("OS-07", "Approaching slower or stationary traffic from highway speed", 70, 110, "E4", "Rated by frequency: happens on almost every highway drive (DQ-036; ISO 26262-3 Table B.3)"),
  ("OS-08", "Close following vehicle behind (gap < 1.5 s)", 50, 110, "E4", "Common in dense traffic"),
  ("OS-09", "Imminent collision where the stock PCS/AEB would intervene", 0, 120, "E2", "PCS-relevant situations are rare"),
  ("OS-10", "Driver override while engaged: braking, cancel or evasive steering", 0, 110, "E3", "Overrides are frequent but short; emergency cases rarer"),
  ("OS-12", "Driver-initiated assisted lane change", 70, 110, "E3", "Lane changes: short duration, several per trip"),
  ("OS-13", "Manual driving, item powered but not engaged", 0, 120, "E4", "Large share of onroad time with the device installed"),
  ("OS-14", "Engaged outside the ODD (residential street, ramp, tight curve): foreseeable misuse", 15, 60, "E3", "Engagement is possible anywhere. RR-2026-011: upstream owners engage openpilot off the highway routinely, so the share is rated 1–10 % (DQ-213 A) (A-ODD)"),
  ("OS-15", "Engaged approaching a signalised or stop-controlled intersection: outside the ODD, foreseeable misuse", 30, 90, "E3", "Outside the highway-only ODD (DQ-023). RR-2026-011: upstream owners engage openpilot off the highway routinely, so the share is rated 1–10 % (DQ-213 A) (A-ODD)"),
  ("OS-16", "Engaged in a rural or arterial curve with oncoming traffic: outside the ODD, foreseeable misuse", 60, 90, "E3", "Outside the highway-only ODD (DQ-023). RR-2026-011: upstream owners engage openpilot off the highway routinely, so the share is rated 1–10 % (DQ-213 A) (A-ODD)"),
  ("OS-17", "Engaged on the highway while the driver is not supervising (eyes off the road or hands off for long periods; responds when alerted): foreseeable misuse", 70, 110, "E2", "H-STPA-1 (DQ-003): sustained non-supervision assumed < 1 % of engaged time; DM is not credited"),
  ("OS-18", "Engaged on the highway with an unresponsive driver (asleep, impaired or incapacitated): foreseeable misuse", 70, 110, "E1", "H-STPA-1, DQ-205: very rare; second-set HE-018 rates it E1"),
  ("OS-19", "Engaged in a roundabout (rotary), cyclists and pedestrians at the entries: outside the ODD, foreseeable misuse", 15, 40, "E2", "RR-2026-011 (DQ-213 A): shown in upstream use; a roundabout is a short part of any trip, so < 1 % of engaged time"),
  ("OS-20", "Engaged through road works: lane shifts, cones, workers near the lane: outside the ODD, foreseeable misuse", 30, 90, "E2", "RR-2026-011 (DQ-213 A): shown in upstream use; work zones are a small share of engaged time"),
  ("OS-21", "Engaged on a road without lane markings (rural back road or residential street): outside the ODD, foreseeable misuse", 30, 90, "E3", "RR-2026-011 (DQ-213 A): the end-to-end model steers without markings and nothing gates on them; rated as OS-03"),
]
WEATHER = [
  ("W01", "Dry, daylight", "E4", "In ODD"),
  ("W02", "Wet road or light rain", "E3", "In ODD"),
  ("W03", "Night, dry, headlights", "E3", "In ODD"),
  ("W04", "Moderate or heavy rain (outside ODD, foreseeable)", "E2", "Outside ODD"),
  ("W05", "Snow or ice (outside ODD, foreseeable)", "E2", "Outside ODD"),
  ("W06", "Fog, visibility below the ODD bound (outside ODD, foreseeable)", "E1", "Outside ODD"),
]
E_RANK = {"E0": 0, "E1": 1, "E2": 2, "E3": 3, "E4": 4}

# ---------------------------------------------------------------------------------------------
# Rating rules: hazard -> situation -> (S, C, S rationale, C rationale). Missing situation = not
# hazardous there (S0) with the reason in NOT_HAZARDOUS. "⚠" marks C ratings that credit an
# unverified AoU; the summary shows the ASIL if that AoU fails (C+1).
# ---------------------------------------------------------------------------------------------
LAT_C = "C2 ⚠: a supervising driver with hands near the wheel corrects an envelope-limited torque deviation within ~1 s in ≥ 90 % of cases; credits AOU-01/AOU-02 (EPS limits LKA torque to an overpowerable level)."
LOSS_C1 = "C1: slow drift on a straight or gently curved road; a supervising driver notices and corrects it (≥ 99 %)."
LOSS_C2 = "C2: drift in a curve develops quickly; a supervising driver corrects it in ≥ 90 % of cases, but loss without warning delays the reaction and hands-off use is foreseeable."
ACC_C = "C2 ⚠: the driver brakes; credits AOU-03 (brake overrides ACC) and AOU-05 (PCM bounds ACC acceleration)."
DEC_C1 = "C1 ⚠: deceleration bounded by the PCM ACC envelope (AOU-05); the following driver and the ego driver (gas override) react in ≥ 99 % of cases."
DEC_C2 = "C2 ⚠: close follower; credits AOU-05 (deceleration bounded by the PCM)."
LOSS_C3 = "C3: at the curve bound a silent loss drifts about 0.6 m in 0.7 s (WP-S-04 OI-2), faster than a supervising driver reacts; re-rated from C2 by decision register DQ-059 (option B)."
NOSUP_C3 = "C3: the driver is not watching the road; the correction the C1/C2 ratings assume does not come in time (OS-17, H-STPA-1, DQ-003)."
UNRESP_C3 = "C3: nobody is able to control the vehicle (OS-18, DQ-205)."

RULES: dict[str, dict[str, tuple[str, str, str, str]]] = {
  "H-01": {
    "OS-01": ("S3", "C2", "S3: lateral departure at 90–110 km/h into adjacent traffic or barrier; loss of control (HE-01.2).", LAT_C),
    "OS-02": ("S3", "C2", "S3: departure in a highway curve into barrier or adjacent traffic.", LAT_C),
    "OS-03": ("S3", "C2", "S3: departure into the oncoming lane; head-on at combined speed > 100 km/h (HE-01.1).", LAT_C),
    "OS-04": ("S3", "C2", "S3: vehicle drifts into a pedestrian or cyclist above 30 km/h (HE-01.3).", LAT_C),
    "OS-05": ("S3", "C2", "S3: lateral departure into adjacent dense traffic up to 110 km/h.", LAT_C),
    "OS-06": ("S1", "C1", "S1: low-speed (< 30 km/h) side contact in a queue.", "C1: at queue speed the driver has time to correct."),
    "OS-07": ("S3", "C2", "S3: departure at highway speed while closing on traffic.", LAT_C),
    "OS-08": ("S3", "C2", "S3: departure at highway speed.", LAT_C),
    "OS-09": ("S3", "C2", "S3: lateral disturbance during an imminent collision changes the impact.", LAT_C),
    "OS-10": ("S3", "C2", "S3: added lateral disturbance during a driver emergency manoeuvre.", LAT_C),
    "OS-12": ("S3", "C2", "S3: lateral motion into a vehicle in the target or original lane during a lane change.", LAT_C),
    "OS-13": ("S3", "C2", "S3: unexpected steering torque during manual driving at up to 120 km/h (HE-01.4).", "C2 ⚠: the driver is steering manually with hands on the wheel; credits AOU-01/AOU-02."),
    "OS-14": ("S3", "C2", "S3: residential VRUs or ramp barrier contact at up to 60 km/h.", LAT_C),
    "OS-15": ("S3", "C2", "S3: lateral departure at an intersection into crossing or oncoming traffic or VRUs.", LAT_C),
    "OS-16": ("S3", "C2", "S3: departure into the oncoming lane in a rural curve.", LAT_C),
    "OS-17": ("S3", "C3", "S3: lateral departure at highway speed.", NOSUP_C3),
    "OS-18": ("S3", "C3", "S3: lateral departure at highway speed.", UNRESP_C3),
    "OS-19": ("S3", "C2", "S3: lateral motion into a cyclist or pedestrian at a roundabout entry, or into circulating traffic.", LAT_C),
    "OS-20": ("S3", "C2", "S3: lateral motion into workers, cones or a barrier in a narrowed lane.", LAT_C),
    "OS-21": ("S3", "C2", "S3: departure into the oncoming side on an unmarked road (as OS-03).", LAT_C),
  },
  "H-02": {
    "OS-01": ("S3", "C1", "S3: lane departure at 90–110 km/h.", LOSS_C1),
    "OS-02": ("S3", "C3", "S3: vehicle goes straight in a highway curve into barrier or adjacent traffic (HE-02.1).", LOSS_C3),
    "OS-03": ("S3", "C1", "S3: drift towards the oncoming lane on a mostly straight undivided road.", LOSS_C1),
    "OS-16": ("S3", "C3", "S3: departure into the oncoming lane in a rural curve (HE-02.2).", LOSS_C3),
    "OS-04": ("S3", "C1", "S3: drift towards VRUs at the lane edge above 30 km/h.", LOSS_C1),
    "OS-05": ("S3", "C1", "S3: drift into adjacent dense traffic.", LOSS_C1),
    "OS-06": ("S1", "C1", "S1: low-speed drift in a queue.", "C1: queue speed."),
    "OS-07": ("S3", "C1", "S3: drift at highway speed.", LOSS_C1),
    "OS-08": ("S3", "C1", "S3: drift at highway speed.", LOSS_C1),
    "OS-09": ("S3", "C1", "S3: loss of lateral control during an imminent collision.", "C1: the driver is already acting on the collision."),
    "OS-12": ("S3", "C2", "S3: lateral control lost mid-lane-change; vehicle straddles lanes next to traffic.", LOSS_C2),
    "OS-14": ("S3", "C3", "S3: tight curve or ramp outside the ODD at up to 60 km/h.", "C3: drift in a tight curve outpaces driver reaction (WP-C-03 OI-7, WP-S-04)."),
    "OS-15": ("S3", "C1", "S3: drift at an intersection towards crossing traffic or VRUs.", LOSS_C1),
    "OS-17": ("S3", "C3", "S3: lane departure at highway speed.", NOSUP_C3),
    "OS-18": ("S3", "C3", "S3: lane departure at highway speed.", UNRESP_C3),
    "OS-19": ("S2", "C1", "S2: loss of lateral control at roundabout speed; the driver is already steering the tight turn.", "C1: at ≤ 40 km/h the driver has time to steer; the turn needs more steering than the item gives anyway."),
    "OS-20": ("S3", "C2", "S3: drift through a lane shift into workers or a barrier.", LOSS_C2),
    "OS-21": ("S3", "C1", "S3: drift towards the oncoming side on an unmarked road.", LOSS_C1),
  },
  "H-03": {
    "OS-01": ("S2", "C1", "S2: speed rises above the set speed in free flow; moderate impacts if traffic slows.", "C1 ⚠: the driver brakes (credits AOU-03); acceleration bounded to +2.0 m/s² by the envelope."),
    "OS-02": ("S3", "C2", "S3: speed rises in a curve beyond the lateral limit; run-off.", ACC_C),
    "OS-03": ("S2", "C1", "S2: overspeed on a rural road.", "C1 ⚠: the driver brakes (credits AOU-03)."),
    "OS-04": ("S3", "C2", "S3: acceleration towards VRUs.", ACC_C),
    "OS-05": ("S2", "C2", "S2: rear-end impact on the lead at moderate speed difference (HE-03.1).", ACC_C),
    "OS-06": ("S3", "C2", "S3: launch from standstill into a crossing pedestrian (HE-03.2).", "C2: the driver must brake immediately; a low-speed launch is limited."),
    "OS-07": ("S3", "C2", "S3: acceleration towards slower traffic at high closing speed (HE-03.3).", ACC_C),
    "OS-09": ("S3", "C3", "S3: acceleration during an imminent collision.", "C3: by definition the driver has not avoided the situation."),
    "OS-10": ("S3", "C2", "S3: acceleration continues while the driver brakes in an emergency.", ACC_C),
    "OS-12": ("S2", "C1", "S2: acceleration during a lane change.", "C1 ⚠: the driver controls the manoeuvre and brakes (credits AOU-03)."),
    "OS-13": ("S2", "C2", "S2: unexpected acceleration while not engaged: during manual driving, after a false engagement, or just after a brake press has cancelled engagement (HE-03.7, DQ-364).", ACC_C),
    "OS-14": ("S3", "C2", "S3: acceleration in a residential street towards VRUs.", ACC_C),
    "OS-15": ("S3", "C2", "S3: acceleration into an intersection with crossing traffic or VRUs.", ACC_C),
    "OS-16": ("S3", "C2", "S3: speed rises in a rural curve beyond the lateral limit; run-off or oncoming lane.", ACC_C),
    "OS-17": ("S2", "C3", "S2: speed rises above the set speed on the highway; moderate impacts if traffic slows (as OS-01).", NOSUP_C3),
    "OS-18": ("S2", "C3", "S2: as OS-17.", UNRESP_C3),
    "OS-19": ("S3", "C2", "S3: acceleration in a roundabout towards a cyclist or crossing pedestrian.", ACC_C),
    "OS-20": ("S3", "C2", "S3: acceleration in a work zone towards workers or a queue.", ACC_C),
    "OS-21": ("S2", "C1", "S2: overspeed on an unmarked road (as OS-03).", "C1 ⚠: the driver brakes (credits AOU-03)."),
  },
  "H-04": {
    "OS-01": ("S2", "C1", "S2: rear impact by following traffic at a normal gap.", DEC_C1),
    "OS-02": ("S2", "C1", "S2: unexpected braking in a curve; rear impact or yaw disturbance.", DEC_C1),
    "OS-03": ("S2", "C1", "S2: rear impact by following traffic.", DEC_C1),
    "OS-04": ("S1", "C1", "S1: low-speed rear impact.", DEC_C1),
    "OS-05": ("S2", "C2", "S2: in dense traffic a follower is close; rear impact.", DEC_C2),
    "OS-06": ("S1", "C1", "S1: queue speed.", DEC_C1),
    "OS-07": ("S1", "C1", "S1: the vehicle is about to slow anyway; earlier braking is benign for following traffic that is also slowing.", DEC_C1),
    "OS-08": ("S2", "C2", "S2: rear impact by a close follower (HE-04.1).", DEC_C2),
    "OS-10": ("S2", "C1", "S2: sudden braking during a driver evasive manoeuvre.", DEC_C1),
    "OS-12": ("S2", "C2", "S2: braking during a lane change in front of traffic in the target lane.", DEC_C2),
    "OS-13": ("S2", "C2", "S2: braking applied during manual driving, follower behind.", DEC_C2),
    "OS-14": ("S1", "C1", "S1: low speed outside the ODD.", DEC_C1),
    "OS-15": ("S2", "C1", "S2: unexpected stop before an intersection with a follower behind.", DEC_C1),
    "OS-16": ("S2", "C1", "S2: unexpected braking in a rural curve; rear impact or yaw disturbance.", DEC_C1),
    "OS-17": ("S2", "C1", "S2: rear impact by following traffic at a normal gap (as OS-01).", DEC_C1 + " The following driver controls the rear impact; the ego driver's attention does not change it."),
    "OS-18": ("S2", "C1", "S2: as OS-17.", DEC_C1 + " As OS-17."),
    "OS-19": ("S1", "C1", "S1: low-speed rear impact in a roundabout.", DEC_C1),
    "OS-20": ("S2", "C1", "S2: rear impact by following traffic in a work zone.", DEC_C1),
    "OS-21": ("S2", "C1", "S2: rear impact by following traffic.", DEC_C1),
  },
  "H-05": {
    "OS-09": ("S3", "C2", "S3: the driver acts on an imminent collision and the system does not release.", "C2 ⚠: credits AOU-01/02/03 (driver can overpower EPS torque; brakes override ACC)."),
    "OS-10": ("S3", "C2", "S3: emergency braking or evasive steering impaired by continued actuation (HE-05.1, HE-05.2).", "C2 ⚠: credits AOU-01/02/03."),
  },
  "H-06": {
    "OS-05": ("S2", "C2", "S2: lead brakes and the ego vehicle does not; rear-end at moderate speed difference.", "C2: supervising driver, but reliance on ACC delays the reaction."),
    "OS-06": ("S1", "C2", "S1: low-speed rear-end (HE-06.2).", "C2: reliance on ACC."),
    "OS-07": ("S3", "C2", "S3: high closing speed on stationary or slow traffic (HE-06.1).", "C2: supervising driver; the stock PCS is not credited."),
    "OS-09": ("S3", "C3", "S3: imminent collision while ACC deceleration is silently lost.", "C3: by definition the driver has not avoided the situation."),
    "OS-14": ("S2", "C2", "S2: lead or obstacle outside the ODD at up to 60 km/h.", "C2: reliance on ACC."),
    "OS-15": ("S2", "C2", "S2: queue at an intersection; rear-end at moderate speed.", "C2: reliance on ACC."),
    "OS-17": ("S3", "C3", "S3: closing on slower or stationary traffic at highway speed while deceleration is silently lost.", NOSUP_C3),
    "OS-18": ("S3", "C3", "S3: as OS-17.", UNRESP_C3),
    "OS-20": ("S2", "C2", "S2: queue in a work zone; rear-end at moderate speed.", "C2: reliance on ACC."),
    "OS-21": ("S2", "C2", "S2: lead or obstacle on an unmarked road at up to 90 km/h.", "C2: reliance on ACC."),
  },
  "H-07": {
    "OS-01": ("S3", "C1", "S3: the driver believes the system steers; lane departure at highway speed.", "C1: on a straight road the drift is slow and an attentive driver notices it."),
    "OS-02": ("S3", "C3", "S3: unnoticed disengagement in a curve; departure.", "C3: the driver believes the system steers; at the curve bound the drift (about 0.6 m in 0.7 s, WP-S-04 OI-2) is faster than the reaction; re-rated with HE-02.1 (DQ-059)."),
    "OS-03": ("S3", "C1", "S3: drift towards the oncoming lane.", "C1: mostly straight road; the drift is slow and an attentive driver notices it."),
    "OS-16": ("S3", "C3", "S3: unnoticed disengagement in a rural curve; departure into the oncoming lane.", "C3: as OS-02."),
    "OS-04": ("S3", "C1", "S3: drift towards VRUs.", "C1: low speed, attentive driver."),
    "OS-05": ("S2", "C2", "S2: the driver expects ACC to brake for the lead; rear-end.", "C2: reliance on a function that is not active."),
    "OS-07": ("S3", "C2", "S3: the driver expects ACC to slow for traffic ahead; high closing speed.", "C2: reliance on a function that is not active."),
    "OS-12": ("S3", "C2", "S3: the driver expects assisted lane change; vehicle straddles lanes.", "C2: as OS-02."),
    "OS-15": ("S3", "C1", "S3: unexpected behaviour at an intersection.", "C1: the driver controls all stops at intersections."),
    "OS-17": ("S3", "C3", "S3: the take-over alert is missing or the display shows engaged; with eyes off the road the sound is the only channel left.", NOSUP_C3),
    "OS-20": ("S3", "C2", "S3: the driver believes the system steers through the lane shift; departure towards workers.", "C2: reliance on a function that is not active."),
    "OS-21": ("S3", "C1", "S3: drift towards the oncoming side.", "C1: mostly straight road; the drift is slow and an attentive driver notices it."),
  },
  "H-08": {
    "OS-09": ("S3", "C3", "S3: PCS-relevant impacts are severe (HE-08.1).", "C3: by definition the driver did not avoid the situation; the stock function exists for this case."),
  },
  "H-09": {
    "OS-17": ("S3", "C2", "S3: the item keeps driving without supervision; any situation it does not handle (stationary vehicle, cut-in, faded lines) ends in a highway-speed collision.", "C2: the DM fails silently, but a distracted driver who can still respond returns attention to the road on their own in most cases (≥ 90 %) before a situation demands it; to be confirmed with the DM clinic (WP-C-08 V-5)."),
    "OS-18": ("S3", "C3", "S3: as OS-17, with nobody able to take over.", "C3: the driver cannot respond; without the no-response reaction (forced deceleration) nothing brings the vehicle to a minimal-risk state."),
  },
  "H-10": {
    "OS-15": ("S3", "C2", "S3: entering an intersection against a red light or stop sign; side impact or VRU.", "C2 ⚠: the driver remains responsible, but Experimental Mode invites over-trust (SH-09, WP-C-05); evidence for C2 needed."),
    "OS-14": ("S3", "C2", "S3: residential stop sign with VRUs.", "C2 ⚠: as OS-15."),
  },
}
NOT_HAZARDOUS = {
  "H-01": "",
  "H-02": "Not hazardous here: the driver is already steering or the item is not engaged.",
  "H-03": "Not hazardous here: acceleration does not reduce the margin in this situation (e.g. pulling away from a close follower).",
  "H-04": "Not hazardous here: braking does not add risk (e.g. during an imminent collision braking helps).",
  "H-05": "Evaluated under OS-09/OS-10, the situations in which the driver acts to override; other situations would double-count the same override event.",
  "H-06": "Not hazardous here: no lead or obstacle requires deceleration, or the driver is already braking, or the item is not engaged.",
  "H-07": "Not hazardous here: covered by the road situations where the driver's belief about the system state matters.",
  "H-08": "Not hazardous here: the stock PCS is not demanded outside an imminent-collision situation.",
  "H-09": "Not hazardous here: the driver supervises, so a missed detection is latent; it removes a measure the controllability of H-02 and H-06 relies on. Rated in OS-17 and OS-18.",
  "H-10": "Not hazardous here: no traffic signal or stop sign is involved.",
}
# Function-specific rules: a false FCW does not actuate; any braking is the driver's own reaction.
FUNCTION_RULES = {
  "F-06": {
    "OS-05": ("S2", "C1", "S2: driver reflex-brakes on a false warning in dense traffic; rear impact by a follower.", "C1: the warning does not actuate; most drivers glance at the scene and brake moderately or not at all (≥ 99 %)."),
    "OS-08": ("S2", "C1", "S2: driver reflex-brakes with a close follower; rear impact.", "C1: as OS-05."),
    "OS-12": ("S2", "C1", "S2: driver reflex-brakes during a lane change in front of target-lane traffic.", "C1: as OS-05."),
    "OS-13": ("S2", "C1", "S2: model FCW also fires when not engaged (selfdrived.py:490); reflex braking with a follower.", "C1: as OS-05."),
  },
}
FUNCTION_NOT_HAZARDOUS = {"F-06": "Not hazardous here: a false warning without a close follower leads at most to a startle or a moderate driver brake (S1, QM in the draft §5.8)."}
# Situations where only unrequested actuation can occur (item not engaged).
NOT_ENGAGED = {"OS-13"}
# Functions that cannot act at all while not engaged (DM forced deceleration is applied through controlsd only when engaged).
ENGAGED_ONLY = {"F-04"}
UNREQUESTED = {"M03", "M10"}
# Pairs that also occur while not engaged although their guide word is not M03/M10: acceleration while not engaged or
# just after a brake press (FTA G3.3; false engagement F-03 M03 reaches the vehicle as an F-02 acceleration), DQ-364.
NOT_ENGAGED_PAIRS = {("F-02", "M05")}
# AoU-credited ratings ("⚠" in C rationale) get a sensitivity line: C+1 if the AoU fails.

C_UP = {"C0": "C1", "C1": "C2", "C2": "C3", "C3": "C3"}
S_UP = {"S0": "S0", "S1": "S2", "S2": "S3", "S3": "S3"}


def weather_adjust(h: str, os_code: str, w: str, S: str, C: str, s_rat: str, c_rat: str):
  if S == "S0":
    return S, C, s_rat, c_rat
  if w == "W05":
    # H-09 is not adjusted: its C rates whether the driver resumes supervision, which the surface does not change.
    if h in {"H-01", "H-02", "H-03", "H-06", "H-07", "H-10"}:
      C, c_rat = C_UP[C], c_rat + " Snow/ice: low friction; a correction or braking can induce a skid (C+1)."
    if h == "H-04":
      S, C = S_UP[S], C_UP[C]
      s_rat += " Snow/ice: unexpected braking can destabilise the vehicle (S+1)."
      c_rat += " Snow/ice (C+1)."
  elif w in {"W02", "W04"} and h == "H-04" and os_code in {"OS-02", "OS-14", "OS-16"}:
    S, C = "S3", "C1"
    s_rat += " Wet: unexpected braking in a curve can cause instability (HE-04.2)."
    c_rat = "C1 ⚠: VSC available (AOU-10); moderate ACC deceleration on wet roads is controllable for most drivers."
  elif w in {"W04", "W06"} and h in {"H-06", "H-10"}:
    C, c_rat = C_UP[C], c_rat + " Reduced visibility outside the ODD delays the driver's detection of the hazard (C+1)."
  return S, C, s_rat, c_rat


ASIL = {("S1", "E3", "C3"): "A", ("S1", "E4", "C2"): "A", ("S1", "E4", "C3"): "B",
        ("S2", "E2", "C3"): "A", ("S2", "E3", "C2"): "A", ("S2", "E3", "C3"): "B",
        ("S2", "E4", "C1"): "A", ("S2", "E4", "C2"): "B", ("S2", "E4", "C3"): "C",
        ("S3", "E1", "C3"): "A", ("S3", "E2", "C2"): "A", ("S3", "E2", "C3"): "B",
        ("S3", "E3", "C1"): "A", ("S3", "E3", "C2"): "B", ("S3", "E3", "C3"): "C",
        ("S3", "E4", "C1"): "B", ("S3", "E4", "C2"): "C", ("S3", "E4", "C3"): "D"}


def asil(S, E, C):
  if S == "S0":
    return "—"
  if E == "E0" or C == "C0":
    return "QM"
  return ASIL.get((S, E, C), "QM")


def rate(f_id, m_id, h, os_row, w_row):
  os_code, _, _, _, os_e, _ = os_row
  w_code, _, w_e, _ = w_row
  E = min(os_e, w_e, key=lambda e: E_RANK[e])
  e_rat = f"{E}: situation {os_code} is {os_e}, condition {w_code} is {w_e}; the combination is no more frequent than the rarer of the two (ISO 26262-3 Table B.2, duration)."
  if os_code in NOT_ENGAGED and f_id in ENGAGED_ONLY:
    return ("S0", E, "C0", f"S0: item not engaged; {f_id} acts on the vehicle only while engaged (controlsd).", e_rat, "n/a")
  if h != "H-08" and f_id not in FUNCTION_RULES and os_code in NOT_ENGAGED and m_id not in UNREQUESTED \
     and (f_id, m_id) not in NOT_ENGAGED_PAIRS:
    return ("S0", E, "C0", f"S0: item not engaged; {m_id} cannot occur without a request (only unrequested actuation, M03/M10, applies).", e_rat, "n/a")
  rules = FUNCTION_RULES.get(f_id, RULES[h])
  rule = rules.get(os_code)
  if rule is None:
    return ("S0", E, "C0", "S0: " + FUNCTION_NOT_HAZARDOUS.get(f_id, NOT_HAZARDOUS[h]), e_rat, "n/a")
  S, C, s_rat, c_rat = rule
  if (f_id, m_id) == ("F-01", "M04") and "⚠" not in c_rat:
    c_rat += " ⚠ Credits AOU-01: the stuck request is bounded by the EPS LKA torque authority (HE-02.3)."
  S, C, s_rat, c_rat = weather_adjust(h, os_code, w_code, S, C, s_rat, c_rat)
  return (S, E, C, s_rat, e_rat, c_rat)


# ---------------------------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------------------------
def build(experimental: bool) -> tuple[dict, list[dict]]:
  funcs = FUNCTIONS + ([EXPERIMENTAL_FUNCTION] if experimental else [])
  ratings, overrides, rows = [], [], []
  for f_id, *_ in funcs:
    for m_id, _ in MALFUNCTIONS:
      cls, h, sub, rat = FM[f_id][m_id]
      hz = f"{h} {HAZARDS[h]}" if h else rat
      ratings.append({"function_id": f_id, "malfunction_id": m_id, "classification": cls, "subsumed_by": sub,
                      "rationale": rat, "hazard_description": hz})
      if cls != SC or sub:
        continue
      for os_row in SITUATIONS:
        for w_row in WEATHER:
          S, E, C, s_rat, e_rat, c_rat = rate(f_id, m_id, h, os_row, w_row)
          overrides.append({"function_id": f_id, "malfunction_id": m_id, "location_code": os_row[0],
                            "weather_code": w_row[0], "S": S, "E": E, "C": C,
                            "S_rationale": s_rat, "E_rationale": e_rat, "C_rationale": c_rat})
          a = asil(S, E, C)
          a_fail = asil(S, E, C_UP[C]) if "⚠" in c_rat else a
          rows.append({"f": f_id, "m": m_id, "h": h, "os": os_row[0], "w": w_row[0], "S": S, "E": E, "C": C,
                       "asil": a, "asil_aou_fail": a_fail, "s_rat": s_rat, "e_rat": e_rat, "c_rat": c_rat})
  data = {
    "item": {"name": "LionDriver Supervised Driving Assistance", "abbr": "LD-SDA", "project": "LionDriver",
             "doc_id": "WP-C-03" + (" (Experimental Mode variant)" if experimental else ""),
             "revision": "0.6 (Cartesian)", "date": "2026-10-19", "author": "Assurance team (draft)",
             "approver": "Safety manager", "company": "LionDriver"},
    "scope_description": "Aftermarket supervised SAE Level 2 feature on the Toyota Corolla, 12th generation (E210), TSS 2.0 (reference configuration, WP-C-01), on limited-access highways only (WP-C-02). Lateral (LKA torque) and longitudinal (ACC) control with driver monitoring; the panda safety MCU envelope bounds actuation. Experimental Mode is "
                         + ("INCLUDED in this variant (D-08 option B)." if experimental else "EXCLUDED (D-08 option A, recommended)."),
    "boundary_diagram_notes": "See WP-C-01 §3.3. Vehicle ECUs (EPS, PCM, ABS/VSC, camera, radar) are outside the item, with AoUs.",
    "assumptions": [
      {"id": "AOU-01", "category": "Vehicle", "assumption": "EPS limits LKA torque to an overpowerable level and fades it out on message loss.", "rationale": "WP-C-01 §7; unverified (⚠)."},
      {"id": "AOU-02", "category": "Driver", "assumption": "A normal driver overrides full LKA torque within the CA-01 criterion.", "rationale": "WP-C-01 §7; unverified (⚠)."},
      {"id": "AOU-03", "category": "Vehicle", "assumption": "Driver braking always brakes and cancels ACC.", "rationale": "WP-C-01 §7; unverified (⚠)."},
      {"id": "AOU-05", "category": "Vehicle", "assumption": "The PCM bounds ACC acceleration and deceleration.", "rationale": "WP-C-01 §7; unverified (⚠)."},
      {"id": "AOU-06", "category": "Driver", "assumption": "Licensed, briefed, attentive driver supervising continuously; controllability rated for this typical driver.", "rationale": "WP-C-01 §7; ISO 26262-3 controllability."},
      {"id": "AOU-10", "category": "Vehicle", "assumption": "VSC/ABS enabled and functional.", "rationale": "WP-C-01 §7."},
      {"id": "A-ENV", "category": "Environment", "assumption": "Situations OS-03, OS-04, OS-14…OS-21 and weather W04–W06 are outside the ODD or the intended driver state and included as foreseeable misuse.", "rationale": "ISO 26262-3 §6.4.2 (foreseeable misuse); WP-C-02 §3 (highway only, DQ-023); H-STPA-1 (DQ-003, DQ-205)."},
      {"id": "A-ODD", "category": "Environment", "assumption": "Engaged driving off the highway is 1–10 % of engaged time (E3); the item does not yet prevent it.", "rationale": "RR-2026-011 (upstream use), DQ-213 A; WP-C-02 §5 (speed floor DQ-280, FM-08 later); at E4 SG-02 would be ASIL D (WP-C-03 §6.1)."},
      {"id": "A-CS", "category": "Cybersec", "assumption": "Cyber-induced malfunctions are analysed in the TARA (WP-C-09) and map onto H-01…H-08.", "rationale": "Scope partition."},
    ],
    "interfaces": [
      {"id": "IF-01", "interface": "Vehicle CAN TX (bus 0)", "direction": "Out", "description": "0x2E4 LKA torque, 0x343 ACC, 0x412 HUD, 0x1D2 cancel"},
      {"id": "IF-02", "interface": "Vehicle/radar CAN RX (bus 0/1)", "direction": "In", "description": "Wheel speeds, torque sensor, PCM cruise, brake, EPS status, radar tracks"},
      {"id": "IF-03", "interface": "Camera CAN forwarding (bus 2)", "direction": "In/Out", "description": "Camera messages incl. PCS forwarded to the car"},
      {"id": "IF-04", "interface": "SoC <-> panda (SPI)", "direction": "Internal", "description": "CAN streams, heartbeat, safety mode"},
      {"id": "IF-06", "interface": "Driver camera", "direction": "In", "description": "DM images"},
      {"id": "IF-07", "interface": "HMI", "direction": "Out/In", "description": "Display, sounds, settings, HUD"},
    ],
    "functions": [{"id": f[0], "name": f[1], "kinetic_authority": f[2], "description": f[3]} for f in funcs],
    "environments": {
      "locations": [{"code": s[0], "name": s[1], "speed_min_kph": s[2], "speed_max_kph": s[3], "default_e": s[4]} for s in SITUATIONS],
      "weather": [{"code": w[0], "name": w[1], "default_e": w[2]} for w in WEATHER],
    },
    "function_malfunction_ratings": ratings,
    "rating_overrides": overrides,
  }
  return data, rows


def _csv(header, rows) -> str:
  buf = io.StringIO()
  w = csv.writer(buf, lineterminator="\n")
  w.writerow(header)
  w.writerows(rows)
  return buf.getvalue()


def events_csv(experimental: bool) -> str:
  """Every hazardous-event row of the workbook (tab 12), one line each, for review on GitHub."""
  fname = {f[0]: f[1] for f in FUNCTIONS + [EXPERIMENTAL_FUNCTION]}
  mname = dict(MALFUNCTIONS)
  osname = {o[0]: o[1] for o in SITUATIONS}
  wname = {w[0]: w[1] for w in WEATHER}
  out = []
  for i, r in enumerate(build(experimental)[1], start=1):
    out.append([f"{r['f']}/{r['m']}/{r['os']}/{r['w']}", f"H-{i:04d}", r["f"], fname[r["f"]], r["m"], mname[r["m"]],
                f"{r['h']} {HAZARDS[r['h']]}", r["os"], osname[r["os"]], r["w"], wname[r["w"]],
                r["S"], r["E"], r["C"], r["asil"], r["asil_aou_fail"], SG_MAP.get(r["h"], ""),
                r["s_rat"], r["e_rat"], r["c_rat"]])
  return _csv(["Key", "Workbook HARA ID", "Function", "Function name", "Guide word", "Guide word name", "Hazard", "Situation",
               "Situation name", "Condition", "Condition name", "S", "E", "C", "ASIL", "ASIL if ⚠ AoUs fail",
               "Safety goal", "S rationale", "E rationale", "C rationale"], out)


def pairs_csv() -> str:
  """The function × guide-word classification (tab 11) with the reason for every pair, including NSC and NA."""
  fname = {f[0]: f[1] for f in FUNCTIONS + [EXPERIMENTAL_FUNCTION]}
  out = []
  for r in build(True)[0]["function_malfunction_ratings"]:
    out.append([f"{r['function_id']}/{r['malfunction_id']}", r["function_id"], fname[r["function_id"]],
                r["malfunction_id"], dict(MALFUNCTIONS)[r["malfunction_id"]], r["classification"],
                r["subsumed_by"] or "", r["hazard_description"] if r["classification"] == SC else "", r["rationale"],
                "Experimental variant only" if r["function_id"] == EXPERIMENTAL_FUNCTION[0] else ""])
  return _csv(["Key", "Function", "Function name", "Guide word", "Guide word name", "Class", "Subsumed by",
               "Hazard", "Rationale", "Scope"], out)


ORDER = ["—", "QM", "A", "B", "C", "D"]


def summary(ref_rows, exp_rows) -> str:
  def fm_counts(experimental):
    funcs = [f[0] for f in FUNCTIONS] + (["F-02X"] if experimental else [])
    c = Counter()
    for f in funcs:
      for m, _ in MALFUNCTIONS:
        cls, _, sub, _ = FM[f][m]
        c[cls] += 1
        if cls == SC:
          c["SC-expanded" if not sub else "SC-subsumed"] += 1
    return len(funcs), c

  def block(rows, experimental, title):
    nf, c = fm_counts(experimental)
    envs = len(SITUATIONS) * len(WEATHER)
    a = Counter(r["asil"] for r in rows)
    af = Counter(r["asil_aou_fail"] for r in rows)
    out = [f"### {title}", "",
           "| Step | Count |", "|---|---|",
           f"| Functions | {nf} |",
           f"| Function × guide-word pairs ({nf} × 14) | {nf * 14} |",
           f"| … classified SC | {c[SC]} ({c['SC-expanded']} expanded, {c['SC-subsumed']} subsumed by another SC pair) |",
           f"| … classified NSC | {c[NSC]} |",
           f"| … classified NA | {c[NA]} |",
           f"| Environments per SC pair ({len(SITUATIONS)} situations × {len(WEATHER)} conditions) | {envs} |",
           f"| Hazardous-event rows generated ({c['SC-expanded']} × {envs}) | {len(rows)} |",
           f"| … not hazardous in that situation (S0, reason recorded) | {a['—']} |",
           f"| … rated QM | {a['QM']} |",
           f"| … rated ASIL A / B / C / D | {a['A']} / {a['B']} / {a['C']} / {a['D']} |",
           f"| … ASIL A–D if every ⚠ AoU fails (C+1) | {af['A']} / {af['B']} / {af['C']} / {af['D']} |",
           f"| Distinct hazardous events (function × guide word × situation with S ≠ S0, weather variants merged) | {len({(r['f'], r['m'], r['os']) for r in rows if r['S'] != 'S0'})} |",
           f"| … of which ASIL ≥ A in at least one condition | {len({(r['f'], r['m'], r['os']) for r in rows if r['asil'] in 'ABCD'})} |",
           "", "| Hazard | Rows rated ASIL ≥ A | Worst-case ASIL | If ⚠ AoUs fail | Worst-case rows (function, guide word, situation, condition) |",
           "|---|---|---|---|---|"]
    by_h = defaultdict(list)
    for r in rows:
      by_h[r["h"]].append(r)
    for h in sorted(by_h):
      rs = by_h[h]
      worst = max((r["asil"] for r in rs), key=ORDER.index)
      worst_f = max((r["asil_aou_fail"] for r in rs), key=ORDER.index)
      n = sum(1 for r in rs if r["asil"] in "ABCD")
      ex = sorted({f"{r['f']} {r['m']} {r['os']} {r['w']}" for r in rs if r["asil"] == worst})
      exs = ", ".join(ex[:4]) + (f" (+{len(ex) - 4} more)" if len(ex) > 4 else "")
      out.append(f"| {h} {HAZARDS[h]} | {n} | {worst} | {worst_f} | {exs} |")
    return out

  lines = ["# HARA summary (generated)", "",
           "Generated by [`hara_model.py`](hara_model.py). Do not edit by hand; run `python3 hara_model.py`.", "",
           "The workbook rows are function × guide word × operational situation × weather/surface condition, expanded only for SC pairs that are not subsumed by another SC pair. Every row has S, E and C with rationale; S0 rows record why the malfunction is not hazardous in that situation, so nothing is pruned silently.", ""]
  lines += block(ref_rows, False, "Reference scope (Chill mode only, D-08 option A)")
  lines += [""]
  lines += block(exp_rows, True, "Variant: Experimental Mode included (D-08 option B)")
  lines += [""]
  return "\n".join(lines)


def counts_table() -> str:
  def stats(experimental):
    _, rows = build(experimental)
    funcs = [f[0] for f in FUNCTIONS] + (["F-02X"] if experimental else [])
    c = Counter()
    for f in funcs:
      for m, _ in MALFUNCTIONS:
        cls, _, sub, _ = FM[f][m]
        c[cls] += 1
        if cls == SC and not sub:
          c["exp"] += 1
    a = Counter(r["asil"] for r in rows)
    af = Counter(r["asil_aou_fail"] for r in rows)
    return {
      "fm": f"{len(funcs)} × 14 = {len(funcs) * 14}",
      "cls": f"{c[SC]} / {c[NSC]} / {c[NA]}",
      "exp": str(c["exp"]),
      "rows": str(len(rows)),
      "s0": str(a["—"]), "qm": str(a["QM"]),
      "asil": " / ".join(str(a[x]) for x in "ABCD"),
      "asil_f": " / ".join(str(af[x]) for x in "ABCD"),
      "he": str(len({(r["f"], r["m"], r["os"]) for r in rows if r["S"] != "S0"})),
      "he_a": str(len({(r["f"], r["m"], r["os"]) for r in rows if r["asil"] in "ABCD"})),
    }
  r, x = stats(False), stats(True)
  lines = ["| Step | Reference scope (Chill only) | With Experimental Mode |", "|---|---|---|"]
  for label, k in [("Functions × guide words", "fm"), ("Pairs classified SC / NSC / NA", "cls"),
                   ("SC pairs expanded (not subsumed)", "exp"),
                   (f"Rows generated (pairs × {len(SITUATIONS)} situations × {len(WEATHER)} conditions)", "rows"),
                   ("Rows not hazardous in that situation (S0, reason recorded)", "s0"), ("Rows rated QM", "qm"),
                   ("Rows rated ASIL A / B / C / D", "asil"), ("Rows ASIL A / B / C / D if every ⚠ AoU fails", "asil_f"),
                   ("Distinct hazardous events (function × guide word × situation, S ≠ S0)", "he"),
                   ("… with ASIL ≥ A in at least one condition", "he_a")]:
    lines.append(f"| {label} | {r[k]} | {x[k]} |")
  return "\n".join(lines)


HARA_MD = HERE.parent / "WP-C-03-hara.md"
START, END = "<!-- hara-counts:start (generated by hara/hara_model.py) -->", "<!-- hara-counts:end -->"


def hara_md_text() -> str:
  md = HARA_MD.read_text()
  i, j = md.index(START), md.index(END)
  return md[:i + len(START)] + "\n" + counts_table() + "\n" + md[j:]


OUTPUTS = {
  "../WP-C-03-hara.md": hara_md_text,
  "build/hara_input.json": lambda: json.dumps(build(False)[0], indent=1, ensure_ascii=False) + "\n",
  "build/hara_input_experimental.json": lambda: json.dumps(build(True)[0], indent=1, ensure_ascii=False) + "\n",
  "hara-cartesian-summary.md": lambda: summary(build(False)[1], build(True)[1]),
  "hara-events.csv": lambda: events_csv(False),
  "hara-events_experimental.csv": lambda: events_csv(True),
  "hara-function-guideword.csv": pairs_csv,
}

# ---------------------------------------------------------------------------------------------
# Post-processing of the generated workbook (LionDriver corrections to the generic tool output)
# ---------------------------------------------------------------------------------------------
ISO_E = [("E0", "Incredible", "Not specified (situations so unusual they are not considered)"),
         ("E1", "Very low probability", "Not specified (situations that occur less often than E2)"),
         ("E2", "Low probability", "< 1 % of average operating time"),
         ("E3", "Medium probability", "1 % to 10 % of average operating time"),
         ("E4", "High probability", "> 10 % of average operating time")]
SG_MAP = {"H-01": "SG-01", "H-02": "SG-02", "H-03": "SG-03", "H-04": "SG-04", "H-05": "SG-05",
          "H-06": "SG-06", "H-07": "SG-02 / SG-06 (see WP-C-03 §6)", "H-08": "SG-07", "H-09": "SG-08", "H-10": "SG-09 (only if D-08 option B)"}


def postprocess(path: Path) -> None:
  from openpyxl import load_workbook
  from openpyxl.styles import Alignment, Font
  wb = load_workbook(path)
  ws = wb["00_Title_Page"]
  ws.cell(row=15, column=2, value="Status").font = Font(bold=True)
  ws.cell(row=15, column=3, value="Draft: ratings are proposals for review; not approved until the I3 confirmation review (WP-C-03 header)")
  ws = wb["08_Exposure_Reference"]
  for i, (e, p, anchor) in enumerate(ISO_E, start=6):
    ws.cell(row=i, column=1, value=e)
    ws.cell(row=i, column=2, value=p)
    ws.cell(row=i, column=3, value=anchor)
  note = "LionDriver: anchors replaced with ISO 26262-3:2018 Table B.2 (duration-based) by hara_model.py --postprocess; the generator's default anchors differ."
  ws.cell(row=12, column=1, value=note).font = Font(italic=True, size=10)
  ws = wb["11_Function_x_Malfunction"]
  ws.cell(row=4, column=8, value="LionDriver rationale").font = Font(bold=True)
  rationale = {(f, m): FM[f][m][3] for f in FM for m, _ in MALFUNCTIONS}
  for r in range(5, ws.max_row + 1):
    key = (ws.cell(row=r, column=1).value, ws.cell(row=r, column=3).value)
    if key in rationale:
      c = ws.cell(row=r, column=8, value=rationale[key])
      c.alignment = Alignment(wrap_text=True, vertical="top")
  ws.column_dimensions["H"].width = 70
  ws = wb["13_Safety_Goals"]
  ws.cell(row=2, column=1, value="Candidate goals per (function, hazard) as grouped by the generator. They are consolidated per hazard into SG-01…SG-08 in WP-C-03 §6; see column H.")
  ws.cell(row=4, column=8, value="Consolidated into").font = Font(bold=True)
  for r in range(5, ws.max_row + 1):
    hz = str(ws.cell(row=r, column=3).value or "")[:4]
    if hz in SG_MAP:
      ws.cell(row=r, column=8, value=SG_MAP[hz])
  ws.column_dimensions["H"].width = 30
  wb.save(path)


def main(argv):
  if len(argv) == 3 and argv[1] == "--postprocess":
    postprocess(Path(argv[2]))
    return 0
  check = "--check" in argv
  stale = []
  for name, gen in OUTPUTS.items():
    text = gen()
    p = HERE / name
    if check and name.startswith("build/"):
      continue
    p.parent.mkdir(exist_ok=True)
    if check:
      if not p.exists() or p.read_text() != text:
        stale.append(name)
    else:
      p.write_text(text)
  if stale:
    print("stale:", ", ".join(stale), "- run python3 hara_model.py")
    return 1
  print("ok" if check else "written: " + ", ".join(OUTPUTS))
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv))
