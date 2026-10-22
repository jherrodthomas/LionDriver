// TE-03 step P4: run the panda's own engaged-mismatch and heartbeat-siren code (TSR-307(a), TSR-516(c)) in the
// order of safety_task_handler() in panda/board/main.c, and let the Copilot monitor that Ogma generated from the
// FRETish requirements watch it, one 100 Hz safety-task tick at a time.
//
// The monitor's inputs are set here from the code's state after each tick: authority_granted (controls_allowed),
// hb_engaged (the last heartbeat's flag), pcm_cruise_active, siren_on (the heartbeat siren is active). not_engaged_ticks
// is computed here from its glossary definition, not read from the code, so the monitor does not check the code
// against its own counter. A violation is a call of a monitor handler; FRET's past-time formulas are "historically"
// (H) properties, so once violated a handler is called on every later tick, and the output gives the first call.
//
//   harness N          run scenario N; one process per scenario, because the generated monitor has no reset
//   harness            print the number of scenarios
// Built by run_monitor.py with -I<panda>/board/drivers and the generated monitor.

#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#include "engaged_mismatch.h"
#include "heartbeat_siren.h"
#include "monitor.h"

// monitor inputs (extern in the generated monitor)
bool authority_granted;
bool hb_engaged;
bool pcm_cruise_active;
bool siren_on;
int64_t not_engaged_ticks;

// first violation tick per handler (-1: none), set by the generated harness_handlers.c from current_tick
extern const char *const handler_names[];
extern long handler_first[];
extern const int handler_total;
long current_tick;

typedef struct {
  const char *name;
  int ticks;
  int hb_off_from, hb_off_to;      // heartbeat reports "not engaged" in [from, to) ticks; to < 0: to the end
  int cruise_off_from;             // PCM cruise drops at this tick; < 0: never
  unsigned long seed;              // 0: scripted; else random heartbeat episodes, cruise changes and re-engagement
} scenario_t;

static const scenario_t SCENARIOS[] = {
  {"selfdrived stop, cruise stays on (MCS-02.9)", 800, 100, -1, -1, 0},
  {"openpilot disengages with an ACC cancel 0.2 s later", 800, 100, -1, 120, 0},
  {"one heartbeat reports not engaged (100 ms)", 800, 100, 110, -1, 0},
  {"not engaged for 0.25 s", 800, 100, 125, -1, 0},
  {"random episodes, seed 1", 200000, 0, 0, -1, 1},
  {"random episodes, seed 2", 200000, 0, 0, -1, 2},
};
#define SCENARIO_COUNT ((int)(sizeof(SCENARIOS) / sizeof(SCENARIOS[0])))

static unsigned long rng_state;
static unsigned long rng(void) {
  rng_state = rng_state * 6364136223846793005UL + 1442695040888963407UL;
  return (unsigned long)(rng_state >> 33);
}

static void run(const scenario_t *s) {
  bool controls_allowed = true;
  bool heartbeat_flag = true;
  bool cruise = true;
  bool siren_active = false;
  bool siren_prev = false;
  bool prev_authority = controls_allowed;
  int first_revoke = -1, first_siren = -1, grant_at = -1, off_left = 0;
  int revocations = 0, siren_starts = 0;
  int64_t ne_ticks = 0;
  engaged_mismatch_reset();
  heartbeat_siren_reset();
  for (int i = 0; i < handler_total; i++) {
    handler_first[i] = -1L;
  }
  rng_state = s->seed;

  for (int t = 0; t < s->ticks; t++) {
    if (s->seed == 0UL) {
      heartbeat_flag = !((t >= s->hb_off_from) && ((s->hb_off_to < 0) || (t < s->hb_off_to)));
      cruise = !((s->cruise_off_from >= 0) && (t >= s->cruise_off_from));
    } else {
      // the heartbeat arrives at 10 Hz: not-engaged episodes of 1 to 12 heartbeats (0.1 to 1.2 s) start at 2 % of
      // the engaged heartbeats
      if ((t % 10) == 0) {
        if ((off_left == 0) && ((rng() % 100UL) < 2UL)) {
          off_left = 1 + (int)(rng() % 12UL);
        }
        heartbeat_flag = (off_left == 0);
        if (off_left > 0) {
          off_left--;
        }
      }
      // PCM cruise drops or comes back about every 4 s
      if ((rng() % 400UL) == 0UL) {
        cruise = !cruise;
      }
      // re-engagement: authority comes back up to 2 s after heartbeat and cruise both say engaged
      if (!controls_allowed && heartbeat_flag && cruise) {
        if (grant_at < 0) {
          grant_at = t + 1 + (int)(rng() % 200UL);
        } else if (t >= grant_at) {
          controls_allowed = true;
          grant_at = -1;
        }
      } else {
        grant_at = -1;
      }
    }

    // the safety mode revokes authority when PCM cruise is inactive (TSR-301), in safety_tick() before this
    if (!cruise) {
      controls_allowed = false;
    }

    // safety_task_handler() order: engaged mismatch, heartbeat siren (before the revocation), then the revocation
    bool mismatch_siren = false;
    const bool revoke = engaged_mismatch_tick(controls_allowed, heartbeat_flag, cruise, &mismatch_siren);
    siren_active = heartbeat_siren_tick(false, controls_allowed, mismatch_siren);
    if (revoke) {
      controls_allowed = false;
    }

    // not_engaged_ticks by its glossary definition: ticks, the first counted as 1, in which the heartbeat has
    // reported not engaged since it first did while authority was granted; 0 when it reports engaged
    if (heartbeat_flag) {
      ne_ticks = 0;
    } else if ((ne_ticks > 0) || prev_authority) {
      ne_ticks += 1;
    } else {
      ne_ticks = 0;
    }

    authority_granted = controls_allowed;
    hb_engaged = heartbeat_flag;
    pcm_cruise_active = cruise;
    siren_on = siren_active;
    not_engaged_ticks = ne_ticks;
    current_tick = t;
    step();
    prev_authority = controls_allowed;

    if (revoke) {
      revocations++;
      if (first_revoke < 0) {
        first_revoke = t;
      }
    }
    if (siren_active && !siren_prev) {
      siren_starts++;
      if (first_siren < 0) {
        first_siren = t;
      }
    }
    siren_prev = siren_active;
  }

  // fields: name, ticks, revocations, siren starts, then for scripted scenarios the ticks from the first "not engaged"
  // heartbeat to the revocation and to the siren (-1: none), then handler=first violation tick (-1: none)
  printf("%s|%d|%d|%d|", s->name, s->ticks, revocations, siren_starts);
  if (s->seed == 0UL) {
    printf("%d|%d", (first_revoke < 0) ? -1 : (first_revoke - s->hb_off_from),
           (first_siren < 0) ? -1 : (first_siren - s->hb_off_from));
  } else {
    printf("|");
  }
  for (int i = 0; i < handler_total; i++) {
    printf("|%s=%ld", handler_names[i], handler_first[i]);
  }
  printf("\n");
}

int main(int argc, char **argv) {
  if (argc < 2) {
    printf("%d\n", SCENARIO_COUNT);
    return 0;
  }
  const int n = atoi(argv[1]);
  if ((n < 0) || (n >= SCENARIO_COUNT)) {
    return 2;
  }
  run(&SCENARIOS[n]);
  return 0;
}
