import math
import multiprocessing
import numpy as np

from abc import ABC, abstractmethod
from collections import namedtuple

W, H = 1928, 1208


vec3 = namedtuple("vec3", ["x", "y", "z"])

class GPSState:
  def __init__(self):
    self.latitude = 0
    self.longitude = 0
    self.altitude = 0

  def from_xy(self, xy):
    """Simulates a lat/lon from an xy coordinate on a plane, for simple simulation. TODO: proper global projection?"""
    BASE_LAT = 32.75308505188913
    BASE_LON = -117.2095393365393
    DEG_TO_METERS = 100000

    self.latitude = float(BASE_LAT + xy[0] / DEG_TO_METERS)
    self.longitude = float(BASE_LON + xy[1] / DEG_TO_METERS)
    self.altitude = 0


class IMUState:
  def __init__(self):
    self.accelerometer: vec3 = vec3(0,0,0)
    self.gyroscope: vec3 = vec3(0,0,0)
    self.bearing: float = 0


class SimulatorState:
  def __init__(self):
    self.valid = False
    self.is_engaged = False
    self.ignition = True

    self.velocity = vec3(0, 0, 0)
    self.bearing: float = 0
    self.gps = GPSState()
    self.imu = IMUState()

    self.steering_angle: float = 0

    self.user_gas: float = 0
    self.user_brake: float = 0
    self.user_torque: float = 0

    self.cruise_button = ""        # one of the CRUISE_* commands of simulated_car, for one step
    self.cruise_set_speed_kph = 0.0  # set speed for CRUISE_SET; 0 uses the current speed

    self.radar_targets: list = []    # simulated_car.RadarTarget, from the world
    self.yaw_rate: float = 0.0
    self.accel: float = 0.0

    self.left_blinker = False
    self.right_blinker = False

  @property
  def speed(self):
    return math.sqrt(self.velocity.x ** 2 + self.velocity.y ** 2 + self.velocity.z ** 2)


class World(ABC):
  def __init__(self, dual_camera):
    self.dual_camera = dual_camera

    self.image_lock = multiprocessing.Semaphore(value=0)
    self.road_image = np.zeros((H, W, 3), dtype=np.uint8)
    self.wide_road_image = np.zeros((H, W, 3), dtype=np.uint8)

    self.exit_event = multiprocessing.Event()

  @abstractmethod
  def apply_controls(self, curvature, accel, /):
    """Move the ego with the car's response: path curvature (1/m) and acceleration (m/s^2)."""

  @abstractmethod
  def tick(self):
    pass

  @abstractmethod
  def read_state(self):
    pass

  @abstractmethod
  def read_sensors(self, simulator_state: SimulatorState, /):
    pass

  @abstractmethod
  def read_cameras(self):
    pass

  @abstractmethod
  def close(self, reason: str):
    pass

  @abstractmethod
  def reset(self):
    pass
