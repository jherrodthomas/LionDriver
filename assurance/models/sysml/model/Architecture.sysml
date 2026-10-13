package LionDriverArchitecture {
    doc
    /*
     * Structure of LD-SDA in its reference configuration (Toyota Corolla E210, TSS 2.0,
     * comma device with the panda safety MCU): the item, its components E-01 to E-05,
     * their parts and software units, the ports through which they interact, and the
     * elements outside the item.
     *
     * Copied from WP-C-01 §3, WP-S-03 §3 and §8 and WP-W-03 §3.1 and §4.1, which stay the
     * documents of record. tools/check_model.py fails when this model and those tables
     * disagree. Status: draft, AI-assisted (Claude), not reviewed.
     */

    private import LionDriverLibrary::*;
    private import ScalarValues::*;
    private import LionDriverMechanisms::*;

    // ================================================================== E-01

    part def SocSoftware :> SoftwareElement {
        doc /* openpilot processes on AGNOS Linux on the Qualcomm SoC (WP-S-03 §3.1, §8). */
        @Source { workProduct = "WP-S-03"; clause = "§3.1, §8"; paths = "openpilot/system/manager/process_config.py:70-121"; }

        part <'host.pandad'> pandad : SoftwareElement {
            doc /* Firmware check and flash, SPI link, CAN in and out, heartbeat, safety-mode set. */
            @Safety { integrity = Integrity::QMBsup; label = "QM (B-sup); FFI interface"; }
            @Source { workProduct = "WP-W-03"; clause = "§4.1"; paths = "openpilot/selfdrive/pandad/"; }
            port spi : SpiPort;
            port bootControl : GpioPort;
        }
        part <'host.card'> card : SoftwareElement {
            doc /* CAN parse to carState; carControl to sendcan; CarParams and fingerprint. */
            @Safety { integrity = Integrity::QMBsup; label = "QM (B-sup)"; }
            @Source { workProduct = "WP-W-03"; clause = "§4.1"; paths = ("openpilot/selfdrive/car/card.py", "opendbc/car/toyota/"); }
        }
        part <'host.controlsd'> controlsd : SoftwareElement {
            doc /* Lateral and longitudinal control law. */
            @Safety { integrity = Integrity::QMBsup; label = "QM (B-sup)"; }
            @Source { workProduct = "WP-W-03"; clause = "§4.1"; paths = "openpilot/selfdrive/controls/controlsd.py"; }
        }
        part <'host.selfdrived'> selfdrived : SoftwareElement {
            doc /* Engagement state machine, event classification, alerts. */
            @Safety { integrity = Integrity::QMBsup; label = "QM (B-sup)"; }
            @Source { workProduct = "WP-W-03"; clause = "§4.1"; paths = "openpilot/selfdrive/selfdrived/"; }
        }
        part <'host.plannerd'> plannerd : SoftwareElement {
            doc /* Longitudinal plan. */
            @Safety { integrity = Integrity::QM; label = "QM (SOTIF)"; }
            @Source { workProduct = "WP-W-03"; clause = "§4.1"; paths = "openpilot/selfdrive/controls/plannerd.py"; }
        }
        part <'host.radard'> radard : SoftwareElement {
            doc /* Lead fusion. */
            @Safety { integrity = Integrity::QM; label = "QM (SOTIF)"; }
            @Source { workProduct = "WP-W-03"; clause = "§4.1"; paths = "openpilot/selfdrive/controls/radard.py"; }
        }
        part <'host.modeld'> modeld : SoftwareElement {
            doc /* Runs the driving model (E-02). */
            @Safety { integrity = Integrity::QM; label = "QM (SOTIF / PAS 8800)"; }
            @Source { workProduct = "WP-W-03"; clause = "§4.1"; paths = "openpilot/selfdrive/modeld/modeld.py"; }
            port roadImages : ImagePort;
        }
        part <'host.dm'> dm : SoftwareElement {
            doc /* Driver monitoring: dmonitoringmodeld runs the DM model (E-02), dmonitoringd applies the policy. */
            @Safety { integrity = Integrity::QM; label = "QM (SOTIF)"; }
            @Source { workProduct = "WP-W-03"; clause = "§4.1"; paths = ("openpilot/selfdrive/modeld/dmonitoringmodeld.py", "openpilot/selfdrive/monitoring/"); }
            port driverImages : ImagePort;
        }
        part <'host.hmi'> hmi : SoftwareElement {
            doc /* ui and soundd: display and audible alerts. */
            @Safety { integrity = Integrity::QMBsup; label = "QM (B-sup)"; }
            @Source { workProduct = "WP-W-03"; clause = "§4.1"; }
            port alerts : HmiPort;
        }
        part <'host.manager'> manager : SoftwareElement {
            doc /* Process start and stop by run condition. */
            @Safety { integrity = Integrity::QM; label = "QM"; }
            @Source { workProduct = "WP-W-03"; clause = "§4.1"; paths = "openpilot/system/manager/"; }
        }
        part <'host.cereal'> cereal : SoftwareElement {
            doc /* Publish and subscribe, alive, valid and frequency checks. No authentication (GAP-20). */
            @Safety { integrity = Integrity::QM; label = "QM"; }
            @Source { workProduct = "WP-W-03"; clause = "§4.1"; paths = ("openpilot/cereal/", "msgq_repo/"); }
        }
        part estimators : SoftwareElement {
            doc /* locationd, calibrationd, paramsd, torqued, lagd, sensord, camerad: pose, calibration, vehicle parameters and sensors. */
            @Safety { integrity = Integrity::QM; label = "QM inputs"; }
            @Source { workProduct = "WP-S-03"; clause = "§8"; }
            port sensors : SensorPort;
        }
        part hardwared : SoftwareElement {
            doc /* Thermal and power management; deviceState.started gates onroad processes. */
            @Safety { integrity = Integrity::QM; label = "Indirect (onroad gating)"; }
            @Source { workProduct = "WP-S-03"; clause = "§8"; }
        }
        part remoteAndLogging : SoftwareElement {
            doc /* loggerd, uploader, athenad, updated, webrtcd and the other non-driving processes (F-09). Interference sources for FFI. */
            @Safety { integrity = Integrity::QM; label = "No (interference sources for FFI)"; }
            @Source { workProduct = "WP-S-03"; clause = "§8"; }
            port network : NetworkPort;
        }
    }

    // ================================================================== E-02

    part def MlModels :> MlElement {
        doc /* Driving model and driver monitoring model (LFS artefacts). */
        @Source { workProduct = "WP-C-01"; clause = "§3.1"; paths = "openpilot/selfdrive/modeld/models/"; }
        part drivingModel : MlElement {
            doc /* Camera-based driving model; executed by host.modeld. */
            @Safety { integrity = Integrity::QM; label = "QM (SOTIF / PAS 8800)"; }
        }
        part dmModel : MlElement {
            doc /* Driver monitoring model; executed by dmonitoringmodeld (host.dm). */
            @Safety { integrity = Integrity::QM; label = "QM (SOTIF / PAS 8800)"; }
        }
    }

    // ================================================================== E-03

    part def SafetyLayer :> SoftwareElement {
        doc /* opendbc safety core and Toyota mode, compiled into the panda firmware (WP-W-03 §3.1). */
        @Source { workProduct = "WP-W-03"; clause = "§3.1"; paths = "opendbc_repo/opendbc/safety/"; }

        part <'panda.safety.core'> core : SoftwareElement {
            doc /* Hook dispatch, RX checks and timeout, authority controls_allowed with grant on the PCM rising edge. */
            @Unit { id = "U-SAF-CORE"; build = Build::both; }
            @Safety { integrity = Integrity::BDagger; label = "B‡"; }
            part <'panda.safety.core.rx_engagement'> rxEngagement : SoftwareElement {
                doc /* rx_timeout_periods and rx_checks_allow_engagement: no grant while an RX check lags or is invalid. */
                @Unit { id = "U-SAF-CORE"; build = Build::both; }
                @Safety { integrity = Integrity::BDagger; label = "B‡"; }
            }
            part <'panda.safety.core.tx_rate_check'> txRateCheck : SoftwareElement {
                doc /* Per-ID TX rate budget over a sliding 250 ms window. */
                @Unit { id = "U-SAF-CORE"; build = Build::reference; }
                @Safety { integrity = Integrity::BDagger; label = "B‡"; }
            }
        }
        part <'panda.safety.lateral'> lateral : SoftwareElement {
            doc /* Torque limit, rate, measured-torque, RT window and steer-request tolerance. */
            @Unit { id = "U-SAF-LAT"; build = Build::both; }
            @Safety { integrity = Integrity::BDagger; label = "B‡"; }
        }
        part <'panda.safety.longitudinal'> longitudinal : SoftwareElement {
            doc /* Longitudinal allowed, acceleration bounds, inactive value. */
            @Unit { id = "U-SAF-LONG"; build = Build::both; }
            @Safety { integrity = Integrity::B; label = "B"; }
        }
        part <'panda.safety.helpers'> helpers : SoftwareElement {
            doc /* Macros, CRC8, message matching, timestamps, interpolation, safety_config. */
            @Unit { id = "U-SAF-HELP"; build = Build::both; }
            @Safety { integrity = Integrity::BDagger; label = "B‡"; }
        }
        part <'panda.safety.toyota'> toyota : SoftwareElement {
            doc /* Toyota RX parsing, TX checks, limits, init and parameter decoding; hook table toyota_hooks. */
            @Unit { id = "U-SAF-TOY"; build = Build::both; }
            @Safety { integrity = Integrity::BDagger; label = "B‡"; }
            part <'panda.safety.toyota.eps_fault'> epsFault : SoftwareElement {
                doc /* Decodes EPS_STATUS.LKA_STATE into safety_eps_fault; refuses torque while it is set. */
                @Unit { id = "U-SAF-TOY"; build = Build::reference; }
                @Safety { integrity = Integrity::BDagger; label = "B‡"; }
            }
            part <'panda.safety.toyota.ref_rx_set'> refRxSet : SoftwareElement {
                doc /* Adds 0x262 and 0x1D3 to the RX checks. */
                @Unit { id = "U-SAF-TOY"; build = Build::reference; }
                @Safety { integrity = Integrity::BDagger; label = "B‡"; }
            }
            part <'panda.safety.toyota.cruise_main'> cruiseMain : SoftwareElement {
                doc /* CRUISE_ACTIVE with MAIN_ON = 0 revokes authority. */
                @Unit { id = "U-SAF-TOY"; build = Build::reference; }
                @Safety { integrity = Integrity::BDagger; label = "B‡"; }
            }
            part <'panda.safety.toyota.tx_budgets'> txBudgets : SoftwareElement {
                doc /* TX rate rows for the non-SecOC configurations. */
                @Unit { id = "U-SAF-TOY"; build = Build::reference; }
                @Safety { integrity = Integrity::BDagger; label = "B‡"; }
            }
        }
        part <'panda.safety.defaults'> defaults : SoftwareElement {
            doc /* SILENT, NOOUTPUT and ELM327 hooks. */
            @Unit { id = "U-SAF-DEF"; build = Build::both; }
            @Safety { integrity = Integrity::BDagger; label = "B‡ (safe-state modes)"; }
        }
        part <'panda.safety.ignition'> ignition : SoftwareElement {
            doc /* CAN ignition detection. */
            @Unit { id = "U-SAF-IGN"; build = Build::both; }
            @Safety { integrity = Integrity::B; label = "B"; }
        }
        part <'panda.safety.other_modes'> otherModes : SoftwareElement {
            doc /* Other brands' modes; linked in both builds, not selectable by the host in the reference build. */
            @Safety { integrity = Integrity::QM; label = "Interference source; dead code"; }
        }
    }

    part def PlatformFirmware :> SoftwareElement {
        doc /* panda main loop, tick handler, CAN and SPI drivers, comms handlers, harness and relay driver, fault handling, bootstub. */
        @Source { workProduct = "WP-W-03"; clause = "§3.1"; paths = "panda/board/"; }

        part <'panda.main'> main : SoftwareElement {
            doc /* Start-up, set_safety_mode, 8 Hz tick. */
            @Unit { id = "U-PND-MAIN"; build = Build::both; }
            @Safety { integrity = Integrity::BDagger; label = "B‡"; }
            part <'panda.main.safety_task'> safetyTask : SoftwareElement {
                doc /* TIM4 safety task at 100 Hz: safety_tick, heartbeat monitor, IWDG feed. */
                @Unit { id = "U-PND-MAIN"; build = Build::both; }
                @Safety { integrity = Integrity::BDagger; label = "B‡"; }
            }
        }
        part <'panda.drivers.heartbeat_monitor'> heartbeatMonitor : SoftwareElement {
            doc /* Revokes authority after 0.3 s without a heartbeat (SWSR-407). */
            @Unit { id = "U-PND-MAIN"; build = Build::both; }
            @Safety { integrity = Integrity::BDagger; label = "B‡"; }
        }
        part <'panda.drivers.heartbeat_siren'> heartbeatSiren : SoftwareElement {
            doc /* Siren for 3 s when the heartbeat monitor revokes authority. */
            @Unit { id = "U-PND-HK"; build = Build::both; }
            @Safety { integrity = Integrity::B; label = "B"; }
        }
        part <'panda.drivers.eps_fault_siren'> epsFaultSiren : SoftwareElement {
            doc /* Siren once the EPS fault has persisted 1 s while authority is granted. */
            @Unit { id = "U-PND-HK"; build = Build::both; }
            @Safety { integrity = Integrity::B; label = "B"; }
        }
        part <'panda.drivers.hw_watchdog'> hwWatchdog : SoftwareElement {
            doc /* IWDG1 window watchdog, started on the first relay drive. */
            @Unit { id = "U-PND-FLT"; build = Build::both; }
            @Safety { integrity = Integrity::BDagger; label = "B‡"; }
        }
        part <'panda.drivers.irq_priorities'> irqPriorities : SoftwareElement {
            doc /* Explicit priority for every enabled IRQ (SWSR-519 partial). */
            @Unit { id = "U-PND-PLAT"; build = Build::both; }
            @Safety { integrity = Integrity::BDagger; label = "B‡"; }
        }
        part <'panda.reference_lock'> referenceLock : SoftwareElement {
            doc /* Limits 0xdc to the reference modes; refuses 0xdf and the softloader in car modes. */
            @Unit { id = "U-PND-COMMS"; build = Build::reference; }
            @Safety { integrity = Integrity::BDagger; label = "B‡"; }
        }
        part <'panda.comms'> comms : SoftwareElement {
            doc /* Control-request dispatcher, health packet, CAN stream packing and unpacking. */
            @Unit { id = "U-PND-COMMS"; build = Build::both; }
            @Safety { integrity = Integrity::BDagger; label = "B‡ (it calls envelope APIs and can change configuration)"; }
        }
        part <'panda.drivers.spi'> spi : SoftwareElement {
            doc /* SPI framing, XOR checksum, DMA control. */
            @Unit { id = "U-PND-SPI"; build = Build::both; }
            @Safety { integrity = Integrity::BDagger; label = "B‡"; }
            port host : SpiPort;
        }
        part <'panda.drivers.usb'> usb : SoftwareElement {
            doc /* USB endpoint handling; not needed by the reference device. */
            @Unit { id = "U-PND-USB"; build = Build::both; }
            @Safety { integrity = Integrity::QM; label = "Not needed by the reference device (SPI); interference source (OI-3)"; }
        }
        part <'panda.drivers.fdcan'> fdcan : SoftwareElement {
            doc /* CAN RX ISR with the forward and RX hooks; TX path through the TX hook. */
            @Unit { id = "U-PND-FDCAN"; build = Build::both; }
            @Safety { integrity = Integrity::BDagger; label = "B‡"; }
            port bus0 : CanPort;
            port bus1 : CanPort;
            port bus2 : CanPort;
        }
        part <'panda.drivers.harness'> harnessDriver : SoftwareElement {
            doc /* Relay drive, orientation and ignition sense. */
            @Unit { id = "U-PND-HARN"; build = Build::both; }
            @Safety { integrity = Integrity::BDagger; label = "B‡ (blocking) / B (PCS restore)"; }
        }
        part <'panda.sys.faults'> faults : SoftwareElement {
            doc /* Fault recording and the software watchdog. */
            @Unit { id = "U-PND-FLT"; build = Build::both; }
            @Safety { integrity = Integrity::BDagger; label = "B‡ (report-only)"; }
        }
        part <'panda.sys.power_saving'> powerSaving : SoftwareElement {
            doc /* Power-save: CAN IRQ and transceiver disable. */
            @Unit { id = "U-PND-PWR"; build = Build::both; }
            @Safety { integrity = Integrity::BDagger; label = "B‡"; }
        }
        part <'panda.drivers.siren'> siren : SoftwareElement {
            doc /* Siren and housekeeping drivers (fan, LED, bootkick, clock source, PWM, ADC). */
            @Unit { id = "U-PND-HK"; build = Build::both; }
            @Safety { integrity = Integrity::B; label = "Mixed: siren B, rest QM"; }
            port audio : HmiPort;
        }
        part <'panda.platform'> platform : SoftwareElement {
            doc /* Reset, exception handlers, clocks, vectors, timers, critical sections. */
            @Unit { id = "U-PND-PLAT"; build = Build::both; }
            @Safety { integrity = Integrity::BDagger; label = "B‡"; }
        }
        part <'panda.bootstub'> bootstub : SoftwareElement {
            doc /* Signature check and soft flasher. */
            @Unit { id = "U-PND-BOOT"; build = Build::both; }
            @Safety { integrity = Integrity::BDagger; label = "B‡ + CS"; }
        }
    }

    part def SafetyMcuFirmware :> SoftwareElement {
        doc /* panda firmware with the opendbc safety Toyota mode (WP-C-01 §3.1). */
        @Source { workProduct = "WP-S-03"; clause = "§3.1"; }
        part <'E-03a'> safetyLayer : SafetyLayer {
            @Safety { integrity = Integrity::BDagger; label = "B‡"; }
            perform LionDriverMechanisms::torqueMagnitudeLimit;
            perform LionDriverMechanisms::torqueRateLimit;
            perform LionDriverMechanisms::measuredTorqueTracking;
            perform LionDriverMechanisms::authorityGating;
            perform LionDriverMechanisms::driverTorqueOverride;
            perform LionDriverMechanisms::epsStatusMonitor;
            perform LionDriverMechanisms::longitudinalBounds;
            perform LionDriverMechanisms::activeSafeStateFrame;
            perform LionDriverMechanisms::rxTimeout;
            perform LionDriverMechanisms::rxChecksumLength;
            perform LionDriverMechanisms::rxPlausibility;
            perform LionDriverMechanisms::commandFreshness;
            perform LionDriverMechanisms::relayMalfunctionDetection;
            perform LionDriverMechanisms::engagementFollowsCruise;
            perform LionDriverMechanisms::forwardingSupervision;
            perform LionDriverMechanisms::pcsTxGate;
            perform LionDriverMechanisms::txRateSupervision;
        }
        part <'E-03b'> platformFirmware : PlatformFirmware {
            @Safety { integrity = Integrity::BDagger; label = "B‡"; }
            perform LionDriverMechanisms::heartbeatLiveness;
            perform LionDriverMechanisms::commandFreshness;
            perform LionDriverMechanisms::spiIntegrity;
            perform LionDriverMechanisms::independentWatchdog;
            perform LionDriverMechanisms::faultToSafeState;
            perform LionDriverMechanisms::memoryIntegrity;
            perform LionDriverMechanisms::configurationLock;
            perform LionDriverMechanisms::independentSiren;
            perform LionDriverMechanisms::engagementFollowsCruise;
            perform LionDriverMechanisms::forwardingSupervision;
            perform LionDriverMechanisms::txReadBack;
            perform LionDriverMechanisms::transceiverSupervision;
            perform LionDriverMechanisms::dieTemperatureMonitor;
        }
    }

    // ================================================================== E-04

    part def SafetyMcuHardware :> HardwareElement {
        doc /* STM32H7 with clock, supply, memories, SPI4, FDCAN1-3, ADC, GPIO, DAC and codec siren path (WP-S-03 §3.1). */
        @Source { workProduct = "WP-S-03"; clause = "§3.1"; }
        part clock : HardwareElement;
        part supply : HardwareElement;
        part memories : HardwareElement { doc /* RAM with ECC and flash. */ }
        part <'SPI4'> spi4 : HardwareElement;
        part fdcanPeripherals : HardwareElement { doc /* FDCAN1 to FDCAN3. */ }
        part adc : HardwareElement;
        part gpio : HardwareElement {
            port relayDrive : GpioPort;
            port bootPins : GpioPort;
        }
        part sirenPath : HardwareElement {
            doc /* DAC and codec path to the speaker. */
        }
        part <'IWDG1'> iwdg1 : HardwareElement {
            doc /* Independent window watchdog. */
        }
    }

    part def DeviceHardwareRest :> HardwareElement {
        doc /* SoC, cameras, IMU, display, speaker, power supply, enclosure (WP-S-03 §3.1, WP-C-01 §3.1). */
        @Source { workProduct = "WP-C-01"; clause = "§3.1"; }
        part soc : HardwareElement { doc /* Qualcomm SoC running AGNOS Linux. */ }
        part roadCameras : HardwareElement {
            doc /* Wide and narrow road-facing cameras. */
            port scene : ImagePort;
            port images : ImagePort;
        }
        part driverCamera : HardwareElement {
            doc /* Driver-facing IR camera. */
            port scene : ImagePort;
            port images : ImagePort;
        }
        part imuGnss : HardwareElement {
            doc /* IMU and GNSS. */
            port messages : SensorPort;
        }
        part display : HardwareElement { port screen : HmiPort; }
        part speaker : HardwareElement { port sound : HmiPort; }
        part canTransceivers : HardwareElement;
        part powerSupply : HardwareElement { port input : PowerPort; }
        part enclosure : HardwareElement { doc /* Enclosure and windscreen mount. */ }
    }

    part def DeviceHardware :> HardwareElement {
        doc /* The comma device (WP-C-01 §3.1). */
        @Source { workProduct = "WP-S-03"; clause = "§3.1"; }
        part <'E-04a'> safetyMcu : SafetyMcuHardware {
            @Safety { integrity = Integrity::BDagger; label = "B‡"; }
            perform LionDriverMechanisms::independentWatchdog;
            perform LionDriverMechanisms::memoryIntegrity;
            perform LionDriverMechanisms::clockMonitor;
            perform LionDriverMechanisms::supplyMonitor;
            perform LionDriverMechanisms::relayReadback;
            perform LionDriverMechanisms::mpuIsolation;
            perform LionDriverMechanisms::independentSiren;
            perform LionDriverMechanisms::txReadBack;
            perform LionDriverMechanisms::transceiverSupervision;
            perform LionDriverMechanisms::dieTemperatureMonitor;
            perform LionDriverMechanisms::harnessDetection;
        }
        part <'E-04b'> restOfDevice : DeviceHardwareRest {
            @Safety { integrity = Integrity::QM; label = "QM"; }
        }
    }

    // ================================================================== E-05

    part def Harness :> HardwareElement {
        doc /* Toyota TSS2 harness with intercept relay between the forward camera and the vehicle CAN. */
        @Source { workProduct = "WP-S-03"; clause = "§3.1"; }
        part wiring : HardwareElement {
            port power : PowerPort;
        }
        part interceptRelay : HardwareElement {
            doc /* Released: camera and vehicle CAN are linked directly (AOU-13). */
            port carSide : CanPort;
            port cameraSide : CanPort;
            port drive : GpioPort;
        }
    }

    // ================================================================== the item

    part def LdSda :> Element {
        doc /* LD-SDA, Supervised Driving Assistance: an aftermarket SAE Level 2 retrofit (WP-C-01 §1). */
        @Source { workProduct = "WP-C-01"; clause = "§1, §3.1"; }
        @Boundary { scope = Scope::inside; }

        part <'E-01'> socSoftware : SocSoftware {
            @Safety { integrity = Integrity::QM; label = "QM"; }
            perform LionDriverMechanisms::hostFaultClassification;
            perform LionDriverMechanisms::driverMonitoring;
            perform LionDriverMechanisms::excessiveActuationDetector;
            perform LionDriverMechanisms::controllerMargin;
            perform LionDriverMechanisms::engagementMismatchDetection;
            perform LionDriverMechanisms::hmiLiveness;
            perform LionDriverMechanisms::boundedItemDeceleration;
            perform LionDriverMechanisms::fcwInputFreshness;
            perform LionDriverMechanisms::accFaultReaction;
            perform LionDriverMechanisms::stockAebIndication;
            perform LionDriverMechanisms::accCancelOnFault;
        }
        part <'E-02'> mlModels : MlModels {
            @Safety { integrity = Integrity::QM; label = "QM (SOTIF/PAS 8800)"; }
            perform LionDriverMechanisms::driverMonitoring;
        }
        part <'E-03'> safetyFirmware : SafetyMcuFirmware {
            @Safety { integrity = Integrity::BDagger; label = "B‡"; }
        }
        part <'E-04'> deviceHardware : DeviceHardware {
            @Safety { integrity = Integrity::BDagger; label = "E-04a B‡, E-04b QM"; }
        }
        part <'E-05'> harness : Harness {
            @Safety { integrity = Integrity::BDagger; label = "B (PCS restore), B‡ (blocking)"; }
            perform LionDriverMechanisms::relayReadback;
            perform LionDriverMechanisms::harnessDetection;
        }

        // ---------------------------------------------------------- where software runs

        allocate socSoftware to deviceHardware.restOfDevice.soc;
        allocate mlModels to deviceHardware.restOfDevice.soc;
        allocate safetyFirmware to deviceHardware.safetyMcu;
        allocate mlModels.drivingModel to socSoftware.modeld;
        allocate mlModels.dmModel to socSoftware.dm;

        // ---------------------------------------------------------- interfaces inside the item

        interface ifSpi : SpiLink
            connect host ::> socSoftware.pandad.spi to device ::> safetyFirmware.platformFirmware.spi.host {
            @InterfaceId { id = "IF-04"; tsr = ("TSR-407", "TSR-408", "TSR-409", "TSR-410", "TSR-411", "TSR-412", "TSR-413", "TSR-511", "TSR-512", "TSR-513", "TSR-514"); }
            @FfiClaim { claims = ("FFI-1", "FFI-2", "FFI-4", "FFI-5"); }
        }
        interface ifBoot : GpioLink
            connect driver ::> socSoftware.pandad.bootControl to receiver ::> deviceHardware.safetyMcu.gpio.bootPins {
            doc /* STM_BOOT0 and STM_RST_N. */
            @InterfaceId { id = "IF-04b"; tsr = "TSR-511"; }
            @FfiClaim { claims = "FFI-3"; }
        }
        interface ifRelay : GpioLink
            connect driver ::> deviceHardware.safetyMcu.gpio.relayDrive to receiver ::> harness.interceptRelay.drive {
            doc /* Relay GPIO and harness (SBU) sense. */
            @InterfaceId { id = "IF-10"; tsr = ("TSR-506", "TSR-701"); }
        }
        interface roadImages : ImageLink
            connect source ::> deviceHardware.restOfDevice.roadCameras.images to target ::> socSoftware.modeld.roadImages {
            doc /* VisionIPC: road images to the driving model (E-02, run by host.modeld). */
            @InterfaceId { id = "IF-05"; }
        }
        interface driverImages : ImageLink
            connect source ::> deviceHardware.restOfDevice.driverCamera.images to target ::> socSoftware.dm.driverImages {
            doc /* VisionIPC: driver images to the DM model (E-02, run by host.dm). */
            @InterfaceId { id = "IF-06"; }
        }
        interface sensorMessages : SensorLink
            connect source ::> deviceHardware.restOfDevice.imuGnss.messages to target ::> socSoftware.estimators.sensors;
        interface hmiDisplay : HmiLink
            connect source ::> socSoftware.hmi.alerts to target ::> deviceHardware.restOfDevice.display.screen {
            @InterfaceId { id = "IF-07"; tsr = "TSR-606"; }
        }
        interface hmiSound : HmiLink
            connect source ::> socSoftware.hmi.alerts to target ::> deviceHardware.restOfDevice.speaker.sound {
            @InterfaceId { id = "IF-07"; tsr = "TSR-606"; }
        }

        // ---------------------------------------------------------- cereal services (WP-S-03 §9)
        // Transcribed from WP-S-03 §9 on 2026-10-13; edit here and in §9 together.
        connection canPandadToCard : DataFlow
            connect publisher ::> socSoftware.pandad to subscriber ::> socSoftware.card {
            :>> service = "can";
            :>> rateHz = 100.0;
        }
        connection sendcanCardToPandad : DataFlow
            connect publisher ::> socSoftware.card to subscriber ::> socSoftware.pandad {
            :>> service = "sendcan";
            :>> rateHz = 100.0;
        }
        connection pandaStatesPandadToSelfdrived : DataFlow
            connect publisher ::> socSoftware.pandad to subscriber ::> socSoftware.selfdrived {
            :>> service = "pandaStates";
            :>> rateHz = 10.0;
        }
        connection pandaStatesPandadToCard : DataFlow
            connect publisher ::> socSoftware.pandad to subscriber ::> socSoftware.card {
            :>> service = "pandaStates";
            :>> rateHz = 10.0;
        }
        connection carStateCardToSelfdrived : DataFlow
            connect publisher ::> socSoftware.card to subscriber ::> socSoftware.selfdrived {
            :>> service = "carState";
            :>> rateHz = 100.0;
        }
        connection carStateCardToControlsd : DataFlow
            connect publisher ::> socSoftware.card to subscriber ::> socSoftware.controlsd {
            :>> service = "carState";
            :>> rateHz = 100.0;
        }
        connection carControlControlsdToCard : DataFlow
            connect publisher ::> socSoftware.controlsd to subscriber ::> socSoftware.card {
            :>> service = "carControl";
            :>> rateHz = 100.0;
        }
        connection carOutputCardToControlsd : DataFlow
            connect publisher ::> socSoftware.card to subscriber ::> socSoftware.controlsd {
            :>> service = "carOutput";
            :>> rateHz = 100.0;
        }
        connection selfdriveStateSelfdrivedToControlsd : DataFlow
            connect publisher ::> socSoftware.selfdrived to subscriber ::> socSoftware.controlsd {
            :>> service = "selfdriveState";
            :>> rateHz = 100.0;
        }
        connection selfdriveStateSelfdrivedToPandad : DataFlow
            connect publisher ::> socSoftware.selfdrived to subscriber ::> socSoftware.pandad {
            :>> service = "selfdriveState";
            :>> rateHz = 100.0;
        }
        connection onroadEventsSelfdrivedToControlsd : DataFlow
            connect publisher ::> socSoftware.selfdrived to subscriber ::> socSoftware.controlsd {
            :>> service = "onroadEvents";
            :>> rateHz = 1.0;
        }
        connection onroadEventsSelfdrivedToCard : DataFlow
            connect publisher ::> socSoftware.selfdrived to subscriber ::> socSoftware.card {
            :>> service = "onroadEvents";
            :>> rateHz = 1.0;
        }
        connection modelV2ModeldToControlsd : DataFlow
            connect publisher ::> socSoftware.modeld to subscriber ::> socSoftware.controlsd {
            :>> service = "modelV2";
            :>> rateHz = 20.0;
        }
        connection modelV2ModeldToPlannerd : DataFlow
            connect publisher ::> socSoftware.modeld to subscriber ::> socSoftware.plannerd {
            :>> service = "modelV2";
            :>> rateHz = 20.0;
        }
        connection modelV2ModeldToSelfdrived : DataFlow
            connect publisher ::> socSoftware.modeld to subscriber ::> socSoftware.selfdrived {
            :>> service = "modelV2";
            :>> rateHz = 20.0;
        }
        connection longitudinalPlanPlannerdToControlsd : DataFlow
            connect publisher ::> socSoftware.plannerd to subscriber ::> socSoftware.controlsd {
            :>> service = "longitudinalPlan";
            :>> rateHz = 20.0;
        }
        connection radarStateRadardToPlannerd : DataFlow
            connect publisher ::> socSoftware.radard to subscriber ::> socSoftware.plannerd {
            :>> service = "radarState";
            :>> rateHz = 20.0;
        }
        connection radarStateRadardToSelfdrived : DataFlow
            connect publisher ::> socSoftware.radard to subscriber ::> socSoftware.selfdrived {
            :>> service = "radarState";
            :>> rateHz = 20.0;
        }
        connection driverMonitoringStateDmToSelfdrived : DataFlow
            connect publisher ::> socSoftware.dm to subscriber ::> socSoftware.selfdrived {
            :>> service = "driverMonitoringState";
            :>> rateHz = 20.0;
        }
        connection driverMonitoringStateDmToControlsd : DataFlow
            connect publisher ::> socSoftware.dm to subscriber ::> socSoftware.controlsd {
            :>> service = "driverMonitoringState";
            :>> rateHz = 20.0;
        }
        connection extrinsicsCalibrationEstimatorsToControlsd : DataFlow
            connect publisher ::> socSoftware.estimators to subscriber ::> socSoftware.controlsd {
            :>> service = "extrinsicsCalibration, deviceMotion, vehicleParameters, lateralTorqueParameters, lateralDelay";
            :>> rateHz = 20.0;
        }
        connection deviceStateHardwaredToPandad : DataFlow
            connect publisher ::> socSoftware.hardwared to subscriber ::> socSoftware.pandad {
            :>> service = "deviceState";
            :>> rateHz = 2.0;
        }
        connection deviceStateHardwaredToSelfdrived : DataFlow
            connect publisher ::> socSoftware.hardwared to subscriber ::> socSoftware.selfdrived {
            :>> service = "deviceState";
            :>> rateHz = 2.0;
        }
    }

    // ================================================================== outside the item

    part def VehicleCan :> ExternalElement {
        doc /* Car-side vehicle CAN (panda bus 0). */
        port bus : CanPort;
    }
    part def RadarCan :> ExternalElement {
        doc /* Radar CAN (panda bus 1). */
        port bus : CanPort;
    }

    part def OperationalContext {
        doc /* LD-SDA in the vehicle and its environment (WP-C-01 §3.2, §3.3). */
        @Source { workProduct = "WP-C-01"; clause = "§3.2, §3.3, §3.4"; }

        part ldsda : LdSda;

        part <'EXT-EPS'> eps : ExternalElement {
            doc /* Receives LKA torque requests; reports driver torque, EPS torque and LKA state. */
            @Boundary { scope = Scope::outside; }
            @Safety { integrity = Integrity::AoU; label = "AOU-01, AOU-02"; }
        }
        part <'EXT-PCM'> ecmPcm : ExternalElement {
            doc /* Engine and powertrain ECU: ACC acceleration, permit-braking, cruise state. */
            @Boundary { scope = Scope::outside; }
            @Safety { integrity = Integrity::AoU; label = "AOU-03, AOU-05, AOU-10"; }
        }
        part absVsc : ExternalElement {
            doc /* Brake actuator: wheel speeds and brake-pedal state. */
            @Boundary { scope = Scope::outside; }
            @Safety { integrity = Integrity::AoU; label = "AOU-03, AOU-10"; }
        }
        part <'EXT-CLU'> cluster : ExternalElement {
            doc /* Instrument cluster and cruise stalk: cruise main, set, resume, cancel; LKA HUD. */
            @Boundary { scope = Scope::outside; }
            @Safety { integrity = Integrity::AoU; label = "AOU-05, AOU-12"; }
        }
        part forwardCamera : ExternalElement {
            doc /* Toyota forward camera: LKA and ACC outputs intercepted, PCS outputs forwarded. */
            @Boundary { scope = Scope::outside; }
            @Safety { integrity = Integrity::AoU; label = "AOU-04"; }
            port can : CanPort;
        }
        part forwardRadar : ExternalElement {
            doc /* Toyota forward radar: lead tracks; supports the stock PCS. */
            @Boundary { scope = Scope::outside; }
            @Safety { integrity = Integrity::AoU; label = "AOU-04"; }
            port can : CanPort;
        }
        part driver : Person {
            doc /* Supervises, overrides and responds to warnings. */
            @Boundary { scope = Scope::outside; }
            @Safety { integrity = Integrity::AoU; label = "AOU-06, AOU-07"; }
            port face : ImagePort;
            port senses : HmiPort;
        }
        part backEnd : ExternalElement {
            doc /* comma.ai back end (connect, athena) and update origin. Not trusted for safety. */
            @Boundary { scope = Scope::outside; }
            @Safety { integrity = Integrity::Untrusted; label = "Untrusted (AOU-11)"; }
            port network : NetworkPort;
        }
        part roadEnvironment : ExternalElement {
            doc /* Road users, lanes, light and weather within the ODD (WP-C-02). */
            @Boundary { scope = Scope::outside; }
            port scene : ImagePort;
        }
        part vehicleSupply : ExternalElement {
            doc /* Vehicle 12 V supply and ignition. */
            @Boundary { scope = Scope::outside; }
            port supply : PowerPort;
        }
        part <'E-06'> externalCompute : HardwareElement {
            doc /* Optional external compute ("Chestnut" eGPU over USB). Proposed for exclusion pending GAP-17 (WP-C-01 OI-4). */
            @Boundary { scope = Scope::excluded; }
        }
        part vehicleCan : VehicleCan {
            @Boundary { scope = Scope::outside; }
        }
        part radarCan : RadarCan {
            @Boundary { scope = Scope::outside; }
        }

        connect eps to vehicleCan;
        connect ecmPcm to vehicleCan;
        connect absVsc to vehicleCan;
        connect cluster to vehicleCan;
        connect forwardRadar.can to radarCan.bus;

        // ---------------------------------------------------------- interfaces across the item boundary

        interface ifCarTx : CanLink
            connect source ::> ldsda.safetyFirmware.platformFirmware.fdcan.bus0 to target ::> vehicleCan.bus {
            doc /* 0x2E4, 0x343, 0x412, 0x1D2 cancel, (0x750 tester present) to EPS and PCM. */
            @InterfaceId { id = "IF-01"; route = "E-05"; tsr = ("TSR-1xx", "TSR-2xx", "TSR-705"); }
        }
        interface ifCarRx : CanLink
            connect source ::> vehicleCan.bus to target ::> ldsda.safetyFirmware.platformFirmware.fdcan.bus0 {
            doc /* 0xAA, 0x260, 0x1D2, 0x226 (+ 0x262, 0x1D3, 0xB4 proposed) from EPS, PCM and ABS. */
            @InterfaceId { id = "IF-02"; route = "E-05"; tsr = ("TSR-3xx", "TSR-401", "TSR-402", "TSR-403", "TSR-404", "TSR-405", "TSR-406"); }
        }
        interface ifRadarRx : CanLink
            connect source ::> radarCan.bus to target ::> ldsda.safetyFirmware.platformFirmware.fdcan.bus1 {
            doc /* Forward radar 0x180 to 0x19F on panda bus 1 (WP-C-01 §3.4). */
            @InterfaceId { id = "IF-02"; }
            @Source { workProduct = "WP-C-01"; clause = "§3.4"; }
        }
        interface ifCamera : CanLink
            connect source ::> forwardCamera.can to target ::> ldsda.safetyFirmware.platformFirmware.fdcan.bus2 {
            doc /* Camera-side CAN; forwarded to the car except intercepted control messages. */
            @InterfaceId { id = "IF-03"; route = "E-05"; tsr = ("TSR-704", "TSR-707"); }
        }
        interface ifRoadCameras : ImageLink
            connect source ::> roadEnvironment.scene to target ::> ldsda.deviceHardware.restOfDevice.roadCameras.scene {
            @InterfaceId { id = "IF-05"; }
        }
        interface ifDriverCamera : ImageLink
            connect source ::> driver.face to target ::> ldsda.deviceHardware.restOfDevice.driverCamera.scene {
            @InterfaceId { id = "IF-06"; }
        }
        interface ifHmiDisplay : HmiLink
            connect source ::> ldsda.deviceHardware.restOfDevice.display.screen to target ::> driver.senses {
            @InterfaceId { id = "IF-07"; tsr = "TSR-606"; }
        }
        interface ifHmiSound : HmiLink
            connect source ::> ldsda.deviceHardware.restOfDevice.speaker.sound to target ::> driver.senses {
            @InterfaceId { id = "IF-07"; tsr = "TSR-606"; }
        }
        interface ifSiren : HmiLink
            connect source ::> ldsda.safetyFirmware.platformFirmware.siren.audio to target ::> driver.senses {
            doc /* SoC-independent siren through the MCU DAC and codec path. */
            @InterfaceId { id = "IF-07"; tsr = "TSR-516"; }
        }
        interface ifDevicePower : PowerLink
            connect supply ::> vehicleSupply.supply to load ::> ldsda.deviceHardware.restOfDevice.powerSupply.input {
            @InterfaceId { id = "IF-08"; route = "E-05"; tsr = ("TSR-505", "TSR-510"); }
        }
        interface ifHarnessPower : PowerLink
            connect supply ::> vehicleSupply.supply to load ::> ldsda.harness.wiring.power {
            @InterfaceId { id = "IF-08"; tsr = ("TSR-505", "TSR-510"); }
        }
        interface ifNetwork : NetworkLink
            connect device ::> ldsda.socSoftware.remoteAndLogging.network to peer ::> backEnd.network {
            doc /* Athena RPC, uploads, OTA updates, SSH. Cybersecurity only (AOU-11). */
            @InterfaceId { id = "IF-09"; }
        }
    }

    part context : OperationalContext;

    // ================================================================== allocation vocabulary
    // Short forms used in the allocated_to fields of assurance/trace/items (WP-S-02 §2.1).

    alias 'P-SW' for LdSda::safetyFirmware;
    alias 'P-HW' for DeviceHardware::safetyMcu;
    alias SoC for LdSda::socSoftware;
    alias HAR for LdSda::harness;
}
