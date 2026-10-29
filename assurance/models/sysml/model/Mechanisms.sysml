package LionDriverMechanisms {
    doc
    /*
     * Safety mechanisms SM-01 to SM-45 of WP-S-03 §6 (catalogue as of version 0.22).
     * Every column of the §6 row is here (SY-05); tools/gen_tables.py writes the table.
     * The elements that perform each mechanism are declared in LionDriverArchitecture
     * (perform statements), following the Element column of WP-S-03 §6.
     */

    private import LionDriverLibrary::*;

    action <'SM-01'> torqueMagnitudeLimit : SafetyMechanism {
        doc /* Torque magnitude limit (speed-dependent) */
        :>> covers = "excessive torque command from SoC";
        :>> dcTarget = "high (for SoC command faults)";
        :>> tsr = ("TSR-101", "TSR-102");
        :>> element = "E-03a";
        :>> status = "Partial";
        :>> latent = "T-SIL each release; table CRC in TSR-503";
    }
    action <'SM-02'> torqueRateLimit : SafetyMechanism {
        doc /* Torque rate and RT-window limit */
        :>> covers = "high-rate torque command";
        :>> dcTarget = "high";
        :>> tsr = "TSR-103";
        :>> element = "E-03a";
        :>> status = "Impl";
        :>> latent = "as SM-01";
    }
    action <'SM-03'> measuredTorqueTracking : SafetyMechanism {
        doc /* Measured-torque tracking */
        :>> covers = "command diverging from EPS output";
        :>> dcTarget = "medium (depends on `0x260` integrity)";
        :>> tsr = "TSR-104";
        :>> element = "E-03a";
        :>> status = "Impl";
        :>> latent = "as SM-01";
    }
    action <'SM-04'> authorityGating : SafetyMechanism {
        doc /* Authority gating (PCM edge, brake, gas, steer request) */
        :>> covers = "actuation when not engaged; no release on driver action";
        :>> dcTarget = "high";
        :>> tsr = ("TSR-105", "TSR-106", "TSR-107", "TSR-203", "TSR-301", "TSR-302", "TSR-303", "TSR-304", "TSR-305", "TSR-306");
        :>> element = "E-03a";
        :>> status = "Impl/Partial";
        :>> latent = "T-SIL; T-VEH at installation (INS-28)";
    }
    action <'SM-05'> driverTorqueOverride : SafetyMechanism {
        doc /* Driver-torque override monitor */
        :>> covers = "actuation opposing driver";
        :>> dcTarget = "medium";
        :>> tsr = ("TSR-304", "TSR-628");
        :>> element = "E-03a";
        :>> status = "New";
        :>> latent = "T-SIL; periodic T-VEH";
    }
    action <'SM-06'> epsStatusMonitor : SafetyMechanism {
        doc /* EPS status monitor */
        :>> covers = "EPS LKA fault while engaged";
        :>> dcTarget = "medium";
        :>> tsr = ("TSR-110", "TSR-607");
        :>> element = "E-03a";
        :>> status = "New at baseline; **Partial** 2026-10-12 (reference build: LKA refused on LKA_STATE fault codes, `epsFault` reported; code set unconfirmed; not verified)";
        :>> latent = "log check";
    }
    action <'SM-07'> longitudinalBounds : SafetyMechanism {
        doc /* Longitudinal bounds and jerk limits */
        :>> covers = "excessive accel/decel or onset";
        :>> dcTarget = "high";
        :>> tsr = ("TSR-201", "TSR-202", "TSR-203", "TSR-204", "TSR-205", "TSR-206", "TSR-207");
        :>> element = "E-03a";
        :>> status = "Partial";
        :>> latent = "T-SIL";
    }
    action <'SM-08'> activeSafeStateFrame : SafetyMechanism {
        doc /* Active safe-state frame */
        :>> covers = "torque persisting after rejection";
        :>> dcTarget = "high";
        :>> tsr = ("TSR-108", "TSR-109");
        :>> element = "E-03a";
        :>> status = "New";
        :>> latent = "T-HIL each release";
    }
    action <'SM-09'> rxTimeout : SafetyMechanism {
        doc /* RX timeout */
        :>> covers = "lost/delayed RX";
        :>> dcTarget = "medium (alone)";
        :>> tsr = "TSR-401";
        :>> element = "E-03a";
        :>> status = "Partial at baseline; **Impl** 2026-10-12 (Toyota RX set, 5 periods at 100 Hz; `0x262` marginal; `0xB4` not in the set; not verified)";
        :>> latent = "T-SIL, FI";
    }
    action <'SM-10'> rxChecksumLength : SafetyMechanism {
        doc /* RX checksum + length */
        :>> covers = "corrupted RX (`0x260`, `0x1D2`)";
        :>> dcTarget = "low (8-bit additive)";
        :>> tsr = "TSR-402";
        :>> element = "E-03a";
        :>> status = "Partial";
        :>> latent = "T-SIL";
    }
    action <'SM-11'> rxPlausibility : SafetyMechanism {
        doc /* RX rate, frozen-content and cross-checks */
        :>> covers = "repeated/inserted/masqueraded RX";
        :>> dcTarget = "medium (combined with SM-09/10)";
        :>> tsr = ("TSR-403", "TSR-404", "TSR-405");
        :>> element = "E-03a";
        :>> status = "New at baseline; **Partial** 2026-10-12 (TSR-405(c) in the reference build; 403, 404, 405(a)(b)(d) open)";
        :>> latent = "LOG, FI";
    }
    action <'SM-12'> heartbeatLiveness : SafetyMechanism {
        doc /* Heartbeat + control-loop liveness */
        :>> covers = "SoC hang, frozen control loop";
        :>> dcTarget = "medium";
        :>> tsr = ("TSR-407", "TSR-409");
        :>> element = "E-03b";
        :>> status = "Partial (2026-10-12: 0.3 s revoke implemented, TSR-409 open)";
        :>> latent = "FI";
    }
    action <'SM-13'> commandFreshness : SafetyMechanism {
        doc /* Command-frame freshness */
        :>> covers = "SoC stops sending commands";
        :>> dcTarget = "high";
        :>> tsr = ("TSR-408", "TSR-614");
        :>> element = "E-03a/b";
        :>> status = "New at baseline; **Partial** 2026-10-16 (TSR-408 in the reference build, opendbc `273f44e`, not verified on hardware; TSR-614 not met)";
        :>> latent = "FI";
    }
    action <'SM-14'> spiIntegrity : SafetyMechanism {
        doc /* SPI CRC + sequence counter + bounds checks */
        :>> covers = "corrupted/stale/oversized SoC transfers";
        :>> dcTarget = "high (with CRC-16/32)";
        :>> tsr = ("TSR-410", "TSR-411", "TSR-412", "TSR-413");
        :>> element = "E-03b";
        :>> status = "Partial";
        :>> latent = "FI";
    }
    action <'SM-15'> independentWatchdog : SafetyMechanism {
        doc /* Independent watchdog */
        :>> covers = "MCU program-flow stall";
        :>> dcTarget = "medium (timeout only) / high (window + logical checkpoint)";
        :>> tsr = "TSR-501";
        :>> element = "E-04a/E-03b";
        :>> status = "New at baseline; **Impl, not verified** 2026-10-12 (IWDG1, window, ≈ 90 ms nominal; LSI tolerance and HIL open)";
        :>> latent = "IWDG reset-path test at defined interval (TSR-515)";
    }
    action <'SM-16'> faultToSafeState : SafetyMechanism {
        doc /* Fault → safe state */
        :>> covers = "any detected platform fault";
        :>> dcTarget = "— (enabler)";
        :>> tsr = ("TSR-406", "TSR-502", "TSR-706");
        :>> element = "E-03b";
        :>> status = "New";
        :>> latent = "FI";
    }
    action <'SM-17'> memoryIntegrity : SafetyMechanism {
        doc /* RAM ECC, flash CRC, register checks */
        :>> covers = "memory/register corruption";
        :>> dcTarget = "high (ECC), medium (register)";
        :>> tsr = "TSR-503";
        :>> element = "E-04a/E-03b";
        :>> status = "Partial";
        :>> latent = "start-up CRC; ECC event counting";
    }
    action <'SM-18'> clockMonitor : SafetyMechanism {
        doc /* Clock monitor (CSS + cross-check) */
        :>> covers = "clock loss/drift";
        :>> dcTarget = "medium";
        :>> tsr = "TSR-504";
        :>> element = "E-04a";
        :>> status = "Partial";
        :>> latent = "start-up check";
    }
    action <'SM-19'> supplyMonitor : SafetyMechanism {
        doc /* Supply monitor (BOR, PVD, input voltage) */
        :>> covers = "under/over-voltage";
        :>> dcTarget = "medium";
        :>> tsr = "TSR-505";
        :>> element = "E-04a";
        :>> status = "Unknown";
        :>> latent = "start-up check";
    }
    action <'SM-20'> relayReadback : SafetyMechanism {
        doc /* Relay readback and latch */
        :>> covers = "relay stuck either way";
        :>> dcTarget = "high (with readback)";
        :>> tsr = ("TSR-506", "TSR-710", "TSR-712");
        :>> element = "E-04a/E-05";
        :>> status = "Partial (one direction, indirect)";
        :>> latent = "relay test at start-up (TSR-515)";
    }
    action <'SM-21'> mpuIsolation : SafetyMechanism {
        doc /* MPU isolation */
        :>> covers = "comms handler corrupting safety data";
        :>> dcTarget = "medium";
        :>> tsr = "TSR-507";
        :>> element = "E-04a";
        :>> status = "New";
        :>> latent = "—";
    }
    action <'SM-22'> configurationLock : SafetyMechanism {
        doc /* Configuration lock and command gating */
        :>> covers = "SoC selects wrong mode/param; debug commands";
        :>> dcTarget = "high";
        :>> tsr = ("TSR-511", "TSR-512", "TSR-513", "TSR-514", "TSR-619", "TSR-620");
        :>> element = "E-03b";
        :>> status = "New at baseline; **Partial** 2026-10-12 (TSR-512/513 in the reference build; 511, 514, 619, 620 open)";
        :>> latent = "release-build check (TSR-514), INS-17/23";
    }
    action <'SM-23'> independentSiren : SafetyMechanism {
        doc /* SoC-independent siren */
        :>> covers = "warning when the SoC is lost, on every envelope revocation that is not a driver action, and when a fault-induced ACC cancel has no effect";
        :>> dcTarget = "— (warning)";
        :>> tsr = "TSR-516";
        :>> element = "E-03b/E-04a";
        :>> status = "Partial (2026-10-12: EPS-fault siren after 1 s persistence in the reference build; 2026-10-13: siren when heartbeat loss revokes granted authority, ≈ 0.56 s after the last heartbeat, all builds, panda `c33343b`)";
        :>> latent = "siren test at start-up (TSR-515)";
    }
    action <'SM-24'> relayMalfunctionDetection : SafetyMechanism {
        doc /* Relay malfunction detection (traffic-based) */
        :>> covers = "relay stuck released / camera on car bus";
        :>> dcTarget = "medium";
        :>> tsr = "TSR-710";
        :>> element = "E-03a";
        :>> status = "Impl";
        :>> latent = "INS-27";
    }
    action <'SM-25'> hostFaultClassification : SafetyMechanism {
        doc /* Host fault classification and freshness */
        :>> covers = "stale/invalid inputs on SoC";
        :>> dcTarget = "QM";
        :>> tsr = ("TSR-601", "TSR-602", "TSR-603", "TSR-604", "TSR-606", "TSR-615", "TSR-616");
        :>> element = "E-01";
        :>> status = "Partial";
        :>> latent = "T-SIL";
    }
    action <'SM-26'> driverMonitoring : SafetyMechanism {
        doc /* Driver monitoring */
        :>> covers = "inattention (misuse)";
        :>> dcTarget = "QM (SOTIF)";
        :>> tsr = ("TSR-608", "TSR-609", "TSR-610", "TSR-611", "TSR-612", "TSR-635");
        :>> element = "E-01/E-02";
        :>> status = "Partial";
        :>> latent = "DM validity (TSR-609)";
    }
    action <'SM-27'> excessiveActuationDetector : SafetyMechanism {
        doc /* Excessive-actuation detector */
        :>> covers = "vehicle response beyond 2× limits";
        :>> dcTarget = "QM";
        :>> tsr = "TSR-617";
        :>> element = "E-01";
        :>> status = "Impl";
        :>> latent = "—";
    }
    action <'SM-28'> controllerMargin : SafetyMechanism {
        doc /* Controller margin */
        :>> covers = "operation at envelope boundary";
        :>> dcTarget = "QM";
        :>> tsr = "TSR-605";
        :>> element = "E-01";
        :>> status = "Partial";
        :>> latent = "—";
    }
    action <'SM-29'> engagementFollowsCruise : SafetyMechanism {
        doc /* Engagement follows PCM cruise; revoke on SoC "not engaged" */
        :>> covers = "engagement state of the envelope differs from the PCM or from the SoC";
        :>> dcTarget = "high";
        :>> tsr = ("TSR-307(a)", "TSR-309");
        :>> element = "E-03a/E-03b";
        :>> status = "Impl (309) / Partial (307(a): 2–3 s)";
        :>> latent = "T-SIL; T-VEH (cluster indication, AOU-12)";
    }
    action <'SM-30'> engagementMismatchDetection : SafetyMechanism {
        doc /* Engagement and authority mismatch detection (SoC side) */
        :>> covers = "envelope blocks or never grants authority while engaged; PCM cruise differs from the item's state";
        :>> dcTarget = "QM (B-sup: SM-08, SM-23)";
        :>> tsr = ("TSR-307(b)", "TSR-308", "TSR-621", "TSR-626");
        :>> element = "E-01";
        :>> status = "Partial (2 s; `cruiseMismatch` 6 s, no reaction)";
        :>> latent = "T-SIL, FI";
    }
    action <'SM-31'> hmiLiveness : SafetyMechanism {
        doc /* HMI path liveness and audible minimum */
        :>> covers = "hung render loop, stalled or muted audio, so the take-over request is not perceived";
        :>> dcTarget = "QM (B-sup: SM-23 siren, SM-29 cluster)";
        :>> tsr = ("TSR-622", "TSR-623", "TSR-627");
        :>> element = "E-01 (HMI)";
        :>> status = "Partial (crash only)";
        :>> latent = "FI; volume check at engagement";
    }
    action <'SM-32'> boundedItemDeceleration : SafetyMechanism {
        doc /* Announced, bounded item-initiated deceleration */
        :>> covers = "deceleration not caused by traffic (DM no-response, soft disable) applied without warning or as a step";
        :>> dcTarget = "QM (B-sup: SM-07)";
        :>> tsr = "TSR-624";
        :>> element = "E-01";
        :>> status = "Partial";
        :>> latent = "T-SIL";
    }
    action <'SM-33'> fcwInputFreshness : SafetyMechanism {
        doc /* FCW input freshness and false-alarm rate */
        :>> covers = "FCW from stale or invalid inputs; false FCW causing reflex braking";
        :>> dcTarget = "ASIL A on QM element (open, WP-C-04 OI-9)";
        :>> tsr = "TSR-625";
        :>> element = "E-01";
        :>> status = "Partial";
        :>> latent = "T-SIL; LOG fleet false-rate monitoring";
    }
    action <'SM-34'> accFaultReaction : SafetyMechanism {
        doc /* PCM ACC-fault reaction */
        :>> covers = "PCM does not execute ACC (ACC or cruise fault)";
        :>> dcTarget = "QM (B-sup: SM-29)";
        :>> tsr = "TSR-618";
        :>> element = "E-01";
        :>> status = "Impl";
        :>> latent = "T-SIL";
    }
    action <'SM-35'> forwardingSupervision : SafetyMechanism {
        doc /* Forwarding with fixed block list and forwarding supervision */
        :>> covers = "camera-side frames lost, delayed or altered; block list wrong";
        :>> dcTarget = "high (block list, design); medium (overflow counting)";
        :>> tsr = ("TSR-704", "TSR-707", "TSR-711");
        :>> element = "E-03a/E-03b";
        :>> status = "Impl (704) / Not verified (707) / Not impl (711)";
        :>> latent = "T-HIL each release";
    }
    action <'SM-36'> pcsTxGate : SafetyMechanism {
        doc /* PCS and DSU message TX gate */
        :>> covers = "item originates or alters frames used by the stock PCS";
        :>> dcTarget = "high (when implemented)";
        :>> tsr = "TSR-705";
        :>> element = "E-03a";
        :>> status = "**Not met** (GAP-42) at baseline; **Met (reference build)** 2026-10-12 (other builds keep `0x411`; not verified on hardware)";
        :>> latent = "T-SIL";
    }
    action <'SM-37'> stockAebIndication : SafetyMechanism {
        doc /* Stock AEB/FCW event indication */
        :>> covers = "driver not told that the stock system intervened";
        :>> dcTarget = "QM";
        :>> tsr = "TSR-709";
        :>> element = "E-01";
        :>> status = "Impl";
        :>> latent = "—";
    }
    action <'SM-38'> txReadBack : SafetyMechanism {
        doc /* Post-load TX read-back */
        :>> covers = "approved actuation frame altered in FDCAN message RAM, FDCAN core or transceiver";
        :>> dcTarget = "high";
        :>> tsr = "TSR-517";
        :>> element = "E-03b/E-04a";
        :>> status = "New";
        :>> latent = "FI each release";
    }
    action <'SM-39'> txRateSupervision : SafetyMechanism {
        doc /* Per-ID TX rate supervision */
        :>> covers = "actuation frames sent faster than nominal (burst, duplicated frames)";
        :>> dcTarget = "medium";
        :>> tsr = "TSR-518";
        :>> element = "E-03a";
        :>> status = "New at baseline; **Impl (reference build)** 2026-10-12 (budgets to be confirmed on logs; not verified)";
        :>> latent = "T-SIL";
    }
    action <'SM-40'> transceiverSupervision : SafetyMechanism {
        doc /* Car-side transceiver supervision */
        :>> covers = "transceiver transmitting from reset; bus-off or persistent TX failure while authority is granted";
        :>> dcTarget = "medium";
        :>> tsr = "TSR-508";
        :>> element = "E-04a/E-03b";
        :>> status = "Partial";
        :>> latent = "start-up check (TSR-515)";
    }
    action <'SM-41'> dieTemperatureMonitor : SafetyMechanism {
        doc /* MCU die-temperature monitor */
        :>> covers = "MCU outside its specified temperature range";
        :>> dcTarget = "medium";
        :>> tsr = "TSR-509";
        :>> element = "E-04a/E-03b";
        :>> status = "Partial (report only)";
        :>> latent = "start-up check";
    }
    action <'SM-42'> harnessDetection : SafetyMechanism {
        doc /* Harness orientation and connection detection */
        :>> covers = "harness flipped, not connected or partly inserted; wrong CAN routing or relay pin";
        :>> dcTarget = "medium";
        :>> tsr = "TSR-701";
        :>> element = "E-04a/E-05";
        :>> status = "Partial";
        :>> latent = "before the relay is first driven (TSR-515)";
    }
    action <'SM-43'> accCancelOnFault : SafetyMechanism {
        doc /* ACC cancel on every fault-induced disengagement */
        :>> covers = "driver not told by an independent cue that the item disengaged on a fault";
        :>> dcTarget = "QM (B-sup: SM-23 via TSR-516(c), SM-29)";
        :>> tsr = "TSR-303";
        :>> element = "E-01";
        :>> status = "Impl (host)";
        :>> latent = "T-VEH (cluster and PCM cue, AOU-12)";
    }
    action <'SM-44'> startupFaultCodeCheck : SafetyMechanism {
        doc /* Start-up fault-code entry check */
        :>> covers = "engagement with an active EPS or ABS/VSC fault code stored at start-up, or with the read incomplete";
        :>> dcTarget = "QM";
        :>> tsr = "TSR-629";
        :>> element = "E-01";
        :>> status = "Impl (host)";
        :>> latent = "T-VEH (VS-SQ-20: whether the reference EPS and ABS/VSC answer UDS 0x19)";
    }
    action <'SM-45'> stockAebStandDown : SafetyMechanism {
        doc /* Stock-AEB stand-down */
        :>> covers = "positive acceleration requested while the stock system brakes for an AEB event";
        :>> dcTarget = "QM (B-sup: PCM AEB priority, AOU-04R)";
        :>> tsr = "TSR-713";
        :>> element = "E-01";
        :>> status = "Impl (host, opendbc)";
        :>> latent = "T-VEH (AOU-04R)";
    }
}
