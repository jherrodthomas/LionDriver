#include <cstdint>
#include <set>

#include <capnp/schema.h>

#include "common/tests/native_test.h"
#include "openpilot/cereal/messaging/messaging.h"
#include "selfdrive/pandad/pandad.h"
#include "panda/board/sys/sys.h"

using FaultType = cereal::PandaState::FaultType;

// SWF-025: pandaStates.faults must never report a relayMalfunction that faults_pkt does not carry

static std::vector<FaultType> convert(uint32_t faults_pkt, uint32_t *unknown) {
  MessageBuilder msg;
  auto ps = msg.initEvent().initPandaStates(1)[0];
  *unknown = fill_panda_faults(ps, faults_pkt);
  std::vector<FaultType> out;
  for (auto f : ps.getFaults()) out.push_back(f);
  return out;
}

static bool has_relay_malfunction(const std::vector<FaultType> &faults) {
  for (auto f : faults) {
    if (f == FaultType::RELAY_MALFUNCTION) return true;
  }
  return false;
}

void test_pandad_faults() {
  uint32_t unknown = 0U;

  // the last enum value in log.capnp is the one pandad maps up to
  CHECK(size_t(PANDA_FAULT_TYPE_MAX) + 1U == capnp::Schema::from<FaultType>().getEnumerants().size());

  // the panda's sound DMA bit is a known FaultType
  CHECK(FAULT_INTERRUPT_RATE_SOUND_DMA == (1UL << uint32_t(FaultType::INTERRUPT_RATE_SOUND_DMA)));

  // no faults
  auto faults = convert(0U, &unknown);
  CHECK(faults.empty());
  CHECK(unknown == 0U);

  // bit 27 alone
  faults = convert(FAULT_INTERRUPT_RATE_SOUND_DMA, &unknown);
  CHECK(faults.size() == 1U);
  CHECK(faults[0] == FaultType::INTERRUPT_RATE_SOUND_DMA);
  CHECK(!has_relay_malfunction(faults));
  CHECK(unknown == 0U);

  // bit 27 with unknown high bits: unknown bits are dropped and reported, never defaulted
  faults = convert(FAULT_INTERRUPT_RATE_SOUND_DMA | (1UL << 28) | (1UL << 31), &unknown);
  CHECK(faults.size() == 1U);
  CHECK(faults[0] == FaultType::INTERRUPT_RATE_SOUND_DMA);
  CHECK(!has_relay_malfunction(faults));
  CHECK(unknown == ((1UL << 28) | (1UL << 31)));

  // only unknown bits
  faults = convert(0xF0000000U, &unknown);
  CHECK(faults.empty());
  CHECK(unknown == 0xF0000000U);

  // a real relay malfunction is still reported, once
  faults = convert(FAULT_RELAY_MALFUNCTION | FAULT_HEARTBEAT_LOOP_WATCHDOG | (1UL << 31), &unknown);
  CHECK(faults.size() == 2U);
  CHECK(faults[0] == FaultType::RELAY_MALFUNCTION);
  CHECK(faults[1] == FaultType::HEARTBEAT_LOOP_WATCHDOG);
  CHECK(unknown == (1UL << 31));

  // every bit set except relayMalfunction: one entry per known bit, in order, none at the default
  faults = convert(0xFFFFFFFEU, &unknown);
  CHECK(faults.size() == size_t(PANDA_FAULT_TYPE_MAX));
  CHECK(!has_relay_malfunction(faults));
  std::set<FaultType> seen(faults.begin(), faults.end());
  CHECK(seen.size() == faults.size());
  for (size_t i = 0; i < faults.size(); i++) {
    CHECK(size_t(faults[i]) == i + 1U);
  }
  CHECK(unknown == (0xFFFFFFFFU << (size_t(PANDA_FAULT_TYPE_MAX) + 1U)));
}

int main() {
  return run_native_test(test_pandad_faults);
}
