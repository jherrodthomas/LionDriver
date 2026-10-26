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
            perform LionDriverFunctions::lateralControl.sendLka;
            perform LionDriverFunctions::longitudinalControl.sendAcc;
            perform LionDriverFunctions::engagement.heartbeat;
        }
        part <'host.card'> card : SoftwareElement {
            doc /* CAN parse to carState; carControl to sendcan; CarParams and fingerprint. */
            @Safety { integrity = Integrity::QMBsup; label = "QM (B-sup)"; }
            @Source { workProduct = "WP-W-03"; clause = "§4.1"; paths = ("openpilot/selfdrive/car/card.py", "opendbc/car/toyota/"); }
            perform LionDriverFunctions::lateralControl.packLka;
            perform LionDriverFunctions::longitudinalControl.packAcc;
            perform LionDriverFunctions::engagement.carState;
            perform LionDriverFunctions::driverInformation.packHud;
        }
        part <'host.controlsd'> controlsd : SoftwareElement {
            doc /* Lateral and longitudinal control law. */
            @Safety { integrity = Integrity::QMBsup; label = "QM (B-sup)"; }
            @Source { workProduct = "WP-W-03"; clause = "§4.1"; paths = "openpilot/selfdrive/controls/controlsd.py"; }
            perform LionDriverFunctions::lateralControl.lateralLaw;
            perform LionDriverFunctions::longitudinalControl.longitudinalLaw;
        }
        part <'host.selfdrived'> selfdrived : SoftwareElement {
            doc /* Engagement state machine, event classification, alerts. */
            @Safety { integrity = Integrity::QMBsup; label = "QM (B-sup)"; }
            @Source { workProduct = "WP-W-03"; clause = "§4.1"; paths = "openpilot/selfdrive/selfdrived/"; }
            perform LionDriverFunctions::engagement.engagementState;
            perform LionDriverFunctions::driverInformation.alertClasses;
            perform LionDriverFunctions::forwardCollisionWarning.fcwEvent;
            perform LionDriverFunctions::laneDepartureWarning.ldwLogic;
        }
        part <'host.plannerd'> plannerd : SoftwareElement {
            doc /* Longitudinal plan. */
            @Safety { integrity = Integrity::QM; label = "QM (SOTIF)"; }
            @Source { workProduct = "WP-W-03"; clause = "§4.1"; paths = "openpilot/selfdrive/controls/plannerd.py"; }
            perform LionDriverFunctions::longitudinalControl.longitudinalPlan;
        }
        part <'host.radard'> radard : SoftwareElement {
            doc /* Lead fusion. */
            @Safety { integrity = Integrity::QM; label = "QM (SOTIF)"; }
            @Source { workProduct = "WP-W-03"; clause = "§4.1"; paths = "openpilot/selfdrive/controls/radard.py"; }
            perform LionDriverFunctions::longitudinalControl.leadFusion;
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
            perform LionDriverFunctions::driverMonitoring.dmPolicy;
        }
        part <'host.hmi'> hmi : SoftwareElement {
            @Zone { id = "Z3"; }
            doc /* ui and soundd: display and audible alerts. */
            @Safety { integrity = Integrity::QMBsup; label = "QM (B-sup)"; }
            @Source { workProduct = "WP-W-03"; clause = "§4.1"; }
            port alerts : HmiPort;
            perform LionDriverFunctions::driverMonitoring.dmAlerts;
            perform LionDriverFunctions::driverInformation.uiSound;
            perform LionDriverFunctions::forwardCollisionWarning.fcwAlert;
            perform LionDriverFunctions::laneDepartureWarning.ldwAlert;
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
            @Zone { id = "Z3"; }
            doc /* loggerd, uploader, athenad, updated, webrtcd and the other non-driving processes (F-09). Interference sources for FFI. */
            @Safety { integrity = Integrity::QM; label = "No (interference sources for FFI)"; }
            @Source { workProduct = "WP-S-03"; clause = "§8"; }
            port network : NetworkPort;
            perform LionDriverFunctions::loggingAndUpdate.logging;
            perform LionDriverFunctions::loggingAndUpdate.remote;
        }
    }

    // ================================================================== E-02

    part def MlModels :> MlElement {
        doc /* Driving model and driver monitoring model (LFS artefacts). */
        @Source { workProduct = "WP-C-01"; clause = "§3.1"; paths = "openpilot/selfdrive/modeld/models/"; }
        part drivingModel : MlElement {
            doc /* Camera-based driving model; executed by host.modeld. */
            @Safety { integrity = Integrity::QM; label = "QM (SOTIF / PAS 8800)"; }
            perform LionDriverFunctions::lateralControl.desiredPath;
            perform LionDriverFunctions::forwardCollisionWarning.hardBrake;
            perform LionDriverFunctions::laneDepartureWarning.laneLines;
        }
        part dmModel : MlElement {
            doc /* Driver monitoring model; executed by dmonitoringmodeld (host.dm). */
            @Safety { integrity = Integrity::QM; label = "QM (SOTIF / PAS 8800)"; }
            perform LionDriverFunctions::driverMonitoring.attention;
        }
    }

    // ================================================================== E-03

    part def SafetyLayer :> SoftwareElement {
        doc /* opendbc safety core and Toyota mode, compiled into the panda firmware (WP-W-03 §3.1). */
        @Source { workProduct = "WP-W-03"; clause = "§3.1"; paths = "opendbc_repo/opendbc/safety/"; }

        part <'panda.safety.core'> core : SoftwareElement {
            doc /* Hook dispatch, RX checks and timeout, authority controls_allowed with grant on the PCM rising edge. */
            @Unit { id = "U-SAF-CORE"; build = Build::both; }
            @Safety { integrity = Integrity::C; label = "C"; }
            @Catalogue {
                description = "Hook dispatch (`safety_rx_hook` `:201-230`, `safety_tx_hook` `:283-302`, `safety_fwd_hook` `:316`); RX checks and timeout (`rx_check_lagging` `:373-386`, `safety_tick` `:404-420`); authority `controls_allowed` (`:57`) with grant on PCM rising edge gated by `rx_checks_allow_engagement` (`:390-401`, `pcm_cruise_check` `:601-610`); generic brake/gas edges (`:426-446`); relay-malfunction detection; TX whitelist (`tx_msg_safety_check` `:232-241`); mode switching (`set_safety_hooks` `:467-565`)";
                sources = "`safety.h`";
            }
            part <'panda.safety.core.rx_engagement'> rxEngagement : SoftwareElement {
                doc /* rx_timeout_periods and rx_checks_allow_engagement: no grant while an RX check lags or is invalid. */
                @Unit { id = "U-SAF-CORE"; build = Build::both; }
                @Safety { integrity = Integrity::C; label = "C"; }
                @Catalogue {
                    description = "`rx_timeout_periods` tightens the lag threshold to N nominal periods with no 1 s floor (`:380-383`); `rx_checks_allow_engagement` refuses a grant while any RX check lags or is invalid. Active for any mode that sets `rx_timeout_periods`; Toyota sets 5 (`modes/toyota.h:83, 543`)";
                    sources = "`safety.h:373-401`; `declarations.h:242`";
                    buildNote = "Toyota";
                }
            }
            part <'panda.safety.core.tx_rate_check'> txRateCheck : SoftwareElement {
                doc /* Per-ID TX rate budget over a sliding 250 ms window. */
                @Unit { id = "U-SAF-CORE"; build = Build::reference; }
                @Safety { integrity = Integrity::C; label = "C"; }
                @Catalogue {
                    description = "Per-ID TX rate budget over a sliding 250 ms window; frames over budget are rejected before the mode's TX hook; on the 3rd rejection while authority is granted, clears `controls_allowed` and sets `safety_tx_rate_exceeded` (`:269-272`) (SWSR-518)";
                    sources = "`safety.h:243-281`, called first in `safety_tx_hook` (`:290-294`)";
                }
            }
        }
        part <'panda.safety.lateral'> lateral : SoftwareElement {
            doc /* Torque limit, rate, measured-torque, RT window and steer-request tolerance. */
            @Unit { id = "U-SAF-LAT"; build = Build::both; }
            @Safety { integrity = Integrity::C; label = "C"; }
            @Catalogue {
                description = "Torque limit, rate, measured-torque, RT window, steer-request tolerance (`steer_torque_cmd_checks`, reads `controls_allowed` at `:64, 99, 141`); angle/curvature checks unused in the reference configuration";
                sources = "`lateral.h`";
            }
        }
        part <'panda.safety.longitudinal'> longitudinal : SoftwareElement {
            doc /* Longitudinal allowed, acceleration bounds, inactive value. */
            @Unit { id = "U-SAF-LONG"; build = Build::both; }
            @Safety { integrity = Integrity::B; label = "B"; }
            @Catalogue {
                description = "Longitudinal allowed, accel bounds, inactive value";
                sources = "`longitudinal.h`";
            }
        }
        part <'panda.safety.helpers'> helpers : SoftwareElement {
            doc /* Macros, CRC8, message matching, timestamps, interpolation, safety_config. */
            @Unit { id = "U-SAF-HELP"; build = Build::both; }
            @Safety { integrity = Integrity::C; label = "C"; }
            @Catalogue {
                description = "Macros, CRC8, message matching, timestamps, interpolation, packet type, `safety_config` incl. `rx_timeout_periods` and `tx_rate_checks` (`declarations.h:242-244`)";
                sources = "`helpers.h`, `declarations.h`, `can.h`";
            }
        }
        part <'panda.safety.toyota'> toyota : SoftwareElement {
            doc /* Toyota RX parsing, TX checks, limits, init and parameter decoding; hook table toyota_hooks. */
            @Unit { id = "U-SAF-TOY"; build = Build::both; }
            @Safety { integrity = Integrity::C; label = "C"; }
            @Catalogue {
                description = "Toyota RX parsing, TX checks, limits, init/param decoding; hook table `toyota_hooks` (`:565-572`)";
                sources = "`modes/toyota.h`";
            }
            part <'panda.safety.toyota.eps_fault'> epsFault : SoftwareElement {
                doc /* Decodes EPS_STATUS.LKA_STATE into safety_eps_fault; refuses torque while it is set. */
                @Unit { id = "U-SAF-TOY"; build = Build::reference; }
                @Safety { integrity = Integrity::C; label = "C"; }
                @Catalogue {
                    description = "`toyota_lka_state_is_fault` decodes `0x262` EPS_STATUS.LKA_STATE into `safety_eps_fault`; while set, `0x2E4` frames with non-zero torque or steer request are refused before the limit checks. Does not clear `controls_allowed` (SWSR-110 partial)";
                    sources = "`modes/toyota.h:91-116, 236-240, 425-434`";
                }
            }
            part <'panda.safety.toyota.ref_rx_set'> refRxSet : SoftwareElement {
                doc /* Adds 0x262 and 0x1D3 to the RX checks. */
                @Unit { id = "U-SAF-TOY"; build = Build::reference; }
                @Safety { integrity = Integrity::C; label = "C"; }
                @Catalogue {
                    description = "Adds `0x262` (25 Hz) and `0x1D3` (33 Hz) to the RX checks (presence, checksum, timeout)";
                    sources = "`modes/toyota.h:56-63`";
                }
            }
            part <'panda.safety.toyota.cruise_main'> cruiseMain : SoftwareElement {
                doc /* CRUISE_ACTIVE with MAIN_ON = 0 revokes authority. */
                @Unit { id = "U-SAF-TOY"; build = Build::reference; }
                @Safety { integrity = Integrity::C; label = "C"; }
                @Catalogue {
                    description = "`toyota_cruise_main_check`: CRUISE_ACTIVE with MAIN_ON = 0 revokes authority at once on a cruise edge, or after 150 ms of disagreement (SWSR-405 (c))";
                    sources = "`modes/toyota.h:123-145, 241-249`";
                }
            }
            part <'panda.safety.toyota.tx_budgets'> txBudgets : SoftwareElement {
                doc /* TX rate rows for the non-SecOC configurations. */
                @Unit { id = "U-SAF-TOY"; build = Build::reference; }
                @Safety { integrity = Integrity::C; label = "C"; }
                @Catalogue {
                    description = "TX rate rows for non-SecOC configurations (`0x2E4` 100 Hz + 5, `0x191`, `0x343`, `0x412`, `0x1D2`, `0x283`, `0x750`)";
                    sources = "`modes/toyota.h:545-560`";
                }
            }
        }
        part <'panda.safety.defaults'> defaults : SoftwareElement {
            doc /* SILENT, NOOUTPUT and ELM327 hooks. */
            @Unit { id = "U-SAF-DEF"; build = Build::both; }
            @Safety { integrity = Integrity::C; label = "C (safe-state modes)"; }
            @Catalogue {
                description = "SILENT/NOOUTPUT/ELM327 hooks";
                sources = "`modes/defaults.h`, `modes/elm327.h`";
            }
        }
        part <'panda.safety.ignition'> ignition : SoftwareElement {
            doc /* CAN ignition detection. */
            @Unit { id = "U-SAF-IGN"; build = Build::both; }
            @Safety { integrity = Integrity::B; label = "B"; }
            @Catalogue {
                description = "CAN ignition detection";
                sources = "`ignition.h`";
                attribution = "B (feeds heartbeat timeout choice, TSR-510)";
            }
        }
        part <'panda.safety.other_modes'> otherModes : SoftwareElement {
            doc /* Other brands' modes; linked in both builds, not selectable by the host in the reference build. */
            @Safety { integrity = Integrity::QM; label = "Interference source; dead code"; }
            @Catalogue {
                description = "Linked in both builds. Standard build: selectable via `0xdc`. Reference build: not selectable by the host (`reference_lock.h:22-29`), so dead code (OI-2)";
                sources = "`modes/*.h` other brands, included at `safety.h:10-33`, registered at `:468-498`";
                attribution = "Interference source (standard build); dead code to be removed or justified (reference build, OI-2)";
            }
        }
    }

    part def PlatformFirmware :> SoftwareElement {
        doc /* panda main loop, tick handler, CAN and SPI drivers, comms handlers, harness and relay driver, fault handling, bootstub. */
        @Source { workProduct = "WP-W-03"; clause = "§3.1"; paths = "panda/board/"; }

        part <'panda.main'> main : SoftwareElement {
            doc /* Start-up, set_safety_mode, 8 Hz tick. */
            @Unit { id = "U-PND-MAIN"; build = Build::both; }
            @Safety { integrity = Integrity::C; label = "C"; }
            @Catalogue {
                description = "Start-up (`main` `:292-383`), `set_safety_mode` (`:38-93`, both `set_safety_hooks` calls in `ENTER_CRITICAL` `:43-45, 49-51`), 8 Hz tick (`tick_handler` `:147-290`: harness, software watchdog kick, siren; 1 Hz: heartbeat counter, `heartbeat_engaged` mismatch, SILENT after 5 s/2 s heartbeat loss, `check_registers`), main loop (`:386-420`)";
                sources = "`board/main.c`";
            }
            part <'panda.main.safety_task'> safetyTask : SoftwareElement {
                doc /* TIM4 safety task at 100 Hz: safety_tick, heartbeat monitor, IWDG feed. */
                @Unit { id = "U-PND-MAIN"; build = Build::both; }
                @Safety { integrity = Integrity::C; label = "C"; }
                @Catalogue {
                    description = "TIM4 safety task at `SAFETY_TASK_FREQ` = 100 Hz: `safety_tick` (`:133`), heartbeat monitor with revocation in car modes (`:135-137`), IWDG feed (`:138`). Rate supervision at 110 calls/s (`main.c:352`) (SWSR-401a partial). Since panda `b790fca` / `c33343b` it also runs the EPS-fault siren and the heartbeat-loss siren (rows below)";
                    sources = "`board/main.c:130-144`; timer `board/drivers/timers.h:30-38`; `board/stm32h7/stm32h7_config.h:39-41`";
                }
            }
        }
        part <'panda.drivers.heartbeat_monitor'> heartbeatMonitor : SoftwareElement {
            doc /* Revokes authority after 0.3 s without a heartbeat (SWSR-407). */
            @Unit { id = "U-PND-MAIN"; build = Build::both; }
            @Safety { integrity = Integrity::C; label = "C"; }
            @Catalogue {
                description = "`heartbeat_age_ticks` reset on `0xf3` (`:20-22`, called from `main_comms.h:301`); incremented in the safety task, returns true at ≥ 30 ticks = 0.3 s (`:15, 25-30`) (SWSR-407)";
                sources = "`board/drivers/heartbeat_monitor.h`";
            }
        }
        part <'panda.drivers.heartbeat_siren'> heartbeatSiren : SoftwareElement {
            doc /* Siren for 3 s when the heartbeat monitor revokes authority. */
            @Unit { id = "U-PND-HK"; build = Build::both; }
            @Safety { integrity = Integrity::B; label = "B"; }
            @Catalogue {
                description = "When the heartbeat monitor revokes authority in a car mode while `controls_allowed` was set, the safety task requests the siren at once and holds it 3 s (`HEARTBEAT_SIREN_HOLD_TICKS` 300); reset on every mode change. Audible ≈ 0.56 s after the last heartbeat worst case (odd 8 Hz ticks) (SWSR-516 (a))";
                sources = "`board/drivers/heartbeat_siren.h` (panda `c33343b`)";
            }
        }
        part <'panda.drivers.eps_fault_siren'> epsFaultSiren : SoftwareElement {
            doc /* Siren once the EPS fault has persisted 1 s while authority is granted. */
            @Unit { id = "U-PND-HK"; build = Build::both; }
            @Safety { integrity = Integrity::B; label = "B"; }
            @Catalogue {
                description = "Once `safety_eps_fault` has been set for 0.7 s, counted from when it was first seen while `controls_allowed` (DQ-048, DQ-367; panda `bf8102a`), siren for at least 3 s, re-triggered while the fault persists; reset on every mode change. Worst case ≈ 0.96 s after the fault onset (SWSR-516 (b), EPS fault). Compiled in every build; only the reference build sets `safety_eps_fault`";
                sources = "`board/drivers/eps_fault_siren.h` (panda `b790fca`)";
            }
        }
        part <'panda.drivers.hw_watchdog'> hwWatchdog : SoftwareElement {
            doc /* IWDG1 window watchdog, started on the first relay drive. */
            @Unit { id = "U-PND-FLT"; build = Build::both; }
            @Safety { integrity = Integrity::C; label = "C"; }
            @Catalogue {
                description = "IWDG1, prescaler /4, RLR 719, window 679 (`:35-37`); started on the first relay drive by `set_intercept_relay` (`drivers/harness.h:16-21`), not at boot (`:45-58`); fed from the safety task only if the main loop has run since the last feed (`:61-76`); first tick after start skipped. A watchdog reset is reported as `HEALTH_FLAG_WATCHDOG_RESET` (`main.c:377-380`) (SWSR-501)";
                sources = "`board/drivers/hw_watchdog.h`";
            }
        }
        part <'panda.drivers.irq_priorities'> irqPriorities : SoftwareElement {
            doc /* Explicit priority for every enabled IRQ (SWSR-519 partial). */
            @Unit { id = "U-PND-PLAT"; build = Build::both; }
            @Safety { integrity = Integrity::C; label = "C"; }
            @Catalogue {
                description = "`interrupt_priorities_init` (`:21-46`, called at `main.c:300` before any `NVIC_EnableIRQ`) sets an explicit priority for every enabled IRQ; five classes, all at level 8 (`:15-19`) (SWSR-519 partial)";
                sources = "`board/drivers/irq_priorities.h`";
            }
        }
        part <'panda.reference_lock'> referenceLock : SoftwareElement {
            doc /* Limits 0xdc to the reference modes; refuses 0xdf and the softloader in car modes. */
            @Unit { id = "U-PND-COMMS"; build = Build::reference; }
            @Safety { integrity = Integrity::C; label = "C"; }
            @Catalogue {
                description = "`reference_request_allowed`: `0xdc` limited to SILENT, NOOUTPUT, ELM327 and TOYOTA param 73, and from TOYOTA only to NOOUTPUT/SILENT (`:22-29`); `0xdf` always refused (`:30-32`); `0xd1` softloader refused in car modes (`:33-36`); `0xc5, 0xd8, 0xdb, 0xde, 0xe5–0xe8, 0xf1, 0xf9, 0xfc` refused in car modes (`:37-49`); refused requests counted in `reference_requests_rejected` (health)";
                sources = "`board/reference_lock.h:13-63`, called at `board/main_comms.h:74-79`";
            }
        }
        part <'panda.comms'> comms : SoftwareElement {
            doc /* Control-request dispatcher, health packet, CAN stream packing and unpacking. */
            @Unit { id = "U-PND-COMMS"; build = Build::both; }
            @Safety { integrity = Integrity::C; label = "C (it calls envelope APIs and can change configuration)"; }
            @Catalogue {
                description = "Control-request dispatcher `comms_control_handler` (`main_comms.h:69-343`), health packet (`:8-61`), CAN stream packing/unpacking (`comms_can_write` `can_comms.h:83-129`)";
                sources = "`board/main_comms.h`, `board/can_comms.h`";
            }
        }
        part <'panda.drivers.spi'> spi : SoftwareElement {
            doc /* SPI framing, XOR checksum, DMA control. */
            @Unit { id = "U-PND-SPI"; build = Build::both; }
            @Safety { integrity = Integrity::C; label = "C"; }
            @Catalogue {
                description = "SPI framing, XOR checksum, DMA control; `spi_rx_done` (`spi.h:106`) runs in the DMA2 Stream2 IRQ (`llspi.h:56-61`)";
                sources = "`board/drivers/spi.h`, `board/stm32h7/llspi.h`";
            }
            port host : SpiPort;
        }
        part <'panda.drivers.usb'> usb : SoftwareElement {
            doc /* USB endpoint handling; not needed by the reference device. */
            @Unit { id = "U-PND-USB"; build = Build::both; }
            @Safety { integrity = Integrity::QM; label = "Not needed by the reference device (SPI); interference source (OI-3)"; }
            @Catalogue {
                description = "USB endpoint handling; reaches the same comms handlers (`usb.h:616` → `comms_can_write`); initialised in both builds (`main.c:356`)";
                sources = "`board/drivers/usb.h`, `board/stm32h7/llusb.h`";
            }
        }
        part <'panda.drivers.fdcan'> fdcan : SoftwareElement {
            doc /* CAN RX ISR with the forward and RX hooks; TX path through the TX hook. */
            @Unit { id = "U-PND-FDCAN"; build = Build::both; }
            @Safety { integrity = Integrity::C; label = "C"; }
            @Catalogue {
                description = "CAN RX ISR `can_rx` (`fdcan.h:154-243`: forward hook `:199`, forwarding with hook skipped `:213`, RX hook `:221`), TX path `can_send` (`can_common.h:161-177`) → TX hook → queue → `process_can` (`fdcan.h:88-150`, XOR check `:100`)";
                sources = "`board/drivers/fdcan.h`, `board/drivers/can_common.h`, `board/stm32h7/llfdcan.h`";
            }
            port bus0 : CanPort;
            port bus1 : CanPort;
            port bus2 : CanPort;
        }
        part <'panda.drivers.harness'> harnessDriver : SoftwareElement {
            doc /* Relay drive, orientation and ignition sense. */
            @Unit { id = "U-PND-HARN"; build = Build::both; }
            @Safety { integrity = Integrity::C; label = "C (blocking) / B (PCS restore)"; }
            @Catalogue {
                description = "Relay drive (`set_intercept_relay` `:9-37`, also starts the IWDG), orientation and ignition sense";
                sources = "`board/drivers/harness.h`";
            }
        }
        part <'panda.sys.faults'> faults : SoftwareElement {
            doc /* Fault recording and the software watchdog. */
            @Unit { id = "U-PND-FLT"; build = Build::both; }
            @Safety { integrity = Integrity::C; label = "C (report-only)"; }
            @Catalogue {
                description = "Fault recording (`fault_occurred`/`fault_recovered` in critical sections, `faults.h:10-11, 25-26`), software watchdog (kicked and checked in the 8 Hz tick, `simple_watchdog.h:7-17`, `main.c:160`), register check (1 Hz), interrupt-rate supervision (`interrupts.h:50`)";
                sources = "`board/sys/faults.h`, `board/drivers/simple_watchdog.h`, `board/drivers/registers.h`, `board/drivers/interrupts.h`";
                attribution = "C (report-only; `PERMANENT_FAULTS 0U`, `sys/sys.h:50`)";
            }
        }
        part <'panda.sys.power_saving'> powerSaving : SoftwareElement {
            doc /* Power-save: CAN IRQ and transceiver disable. */
            @Unit { id = "U-PND-PWR"; build = Build::both; }
            @Safety { integrity = Integrity::C; label = "C"; }
            @Catalogue {
                description = "Power-save: CAN IRQ and transceiver disable";
                sources = "`board/sys/power_saving.h`";
                attribution = "C (can stop camera-side forwarding, WP-A-02 FFI-CM-08)";
            }
        }
        part <'panda.drivers.siren'> siren : SoftwareElement {
            doc /* Siren and housekeeping drivers (fan, LED, bootkick, clock source, PWM, ADC). */
            @Unit { id = "U-PND-HK"; build = Build::both; }
            @Safety { integrity = Integrity::C; label = "C"; }
            @Catalogue {
                name = "`panda.drivers.siren` / housekeeping";
                description = "Siren (B, TSR-516); fan, LED and the rest developed to ASIL C, no FFI claimed (WP-A-02 §2, DQ-126)";
                sources = "`board/drivers/fake_siren.h`, `board/stm32h7/sound.h`, `board/drivers/{fan,led,bootkick,clock_source,pwm}.h`, `board/stm32h7/lldts.h`, ADC";
            }
            port audio : HmiPort;
        }
        part <'panda.platform'> platform : SoftwareElement {
            doc /* Reset, exception handlers, clocks, vectors, timers, critical sections. */
            @Unit { id = "U-PND-PLAT"; build = Build::both; }
            @Safety { integrity = Integrity::C; label = "C"; }
            @Catalogue {
                description = "Reset, exception handlers (NMI/HardFault `early_init.h:73-81`), clocks, vectors, timers, critical sections (`sys.h:10-22`)";
                sources = "`board/stm32h7/startup_stm32h7x5xx.s`, `board/early_init.h`, `board/stm32h7/{clock,peripherals,interrupt_handlers,llflash}.h`, `board/drivers/timers.h`, `board/sys/sys.h`";
            }
        }
        part <'panda.bootstub'> bootstub : SoftwareElement {
            doc /* Signature check and soft flasher. */
            @Unit { id = "U-PND-BOOT"; build = Build::both; }
            @Safety { integrity = Integrity::C; label = "C + CS"; }
            @Catalogue {
                description = "Signature check (`bootstub.c:33-82`), soft flasher";
                sources = "`board/bootstub.c`, `board/crypto/*`, `board/flasher.h`";
            }
        }
    }

    part def SafetyMcuFirmware :> SoftwareElement {
        doc /* panda firmware with the opendbc safety Toyota mode (WP-C-01 §3.1). */
        @Source { workProduct = "WP-S-03"; clause = "§3.1"; }
        part <'E-03a'> safetyLayer : SafetyLayer {
            @Safety { integrity = Integrity::C; label = "C"; }
            @Catalogue {
                name = "Safety layer";
                description = "opendbc safety core + Toyota mode, compiled into the panda firmware";
                sources = "`opendbc_repo/opendbc/safety/{safety.h,lateral.h,longitudinal.h,helpers.h,modes/toyota.h}`";
            }
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
            perform LionDriverFunctions::lateralControl.limitTorque;
            perform LionDriverFunctions::longitudinalControl.boundAccel;
            perform LionDriverFunctions::engagement.authority;
            perform LionDriverFunctions::safetyEnvelope.rxChecks;
            perform LionDriverFunctions::safetyEnvelope.txChecks;
        }
        part <'E-03b'> platformFirmware : PlatformFirmware {
            @Safety { integrity = Integrity::C; label = "C"; }
            @Catalogue {
                name = "Panda platform firmware";
                description = "main loop, tick handler, CAN/SPI drivers, comms handlers, harness/relay driver, fault handling, bootstub";
                sources = "`panda/board/{main.c,main_comms.h,can_comms.h,drivers/*,sys/*,stm32h7/*,bootstub.c}`";
            }
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
            perform LionDriverFunctions::safetyEnvelope.canRx;
            perform LionDriverFunctions::safetyEnvelope.supervision;
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
        part core : HardwareElement {
            doc /* Cortex-M7 core: interrupt controller (NVIC) with the fault vectors, memory protection unit (MPU) and the die temperature sensor. */
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
            perform LionDriverFunctions::lateralControl.lateralRoadImages;
            perform LionDriverFunctions::longitudinalControl.longitudinalRoadImages;
            perform LionDriverFunctions::forwardCollisionWarning.fcwRoadImages;
            perform LionDriverFunctions::laneDepartureWarning.ldwRoadImages;
        }
        part driverCamera : HardwareElement {
            doc /* Driver-facing IR camera. */
            port scene : ImagePort;
            port images : ImagePort;
            perform LionDriverFunctions::driverMonitoring.driverImages;
        }
        part imuGnss : HardwareElement {
            doc /* IMU and GNSS. */
            port messages : SensorPort;
        }
        part display : HardwareElement {
            port screen : HmiPort;
            perform LionDriverFunctions::driverInformation.displaySpeaker;
        }
        part speaker : HardwareElement {
            port sound : HmiPort;
            perform LionDriverFunctions::driverInformation.displaySpeaker;
        }
        part canTransceivers : HardwareElement;
        part powerSupply : HardwareElement { port input : PowerPort; }
        part enclosure : HardwareElement { doc /* Enclosure and windscreen mount. */ }
    }

    part def DeviceHardware :> HardwareElement {
        doc /* The comma device (WP-C-01 §3.1). */
        @Source { workProduct = "WP-S-03"; clause = "§3.1"; }
        part <'E-04a'> safetyMcu : SafetyMcuHardware {
            @Zone { id = "Z1"; }
            @Safety { integrity = Integrity::C; label = "C"; }
            @Catalogue {
                name = "Safety MCU hardware";
                description = "STM32H7 with clock, supply, memories, SPI4, FDCAN1–3, ADC, GPIO, DAC/codec siren path";
                sources = "[WP-H-02](../04-hardware/WP-H-02-hardware-design.md)";
            }
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
            @Zone { id = "Z7"; }
            @Safety { integrity = Integrity::QM; label = "QM"; }
            @Catalogue {
                name = "Device hardware (rest)";
                description = "SoC, cameras, IMU, display, speaker, power supply, enclosure";
                sources = "WP-H-02";
            }
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
            @Zone { id = "Z2"; }
            @Safety { integrity = Integrity::QM; label = "QM"; }
            @Catalogue {
                name = "SoC software";
                description = "openpilot processes on AGNOS Linux (Qualcomm SoC); §8";
                sources = "`openpilot/system/manager/process_config.py:70-121`";
            }
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
            @Zone { id = "Z2"; }
            @Safety { integrity = Integrity::QM; label = "QM (SOTIF/PAS 8800)"; }
            @Catalogue {
                name = "ML models";
                description = "Driving model, DM model";
                sources = "`openpilot/selfdrive/modeld/`";
            }
            perform LionDriverMechanisms::driverMonitoring;
        }
        part <'E-03'> safetyFirmware : SafetyMcuFirmware {
            @Zone { id = "Z1"; }
            @Safety { integrity = Integrity::C; label = "C"; }
        }
        part <'E-04'> deviceHardware : DeviceHardware {
            @Safety { integrity = Integrity::C; label = "E-04a C, E-04b QM"; }
        }
        part <'E-05'> harness : Harness {
            @Zone { id = "Z5"; }
            @Safety { integrity = Integrity::C; label = "B (PCS restore), C (blocking)"; }
            @Catalogue {
                name = "Harness";
                description = "Toyota TSS2 harness with intercept relay, ignition line, orientation sense";
                sources = "WP-H-02";
            }
            perform LionDriverMechanisms::relayReadback;
            perform LionDriverMechanisms::harnessDetection;
            perform LionDriverFunctions::safetyEnvelope.intercept;
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
            @InterfaceId { id = "IF-04"; tsr = ("TSR-407", "TSR-408", "TSR-409", "TSR-410", "TSR-411", "TSR-412", "TSR-413", "TSR-511", "TSR-512", "TSR-513", "TSR-514");
                name = "SoC ↔ MCU SPI";
                between = "E-01 ↔ E-03";
                content = "control requests, CAN streams, health";
                relevance = "C (FFI)";
                detail = "WP-S-05 §4";
            }
            @FfiClaim { claims = ("FFI-1", "FFI-2", "FFI-4", "FFI-5"); }
        }
        interface ifBoot : GpioLink
            connect driver ::> socSoftware.pandad.bootControl to receiver ::> deviceHardware.safetyMcu.gpio.bootPins {
            doc /* STM_BOOT0 and STM_RST_N. */
            @InterfaceId { id = "IF-04b"; tsr = "TSR-511";
                name = "SoC → MCU boot/reset GPIO";
                between = "E-01 → E-04a";
                content = "`STM_BOOT0`, `STM_RST_N`";
                relevance = "C (FFI, CS)";
                detail = "WP-S-05 §7";
            }
            @FfiClaim { claims = "FFI-3"; }
        }
        interface ifRelay : GpioLink
            connect driver ::> deviceHardware.safetyMcu.gpio.relayDrive to receiver ::> harness.interceptRelay.drive {
            doc /* Relay GPIO and harness (SBU) sense. */
            @InterfaceId { id = "IF-10"; tsr = ("TSR-506", "TSR-701");
                name = "Relay drive / harness sense";
                between = "E-04a ↔ E-05";
                content = "relay GPIO, SBU sense";
                relevance = "C/B";
                detail = "WP-S-05 §6";
            }
        }
        interface roadImages : ImageLink
            connect source ::> deviceHardware.restOfDevice.roadCameras.images to target ::> socSoftware.modeld.roadImages {
            doc /* VisionIPC: road images to the driving model (E-02, run by host.modeld). */
            @InterfaceId { id = "IF-05";
                label = "IF-05/06";
                name = "Cameras";
                between = "→ E-01/E-02";
                content = "images";
                relevance = "SOTIF";
                detail = "—";
            }
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
            @InterfaceId { id = "IF-07"; tsr = "TSR-606";
                name = "HMI";
                between = "E-01 ↔ driver; E-03 siren";
                content = "alerts";
                relevance = "QM; B for siren";
                detail = "—";
            }
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
            @Zone { id = "Z5"; }
            doc /* Receives LKA torque requests; reports driver torque, EPS torque and LKA state. */
            @Boundary { scope = Scope::outside; }
            @Safety { integrity = Integrity::AoU; label = "AOU-01, AOU-02"; }
            @Catalogue {
                description = "Toyota EPS";
                sources = "[WP-C-04 §11](../02-concept/WP-C-04-functional-safety-concept.md)";
            }
            perform LionDriverFunctions::lateralControl.applyTorque;
        }
        part <'EXT-PCM'> ecmPcm : ExternalElement {
            @Zone { id = "Z5"; }
            doc /* Engine and powertrain ECU: ACC acceleration, permit-braking, cruise state. */
            @Boundary { scope = Scope::outside; }
            @Safety { integrity = Integrity::AoU; label = "AOU-03, AOU-05, AOU-10"; }
            @Catalogue {
                description = "PCM/brake";
                sources = "[WP-C-04 §11](../02-concept/WP-C-04-functional-safety-concept.md)";
            }
            perform LionDriverFunctions::longitudinalControl.applyAccel;
            perform LionDriverFunctions::engagement.cruiseInputs;
        }
        part absVsc : ExternalElement {
            @Zone { id = "Z5"; }
            doc /* Brake actuator: wheel speeds and brake-pedal state. */
            @Boundary { scope = Scope::outside; }
            @Safety { integrity = Integrity::AoU; label = "AOU-03, AOU-10"; }
        }
        part <'EXT-CLU'> cluster : ExternalElement {
            @Zone { id = "Z5"; }
            doc /* Instrument cluster and cruise stalk: cruise main, set, resume, cancel; LKA HUD. */
            @Boundary { scope = Scope::outside; }
            @Safety { integrity = Integrity::AoU; label = "AOU-05, AOU-12"; }
            @Catalogue {
                description = "cluster";
                sources = "[WP-C-04 §11](../02-concept/WP-C-04-functional-safety-concept.md)";
            }
            perform LionDriverFunctions::driverInformation.clusterHud;
        }
        part forwardCamera : ExternalElement {
            @Zone { id = "Z5"; }
            doc /* Toyota forward camera: LKA and ACC outputs intercepted, PCS outputs forwarded. */
            @Boundary { scope = Scope::outside; }
            @Safety { integrity = Integrity::AoU; label = "AOU-04"; }
            port can : CanPort;
        }
        part forwardRadar : ExternalElement {
            @Zone { id = "Z5"; }
            doc /* Toyota forward radar: lead tracks; supports the stock PCS. */
            @Boundary { scope = Scope::outside; }
            @Safety { integrity = Integrity::AoU; label = "AOU-04"; }
            port can : CanPort;
            perform LionDriverFunctions::longitudinalControl.radarTracks;
        }
        part driver : Person {
            doc /* Supervises, overrides and responds to warnings. */
            @Boundary { scope = Scope::outside; }
            @Safety { integrity = Integrity::AoU; label = "AOU-06, AOU-07"; }
            port face : ImagePort;
            port senses : HmiPort;
        }
        part backEnd : ExternalElement {
            @Zone { id = "Z4"; }
            doc /* comma.ai back end (connect, athena) and update origin. Not trusted for safety. */
            @Boundary { scope = Scope::outside; }
            @Safety { integrity = Integrity::Untrusted; label = "Untrusted (AOU-11)"; }
            port network : NetworkPort;
            perform LionDriverFunctions::loggingAndUpdate.backEnd;
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
            @Zone { id = "Z5"; }
            @Boundary { scope = Scope::outside; }
        }
        part radarCan : RadarCan {
            @Zone { id = "Z5"; }
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
            @InterfaceId { id = "IF-01"; route = "E-05"; tsr = ("TSR-1xx", "TSR-2xx", "TSR-705");
                name = "Car-side CAN TX";
                between = "E-03 → EPS, PCM";
                content = "`0x2E4`, `0x343`, `0x412`, `0x1D2` cancel, (`0x750` tester present)";
                relevance = "C actuation";
                detail = "WP-S-05 §5";
            }
        }
        interface ifCarRx : CanLink
            connect source ::> vehicleCan.bus to target ::> ldsda.safetyFirmware.platformFirmware.fdcan.bus0 {
            doc /* 0xAA, 0x260, 0x1D2, 0x226 (+ 0x262, 0x1D3, 0xB4 proposed) from EPS, PCM and ABS. */
            @InterfaceId { id = "IF-02"; route = "E-05"; tsr = ("TSR-3xx", "TSR-401", "TSR-402", "TSR-403", "TSR-404", "TSR-405", "TSR-406");
                name = "Car-side CAN RX";
                between = "EPS, PCM, ABS → E-03";
                content = "`0xAA`, `0x260`, `0x1D2`, `0x226` (+ `0x262`, `0x1D3`, `0xB4` proposed)";
                relevance = "C gating/limiting";
                detail = "WP-S-05 §5";
            }
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
            @InterfaceId { id = "IF-03"; route = "E-05"; tsr = ("TSR-704", "TSR-707");
                name = "Camera-side CAN";
                between = "camera ↔ E-03";
                content = "forwarding";
                relevance = "B (SG-07)";
                detail = "WP-S-05 §5";
            }
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
            @InterfaceId { id = "IF-08"; route = "E-05"; tsr = ("TSR-505", "TSR-510");
                name = "Power, ignition";
                between = "vehicle → E-04, E-05";
                content = "12 V, ignition line";
                relevance = "B";
                detail = "WP-S-05 §6";
            }
        }
        interface ifHarnessPower : PowerLink
            connect supply ::> vehicleSupply.supply to load ::> ldsda.harness.wiring.power {
            @InterfaceId { id = "IF-08"; tsr = ("TSR-505", "TSR-510"); }
        }
        interface ifNetwork : NetworkLink
            connect device ::> ldsda.socSoftware.remoteAndLogging.network to peer ::> backEnd.network {
            doc /* Athena RPC, uploads, OTA updates, SSH. Cybersecurity only (AOU-11). */
            @InterfaceId { id = "IF-09";
                name = "Network";
                between = "E-01 ↔ back end";
                content = "athena, updates";
                relevance = "CS only (AOU-11)";
                detail = "[WP-S-07](WP-S-07-cybersecurity-requirements-architecture.md)";
            }
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
