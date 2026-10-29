import contextlib
import threading
import time
from unittest import mock

from opendbc.car.structs import car
from opendbc.car.toyota.values import CAR as TOYOTA
from openpilot.cereal import log
from openpilot.common.params import Params
from openpilot.common.test import OpenpilotTestCase
from openpilot.selfdrive.monitoring import dmonitoringd
from openpilot.selfdrive.monitoring.dmonitoringd import demo_active
from openpilot.selfdrive.selfdrived.events import ET, Events
from openpilot.selfdrive.selfdrived.selfdrived import SelfdriveD

# TSR-610 (SWSR-610): driver monitoring demo mode, the driver-camera view (IsDriverViewEnabled), is not active while the
# item can engage. selfdrived refuses engagement while the parameter is set and soft-disables if it is set while engaged;
# dmonitoringd ignores it while card runs (SWF-085.C1, SWF-085.C2)

EventName = log.OnroadEvent.EventName


def selfdrived(driver_view):
  Params().put_bool("IsDriverViewEnabled", driver_view, block=True)
  CP = car.CarParams.new_message()
  CP.carFingerprint = TOYOTA.TOYOTA_COROLLA_TSS2
  sd = SelfdriveD(CP=CP.as_reader())
  sd.initialized = True
  return sd


def events(sd):
  sd.update_events(car.CarState.new_message())
  return sd.events


class TestDriverViewInterlock(OpenpilotTestCase):
  def test_parameter_read_at_start(self):
    assert selfdrived(True).driver_view
    assert not selfdrived(False).driver_view

  def test_refuses_entry_and_soft_disables(self):
    ev = events(selfdrived(True))
    assert EventName.driverViewActive in ev.names
    # the event itself refuses entry and soft-disables; other events of a bare SelfdriveD may too, so check it alone
    only = Events()
    only.add(EventName.driverViewActive)
    assert only.contains(ET.NO_ENTRY)
    assert only.contains(ET.SOFT_DISABLE)
    assert not only.contains(ET.IMMEDIATE_DISABLE)

  def test_no_event_without_the_view(self):
    assert EventName.driverViewActive not in events(selfdrived(False)).names

  def test_set_while_running(self):
    sd = selfdrived(False)
    assert EventName.driverViewActive not in events(sd).names
    Params().put_bool("IsDriverViewEnabled", True, block=True)
    stop = threading.Event()
    t = threading.Thread(target=sd.params_thread, args=(stop,))
    t.start()
    try:
      deadline = time.monotonic() + 2.
      while not sd.driver_view and time.monotonic() < deadline:
        time.sleep(0.01)
    finally:
      stop.set()
      t.join()
    assert EventName.driverViewActive in events(sd).names

class TestDemoModeInDmonitoringd(OpenpilotTestCase):
  def test_demo_only_offroad(self):
    assert demo_active(True, car_state_alive=False)
    assert not demo_active(True, car_state_alive=True)
    assert not demo_active(False, car_state_alive=False)
    assert not demo_active(False, car_state_alive=True)


class Stop(Exception):
  pass


class FakeSubMaster:
  """dmonitoringd's inputs: a new driverStateV2 every update, every input valid; carState alive only while started"""
  def __init__(self, started):
    self.frame = 0
    self.started = started
    self.data = {s: log.Event.new_message().init(s) for s in ('driverStateV2', 'extrinsicsCalibration', 'carState',
                                                                'selfdriveState', 'modelV2')}
    self.updated = {'driverStateV2': True}
    self.valid = dict.fromkeys(self.data, True)
    self.alive = dict.fromkeys(self.data, True)
    self.alive['carState'] = started
    self.data['modelV2'].meta.disengagePredictions.brakeDisengageProbs = [0.] * 6

  def update(self, timeout=None):
    self.frame += 1
    self.data['driverStateV2'].frameId = self.frame

  def all_checks(self):
    return self.started

  def __getitem__(self, s):
    return self.data[s]


def run_dmonitoringd(started, frames=3):
  """Run the real dmonitoringd loop for a few model frames with IsDriverViewEnabled set; return run_step's demo flags"""
  Params().put_bool("IsDriverViewEnabled", True, block=True)
  sm, sent, demos = FakeSubMaster(started), [], []
  real_run_step = dmonitoringd.DriverMonitoring.run_step

  def run_step(dm, sm_, demo=False):
    demos.append(demo)
    return real_run_step(dm, sm_, demo=demo)

  def send(service, dat):
    sent.append(dat)
    if len(sent) == frames:
      raise Stop

  pm = mock.Mock(send=send)
  with mock.patch.object(dmonitoringd, 'config_realtime_process'), \
       mock.patch.object(dmonitoringd.messaging, 'SubMaster', return_value=sm), \
       mock.patch.object(dmonitoringd.messaging, 'PubMaster', return_value=pm), \
       mock.patch.object(dmonitoringd.DriverMonitoring, 'run_step', run_step), \
       contextlib.suppress(Stop):
    dmonitoringd.dmonitoringd_thread()
  return demos


class TestDmonitoringdLoop(OpenpilotTestCase):
  # the parameter is read on frame 1 and applies from frame 2; offroad the inputs are not valid, so only demo mode steps
  def test_demo_mode_offroad(self):
    assert run_dmonitoringd(started=False) == [True, True]

  def test_no_demo_mode_while_started(self):
    assert run_dmonitoringd(started=True) == [False, False, False]
