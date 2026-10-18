import os

import numpy as np
import panda3d.core as p3d

from direct.filter.FilterManager import FilterManager
from metadrive.component.sensors.rgb_camera import RGBCamera
from metadrive.constants import CameraTagStateKey, Semantics
from metadrive.third_party.simplepbr import _load_shader_str
from panda3d.core import Texture, GraphicsOutput

# Headless runs (CI, no display) render through panda3d's EGL pipe on Mesa llvmpipe, which cannot create the 16x
# multisampled float buffers MetaDrive asks for. HEADLESS_MSAA_SAMPLES is used there instead.
HEADLESS = "DISPLAY" not in os.environ
HEADLESS_MSAA_SAMPLES = 0


def msaa_samples(default: int) -> int:
  return HEADLESS_MSAA_SAMPLES if HEADLESS else default


def configure_headless_rendering():
  """Select panda3d's EGL pipe and lower MSAA when there is no display. Call before MetaDriveEnv is created."""
  if not HEADLESS:
    return
  p3d.loadPrcFileData("", "load-display p3headlessgl")
  p3d.loadPrcFileData("", "audio-library-name null")

  import metadrive.engine.core.engine_core as engine_core
  pbr_init = engine_core.init
  engine_core.init = lambda **kwargs: pbr_init(**{**kwargs, "msaa_samples": msaa_samples(kwargs.get("msaa_samples", 16))})


class CopyRamRGBCamera(RGBCamera):
  """Camera which copies its content into RAM during the render process, for faster image grabbing."""
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.cpu_texture = Texture()
    self.buffer.addRenderTexture(self.cpu_texture, GraphicsOutput.RTMCopyRam)

  def _setup_effect(self):
    # Same as RGBCamera._setup_effect, with the multisample count from msaa_samples()
    cam = self.get_cam().node()
    cam.setTagStateKey(CameraTagStateKey.RGB)
    from metadrive.engine.core.terrain import Terrain
    cam.setTagState(Semantics.TERRAIN.label, Terrain.make_render_state(self.engine, "terrain.vert.glsl", "terrain.frag.glsl"))

    self.scene_tex = None
    self.manager = FilterManager(self.buffer, self.cam)
    fbprops = p3d.FrameBufferProperties()
    fbprops.float_color = True
    fbprops.set_rgba_bits(16, 16, 16, 16)
    fbprops.set_depth_bits(24)
    fbprops.set_multisamples(msaa_samples(16))
    self.scene_tex = p3d.Texture()
    self.scene_tex.set_format(p3d.Texture.F_rgba16)
    self.scene_tex.set_component_type(p3d.Texture.T_float)
    self.tonemap_quad = self.manager.render_scene_into(colortex=self.scene_tex, fbprops=fbprops)

    tonemap_shader = p3d.Shader.make(p3d.Shader.SL_GLSL, vertex=_load_shader_str('post.vert', {}),
                                     fragment=_load_shader_str('tonemap.frag', {}))
    self.tonemap_quad.set_shader(tonemap_shader)
    self.tonemap_quad.set_shader_input('tex', self.scene_tex)
    self.tonemap_quad.set_shader_input('exposure', 1.0)

  def get_rgb_array_cpu(self):
    origin_img = self.cpu_texture
    img = np.frombuffer(origin_img.getRamImageAs("RGB").getData(), dtype=np.uint8)
    img = img.reshape((origin_img.getYSize(), origin_img.getXSize(), 3))
    img = img[::-1]  # Flip on vertical axis
    return img


class RGBCameraWide(CopyRamRGBCamera):
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    lens = self.get_lens()
    lens.setFov(120)
    lens.setNear(0.1)


class RGBCameraRoad(CopyRamRGBCamera):
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    lens = self.get_lens()
    lens.setFov(40)
    lens.setNear(0.1)
