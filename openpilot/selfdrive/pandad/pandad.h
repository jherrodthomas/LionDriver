#pragma once

#include <string>

#include "common/params.h"
#include "selfdrive/pandad/panda.h"

void pandad_main_thread(std::string serial);

// Last cereal::PandaState::FaultType; faults_pkt bits above it have no FaultType.
constexpr cereal::PandaState::FaultType PANDA_FAULT_TYPE_MAX = cereal::PandaState::FaultType::INTERRUPT_RATE_SOUND_DMA;

// Converts the panda's faults_pkt bitset into ps.faults. Bits without a FaultType are
// left out of the list (never sent as the default relayMalfunction) and returned.
uint32_t fill_panda_faults(cereal::PandaState::Builder &ps, uint32_t faults_pkt);

class PandaSafety {
public:
  PandaSafety(Panda *panda) : panda_(panda) {}
  void configureSafetyMode(bool is_onroad);

private:
  void updateMultiplexingMode();
  std::string fetchCarParams();
  void setSafetyMode(const std::string &params_string);

  bool initialized_ = false;
  bool log_once_ = false;
  bool safety_configured_ = false;
  bool prev_obd_multiplexing_ = false;
  Panda *panda_;
  Params params_;
};
