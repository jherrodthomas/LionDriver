"""pandad's SPI host (spi.cc) against the panda firmware's SPI driver, both compiled for the host (LionDriver
SWSR-410, 410a, 410h, 412; WP-S-05 §4.1).

spi_protocol_host.cc runs the real PandaSpiHandle over the simulated SPI4 bus of panda/tests/spi_protocol/harness.c,
which contains the real board/drivers/spi.h: connect, control requests through a counter wrap, CAN writes split
within the 2047-byte data phase with their control-frame index, a CAN read, and a second host session that moves the
panda's counter. Bus timing and the SPI_ERR_PROB fault injection need the device (test_pandad_spi.py, HIL).
"""
import os
import subprocess
import tempfile

BASEDIR = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
PANDA_DIR = os.path.join(BASEDIR, "panda")
OPENDBC_DIR = os.path.join(BASEDIR, "opendbc_repo")
OPENPILOT_DIR = os.path.join(BASEDIR, "openpilot")


def test_pandad_spi_host_against_panda_firmware():
  with tempfile.TemporaryDirectory() as tmp:
    harness = os.path.join(tmp, "harness.o")
    exe = os.path.join(tmp, "spi_protocol_host")
    subprocess.check_call(["gcc", "-c", "-std=gnu11", "-Wall", "-Werror", "-Wno-unused-function", "-I", PANDA_DIR, "-I", OPENDBC_DIR,
                           os.path.join(PANDA_DIR, "tests", "spi_protocol", "harness.c"), "-o", harness])
    subprocess.check_call(["g++", "-std=c++2a", "-I", OPENPILOT_DIR, "-I", BASEDIR,
                           os.path.join(OPENPILOT_DIR, "selfdrive", "pandad", "spi.cc"),
                           os.path.join(os.path.dirname(__file__), "spi_protocol_host.cc"), harness,
                           "-Wl,--wrap=open", "-o", exe])
    # a protocol fault sends pandad into its NACK drain, which the simulated bus never ends: a hang is a failure
    out = subprocess.run([exe], capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == "OK"
