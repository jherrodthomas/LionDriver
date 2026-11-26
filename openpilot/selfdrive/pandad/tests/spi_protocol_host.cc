// pandad's SPI host (spi.cc) against the panda firmware's SPI driver (panda/board/drivers/spi.h), both compiled for
// the host: the spidev ioctl is replaced by the simulated SPI4 bus of panda/tests/spi_protocol/harness.c.
// LionDriver SWSR-410, 410a, 410h, 412. Built and run by test_pandad_spi_protocol.py.
#include <cassert>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <fcntl.h>
#include <linux/spi/spidev.h>
#include <string>
#include <unistd.h>

#include "common/util.h"
#include "selfdrive/pandad/panda_comms.h"

extern "C" {
uint8_t bus_byte(uint8_t mosi);
void end_transaction(void);
void reset_mcu(void);
uint16_t errors(void);
uint8_t last_frame_index(void);
uint32_t written_bytes(void);
int written_calls(void);
int controls(void);
void set_can_read_avail(int n);
}

// --- stand-ins for the parts of openpilot's common library spi.cc uses ---
void cloudlog_e(int levelnum, const char* filename, int lineno, const char* func, const char* fmt, ...) {
  (void)levelnum; (void)filename; (void)lineno; (void)func; (void)fmt;
}
namespace util {
int safe_ioctl(int fd, unsigned long request, void *argp, const char* exception_msg) {
  (void)fd; (void)exception_msg;
  if (request == SPI_IOC_MESSAGE(1)) {
    spi_ioc_transfer *t = (spi_ioc_transfer *)argp;
    const uint8_t *tx = (const uint8_t *)t->tx_buf;
    uint8_t *rx = (uint8_t *)t->rx_buf;
    for (uint32_t i = 0; i < t->len; i++) {
      const uint8_t miso = bus_byte((tx != nullptr) ? tx[i] : 0U);
      if (rx != nullptr) rx[i] = miso;
    }
    end_transaction();
    return (int)t->len;
  }
  return 0;
}
bool file_exists(const std::string& fn) { (void)fn; return true; }
std::string hexdump(const uint8_t* in, const size_t size) { (void)in; (void)size; return ""; }
std::string getenv(const char* key, std::string default_val) {
  const char *v = ::getenv(key);
  return (v != nullptr) ? std::string(v) : default_val;
}
}  // namespace util

// the handle opens /dev/spidev0.0; give it a descriptor flock() accepts
extern "C" int __real_open(const char *path, int flags, ...);
extern "C" int __wrap_open(const char *path, int flags, ...) {
  if (std::string(path) == "/dev/spidev0.0") return __real_open("/dev/null", O_RDWR);
  va_list ap; va_start(ap, flags); int mode = va_arg(ap, int); va_end(ap);
  return __real_open(path, flags, mode);
}

#define CHECK(c) do { if (!(c)) { fprintf(stderr, "FAILED line %d: %s\n", __LINE__, #c); return 1; } } while (0)

int main() {
  reset_mcu();

  // connect: the constructor reads the serial (0xc3) as the session's first transfer, counter 0
  PandaSpiHandle h("");
  CHECK(h.hw_serial == "c3c4c5c6c7c8c9cacbcccdce");
  CHECK(controls() == 1);

  // control requests through a counter wrap (255 is followed by 1)
  for (int i = 0; i < 600; i++) CHECK(h.control_write(0xdc, 0, 0) == 0);
  uint8_t buf[2048];
  CHECK(h.control_read(0xd2, 0, 0, buf, 10) == 10);
  for (int i = 0; i < 10; i++) CHECK(buf[i] == (uint8_t)(0xd2 + i));
  CHECK(controls() == 602);

  // CAN writes: one sendcan message split into transfers within the 2047-byte data phase, each with its frame index
  uint8_t data[5000];
  for (int i = 0; i < 5000; i++) data[i] = (uint8_t)i;
  h.can_frame_index = 41;
  CHECK(h.bulk_write(3, data, sizeof(data), 0) >= 0);  // returns the bytes read back, 0 for a write
  CHECK(written_bytes() == 5000);
  CHECK(written_calls() == 3);
  CHECK(last_frame_index() == 41);
  // other endpoints carry index 0
  CHECK(h.control_write(0xdc, 0, 0) == 0);
  CHECK(last_frame_index() == 0);

  // CAN read
  set_can_read_avail(3000);
  CHECK(h.bulk_read(0x81, buf, 1984, 0) == 1984);
  CHECK(buf[0] == 0xA0);
  CHECK(errors() == 0);

  // a second host session (another process) moves the panda's counter; this handle gets one sequence NACK,
  // restarts at 0 and goes on
  {
    PandaSpiHandle other("");
    CHECK(other.control_write(0xdc, 0, 0) == 0);
  }
  const int before = controls();
  CHECK(h.control_write(0xdc, 0, 0) == 0);
  CHECK(h.control_write(0xdc, 0, 0) == 0);
  CHECK(controls() == before + 2);
  CHECK(errors() == 1);

  printf("OK\n");
  return 0;
}
