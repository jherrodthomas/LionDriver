#!/usr/bin/env python3
"""Draw the loss scenario sheets of WP-A-05 §5: one card per loss scenario, how its unsafe control action comes about.

Four sheets by the §4 section of the scenario's first UCA (its number range): the driver (`fig-a05-5-7-ls-driver.svg`),
openpilot's control actions (§4.2, `-5-8-ls-openpilot.svg`), inside openpilot, configuration and updates (§4.6,
`-5-9-ls-inside.svg`), and the panda, the harness box and the car's own controllers (§4.3, §4.4, `-5-10-ls-panda.svg`).
Each card shows:

- the scenario as three steps: the cause, what the controller then believes or never learns (the step is named after
  the scenario's causal-factor type in its Type column), and the unsafe control action on the road;
- a road scene of the outcome (SMIL, 6 s loop; a viewer that does not animate shows the last frame);
- the Covered-by IDs of its §5 row, its status from stpa-map.yaml and why it is still open.

The steps are short paraphrases of the scenario row. Each carries a phrase quoted from the row (steps 1 and 2) or from
its UCA's text in §4 (step 3), and the build fails if that phrase is no longer there: change the row, and its card must
be redrawn. IDs, UCAs, types, statuses and the Covered-by column are read, not written here. The build also fails if a
scenario in §5 or stpa-map.yaml has no card, or a card has no scenario. The scenes are schematic.

Built and checked by fig_a05_stpa.py, which passes itself in (it runs as __main__). Drawing helpers come from
../../02-concept/sotif/fm_scenes.py and ../../02-concept/hara/hara_figures.py.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
for p in (HERE.parent.parent / "02-concept" / "sotif", HERE.parent.parent / "02-concept" / "hara"):
  sys.path.insert(0, str(p))
import fm_scenes as fm  # noqa: E402
import hara_figures as hf  # noqa: E402
from fm_scenes import BAD, GOOD, NOTE, LANE, NEXT, X0, X1, badge, ego, other, road, sample, still, tag  # noqa: E402
from hara_figures import HAIR, INK, MUTED, pill, svg_doc, t, wrap  # noqa: E402

K = None  # fig_a05_stpa, passed in by sheets()


def fail(msg):
  raise K.ParseError(f"loss scenario cards: {msg}")


SHEETS = {  # by the controller of the scenario's first UCA, so a UCA moving between sections keeps its sheet
  "fig-a05-5-7-ls-driver.svg": ("5-7", "the driver (C1)", lambda ctrl: ctrl.startswith("C1 ")),
  "fig-a05-5-8-ls-openpilot.svg": ("5-8", "openpilot's control actions (C2)", lambda ctrl: ctrl.startswith("C2 ")),
  "fig-a05-5-9-ls-inside.svg": ("5-9", "inside openpilot, configuration and updates (C2.x, C7)",
                                lambda ctrl: ctrl.startswith(("C2.", "C7 "))),
  "fig-a05-5-10-ls-panda.svg": ("5-10", "the panda, the harness box and the car's controllers (C3 to C6)",
                                lambda ctrl: ctrl.startswith(("C3 ", "C4 ", "C5 ", "C6 "))),
}
STATUS = {"new": ("#FEE2E2", "#7F1D1D", "New finding"), "known_gap": ("#FEF3C7", "#78350F", "Known gap"),
          "covered": ("#DCFCE7", "#14532D", "Covered"), "open_test": ("#E0F2FE", "#075985", "Open test")}
TYPES = [  # first keyword of the Type column -> (step-2 heading, colour, chip)
  ("feedback", "Feedback", "#2563EB"), ("process model", "Belief", "#7C3AED"), ("control algorithm", "Algorithm", "#B45309"),
  ("component failure", "Effect", "#B91C1C"), ("actuator failure", "Effect", "#B91C1C"), ("unsafe control", "Then", "#0F766E"),
  ("flawed process (", "Then", "#0F766E"), ("external controller", "Then", "#475569")]
STEP_COL = ["#475569", None, "#DC2626"]


def _plain(s):
  return re.sub(r"\*+([^*]+)\*+", r"\1", s).replace("`", "")


def kind(type_cell):
  low = type_cell.lower()
  hits = [(low.find(k), k, h, c) for k, h, c in TYPES if k in low]
  if not hits:
    fail(f"no causal-factor type in '{type_cell}'")
  _, k, h, c = min(hits)
  return h, c


# ---------------------------------------------------------------- scenes (280 x 70, fm_scenes vocabulary)

def go(x0, x1, y=LANE, f1=1.0):
  return sample(lambda f: (x0 + (x1 - x0) * min(1, f / f1), y))


def tags(t1, t2, y1=34, y2=66):
  return [tag(0.3, 90, y1, t1, NOTE), tag(0.75, 190, y2, t2, BAD)]


def sc_drift(dy, f0=0.3, k=1.6, extra=()):
  def draw(t1, t2):
    return road() + list(extra) + ego(fm.drifting(f0, dy, k=k)) + tags(t1, t2, 34 if dy > 0 else 66, 66 if dy > 0 else 34)
  return draw


def sc_fault(dy=8):
  def draw(t1, t2):
    f0 = 0.3
    return road() + ego(fm.drifting(f0, dy, k=1.4)) + [fm.marker(X0 + 248 * f0, LANE, f0)] + tags(t1, t2)
  return draw


def sc_lead(end, f1=0.85, accel=False):
  def draw(t1, t2):
    path = sample(lambda f: (X0 + (end - X0) * f ** 1.6, LANE)) if accel else go(X0, end, f1=f1)
    return road() + [still(end + 24, LANE)] + ego(path) + tags(t1, t2)
  return draw


def sc_phantom(t1, t2):
  stop = 0.4
  xs = lambda f: X0 + 248 * (f if f < stop else stop + (f - stop) * 0.15)
  return road() + [other(sample(lambda f: (min(xs(f) - 26, X0 - 40 + 248 * 0.75 * f), LANE)))] + \
      ego(sample(lambda f: (xs(f), LANE))) + tags(t1, t2)


def sc_light(t1, t2):
  light = ('<rect x="236" y="2" width="9" height="20" rx="2" fill="#1F2937"/><circle cx="240.5" cy="8" r="3" fill="#EF4444"/>'
           '<circle cx="240.5" cy="16" r="3" fill="#374151"/>')
  return road() + [light, still(250, LANE)] + ego(go(X0, 226, f1=0.85)) + tags(t1, t2)


def sc_unmarked(t1, t2):
  return road(False) + ['<line x1="0" y1="16" x2="280" y2="16" stroke="#F8FAFC" stroke-width="1" opacity="0.35"/>'] + \
      ego(go(X0, 220)) + tags(t1, t2)


def sc_straight(t1, t2):
  return road() + ego(go(X0, X1)) + tags(t1, t2)


def sc_slow_stop(t1, t2):
  return road() + ego(sample(lambda f: (X0 + 200 * (1 - (1 - f) ** 2), LANE))) + tags(t1, t2)


def sc_resume(t1, t2):
  return road() + [still(250, LANE)] + ego(sample(lambda f: (X0 + 140 * min(f, 0.5) / 0.5 + 86 * max(0, f - 0.5) / 0.5, LANE))) + \
      tags(t1, t2)


SCENES = {"steer": sc_drift(-12, k=1.4), "lane": sc_drift(-21), "curve": sc_drift(9, k=1.4), "fault": sc_fault(),
          "accel": sc_lead(213, accel=True), "late": sc_lead(212), "pcs": sc_lead(217, f1=0.8), "phantom": sc_phantom,
          "light": sc_light, "unmarked": sc_unmarked, "straight": sc_straight, "stop": sc_slow_stop, "resume": sc_resume}


# ---------------------------------------------------------------- one model per loss scenario
# title, scene, (scene tag 1, scene tag 2), steps: (text, quoted phrase) x 3; phrases 1-2 from the row, 3 from the UCA (or row)

MODELS = {
  "LS-01": ("Steering against it, it keeps steering", "steer", ("driver steers away", "item keeps pulling"), [
    ("The driver steers against the item to avoid an obstacle.", "The driver steers against the item to avoid an obstacle"),
    ("Driver torque only freezes the integrator; 'overriding' is an active state, and the panda limits have no driver-torque term.",
     "only freezes the torque integrator"),
    ("The item keeps commanding torque against the driver.", "Lateral torque commanded while the driver is steering against it")]),
  "LS-02": ("A light correction the item ignores", "steer", ("light correction (< 100 raw)", "keeps steering, no cue"), [
    ("The driver corrects with torque below the 100-raw threshold.", "corrective torque below the 100-raw threshold"),
    ("No override is detected; nothing on screen or in sound changes. Above it, only a grey border.", "No override is detected"),
    ("The driver stops correcting, believing the item has yielded.", "believes the item has yielded")]),
  "LS-03": ("Expects a stop at the red light", "light", ("Chill Mode: no stop", "driver does not brake"), [
    ("The driver has used Experimental Mode, or read upstream docs.", "The driver has used Experimental Mode before"),
    ("The driver expects stops at lights; the reference configuration runs Chill Mode.", "expects stops at lights"),
    ("The driver does not brake for the light or the stopped car.", "does not brake (Chill Mode does not stop for lights)")]),
  "LS-04": ("Watchdog reset silences the siren", "fault", ("MCU reset", "siren silent"), [
    ("The panda watchdog resets the MCU while engaged.", "The panda watchdog resets the MCU while engaged"),
    ("The MCU boots SILENT with the siren off. Only the SoC alerts, within 0.5 s.", "boots in SILENT with the siren off"),
    ("Steering and braking stop at once; the panda's own siren cannot sound.", "Withdraws authority abruptly while engaged")]),
  "LS-05": ("controlsd stalls, the last command repeats", "fault", ("controlsd stalls", "≈0.16 s on stale data"), [
    ("controlsd stalls while pandad keeps sending heartbeats.", "controlsd stalls while pandad keeps sending heartbeats"),
    ("About 0.1 s of a repeated in-limit command (by design); the arrival check revokes at about 0.16 s, no siren.",
     "about 0.1 s of a repeated in-limit command"),
    ("Authority is kept briefly on stale data.", "Keeps authority too long after SoC loss or stale vehicle data")]),
  "LS-06": ("Cruise on, openpilot off", "straight", ("PCM engages, openpilot not", "cancel, alert at 1 s"), [
    ("The driver presses SET while openpilot is not ready; the PCM engages cruise.",
     "the PCM engages cruise but openpilot stays disengaged"),
    ("Until v0.3 the panda granted authority on the PCM edge; now only once the heartbeat reports openpilot engaged.",
     "authority is granted once the heartbeat reports openpilot engaged"),
    ("Acceleration or torque while openpilot is not engaged but cruise is.",
     "Acceleration or torque commanded while openpilot is not engaged but PCM cruise is")]),
  "LS-07": ("The panda hangs while intercepting", "pcs", ("panda hangs, switches driven", "PCS frames lost"), [
    ("The panda hangs with the intercept switches driven.", "The panda hangs with the intercept switches driven"),
    ("A watchdog reset after about 90 ms releases the switches; a forwarding stall with the MCU running is not caught.",
     "A forwarding failure with the MCU still running"),
    ("Stock PCS frames are not forwarded while the switches intercept.", "while not forwarding stock PCS messages")]),
  "LS-08": ("The camera gives up on PCS", "pcs", ("LKA/ACC frames blocked", "camera fault: no PCS"), [
    ("The item blocks the stock camera's LKA/ACC messages.", "for its blocked LKA/ACC messages"),
    ("The camera receives no feedback for them.", "receives no feedback"),
    ("It sets a fault that also disables PCS; only a vehicle test can tell.", "sets a fault that also disables PCS")]),
  "LS-09": ("Sunglasses: DM falls back to wheel touch", "straight", ("sunglasses: wheel touch", "unsupervised for 25 s"), [
    ("Sunglasses or low light lower driver-monitoring confidence.", "Sunglasses or low light lower DM confidence"),
    ("The policy falls back to wheel touch (5/15/25 s) while the driver looks at a phone.", "falls back to wheel touch (5/15/25 s)"),
    ("Up to 25 s, several hundred metres, unsupervised; speed escalation (TSR-634) is unit-tested only.",
     "several hundred metres unsupervised")]),
  "LS-10": ("Faded lines, a wrong path", "lane", ("lines faded", "leaves the lane"), [
    ("Lane lines are faded or misleading (construction).", "Lane lines are faded or misleading (construction)"),
    ("The model plans a wrong curvature; the torque stays within the envelope, so the panda does not act.",
     "torque stays within the envelope, so the panda does not act"),
    ("The car leaves its lane; the driver is the only control.", "the driver is the only control")]),
  "LS-11": ("The envelope is the controller", "lane", ("limits = controller limits", "nothing stops it"), [
    ("The envelope limits are the controller limits.", "Envelope limits still equal the controller limits"),
    ("Torque 1500, rate 15/25, deceleration −3.5 m/s² on both sides: no margin, nothing derived from the vehicle.",
     "torque 1500, rate 15/25"),
    ("Requests outside the controllable envelope pass.", "outside the controllable envelope")]),
  "LS-12": ("A wrong fingerprint", "straight", ("wrong platform", "wrong host tuning"), [
    ("A wrong fingerprint selects another platform.", "A wrong fingerprint selects another platform"),
    ("The reference lock stops a wrong brand or parameter, but another Toyota with scale 73 gets the right limits and wrong tuning.",
     "another Toyota with EPS scale 73"),
    ("The wrong safety mode or parameter is sent to the panda.", "Wrong safety mode or parameter sent to the panda")]),
  "LS-13": ("Engaged on a road it does not handle", "unmarked", ("engaged above 60 km/h", "road it cannot handle"), [
    ("The driver engages on a road the item does not handle.", "The driver engages on a road the item does not handle"),
    ("Entry needs only a PCM edge and 60 km/h; nothing checks road type, curve radius or glare.",
     "none but the 60 km/h floor"),
    ("The item runs outside what it handles.", "Driver engages in conditions outside what the item handles")]),
  "LS-14": ("Steering does not disengage it", "steer", ("driver steers to disengage", "still engaged"), [
    ("The driver steers against the item and expects that to disengage it.", "expects that to disengage it"),
    ("By design steering only overrides; the torque continues as in LS-01.", "steering only overrides"),
    ("The driver never brakes or cancels.", "the driver never brakes or cancels")]),
  "LS-15": ("EPS fault while touching the wheel", "curve", ("EPS fault, hands on", "steering gone, no alert"), [
    ("An EPS temporary fault starts while the driver touches the wheel.",
     "An EPS temporary fault starts while the driver touches the wheel"),
    ("No event, or only a silent one; the EPS-fault siren after 1 s is the only cue.",
     "The only cue is the EPS-fault siren after 1 s persistence"),
    ("The driver reacts late to the silent loss of steering.", "after a silent loss of control")]),
  "LS-16": ("Stops steering in a curve, no alert", "curve", ("torque saturates", "no alert"), [
    ("The item stops steering in a curve.", "The item stops steering in a curve without an alert"),
    ("The saturation warning needs three conditions and is suppressed for 2 s after any steering press.",
     "is suppressed for 2 s after any steeringPressed"),
    ("No torque in the curve and no alert.", "Lateral torque not commanded in a curve while engaged and no alert given")]),
  "LS-17": ("The model misses a stopped lead", "accel", ("model: no lead", "accelerates toward it"), [
    ("The driving model misses a stationary or slower lead in Chill Mode.",
     "The model misses a stationary or slower lead in Chill Mode"),
    ("The planner plans acceleration; the panda knows nothing of leads and passes up to +2.0 m/s².",
     "the panda passes up to +2.0 m/s²"),
    ("The car accelerates toward the lead.", "Positive acceleration commanded towards a stopped or slower lead")]),
  "LS-18": ("A cut-in seen late", "late", ("cut-in detected late", "brakes too late"), [
    ("A cut-in or a slowing lead is detected late.", "A cut-in or a slowing lead is detected late"),
    ("The leads come from the driving model, so the same miss removes planner braking and the FCW together.",
     "the same miss removes planner braking and the FCW together"),
    ("Deceleration comes too late, and is capped at −3.5 m/s².", "Deceleration commanded too late for a lead vehicle")]),
  "LS-19": ("Phantom braking passes the envelope", "phantom", ("false lead", "hard braking, follower close"), [
    ("A false lead brakes hard.", "A false lead brakes hard"),
    ("The envelope passes any in-bound step and has no jerk limit.", "the envelope has no jerk limit"),
    ("Hard deceleration without a real obstacle.", "Hard deceleration commanded without a real obstacle")]),
  "LS-20": ("A take-over request nobody hears", "fault", ("HMI hung", "no alert reaches the driver"), [
    ("A take-over request is not perceived.", "A take-over request is not perceived"),
    ("Every alert goes through ui and soundd, so a hung HMI mutes them; the panda siren covers heartbeat loss and EPS faults only.",
     "a hung HMI mutes them all"),
    ("The take-over alert is not given when control is lost.", "Take-over alert not given")]),
  "LS-21": ("A stuck brake frame", "resume", ("0x226 stuck 'not pressed'", "keeps authority while braking"), [
    ("The brake frame 0x226 has no checksum or counter.", "has no checksum or counter"),
    ("A stuck 'not pressed' value with live timing passes.", "value with live timing passes"),
    ("The panda keeps authority while the driver brakes.", "the panda keeps authority while the driver brakes")]),
  "LS-22": ("Switches stuck in pass-through", "lane", ("switch stuck in pass-through", "two commands reach the car"), [
    ("The intercept switches stay in pass-through while the item transmits.",
     "The intercept switches stay in pass-through while the item transmits"),
    ("Stock and item frames both reach the car; no switch position is fed back.", "No switch position is fed back"),
    ("Stock LKA/ACC messages are not blocked.", "Does not block stock camera LKA/ACC messages")]),
  "LS-23": ("modeld stops while engaged", "fault", ("modeld stops", "dropped after 0.5 s"), [
    ("modeld or plannerd stops or lags while engaged.", "modeld or plannerd stops or lags while engaged"),
    ("controlsd drops control when the plan is older than 0.5 s and raises commIssue, a soft disable.", "older than 0.5 s"),
    ("Plan or model output is held after its publisher stops.", "Plan or model output held after its publisher stops or lags")]),
  "LS-24": ("The panda revokes, the screen says engaged", "fault", ("panda revokes", "shown engaged ≤ 0.5 s"), [
    ("The panda revokes authority while selfdriveState is still engaged.", "while `selfdriveState` is still engaged"),
    ("Two pandaStates with controlsAllowed false give controlsMismatch, an immediate disable, within 0.5 s.",
     "an immediate disable"),
    ("'Engaged' is shown while the panda grants nothing.", "provided while the panda does not grant authority")]),
  "LS-25": ("Big-model loading masks the alert", "curve", ("big model loading", "control ends, no alert"), [
    ("The external big model loads or warms up.", "the external big model (E-06) loads or warms up"),
    ("selfdrived suppresses commIssue and the localizer checks.", "suppresses commIssue and the localizer checks"),
    ("Control ends without a take-over alert.", "control ends without a take-over alert")]),
  "LS-26": ("Wrong learned parameters", "lane", ("tyre change: wrong ratio", "over-steers in the curve"), [
    ("After a tyre, alignment or load change, paramsd and torqued learn wrong values.", "After a tyre, alignment or load change"),
    ("They are bounded only to 0.5–2× the platform value; the panda bounds the torque, not the tracking.",
     "The panda bounds the torque, not the tracking"),
    ("The car under- or over-steers in curves within the envelope.", "under- or over-steers in curves within the envelope")]),
  "LS-27": ("The device moved on its mount", "lane", ("mount moved < threshold", "path biased"), [
    ("The device moves on its windscreen mount by less than the recalibration threshold.", "The device moves on its windscreen mount"),
    ("The model output keeps its confidence.", "The model output keeps its confidence"),
    ("The path is biased within the envelope.", "the path is biased within the envelope")]),
  "LS-28": ("A mode change while driving", "fault", ("reset or BOOT0 from the SoC", "only the SoC alerts"), [
    ("A pandad defect or a compromised SoC requests a mode change while driving, or asserts reset or BOOT0.",
     "requests ELM327, power save or a mode change while driving"),
    ("The panda refuses mode changes in a car mode, but not the reset and BOOT0 lines.", "which the panda cannot refuse"),
    ("Control ends with the SoC's own alert only.", "control ends with the SoC's own alert only")]),
  "LS-29": ("The wrong panda image in a release", "straight", ("non-reference image", "DEBUG image passes"), [
    ("A release bundles a panda image built without the reference flag, or a rollback brings an older one.",
     "built without the reference flag"),
    ("pandad flashes it, then refuses a car mode; a DEBUG image with the flag set would pass.",
     "A DEBUG image with the flag set would pass"),
    ("The panda runs firmware other than the reference build.", "Panda flashed with firmware other than the assured reference build")]),
  "LS-30": ("Unapproved software installed", "straight", ("upstream installer", "logged, not refused"), [
    ("The owner installs from the upstream installer or a development branch.",
     "The owner installs from the upstream installer or a development branch"),
    ("Nothing checks for an approved release; it is logged, but the driver is not told.",
     "the driver is not told and engagement is not refused"),
    ("Software that is not an approved release drives.", "Update installed that is not an approved LionDriver release")]),
  "LS-31": ("Experimental Mode from an old setup", "phantom", ("stored ExperimentalMode = 1", "outside the reference config"), [
    ("ExperimentalMode defaulted to on at v0.3.", "defaulted to on"),
    ("A device not set up per the release instructions starts in Experimental Mode.",
     "starts in Experimental Mode, outside the reference configuration"),
    ("The driving mode is set outside the reference configuration.", "Driving mode or toggles set outside the reference configuration")]),
  "LS-32": ("The harness box loses its supply", "pcs", ("box supply lost", "engageable, PCS lost"), [
    ("The ignition branch to the harness box opens, or its supply shorts.", "The ignition branch to the harness box opens"),
    ("The switches' state is undefined, and nothing in the item sees the stock path.", "Nothing in the item sees the stock path"),
    ("The item stays engageable while stock PCS is lost.", "the item stays engageable while stock PCS is lost")]),
  "LS-33": ("An open pull-down keeps the intercept", "pcs", ("R2/R3 open (latent)", "PCS frames stopped"), [
    ("Pull-down R2 or R3 is open (latent).", "Pull-down R2 or R3 is open (latent)"),
    ("Nothing shows it until the panda stops driving the switches; then they may stay in intercept.",
     "the switches may stay in intercept"),
    ("Stock PCS frames are neither passed through nor forwarded.", "neither passed through nor forwarded")]),
  "LS-34": ("Alpha longitudinal knocks out the radar", "pcs", ("radar ECU disabled", "PCS off"), [
    ("On a radar-ACC platform, alpha longitudinal disables the stock radar ECU over UDS.", "disable the stock radar ECU over UDS"),
    ("That turns PCS off; since v0.4 card refuses the alpha request on any vehicle.", "card refuses the alpha request on any vehicle"),
    ("The stock radar, and with it PCS/AEB, is silenced.", "silencing the stock radar or ADAS ECU and with it PCS/AEB")]),
  "LS-35": ("The driver falls asleep", "stop", ("driver unresponsive", "slows in lane: unassured"), [
    ("The driver falls asleep or becomes unwell.", "The driver falls asleep or becomes unwell"),
    ("Alerts escalate to level three; 5 s later the car brakes towards a stop in the lane, on the same QM chain.",
     "brakes towards a stop in the lane, still steering"),
    ("No specified and assured minimal-risk behaviour.", "No specified and assured minimal-risk behaviour")]),
  "LS-36": ("Gas override, then a surprise", "resume", ("gas pressed: grey border", "resumes, unexpected"), [
    ("The driver presses the accelerator to pass.", "The driver presses the accelerator to pass"),
    ("The driver sees the grey border and no text, and takes the item to be off.", "takes the item to be off"),
    ("On release the car brakes or accelerates back, unexpected.", "the car brakes or accelerates without the driver expecting it")]),
}


# ---------------------------------------------------------------- data

RESIDUAL = {  # covered with a residual: the card's status line carries it (text, phrase of the row's Status cell)
  "LS-05": ("Covered in the reference build (default since e84f850); not verified on the vehicle.", "not verified on the vehicle"),
  "LS-06": ("Covered since v0.3.1: authority only once openpilot reports engaged; open test for the PCM response (OI-4).",
            "open test for the PCM response"),
  "LS-07": ("Covered for a hang (bench confirmation open); known gap for forwarding stalls.", "known gap for forwarding stalls"),
  "LS-12": ("Covered in the default build; known gap for same-parameter Toyotas and for the opt-out build.",
            "known gap for same-parameter Toyotas"),
  "LS-28": ("Covered for commands; known gap for reset and BOOT0, and for an ELM327 request after a false ignition-off.",
            "known gap for reset and BOOT0"),
  "LS-29": ("Covered for a non-reference image; known gap for a DEBUG reference image.", "known gap for a DEBUG reference image"),
  "LS-31": ("Covered: default off since 2026-10-14. Residual: devices set up before keep a stored 1, logged but not shown to the driver.",
            "devices set up before the change keep a stored 1"),
  "LS-24": ("Covered (#51); not verified on the vehicle.", "not verified on the vehicle"),
  "LS-34": ("Covered: unit-tested, not verified on a vehicle; applies to every non-reference platform.", "not verified on a vehicle"),
}
RESIDUAL_WORDS = re.compile(r"known gap|residual|open test|not verified", re.I)

def rows(S):
  out = {}
  for c in S._rows(r"LS-\d+"):
    if len(c) >= 6 and c[1].startswith("UCA"):
      out[c[0]] = dict(ucas=re.findall(r"UCA-\d+", c[1]), scen=c[2], type=c[3], cov=c[4], status_text=c[5])
  return out


def cards(S, models=None):
  models = MODELS if models is None else models
  R, M = rows(S), {s["id"]: s for s in S.smap["scenarios"]}
  if sorted(R) != sorted(M):
    fail(f"WP-A-05 §5 scenarios {sorted(set(R) ^ set(M))} are not in both §5 and stpa-map.yaml")
  if missing := sorted(set(R) - set(models)):
    fail(f"no card for {', '.join(missing)}")
  if extra := sorted(set(models) - set(R)):
    fail(f"card for {', '.join(extra)}, which WP-A-05 §5 does not have")
  out = []
  for ls in sorted(R, key=lambda x: int(x[3:])):
    r, m = R[ls], M[ls]
    title, scene, stags, steps = models[ls]
    uca = r["ucas"][0]
    if uca not in S.ucas:
      fail(f"{ls}: {uca} is not in WP-A-05 §4")
    for i, (_, q) in enumerate(steps):
      hay = _plain(r["scen"]) if i < 2 else _plain(S.ucas[uca]["text"]) + " " + _plain(r["scen"])
      if _plain(q) not in hay:
        fail(f"{ls} step {i + 1}: '{q}' is no longer in its {'§5 row' if i < 2 else 'UCA or §5 row'}; redraw the card")
    if scene not in SCENES:
      fail(f"{ls}: unknown scene '{scene}'")
    why = m.get("open_because") or _plain(r["status_text"]).split(". ")[0]
    if m["status"] == "covered" and RESIDUAL_WORDS.search(_plain(r["status_text"])):
      if ls not in RESIDUAL:
        fail(f"{ls} is covered with a residual ('{_plain(r['status_text'])[:60]}…'); add its RESIDUAL line")
      why, q = RESIDUAL[ls]
      if _plain(q) not in _plain(r["status_text"]):
        fail(f"{ls} residual: '{q}' is no longer in its §5 Status cell; redraw the card")
    head2, col2 = kind(r["type"])
    out.append(dict(ls=ls, title=title, ucas=r["ucas"], uca=uca, uca_type=S.ucas[uca]["type"], ctrl=S.ucas[uca]["ctrl"],
                    uca_text=_plain(S.ucas[uca]["text"]), type=r["type"].split(";")[0].strip(), head2=head2, col2=col2,
                    steps=steps, scene=scene, stags=stags, hazards=m.get("hazards", []), status=m["status"],
                    why=why, cov=_plain(r["cov"])))
  return out


# ---------------------------------------------------------------- drawing

COLS, CW, GAP, M = 3, 400, 20, 40
PW = CW - 24
ST_H = PW * 70 / 280


def step(x, y, w, h, n, head, body, col, begin):
  ls = wrap(body, w - 14, 9)
  if len(ls) > 6:
    fail(f"step text too long for its box: '{body[:40]}…'")
  anim = (f'<animate attributeName="opacity" values="0.35;0.35;1;1" keyTimes="0;{begin:.3f};{begin + 0.03:.3f};1" '
          f'dur="6s" repeatCount="indefinite"/>')
  b = [f'<g>{anim}<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h}" rx="7" fill="#FFFFFF" stroke="{col}" stroke-width="1.4"/>',
       f'<circle cx="{x + 13:.1f}" cy="{y + 13:.1f}" r="8" fill="{col}"/>', t(round(x + 13, 1), round(y + 16.5, 1), str(n), 9.5, "#FFFFFF", 700, "middle"),
       t(round(x + 26, 1), round(y + 17, 1), head, 9.5, col, 700)]
  b += [t(round(x + 8, 1), round(y + 32 + 11.5 * i, 1), ln, 9, INK) for i, ln in enumerate(ls)]
  return b + ["</g>"]


def card_svg(x, y, c):
  b = [None]
  px, yy = x + 12, y + 26
  b.append(t(px, yy, c["ls"], 12, MUTED, 600))
  b.append(t(px + 44, yy, c["title"], 13.5, INK, 700))
  yy += 12
  chips = [("#F1F5F9", "#334155", f"{', '.join(c['ucas'])} ({c['uca_type']})"), ("#FFFFFF", c["col2"], c["type"]), STATUS[c["status"]]]
  cx = px
  for bg, fg, s in chips:
    w = hf.text_w(s, 10, True) + 14
    if cx + w > px + PW:
      cx, yy = px, yy + 22
    b.append(pill(cx, yy, s, bg, fg, 18, 10, fg if bg == "#FFFFFF" else None)[0])
    cx += w + 6
  yy += 30
  ut = wrap(f"{c['uca']}: {c['uca_text']}", PW - 12, 9.5)
  for i, ln in enumerate(ut[:2]):
    b.append(t(px, yy + 12 * i, ln + (" …" if i == 1 and len(ut) > 2 else ""), 9.5, MUTED))
  yy += 12 * min(len(ut), 2) + 8
  sw, sh = (PW - 28) / 3, 104
  heads = ["Cause", c["head2"], "Unsafe action"]
  for i, (text, _) in enumerate(c["steps"]):
    sx = px + i * (sw + 14)
    b += step(sx, yy, sw, sh, i + 1, heads[i], text, STEP_COL[i] or c["col2"], 0.1 + 0.25 * i)
    if i < 2:
      b.append(f'<path d="M{sx + sw + 3:.1f} {yy + sh / 2 - 6:.1f} L{sx + sw + 11:.1f} {yy + sh / 2:.1f} L{sx + sw + 3:.1f} {yy + sh / 2 + 6:.1f} Z" fill="#94A3B8"/>')
  yy += sh + 8
  cid = f"ls{c['ls']}"
  hz = " · ".join(c["hazards"][:3])
  b.append(f'<svg x="{px}" y="{yy:.1f}" width="{PW}" height="{ST_H:.1f}" viewBox="0 0 280 70">'
           f'<clipPath id="{cid}"><rect width="280" height="70" rx="5"/></clipPath><g clip-path="url(#{cid})">' +
           "".join(SCENES[c["scene"]](*c["stags"]) + ([badge(hz, "#DC2626")] if hz else [])) + "</g></svg>")
  yy += ST_H + 16
  for k, v, n in (("Covered by", c["cov"], 2), ("Open because" if c["status"] != "covered" else "Status", c["why"], 3)):
    ls = wrap(v, PW - 84, 9.5)
    b.append(t(px, yy, k, 9.5, MUTED))
    if k == "Status" and len(ls) > n:
      fail(f"{c['ls']}: status line does not fit {n} lines; shorten it")
    for i, ln in enumerate(ls[:n]):
      b.append(t(px + 84, yy + 12 * i, ln + (" …" if i == n - 1 and len(ls) > n else ""), 9.5, INK))
    yy += 12 * min(len(ls), n) + 5
  return b, yy + 8 - y


def legend(y):
  b, x = [], M
  seen = []
  for _, h, col in TYPES:
    if (h, col) in seen:
      continue
    seen.append((h, col))
  for kk, (bg, fg, lab) in STATUS.items():
    b.append(pill(x, y - 13, lab, bg, fg, 18, 10)[0])
    x += hf.text_w(lab, 10, True) + 22
  b.append(t(x + 6, y, "Steps: 1 the cause · 2 named after the scenario's causal-factor type · 3 the unsafe control action", 11, INK))
  return b


def sheet(name, cs):
  num, who, pick = SHEETS[name]
  cs = [c for c in cs if pick(c["ctrl"])]
  if not cs:
    fail(f"sheet {name} has no cards")
  w = 2 * M + COLS * CW + (COLS - 1) * GAP
  body = hf.header(w, f"Loss scenarios · {who}",
                   "How each unsafe control action comes about: the cause, what the controller believes or never learns, and the action on the road.",
                   "WP-A-05 §4-§5 · stpa-map.yaml", "Schematic scenes")
  body += legend(108)
  y, out = 128, []
  for r in range(0, len(cs), COLS):
    built = [card_svg(M + k * (CW + GAP), y, c) for k, c in enumerate(cs[r:r + COLS])]
    row_h = max(h for _, h in built)
    for (b, _), k in zip(built, range(COLS)):
      b[0] = f'<rect x="{M + k * (CW + GAP)}" y="{y}" width="{CW}" height="{row_h:.0f}" rx="10" fill="#FFFFFF" stroke="{HAIR}"/>'
      out += b
    y += row_h + GAP
  body += out
  body.append(t(M, y + 6, "Steps paraphrase the §5 row; each quotes a phrase of it (or of the UCA), checked at build. Status and "
                "'open because' from stpa-map.yaml; a covered scenario's residual from its §5 Status cell.", 10.5, MUTED))
  body.append(t(w - M, y + 24, "Generated by stpa_ls_scenes.py", 10, MUTED, None, "end"))
  desc = (f"Figure {num}: {len(cs)} loss scenario cards for {who}. " +
          " ".join(f"{c['ls']} ({', '.join(c['ucas'])}, {STATUS[c['status']][2]}): " + " ".join(s for s, _ in c["steps"]) + f" {c['why'].rstrip('.')}." for c in cs))
  return svg_doc(w, int(y + 36), f"Figure {num}. Loss scenarios: {who} (WP-A-05 §5)", desc, body)


def sheets(S, kit) -> dict[str, str]:
  global K
  K = kit
  cs = cards(S)
  for c in cs:
    on = [name for name in SHEETS if SHEETS[name][2](c["ctrl"])]
    if len(on) != 1:
      fail(f"{c['ls']} ({c['uca']}, {c['ctrl']}) must be on exactly one sheet, not {on or 'none'}")
  return {name: sheet(name, cs) for name in SHEETS}
