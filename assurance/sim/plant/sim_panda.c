// Panda safety code in the loop of the fault-injection plant model (assurance/sim).
//
// Compiled by panda_loop.py into a host shared library. Everything that decides what reaches the car is the
// firmware's own source, included unchanged:
//   - opendbc libsafety (the safety hooks of every mode, Toyota included, and the test helpers), and
//   - the panda board drivers that the 100 Hz safety task runs: heartbeat monitor (TSR-407), heartbeat-loss siren
//     and EPS-fault siren (TSR-516(b)) and the IWDG feed (TSR-501).
// Only the glue of panda/board/main.c is restated below (is_car_safety_mode, the body of safety_task_handler, the
// siren condition of tick_handler and its 1 Hz engaged-mismatch check, the 0xf3 heartbeat handler of main_comms.h).
// test_plant.py fails when those source lines change, so this copy cannot drift silently. The IWDG peripheral is a plain register block; panda_loop.py
// models the hardware counter from the values the firmware writes into it.

#include "opendbc/safety/tests/libsafety/safety.c"

#include "board/drivers/heartbeat_monitor.h"
#include "board/drivers/heartbeat_siren.h"
#include "board/drivers/eps_fault_siren.h"

typedef struct {
  uint32_t KR;
  uint32_t PR;
  uint32_t RLR;
  uint32_t SR;
  uint32_t WINR;
} sim_iwdg_t;
sim_iwdg_t sim_iwdg;
#define IND_WDG (&sim_iwdg)
#define IWDG_SR_PVU 0x1U
#define IWDG_SR_RVU 0x2U
#define IWDG_SR_WVU 0x4U
#include "board/drivers/hw_watchdog.h"

static bool heartbeat_siren_active = false;
static bool eps_fault_siren_active = false;

// panda/board/main.c is_car_safety_mode
bool is_car_safety_mode(uint16_t mode) {
  return (mode != SAFETY_SILENT) &&
         (mode != SAFETY_NOOUTPUT) &&
         (mode != SAFETY_ALLOUTPUT) &&
         (mode != SAFETY_ELM327);
}

// panda/board/main.c safety_task_handler, without the timer register (called every 10 ms by the plant loop)
void sim_safety_task(void) {
    safety_tick();
    const bool heartbeat_revoke = heartbeat_monitor_tick() && is_car_safety_mode(current_safety_mode);
    heartbeat_siren_active = heartbeat_siren_tick(heartbeat_revoke, controls_allowed, safety_tx_arrival_revoked);
    if (heartbeat_revoke) {
      controls_allowed = false;
    }
    eps_fault_siren_active = eps_fault_siren_tick(safety_eps_fault, controls_allowed);
    hw_watchdog_tick();
}

// panda/board/main.c tick_handler, 1 Hz part: the engaged-mismatch check (WP-A-04 MCS-02.9). Authority that the
// heartbeat reports as not engaged on three 1 Hz ticks in a row is revoked; nothing else in this check sounds a siren.
// The counter is declared in opendbc safety.h

void sim_tick_1hz(void) {
  // exit controls allowed if unused by openpilot for a few seconds
  if (controls_allowed && !heartbeat_engaged) {
    heartbeat_engaged_mismatches += 1U;
    if (heartbeat_engaged_mismatches >= 3U) {
      controls_allowed = false;
    }
  } else {
    heartbeat_engaged_mismatches = 0U;
  }
}

// panda/board/main_comms.h 0xf3 handler, the parts the safety code reads
void sim_heartbeat(bool engaged) {
  heartbeat_monitor_reset();
  heartbeat_engaged = engaged;
}

// panda/board/main.c tick_handler (8 Hz): the speaker sounds on odd ticks while a siren is requested.
// The 1 Hz siren_countdown path (T-07, 4-5 s) is not modelled: it starts after every case of the plant model ends.
bool sim_siren_on(uint8_t loop_counter) {
  return ((loop_counter & 1U) != 0U) && (eps_fault_siren_active || heartbeat_siren_active);
}

// panda/board/main.c: the IWDG starts the first time the relay is driven (set_intercept_relay)
void sim_relay_driven(void) {
  hw_watchdog_start();
}

void sim_main_loop_alive(void) {
  hw_watchdog_main_loop_alive();
}

// cold start after a reset: the firmware's static state starts from zero
void sim_board_reset(void) {
  heartbeat_monitor_reset();
  heartbeat_siren_reset();
  eps_fault_siren_reset();
  heartbeat_engaged_mismatches = 0U;
  heartbeat_siren_active = false;
  eps_fault_siren_active = false;
  hw_watchdog_running = false;
  hw_watchdog_main_loop_ran = false;
  hw_watchdog_skip_tick = false;
  sim_iwdg = (sim_iwdg_t){0};
}

bool sim_get_heartbeat_siren(void) { return heartbeat_siren_active; }
bool sim_get_eps_fault_siren(void) { return eps_fault_siren_active; }
bool sim_get_relay_malfunction(void) { return relay_malfunction; }
uint32_t sim_iwdg_kr(void) { return sim_iwdg.KR; }
void sim_iwdg_clear_kr(void) { sim_iwdg.KR = 0U; }
uint32_t sim_iwdg_pr(void) { return sim_iwdg.PR; }
uint32_t sim_iwdg_rlr(void) { return sim_iwdg.RLR; }
uint32_t sim_iwdg_winr(void) { return sim_iwdg.WINR; }
bool sim_iwdg_running(void) { return hw_watchdog_running; }
