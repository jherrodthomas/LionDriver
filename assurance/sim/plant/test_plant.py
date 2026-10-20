#!/usr/bin/env python3
"""Tests of the fault-injection plant model: the glue copied from the panda firmware is still the firmware's, the
parameters are still the ones opendbc holds, the kinematics agree with WP-S-04 §3.1, the safety code in the loop
behaves as its own unit tests say, and the committed results are current."""

import re
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import corolla  # noqa: E402
import kinematics as kin  # noqa: E402
import report  # noqa: E402
from cases import all_cases  # noqa: E402
from panda_loop import Panda  # noqa: E402
from simulate import Case, simulate  # noqa: E402

ROOT = corolla.ROOT
WP_S_04 = ROOT / "assurance" / "03-system" / "WP-S-04-timing-ftti-budget.md"


def statements(text: str) -> list[str]:
  return [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.strip().startswith("//")]


class TestFirmwareGlue(unittest.TestCase):
  """sim_panda.c restates a few lines of panda/board; they must still be in the firmware, in the same order."""

  def setUp(self):
    self.harness = (HERE / "sim_panda.c").read_text(encoding="utf-8")
    self.main = (ROOT / "panda" / "board" / "main.c").read_text(encoding="utf-8")

  def body(self, text: str, signature: str) -> list[str]:
    start = text.index(signature)
    depth, i = 0, text.index("{", start)
    for j in range(i, len(text)):
      depth += {"{": 1, "}": -1}.get(text[j], 0)
      if depth == 0:
        return statements(text[i + 1:j])
    raise AssertionError(signature)

  def test_safety_task_matches_main(self):
    sim = self.body(self.harness, "void sim_safety_task(void)")
    fw = self.body(self.main, "static void safety_task_handler(void)")
    fw = [s for s in fw if "SAFETY_TASK_TIMER" not in s and "LIONDRIVER_FAULT_INJECTION" not in s
          and "fault_injection_safety_task" not in s and s != "#endif"]
    self.assertEqual(fw[-1], "}")   # closes `if (SAFETY_TASK_TIMER->SR != 0U)`
    fw = fw[:-1]
    self.assertEqual(sim, fw)

  def test_is_car_safety_mode_matches_main(self):
    self.assertEqual(self.body(self.harness, "bool is_car_safety_mode(uint16_t mode)"),
                     self.body(self.main, "bool is_car_safety_mode(uint16_t mode)"))

  def test_siren_condition_matches_tick_handler(self):
    self.assertIn("current_board->set_siren((loop_counter & 1U) && (siren_enabled || (siren_countdown > 0U) || "
                  "eps_fault_siren_active || heartbeat_siren_active));", self.main)

  def test_engaged_mismatch_matches_tick_handler(self):
    sim = self.body(self.harness, "void sim_tick_1hz(void)")
    fw = statements(self.main)
    i = fw.index(sim[0])
    self.assertEqual(fw[i:i + len(sim)], sim)

  def test_heartbeat_handler(self):
    comms = (ROOT / "panda" / "board" / "main_comms.h").read_text(encoding="utf-8")
    self.assertRegex(comms, r"heartbeat_monitor_reset\(\);\s*heartbeat_lost = false;\s*heartbeat_disabled = false;\s*"
                            r"heartbeat_engaged = \(req->param1 == 1U\);")

  def test_reference_param(self):
    lock = (ROOT / "panda" / "board" / "reference_lock.h").read_text(encoding="utf-8")
    self.assertIn("#define LIONDRIVER_REFERENCE_TOYOTA_PARAM 73U", lock)


class TestParameters(unittest.TestCase):
  def test_opendbc_values(self):
    o = corolla.opendbc_values()
    self.assertAlmostEqual(o["wheelbase"], 2.67)
    self.assertAlmostEqual(o["mass_lb"], 3060.0)
    self.assertGreater(o["lat_accel_factor"], 1.0)

  def test_every_param_has_source_and_status(self):
    for p in corolla.corolla_params():
      self.assertIn(p.status, {"opendbc", "scaled", "vehicle2", "confirmed"}, p.name)
      self.assertTrue(p.source, p.name)

  def test_single_track_is_neutral_steer(self):
    # equal normalised cornering stiffness front and rear: no understeer, so delta = L a_y / v^2
    self.assertAlmostEqual(corolla.understeer_gradient(), 0.0, places=12)

  def test_width_matches_wp_v_02(self):
    text = (ROOT / "assurance/06-validation/WP-V-02-sotif-vv-strategy.md").read_text(encoding="utf-8")
    self.assertIn("| Ego width | 1.78 m (WP-S-04) | 1,781 mm | Confirmed |", text)


class TestKinematics(unittest.TestCase):
  def test_matches_wp_s_04_table(self):
    text = WP_S_04.read_text(encoding="utf-8")
    rows = re.findall(r"^\| (0\.[369]) m \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \| (step|1 s ramp)", text, re.M)
    self.assertGreaterEqual(len(rows), 5)
    for d, *ts, profile in rows:
      for a, t in zip((1, 2, 3, 4, 5), ts):
        f = kin.t_step if profile == "step" else kin.t_ramp
        self.assertAlmostEqual(f(float(d), a), float(t), delta=0.006, msg=(d, a, profile))


class TestSafetyInTheLoop(unittest.TestCase):
  def test_iwdg_timeout_from_firmware_registers(self):
    p = Panda()
    p.safety_task()
    self.assertAlmostEqual(p.iwdg_timeout(), 0.090, places=6)   # WP-S-04 T-09a

  def test_nominal_engagement_holds_lane(self):
    r = simulate(Case("t", "nominal", "none", "straight", "", "", t_fault=3.0, duration=1.0))
    self.assertEqual([k for k in r.metrics["events"] if k != "fault"], [])
    self.assertLess(abs(r.metrics["max_dev"]), 0.01)

  def test_overlimit_torque_never_reaches_the_eps(self):
    r = simulate(Case("t", "overlimit", "overlimit", "straight", "", "", t_fault=3.0, duration=0.5))
    self.assertIn("panda refuses STEERING_LKA", r.metrics["events"])
    self.assertLess(max(abs(x) for x in r.torque), 1500)

  def test_heartbeat_loss_revocation_within_t06a(self):
    r = simulate(Case("t", "hb", "heartbeat", "straight", "", "", t_fault=3.05, duration=1.0))
    # last heartbeat at 3.0 s; revocation <= 0.3 s + one task period after it (T-06a)
    self.assertLessEqual(r.metrics["events"]["authority revoked"] + 0.05, 0.31 + 1e-9)

  def test_iwdg_reset_after_hang(self):
    r = simulate(Case("t", "hang", "mcu_hang", "straight", "", "", t_fault=3.0, duration=0.5))
    t = r.metrics["events"]["IWDG reset, switch to pass-through"]
    self.assertGreater(t, 0.079)
    self.assertLessEqual(t, 0.091)


class TestFaultCatalog(unittest.TestCase):
  """faults.yaml: every FMEA cause and TSR it names exists, and every kind is implemented by simulate.py."""

  @classmethod
  def setUpClass(cls):
    import yaml
    from cases import catalog
    cls.faults = catalog()
    ids = set()
    for name in ("system-fmea.yaml", "sw-fmea.yaml", "dfmea.yaml"):
      data = yaml.safe_load((ROOT / "assurance/08-analyses/fmea/analyses" / name).read_text(encoding="utf-8"))
      ids |= {fm["id"] for fm in data.get("failure_modes", [])}
    cls.fmea_ids = ids
    wp_s_02 = (ROOT / "assurance/03-system/WP-S-02-technical-safety-requirements.md").read_text(encoding="utf-8")
    cls.tsr_ids = set(re.findall(r"^\| (TSR-\d+) \|", wp_s_02, re.M))
    cls.simulate_src = (HERE / "simulate.py").read_text(encoding="utf-8")

  def test_required_fields(self):
    for f in self.faults:
      for key in ("id", "title", "kind", "sg", "causes", "tsr", "injection", "expected", "road", "t_fault"):
        self.assertIn(key, f, f.get("id"))
      self.assertEqual(set(f["injection"]), {"point", "trigger", "duration"}, f["id"])

  def test_causes_exist_in_fmea(self):
    for f in self.faults:
      for c in f["causes"]:
        self.assertIn(c, self.fmea_ids, f"{f['id']}: {c}")

  def test_tsrs_exist_in_wp_s_02(self):
    for f in self.faults:
      for t in f["tsr"]:
        self.assertIn(t, self.tsr_ids, f"{f['id']}: {t}")

  def test_kinds_implemented(self):
    for f in self.faults:
      self.assertIn(f'"{f["kind"]}"', self.simulate_src, f["id"])

  def test_backlog_faults_covered(self):
    kinds = {f["kind"] for f in self.faults}
    for k in ("overlimit", "not_engaged", "frozen", "heartbeat", "mcu_hang", "switch_pass", "mcu_hang_stuck_intercept",
              "eps_fault", "rx_loss", "accel_max", "decel_min"):
      self.assertIn(k, kinds)


class TestOutputs(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.files = report.build()

  def test_committed_outputs_current(self):
    for path, content in self.files.items():
      self.assertTrue(path.exists(), path)
      self.assertEqual(path.read_text(encoding="utf-8"), content, f"{path.name} is stale; run report.py")

  def test_svgs_parse_and_have_title(self):
    for path, content in self.files.items():
      if path.suffix == ".svg":
        root = ET.fromstring(content)
        self.assertIsNotNone(root.find("{http://www.w3.org/2000/svg}title"), path.name)

  def test_results_labelled_synthetic(self):
    self.assertIn("Synthetic data (DSR-12)", self.files[report.TABLE])
    self.assertIn("No evidence credit", self.files[report.TABLE])

  def test_case_ids_unique(self):
    ids = [c.id for c in all_cases()]
    self.assertEqual(len(ids), len(set(ids)))


if __name__ == "__main__":
  unittest.main()
