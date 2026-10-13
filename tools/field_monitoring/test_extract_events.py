#!/usr/bin/env python3
"""Tests for extract_events.py on synthetic message streams with known answers."""
from __future__ import annotations

import unittest
from types import SimpleNamespace as NS

from tools.field_monitoring import extract_events as fx

DT = 0.01  # 100 Hz


def car(v=20.0, a=0.0, **kw):
  return NS(vEgo=v, aEgo=a, brakePressed=kw.get("brake", False), gasPressed=kw.get("gas", False),
            steeringPressed=kw.get("steer", False), leftBlinker=kw.get("left", False), rightBlinker=False)


def ev(name, soft=False, immediate=False):
  return NS(name=name, softDisable=soft, immediateDisable=immediate)


def lane_model(y_left=-1.8, y_right=1.8, prob=0.9, lead_prob=0.0, x=(0.0, 1.0)):
  lines = [NS(y=[-5.4]), NS(y=[y_left]), NS(y=[y_right]), NS(y=[5.4])]
  return NS(position=NS(x=list(x)), laneLines=lines, laneLineProbs=[0.1, prob, prob, 0.1],
            leadsV3=[NS(prob=lead_prob, xStd=[0.5])])


class Stream:
  """Builds a time-ordered message list."""

  def __init__(self):
    self.t = 0.0
    self.msgs = []

  def step(self, *pairs, n=1):
    for _ in range(n):
      for service, msg in pairs:
        self.msgs.append((self.t, service, msg))
      self.t += DT
    return self

  def scan(self, **kw):
    return fx.scan_messages("route", self.msgs, **kw)


def engaged(on=True):
  return ("selfdriveState", NS(enabled=on))


def by(sc, mon=None, sig=None):
  return [e for e in sc.events if (mon is None or e.mon == mon) and (sig is None or sig in e.signatures)]


class ExtractEventsTest(unittest.TestCase):
  def test_exposure_counts_engaged_time_distance_and_band(self):
    # each interval counts in the state at its end: 1000 engaged samples are 10 s engaged
    sc = Stream().step(engaged(False), ("carState", car(20.0)), n=500).step(engaged(), ("carState", car(20.0)), n=1000).scan()
    self.assertAlmostEqual(sc.exposure.engaged_s, 10.0, places=6)
    self.assertAlmostEqual(sc.exposure.engaged_m, 200.0, places=4)
    self.assertAlmostEqual(sc.exposure.total_s, 14.99, places=6)
    self.assertAlmostEqual(sc.exposure.engaged_m_by_band["60-90"], 200.0, places=4)  # 72 km/h

  def test_events_count_once_on_the_rising_edge(self):
    s = Stream().step(engaged(), ("onroadEvents", [ev("steerSaturated")]), n=50).step(engaged(), ("onroadEvents", []), n=5)
    s.step(engaged(), ("onroadEvents", [ev("steerSaturated")]), n=5)
    sc = s.scan()
    sat = by(sc, "MON-09")
    self.assertEqual(len(sat), 2)
    self.assertEqual(sat[0].signatures, ["AS-11"])
    self.assertEqual(sat[0].triage, "T3")

  def test_driver_brake_disengagement_and_as02(self):
    s = Stream().step(engaged(), ("carState", car()), n=10)
    s.step(("carState", car(brake=True)), engaged(False), n=1)
    s.step(engaged(False), ("carState", car(a=-4.5, brake=True)), n=50)
    sc = s.scan()
    self.assertEqual([e.trigger for e in by(sc, "MON-01")], ["driverDisengage", "brakeDisengageHardDecel"])
    self.assertEqual(len(by(sc, sig="AS-02")), 1)

  def test_no_as02_after_the_window(self):
    s = Stream().step(engaged(), ("carState", car()), n=10).step(("carState", car(brake=True)), engaged(False))
    s.step(engaged(False), ("carState", car()), n=250).step(("carState", car(a=-5.0)), n=5)
    self.assertEqual(by(s.scan(), sig="AS-02"), [])

  def test_fault_disengagement_is_mon02_t2(self):
    s = Stream().step(engaged(), ("carState", car()), n=10)
    s.step(("onroadEvents", [ev("commIssue", soft=True)]), ("carState", car()), engaged(False))
    sc = s.scan()
    fault = by(sc, "MON-02")
    self.assertEqual(len(fault), 1)
    self.assertEqual(fault[0].triage, "T2")
    self.assertEqual(by(sc, "MON-01"), [])

  def test_as01_steering_override_but_not_with_blinker(self):
    s = Stream().step(engaged(), ("carState", car(steer=True)), n=20).step(engaged(), ("carState", car()), n=5)
    s.step(engaged(), ("carState", car(steer=True, left=True)), n=20)
    self.assertEqual(len(by(s.scan(), sig="AS-01")), 1)

  def test_as03_gas_while_planner_decelerates(self):
    s = Stream().step(engaged(), ("longitudinalPlan", NS(aTarget=-2.0)), ("carState", car(gas=True)), n=20)
    s.step(engaged(), ("longitudinalPlan", NS(aTarget=-1.0)), ("carState", car(gas=True)), n=20)
    sc = s.scan()
    self.assertEqual(len(by(sc, "MON-17", "AS-03")), 1)

  def test_as06_phantom_decel_only_without_a_close_lead(self):
    no_lead = NS(leadOne=NS(status=False, dRel=0.0, vRel=0.0))
    close = NS(leadOne=NS(status=True, dRel=30.0, vRel=-10.0))  # TTC 3 s
    s = Stream().step(engaged(), ("radarState", close), ("carState", car(a=-3.0)), n=20)
    s.step(engaged(), ("radarState", no_lead), ("carState", car(a=-3.0)), n=20)
    phantom = by(s.scan(), "MON-17", "AS-06")
    self.assertEqual(len(phantom), 1)
    self.assertAlmostEqual(phantom[0].t_s, 0.2, places=6)

  def test_panda_tx_blocks_and_flags(self):
    p = lambda blocked, **kw: [NS(safetyTxBlocked=blocked, safetyRxInvalid=0, heartbeatLost=False, faults=[], **kw)]  # noqa: E731
    s = Stream().step(engaged(), ("pandaStates", p(0)), n=2).step(engaged(), ("pandaStates", p(3)))
    s.step(engaged(False), ("pandaStates", p(4)))
    s.step(engaged(False), ("pandaStates", p(4, txRateExceeded=True, epsFault=True)), n=3)
    sc = s.scan()
    tx = [e for e in by(sc, "MON-06") if e.trigger == "safetyTxBlocked"]
    self.assertEqual([e.detail["blocked"] for e in tx], [3, 1])
    self.assertEqual([e.triage for e in tx], ["T2", "T3"])
    self.assertEqual(tx[0].signatures, ["AS-04"])
    self.assertEqual([e.trigger for e in by(sc, "MON-06")][-1], "txRateExceeded")
    self.assertEqual([e.trigger for e in by(sc, "MON-02")], ["epsFault"])

  def test_t1_classes(self):
    s = Stream().step(engaged(), ("onroadEvents", [ev("excessiveActuation")]), ("onroadEvents", [ev("excessiveActuation")]))
    s.step(engaged(), ("onroadEvents", [ev("controlsMismatch"), ev("relayMalfunction")]))
    s.step(engaged(), ("userBookmark", NS()))
    sc = s.scan()
    self.assertEqual({e.mon for e in sc.events if e.triage == "T1"}, {"MON-03", "MON-04", "MON-05", "MON-14"})
    self.assertEqual(by(sc, "MON-05")[0].signatures, ["AS-11"])

  def test_stock_aeb_is_t2_only_when_engaged_and_fcw_is_as07(self):
    s = Stream().step(engaged(False), ("onroadEvents", [ev("stockAeb")])).step(engaged(False), ("onroadEvents", []))
    s.step(engaged(), ("onroadEvents", [ev("stockAeb"), ev("fcw")]))
    sc = s.scan()
    self.assertEqual([e.triage for e in sc.events if e.trigger == "stockAeb"], ["T3", "T2"])
    self.assertEqual(by(sc, sig="AS-07")[0].trigger, "fcw")

  def test_as05_lane_line_proximity_needs_a_seen_line(self):
    # right line at 1.1 m: clearance 1.1 - 0.89 = 0.21 m < 0.3 m
    s = Stream().step(engaged(), ("modelV2", lane_model(y_right=1.1, prob=0.3)), n=10)
    s.step(engaged(), ("modelV2", lane_model(y_right=1.1)), n=10)
    self.assertEqual(len(by(s.scan(), "MON-17", "AS-05")), 1)

  def test_as08_lead_flicker_and_mon13_non_finite(self):
    s = Stream()
    for i in range(30):
      s.step(engaged(), ("modelV2", lane_model(lead_prob=0.9 if i % 2 else 0.1)))
    s.step(engaged(), ("modelV2", lane_model(x=(0.0, float("nan")))))
    sc = s.scan()
    self.assertGreaterEqual(len(by(sc, "MON-13", "AS-08")), 1)
    nonfinite = [e for e in sc.events if e.trigger == "nonFiniteModelOutput"]
    self.assertEqual(len(nonfinite), 1)
    self.assertEqual(nonfinite[0].triage, "T2")

  def test_as09_only_with_evaluation_limits(self):
    msgs = Stream().step(engaged(), ("modelV2", lane_model()), n=5).msgs
    self.assertIn("AS-09 (no --uncertainty-limits from the evaluation set)", fx.scan_messages("r", msgs).not_scored)
    sc = fx.scan_messages("r", msgs, uncertainty_limits={"lead_x_std": 0.4})
    self.assertEqual(len(by(sc, "MON-13", "AS-09")), 1)

  def test_qlog_without_model_reports_what_is_not_scored(self):
    sc = Stream().step(engaged(), ("carState", car()), n=5).scan()
    self.assertIn("AS-05", sc.not_scored)
    self.assertIn("MON-16 (no --release record)", sc.not_scored)

  def test_mon16_configuration_drift(self):
    s = Stream().step(("initData", NS(gitCommit="abc", version="0.1", dirty=False)),
                      ("carParams", NS(carFingerprint="TOYOTA_COROLLA_TSS2", fuzzyFingerprint=False, carFw=[])))
    ok = s.scan(release={"initData.gitCommit": "abc", "carParams.carFingerprint": "TOYOTA_COROLLA_TSS2"})
    self.assertEqual(by(ok, "MON-16"), [])
    drift = s.scan(release={"initData.gitCommit": "def", "carParams.fuzzyFingerprint": False})
    self.assertEqual(list(by(drift, "MON-16")[0].detail["fields"]), ["initData.gitCommit"])
    self.assertEqual(by(drift, "MON-16")[0].triage, "T1")

  def test_calibration_odd_speed_and_crash_candidate(self):
    s = Stream().step(("liveCalibration", NS(calStatus="calibrated")), n=2).step(("liveCalibration", NS(calStatus="recalibrating")))
    s.step(engaged(), ("carState", car(v=35.0)), n=5).step(engaged(), ("carState", car(v=30.0, a=-7.0)), n=5)
    sc = s.scan()
    self.assertEqual(by(sc, "MON-11")[0].trigger, "calibration:recalibrating")
    self.assertEqual(len(by(sc, "MON-15")), 1)
    self.assertEqual(by(sc, "MON-14")[0].trigger, "highDecelCandidate")

  def test_summary_rates_and_markdown(self):
    s = Stream().step(engaged(), ("carState", car(20.0)), n=361)  # 3.6 s engaged = 0.001 h
    s.step(engaged(), ("onroadEvents", [ev("steerSaturated")]), ("carState", car(20.0)))
    summary = fx.summarise([s.scan()])
    self.assertEqual(summary["signature_set"], fx.SIGNATURE_SET_VERSION)
    self.assertEqual(summary["counts_by_mon"]["MON-09"]["count"], 1)
    self.assertAlmostEqual(summary["counts_by_mon"]["MON-09"]["per_engaged_h"], 1 / 0.001, delta=5)
    self.assertIn("| MON-09 | 1 |", fx.markdown(summary))
    self.assertEqual(summary["triage"], {"T1": 0, "T2": 0, "T3": 1})


  def test_poisson_bounds_match_tables(self):
    self.assertEqual(fx.poisson_bounds(0)[0], 0.0)
    self.assertAlmostEqual(fx.poisson_bounds(0)[1], 2.9957, places=3)
    self.assertAlmostEqual(fx.poisson_bounds(1)[0], 0.0513, places=3)
    self.assertAlmostEqual(fx.poisson_bounds(5)[1], 10.5130, places=3)

  def kpi(self, rows, kid):
    return next(r for r in rows if r["id"] == kid)

  def test_kpi_status_by_evidence(self):
    phantom = [fx.Event("r", 0.0, "MON-17", ["AS-06"], "phantomDecel", True) for _ in range(3)]
    # 3 events in 10,000 km: rate 0.3/1000 km, upper bound 7.75/10 = 0.775 <= 1 -> MET
    self.assertEqual(self.kpi(fx.evaluate_kpis(phantom, 100, 10000), "K-13")["status"], "MET")
    # 3 events in 2,000 km: rate 1.5 > 1, lower bound 0.82/2 = 0.41 -> WATCH
    self.assertEqual(self.kpi(fx.evaluate_kpis(phantom, 100, 2000), "K-13")["status"], "WATCH")
    # 3 events in 500 km: lower bound 0.82/0.5 = 1.64 > 1 -> BREACH
    self.assertEqual(self.kpi(fx.evaluate_kpis(phantom, 100, 500), "K-13")["status"], "BREACH")
    # no events in 1,000 km: upper bound 3.0 > 1 -> OPEN; 3,000 km would be needed
    open_row = self.kpi(fx.evaluate_kpis([], 10, 1000), "K-13")
    self.assertEqual(open_row["status"], "OPEN")
    self.assertAlmostEqual(open_row["exposure_to_demonstrate"], 3.0, places=1)

  def test_zero_tolerance_and_baseline_kpis(self):
    events = [fx.Event("r", 0.0, "MON-05", ["AS-11"], "excessiveActuation", True),
              fx.Event("r", 1.0, "MON-06", ["AS-04"], "safetyTxBlocked", False)]
    rows = fx.evaluate_kpis(events, 10, 500)
    self.assertEqual(self.kpi(rows, "K-02")["status"], "FINDING")
    self.assertEqual(self.kpi(rows, "K-03")["status"], "OK")
    k04 = self.kpi(rows, "K-04")
    self.assertEqual((k04["status"], k04["count"]), ("BASELINE", 0))  # the TX block was not engaged

  def test_kpis_in_summary_and_markdown(self):
    s = Stream().step(engaged(), ("carState", car(20.0)), n=361)
    summary = fx.summarise([s.scan()])
    ids = [k["id"] for k in summary["kpis"]]
    self.assertEqual(ids, [k["id"] for k in fx.KPIS])
    self.assertIn("| K-13 phantom decelerations, AS-06 | 0 |", fx.markdown(summary))

if __name__ == "__main__":
  unittest.main()
