package LionDriverMechanisms {
    doc
    /*
     * Safety mechanisms SM-01 to SM-43 of WP-S-03 §6 (catalogue as of version 0.6).
     * Status, coverage notes and latent-fault handling stay in WP-S-03 §6.
     * The elements that perform each mechanism are declared in LionDriverArchitecture
     * (perform statements), following the Element column of WP-S-03 §6.
     */

    private import LionDriverLibrary::*;

    action <'SM-01'> torqueMagnitudeLimit : SafetyMechanism {
        doc /* Torque magnitude limit (speed-dependent) */
        :>> covers = "excessive torque command from SoC";
        :>> dcTarget = "high (for SoC command faults)";
        :>> tsr = ("TSR-101", "TSR-102");
    }
    action <'SM-02'> torqueRateLimit : SafetyMechanism {
        doc /* Torque rate and RT-window limit */
        :>> covers = "high-rate torque command";
        :>> dcTarget = "high";
        :>> tsr = "TSR-103";
    }
    action <'SM-03'> measuredTorqueTracking : SafetyMechanism {
        doc /* Measured-torque tracking */
        :>> covers = "command diverging from EPS output";
        :>> dcTarget = "medium (depends on 0x260 integrity)";
        :>> tsr = "TSR-104";
    }
    action <'SM-04'> authorityGating : SafetyMechanism {
        doc /* Authority gating (PCM edge, brake, gas, steer request) */
        :>> covers = "actuation when not engaged; no release on driver action";
        :>> dcTarget = "high";
        :>> tsr = ("TSR-105", "TSR-106", "TSR-107", "TSR-203", "TSR-301", "TSR-302", "TSR-303", "TSR-304", "TSR-305", "TSR-306");
    }
    action <'SM-05'> driverTorqueOverride : SafetyMechanism {
        doc /* Driver-torque override monitor */
        :>> covers = "actuation opposing driver";
        :>> dcTarget = "medium";
        :>> tsr = ("TSR-304", "TSR-628");
    }
    action <'SM-06'> epsStatusMonitor : SafetyMechanism {
        doc /* EPS status monitor */
        :>> covers = "EPS LKA fault while engaged";
        :>> dcTarget = "medium";
        :>> tsr = ("TSR-110", "TSR-607");
    }
    action <'SM-07'> longitudinalBounds : SafetyMechanism {
        doc /* Longitudinal bounds and jerk limits */
        :>> covers = "excessive accel/decel or onset";
        :>> dcTarget = "high";
        :>> tsr = ("TSR-201", "TSR-202", "TSR-203", "TSR-204", "TSR-205", "TSR-206", "TSR-207");
    }
    action <'SM-08'> activeSafeStateFrame : SafetyMechanism {
        doc /* Active safe-state frame */
        :>> covers = "torque persisting after rejection";
        :>> dcTarget = "high";
        :>> tsr = ("TSR-108", "TSR-109");
    }
    action <'SM-09'> rxTimeout : SafetyMechanism {
        doc /* RX timeout */
        :>> covers = "lost/delayed RX";
        :>> dcTarget = "medium (alone)";
        :>> tsr = "TSR-401";
    }
    action <'SM-10'> rxChecksumLength : SafetyMechanism {
        doc /* RX checksum + length */
        :>> covers = "corrupted RX (0x260, 0x1D2)";
        :>> dcTarget = "low (8-bit additive)";
        :>> tsr = "TSR-402";
    }
    action <'SM-11'> rxPlausibility : SafetyMechanism {
        doc /* RX rate, frozen-content and cross-checks */
        :>> covers = "repeated/inserted/masqueraded RX";
        :>> dcTarget = "medium (combined with SM-09/10)";
        :>> tsr = ("TSR-403", "TSR-404", "TSR-405");
    }
    action <'SM-12'> heartbeatLiveness : SafetyMechanism {
        doc /* Heartbeat + control-loop liveness */
        :>> covers = "SoC hang, frozen control loop";
        :>> dcTarget = "medium";
        :>> tsr = ("TSR-407", "TSR-409");
    }
    action <'SM-13'> commandFreshness : SafetyMechanism {
        doc /* Command-frame freshness */
        :>> covers = "SoC stops sending commands";
        :>> dcTarget = "high";
        :>> tsr = ("TSR-408", "TSR-614");
    }
    action <'SM-14'> spiIntegrity : SafetyMechanism {
        doc /* SPI CRC + sequence counter + bounds checks */
        :>> covers = "corrupted/stale/oversized SoC transfers";
        :>> dcTarget = "high (with CRC-16/32)";
        :>> tsr = ("TSR-410", "TSR-411", "TSR-412", "TSR-413");
    }
    action <'SM-15'> independentWatchdog : SafetyMechanism {
        doc /* Independent watchdog */
        :>> covers = "MCU program-flow stall";
        :>> dcTarget = "medium (timeout only) / high (window + logical checkpoint)";
        :>> tsr = "TSR-501";
    }
    action <'SM-16'> faultToSafeState : SafetyMechanism {
        doc /* Fault → safe state */
        :>> covers = "any detected platform fault";
        :>> dcTarget = "— (enabler)";
        :>> tsr = ("TSR-406", "TSR-502", "TSR-706");
    }
    action <'SM-17'> memoryIntegrity : SafetyMechanism {
        doc /* RAM ECC, flash CRC, register checks */
        :>> covers = "memory/register corruption";
        :>> dcTarget = "high (ECC), medium (register)";
        :>> tsr = "TSR-503";
    }
    action <'SM-18'> clockMonitor : SafetyMechanism {
        doc /* Clock monitor (CSS + cross-check) */
        :>> covers = "clock loss/drift";
        :>> dcTarget = "medium";
        :>> tsr = "TSR-504";
    }
    action <'SM-19'> supplyMonitor : SafetyMechanism {
        doc /* Supply monitor (BOR, PVD, input voltage) */
        :>> covers = "under/over-voltage";
        :>> dcTarget = "medium";
        :>> tsr = "TSR-505";
    }
    action <'SM-20'> relayReadback : SafetyMechanism {
        doc /* Relay readback and latch */
        :>> covers = "relay stuck either way";
        :>> dcTarget = "high (with readback)";
        :>> tsr = ("TSR-506", "TSR-710", "TSR-712");
    }
    action <'SM-21'> mpuIsolation : SafetyMechanism {
        doc /* MPU isolation */
        :>> covers = "comms handler corrupting safety data";
        :>> dcTarget = "medium";
        :>> tsr = "TSR-507";
    }
    action <'SM-22'> configurationLock : SafetyMechanism {
        doc /* Configuration lock and command gating */
        :>> covers = "SoC selects wrong mode/param; debug commands";
        :>> dcTarget = "high";
        :>> tsr = ("TSR-511", "TSR-512", "TSR-513", "TSR-514", "TSR-619", "TSR-620");
    }
    action <'SM-23'> independentSiren : SafetyMechanism {
        doc /* SoC-independent siren */
        :>> covers = "warning when the SoC is lost, on every envelope revocation that is not a driver action, and when a fault-induced ACC cancel has no effect";
        :>> dcTarget = "— (warning)";
        :>> tsr = "TSR-516";
    }
    action <'SM-24'> relayMalfunctionDetection : SafetyMechanism {
        doc /* Relay malfunction detection (traffic-based) */
        :>> covers = "relay stuck released / camera on car bus";
        :>> dcTarget = "medium";
        :>> tsr = "TSR-710";
    }
    action <'SM-25'> hostFaultClassification : SafetyMechanism {
        doc /* Host fault classification and freshness */
        :>> covers = "stale/invalid inputs on SoC";
        :>> dcTarget = "QM";
        :>> tsr = ("TSR-601", "TSR-602", "TSR-603", "TSR-604", "TSR-606", "TSR-615", "TSR-616");
    }
    action <'SM-26'> driverMonitoring : SafetyMechanism {
        doc /* Driver monitoring */
        :>> covers = "inattention (misuse)";
        :>> dcTarget = "QM (SOTIF)";
        :>> tsr = ("TSR-608", "TSR-609", "TSR-610", "TSR-611", "TSR-612");
    }
    action <'SM-27'> excessiveActuationDetector : SafetyMechanism {
        doc /* Excessive-actuation detector */
        :>> covers = "vehicle response beyond 2× limits";
        :>> dcTarget = "QM";
        :>> tsr = "TSR-617";
    }
    action <'SM-28'> controllerMargin : SafetyMechanism {
        doc /* Controller margin */
        :>> covers = "operation at envelope boundary";
        :>> dcTarget = "QM";
        :>> tsr = "TSR-605";
    }
    action <'SM-29'> engagementFollowsCruise : SafetyMechanism {
        doc /* Engagement follows PCM cruise; revoke on SoC "not engaged" */
        :>> covers = "engagement state of the envelope differs from the PCM or from the SoC";
        :>> dcTarget = "high";
        :>> tsr = ("TSR-307(a)", "TSR-309");
    }
    action <'SM-30'> engagementMismatchDetection : SafetyMechanism {
        doc /* Engagement and authority mismatch detection (SoC side) */
        :>> covers = "envelope blocks or never grants authority while engaged; PCM cruise differs from the item's state";
        :>> dcTarget = "QM (B-sup: SM-08, SM-23)";
        :>> tsr = ("TSR-307(b)", "TSR-308", "TSR-621", "TSR-626");
    }
    action <'SM-31'> hmiLiveness : SafetyMechanism {
        doc /* HMI path liveness and audible minimum */
        :>> covers = "hung render loop, stalled or muted audio, so the take-over request is not perceived";
        :>> dcTarget = "QM (B-sup: SM-23 siren, SM-29 cluster)";
        :>> tsr = ("TSR-622", "TSR-623", "TSR-627");
    }
    action <'SM-32'> boundedItemDeceleration : SafetyMechanism {
        doc /* Announced, bounded item-initiated deceleration */
        :>> covers = "deceleration not caused by traffic (DM no-response, soft disable) applied without warning or as a step";
        :>> dcTarget = "QM (B-sup: SM-07)";
        :>> tsr = "TSR-624";
    }
    action <'SM-33'> fcwInputFreshness : SafetyMechanism {
        doc /* FCW input freshness and false-alarm rate */
        :>> covers = "FCW from stale or invalid inputs; false FCW causing reflex braking";
        :>> dcTarget = "ASIL A on QM element (open, WP-C-04 OI-9)";
        :>> tsr = "TSR-625";
    }
    action <'SM-34'> accFaultReaction : SafetyMechanism {
        doc /* PCM ACC-fault reaction */
        :>> covers = "PCM does not execute ACC (ACC or cruise fault)";
        :>> dcTarget = "QM (B-sup: SM-29)";
        :>> tsr = "TSR-618";
    }
    action <'SM-35'> forwardingSupervision : SafetyMechanism {
        doc /* Forwarding with fixed block list and forwarding supervision */
        :>> covers = "camera-side frames lost, delayed or altered; block list wrong";
        :>> dcTarget = "high (block list, design); medium (overflow counting)";
        :>> tsr = ("TSR-704", "TSR-707", "TSR-711");
    }
    action <'SM-36'> pcsTxGate : SafetyMechanism {
        doc /* PCS and DSU message TX gate */
        :>> covers = "item originates or alters frames used by the stock PCS";
        :>> dcTarget = "high (when implemented)";
        :>> tsr = "TSR-705";
    }
    action <'SM-37'> stockAebIndication : SafetyMechanism {
        doc /* Stock AEB/FCW event indication */
        :>> covers = "driver not told that the stock system intervened";
        :>> dcTarget = "QM";
        :>> tsr = "TSR-709";
    }
    action <'SM-38'> txReadBack : SafetyMechanism {
        doc /* Post-load TX read-back */
        :>> covers = "approved actuation frame altered in FDCAN message RAM, FDCAN core or transceiver";
        :>> dcTarget = "high";
        :>> tsr = "TSR-517";
    }
    action <'SM-39'> txRateSupervision : SafetyMechanism {
        doc /* Per-ID TX rate supervision */
        :>> covers = "actuation frames sent faster than nominal (burst, duplicated frames)";
        :>> dcTarget = "medium";
        :>> tsr = "TSR-518";
    }
    action <'SM-40'> transceiverSupervision : SafetyMechanism {
        doc /* Car-side transceiver supervision */
        :>> covers = "transceiver transmitting from reset; bus-off or persistent TX failure while authority is granted";
        :>> dcTarget = "medium";
        :>> tsr = "TSR-508";
    }
    action <'SM-41'> dieTemperatureMonitor : SafetyMechanism {
        doc /* MCU die-temperature monitor */
        :>> covers = "MCU outside its specified temperature range";
        :>> dcTarget = "medium";
        :>> tsr = "TSR-509";
    }
    action <'SM-42'> harnessDetection : SafetyMechanism {
        doc /* Harness orientation and connection detection */
        :>> covers = "harness flipped, not connected or partly inserted; wrong CAN routing or relay pin";
        :>> dcTarget = "medium";
        :>> tsr = "TSR-701";
    }
    action <'SM-43'> accCancelOnFault : SafetyMechanism {
        doc /* ACC cancel on every fault-induced disengagement */
        :>> covers = "driver not told by an independent cue that the item disengaged on a fault";
        :>> dcTarget = "QM (B-sup: SM-23 via TSR-516(c), SM-29)";
        :>> tsr = "TSR-303";
    }
}
