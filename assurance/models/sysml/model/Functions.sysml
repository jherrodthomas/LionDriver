package LionDriverFunctions {
    doc
    /*
     * Functional architecture: the functions F-01 to F-09 of WP-C-01 §2.1, each decomposed
     * into the steps of its functional chain (sense, perceive, plan or decide, control, command path,
     * envelope, act or inform). The element that performs a step is declared in
     * LionDriverArchitecture with a perform statement, so the chain allocates every function
     * to the physical architecture. Steps follow WP-C-01 §2.1 (main implementation),
     * WP-S-03 §8 (processes) and §9 (cereal services).
     *
     * Status: draft, AI-assisted (Claude), not reviewed (I0). Function IDs and titles are
     * checked against WP-C-01 §2.1 (M9); the decomposition itself is new here.
     */

    private import LionDriverLibrary::*;

    action <'F-01'> lateralControl : ItemFunction {
        doc /* Lateral control (lane centring) */
        action <'F-01.1'> lateralRoadImages : FunctionStep { doc /* road images */ :>> stage = Stage::sense; }
        action <'F-01.2'> desiredPath : FunctionStep { doc /* desired path and curvature (driving model) */ :>> stage = Stage::perceive; }
        action <'F-01.3'> lateralLaw : FunctionStep { doc /* lateral control law (torque) */ :>> stage = Stage::control; }
        action <'F-01.4'> packLka : FunctionStep { doc /* pack STEERING_LKA 0x2E4 */ :>> stage = Stage::command; }
        action <'F-01.5'> sendLka : FunctionStep { doc /* send over SPI */ :>> stage = Stage::command; }
        action <'F-01.6'> limitTorque : FunctionStep { doc /* torque limits, rate, gating */ :>> stage = Stage::envelope; }
        action <'F-01.7'> applyTorque : FunctionStep { doc /* apply steering torque */ :>> stage = Stage::act; }
    }

    action <'F-02'> longitudinalControl : ItemFunction {
        doc /* Longitudinal control (ACC with stop-and-go) */
        action <'F-02.1'> longitudinalRoadImages : FunctionStep { doc /* road images */ :>> stage = Stage::sense; }
        action <'F-02.2'> radarTracks : FunctionStep { doc /* radar lead tracks */ :>> stage = Stage::sense; }
        action <'F-02.3'> leadFusion : FunctionStep { doc /* lead fusion (vision and radar) */ :>> stage = Stage::perceive; }
        action <'F-02.4'> longitudinalPlan : FunctionStep { doc /* longitudinal plan (accel target) */ :>> stage = Stage::plan; }
        action <'F-02.5'> longitudinalLaw : FunctionStep { doc /* longitudinal control law */ :>> stage = Stage::control; }
        action <'F-02.6'> packAcc : FunctionStep { doc /* pack ACC_CONTROL 0x343 */ :>> stage = Stage::command; }
        action <'F-02.7'> sendAcc : FunctionStep { doc /* send over SPI */ :>> stage = Stage::command; }
        action <'F-02.8'> boundAccel : FunctionStep { doc /* acceleration bounds, gating */ :>> stage = Stage::envelope; }
        action <'F-02.9'> applyAccel : FunctionStep { doc /* drive and brake */ :>> stage = Stage::act; }
    }

    action <'F-03'> engagement : ItemFunction {
        doc /* Engagement and mode management */
        action <'F-03.1'> cruiseInputs : FunctionStep { doc /* cruise state, brake, gas on vehicle CAN */ :>> stage = Stage::sense; }
        action <'F-03.2'> carState : FunctionStep { doc /* parse carState */ :>> stage = Stage::perceive; }
        action <'F-03.3'> engagementState : FunctionStep { doc /* engagement state machine, events */ :>> stage = Stage::plan; }
        action <'F-03.4'> heartbeat : FunctionStep { doc /* heartbeat and safety-mode set */ :>> stage = Stage::command; }
        action <'F-03.5'> authority : FunctionStep { doc /* authority on the PCM cruise edge; revoke on brake */ :>> stage = Stage::envelope; }
    }

    action <'F-04'> driverMonitoring : ItemFunction {
        doc /* Driver monitoring */
        action <'F-04.1'> driverImages : FunctionStep { doc /* driver images (IR) */ :>> stage = Stage::sense; }
        action <'F-04.2'> attention : FunctionStep { doc /* attention estimate (DM model) */ :>> stage = Stage::perceive; }
        action <'F-04.3'> dmPolicy : FunctionStep { doc /* warnings, forced decel, lockout */ :>> stage = Stage::plan; }
        action <'F-04.4'> dmAlerts : FunctionStep { doc /* DM alerts on display and speaker */ :>> stage = Stage::act; }
    }

    action <'F-05'> driverInformation : ItemFunction {
        doc /* Driver information and warnings */
        action <'F-05.1'> alertClasses : FunctionStep { doc /* event classes and alerts */ :>> stage = Stage::plan; }
        action <'F-05.2'> uiSound : FunctionStep { doc /* UI and sounds */ :>> stage = Stage::command; }
        action <'F-05.3'> packHud : FunctionStep { doc /* pack LKAS_HUD 0x412 */ :>> stage = Stage::command; }
        action <'F-05.4'> displaySpeaker : FunctionStep { doc /* display and speaker */ :>> stage = Stage::act; }
        action <'F-05.5'> clusterHud : FunctionStep { doc /* cluster LKA HUD */ :>> stage = Stage::act; }
    }

    action <'F-06'> forwardCollisionWarning : ItemFunction {
        doc /* Forward collision warning */
        action <'F-06.1'> fcwRoadImages : FunctionStep { doc /* road images */ :>> stage = Stage::sense; }
        action <'F-06.2'> hardBrake : FunctionStep { doc /* hard-brake prediction (driving model) */ :>> stage = Stage::perceive; }
        action <'F-06.3'> fcwEvent : FunctionStep { doc /* FCW event (no braking) */ :>> stage = Stage::plan; }
        action <'F-06.4'> fcwAlert : FunctionStep { doc /* FCW alert */ :>> stage = Stage::act; }
    }

    action <'F-07'> laneDepartureWarning : ItemFunction {
        doc /* Lane departure warning */
        action <'F-07.1'> ldwRoadImages : FunctionStep { doc /* road images */ :>> stage = Stage::sense; }
        action <'F-07.2'> laneLines : FunctionStep { doc /* lane lines (driving model) */ :>> stage = Stage::perceive; }
        action <'F-07.3'> ldwLogic : FunctionStep { doc /* LDW logic (not engaged, above 31 mph) */ :>> stage = Stage::plan; }
        action <'F-07.4'> ldwAlert : FunctionStep { doc /* LDW alert */ :>> stage = Stage::act; }
    }

    action <'F-08'> safetyEnvelope : ItemFunction {
        doc /* Safety envelope */
        action <'F-08.1'> canRx : FunctionStep { doc /* vehicle and camera CAN RX */ :>> stage = Stage::sense; }
        action <'F-08.2'> rxChecks : FunctionStep { doc /* RX checks: checksum, counter, timeout */ :>> stage = Stage::perceive; }
        action <'F-08.3'> supervision : FunctionStep { doc /* heartbeat and loop supervision */ :>> stage = Stage::plan; }
        action <'F-08.4'> txChecks : FunctionStep { doc /* TX whitelist, limits, gating */ :>> stage = Stage::envelope; }
        action <'F-08.5'> intercept : FunctionStep { doc /* intercept or forward (relay) */ :>> stage = Stage::act; }
    }

    action <'F-09'> loggingAndUpdate : ItemFunction {
        doc /* Data logging, upload, remote access, software update (non-driving) */
        action <'F-09.1'> logging : FunctionStep { doc /* drive logging */ :>> stage = Stage::sense; }
        action <'F-09.2'> remote : FunctionStep { doc /* upload, athena, OTA update */ :>> stage = Stage::command; }
        action <'F-09.3'> backEnd : FunctionStep { doc /* server, updates */ :>> stage = Stage::act; }
    }
}
