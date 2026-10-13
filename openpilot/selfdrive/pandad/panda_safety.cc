#include "selfdrive/pandad/pandad.h"
#include "openpilot/cereal/messaging/messaging.h"
#include "common/swaglog.h"

void PandaSafety::configureSafetyMode(bool is_onroad) {
  if (is_onroad && !safety_configured_) {
    updateMultiplexingMode();

    auto car_params = fetchCarParams();
    if (!car_params.empty()) {
      LOGW("got %lu bytes CarParams", car_params.size());
      setSafetyMode(car_params);
      safety_configured_ = true;
    }
  } else if (!is_onroad) {
    initialized_ = false;
    safety_configured_ = false;
    log_once_ = false;
  }
}

void PandaSafety::updateMultiplexingMode() {
  // Initialize to ELM327 without OBD multiplexing for initial fingerprinting
  if (!initialized_) {
    prev_obd_multiplexing_ = false;
    panda_->set_safety_model(cereal::CarParams::SafetyModel::ELM327, 1U);
    initialized_ = true;
  }

  // Switch between multiplexing modes based on the OBD multiplexing request
  bool obd_multiplexing_requested = params_.getBool("ObdMultiplexingEnabled");
  if (obd_multiplexing_requested != prev_obd_multiplexing_) {
    const uint16_t safety_param = obd_multiplexing_requested ? 0U : 1U;
    panda_->set_safety_model(cereal::CarParams::SafetyModel::ELM327, safety_param);
    prev_obd_multiplexing_ = obd_multiplexing_requested;
    params_.putBool("ObdMultiplexingChanged", true);
  }
}

bool PandaSafety::panda_reference_build() {
  // a failed read counts as "not a reference build"
  auto health = panda_->get_state();
  return health.has_value() && ((health->flags_pkt & HEALTH_FLAG_REFERENCE_BUILD) != 0U);
}

std::string PandaSafety::fetchCarParams() {
  if (!params_.getBool("FirmwareQueryDone")) {
    return {};
  }

  if (!log_once_) {
    LOGW("Finished FW query, Waiting for params to set safety model");
    log_once_ = true;
  }

  if (!params_.getBool("ControlsReady")) {
    return {};
  }
  return params_.get("CarParams");
}

void PandaSafety::setSafetyMode(const std::string &params_string) {
  AlignedBuffer aligned_buf;
  capnp::FlatArrayMessageReader cmsg(aligned_buf.align(params_string.data(), params_string.size()));
  cereal::CarParams::Reader car_params = cmsg.getRoot<cereal::CarParams>();

  auto safety_configs = car_params.getSafetyConfigs();
  uint16_t alternative_experience = car_params.getAlternativeExperience();

  cereal::CarParams::SafetyModel safety_model = safety_configs[0].getSafetyModel();
  uint16_t safety_param = safety_configs[0].getSafetyParam();

#ifdef LIONDRIVER_REFERENCE
  // LionDriver (TSR-619, TSR-514): a car safety mode is configured only on a panda whose firmware carries the
  // safety-mode lock of the reference build. Otherwise the panda stays in NOOUTPUT (no TX); selfdrived then sees the
  // safety model differ from CarParams (controlsMismatch) and does not allow engagement.
  if (!panda_reference_build()) {
    LOGE("panda firmware is not a LionDriver reference build: refusing safety model %d, param %d; panda kept in "
         "NOOUTPUT", (int)safety_model, safety_param);
    panda_->set_safety_model(cereal::CarParams::SafetyModel::NO_OUTPUT, 0U);
    return;
  }
#endif

  LOGW("setting safety model: %d, param: %d, alternative experience: %d", (int)safety_model, safety_param, alternative_experience);
  panda_->set_alternative_experience(alternative_experience);
  panda_->set_safety_model(safety_model, safety_param);
}
