import signal
import threading
import functools
import time

from collections import namedtuple
from enum import Enum
from multiprocessing import Process, Queue, Value
from abc import ABC, abstractmethod
from openpilot.common.params import Params
from openpilot.common.realtime import Ratekeeper
from openpilot.selfdrive.test.helpers import set_params_enabled
from openpilot.tools.sim.lib.common import SimulatorState, World
from openpilot.tools.sim.lib.simulated_car import SimulatedCar, CRUISE_ACCEL, CRUISE_CANCEL, CRUISE_MAIN, CRUISE_SET
from openpilot.tools.sim.lib.simulated_sensors import SimulatedSensors

QueueMessage = namedtuple("QueueMessage", ["type", "info"], defaults=[None])

class QueueMessageType(Enum):
  START_STATUS = 0
  CONTROL_COMMAND = 1
  TERMINATION_INFO = 2
  CLOSE_STATUS = 3

def control_cmd_gen(cmd: str):
  return QueueMessage(QueueMessageType.CONTROL_COMMAND, cmd)

def rk_loop(function, hz, exit_event: threading.Event):
  rk = Ratekeeper(hz, None)
  while not exit_event.is_set():
    function()
    rk.keep_time()


class SimulatorBridge(ABC):
  TICKS_PER_FRAME = 5

  def __init__(self, dual_camera, high_quality):
    set_params_enabled()
    self.params = Params()
    # the reference Corolla (TSS2, camera ACC) has openpilot longitudinal without the alpha toggle
    self.params.put_bool("AlphaLongitudinalEnabled", False, block=True)

    self.rk = Ratekeeper(100, None)

    self.dual_camera = dual_camera
    self.high_quality = high_quality

    self._exit_event: threading.Event | None = None
    self._threads = []
    self._keep_alive = True
    self.started = Value('i', False)
    signal.signal(signal.SIGTERM, self._on_shutdown)
    self.simulator_state = SimulatorState()

    self.world: World | None = None

    self.past_startup_engaged = False
    self.startup_button_prev = True

    self.test_run = False
    self.scenario = None          # scenarios.Scenario, scripted driver and traffic
    self.engage_on_start = True

  def _on_shutdown(self, signal, frame):
    self.shutdown()

  def shutdown(self):
    self._keep_alive = False

  def bridge_keep_alive(self, q: Queue, retries: int):
    try:
      self._run(q)
    finally:
      self.close("bridge terminated")

  def close(self, reason):
    self.started.value = False

    if self._exit_event is not None:
      self._exit_event.set()

    if self.world is not None:
      self.world.close(reason)

  def run(self, queue, retries=-1):
    bridge_p = Process(name="bridge", target=self.bridge_keep_alive, args=(queue, retries))
    bridge_p.start()
    return bridge_p

  def print_status(self):
    print(
    f"""
State:
Ignition: {self.simulator_state.ignition} Engaged: {self.simulator_state.is_engaged}
    """)

  @abstractmethod
  def spawn_world(self, q: Queue, /) -> World:
    pass

  def _run(self, q: Queue):
    self.world = self.spawn_world(q)

    self.simulated_car = SimulatedCar()
    self.simulated_sensors = SimulatedSensors(self.dual_camera)

    self._exit_event = threading.Event()

    self.simulated_car_thread = threading.Thread(target=rk_loop, args=(functools.partial(self.simulated_car.update, self.simulator_state),
                                                                        100, self._exit_event))
    self.simulated_car_thread.start()

    self.simulated_camera_thread = threading.Thread(target=rk_loop, args=(functools.partial(self.simulated_sensors.send_camera_images, self.world),
                                                                        20, self._exit_event))
    self.simulated_camera_thread.start()

    # Simulation tends to be slow in the initial steps. This prevents lagging later
    for _ in range(20):
      self.world.tick()

    last_engage_press = 0.0
    while self._keep_alive:
      steer_manual = throttle_manual = brake_manual = 0.

      self.simulator_state.left_blinker = False
      self.simulator_state.right_blinker = False

      # Read manual controls
      if not q.empty():
        message = q.get()
        if message.type == QueueMessageType.CONTROL_COMMAND:
          m = message.info.split('_')
          if m[0] == "steer":
            steer_manual = float(m[1])
          elif m[0] == "throttle":
            throttle_manual = float(m[1])
          elif m[0] == "brake":
            brake_manual = float(m[1])
          elif m[0] == "cruise":
            self.simulator_state.cruise_button = {"down": CRUISE_SET, "up": CRUISE_ACCEL,
                                                  "cancel": CRUISE_CANCEL, "main": CRUISE_MAIN}.get(m[1], "")
          elif m[0] == "blinker":
            if m[1] == "left":
              self.simulator_state.left_blinker = True
            elif m[1] == "right":
              self.simulator_state.right_blinker = True
          elif m[0] == "ignition":
            self.simulator_state.ignition = not self.simulator_state.ignition
          elif m[0] == "reset":
            self.world.reset()
          elif m[0] == "quit":
            break

      # the driver: keyboard/wheel inputs, or the scenario's scripted driver
      self.simulator_state.user_brake = brake_manual
      self.simulator_state.user_gas = throttle_manual
      self.simulator_state.user_torque = steer_manual * -1500
      if self.scenario is not None:
        self.scenario.drive(self.simulator_state, self.simulated_car)

      # Update openpilot on current sensor state
      self.simulated_sensors.update(self.simulator_state, self.world)

      self.simulator_state.is_engaged = self.simulated_car.engaged
      if self.simulator_state.is_engaged:
        self.past_startup_engaged = True
      elif not self.past_startup_engaged and self.simulated_car.engageable and self.engage_on_start and \
           time.monotonic() - last_engage_press > 1.0:
        # the driver presses SET on the cruise stalk; the PCM engages and openpilot follows it (pcmCruise)
        self.simulator_state.cruise_button = CRUISE_SET
        last_engage_press = time.monotonic()

      # the car moves as its EPS and PCM respond to the frames the panda let through (simulated_car); openpilot's
      # carControl is never read here
      out = self.simulated_car.get_outputs()
      self.world.apply_controls(out.curvature, out.accel)
      self.world.read_state()
      self.world.read_sensors(self.simulator_state)
      if self.scenario is not None:
        self.scenario.observe(self.simulator_state, self.simulated_car, self.world)

      if self.world.exit_event.is_set():
        self.shutdown()

      if self.rk.frame % self.TICKS_PER_FRAME == 0:
        self.world.tick()
        self.world.read_cameras()

      # don't print during test, so no print/IO Block between OP and metadrive processes
      if not self.test_run and self.rk.frame % 25 == 0:
        self.print_status()

      self.started.value = True

      self.rk.keep_time()
