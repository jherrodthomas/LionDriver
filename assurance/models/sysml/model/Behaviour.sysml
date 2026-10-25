package LionDriverBehaviour {
    doc
    /*
     * Behaviour of the item: its operating modes (WP-C-01 §4) as a SysML v2 state machine.
     * Every mode row of §4 is a state with its description and actuation (check M12 holds
     * them to WP-C-01 cell by cell); host and panda name the states of the state-machine
     * records (assurance/05-software/state-machines) a mode stands for, and every transition
     * names the record transitions it stands for and who enforces it: the panda envelope,
     * the host only, or the host only while the envelope still allows actuation (GAP-16).
     * Transitions and record mapping follow WP-C-01 Figure 4-1.
     *
     * Status: draft, AI-assisted (Claude), not reviewed (I0).
     */

    private import LionDriverLibrary::*;

    state def <'SM-SYS'> SystemModes {
        doc /* Operating modes and actuation authority of LD-SDA */
        @ModeConfigurations { rows = ("Chill vs Experimental Mode", "Debug / maneuver / joystick modes"); }
        entry; then off;

        state off {
            doc /* Off / offroad */
            @ModeRow {
                description = "Ignition off or device offroad. pandad puts the panda in `NO_OUTPUT` (`pandad.cc:204-207`). A panda found in `SILENT` is also switched to `NO_OUTPUT` (`pandad.cc:195-196`)";
                actuation = "None";
                panda = ("SM-SAFETY-MODE NOOUTPUT", "SM-SAFETY-MODE SILENT");
            }
        }
        state disengaged {
            doc /* Onroad, disengaged */
            @ModeRow {
                description = "Car safety mode active, `controls_allowed = false`";
                actuation = "None (non-zero torque or accel rejected, `lateral.h:98-101`)";
                host = "SM-SELFDRIVED disabled";
                panda = ("SM-SAFETY-MODE TOYOTA", "SM-TOY-AUTH NOT_ALLOWED");
            }
        }
        state engaged {
            doc /* Engaged: authority granted by the envelope (host enabled, overriding or soft disabling) */
            entry; then enabled;
            state enabled {
                doc /* Pre-enabled / enabled */
                @ModeRow {
                    description = "Engaged after the PCM cruise rising edge and no NO_ENTRY condition (`state.py:79-90`)";
                    actuation = "Lateral and longitudinal";
                    host = ("SM-SELFDRIVED preEnabled", "SM-SELFDRIVED enabled");
                    panda = ("SM-SAFETY-MODE TOYOTA", "SM-TOY-AUTH ALLOWED");
                }
            }
            state overriding {
                doc /* Overriding */
                @ModeRow {
                    description = "Driver gas or steering input while engaged. Longitudinal blocked while gas pressed (`longitudinal.h:3-5`)";
                    actuation = "Lateral; no longitudinal";
                    host = "SM-SELFDRIVED overriding";
                    panda = "SM-TOY-AUTH ALLOWED";
                }
            }
            state softDisabling {
                doc /* Soft disabling */
                @ModeRow {
                    description = "Fault detected; warning; actuation continues up to 3 s (`state.py:7`) — see GAP-16";
                    actuation = "Lateral and longitudinal (forced decel)";
                    host = "SM-SELFDRIVED softDisabling";
                    panda = "SM-TOY-AUTH ALLOWED";
                }
            }
            transition gasOrSteering first enabled then overriding {
                doc /* gas or steering */
                @Enforcement { kind = Enforcer::host; records = "SM-SELFDRIVED E2"; }
            }
            transition released first overriding then enabled {
                doc /* released */
                @Enforcement { kind = Enforcer::host; records = "SM-SELFDRIVED O2"; }
            }
            transition softDisable first enabled then softDisabling {
                doc /* SOFT_DISABLE */
                @Enforcement { kind = Enforcer::gap16; records = "SM-SELFDRIVED E1"; }
            }
            transition softFromOverride first overriding then softDisabling {
                doc /* SOFT_DISABLE */
                @Enforcement { kind = Enforcer::gap16; records = "SM-SELFDRIVED O1"; }
            }
            transition cleared first softDisabling then enabled {
                doc /* cleared */
                @Enforcement { kind = Enforcer::host; records = "SM-SELFDRIVED SD1"; }
            }
        }
        state immediateDisable {
            doc /* Immediate disable */
            @ModeRow {
                description = "Critical fault; control released at once";
                actuation = "None";
            }
        }
        state lockout {
            doc /* Driver lockout */
            @ModeRow {
                description = "DM non-compliance; engagement prevented for 1–30 min (`policy.py:47-49`)";
                actuation = "None";
                host = "SM-SELFDRIVED disabled";
            }
        }

        transition onroad first off then disengaged {
            doc /* onroad: 0xdc TOYOTA */
            @Enforcement { kind = Enforcer::envelope; records = ("SM-SAFETY-MODE M2", "SM-SAFETY-MODE M4"); }
        }
        transition offroad first disengaged then off {
            doc /* offroad: NOOUTPUT */
            @Enforcement { kind = Enforcer::envelope; records = ("SM-SAFETY-MODE M2", "SM-SAFETY-MODE M5", "SM-TOY-AUTH T7"); }
        }
        transition heartbeatLost first disengaged then off {
            doc /* heartbeat lost: SILENT */
            @Enforcement { kind = Enforcer::envelope; records = ("SM-SAFETY-MODE M7", "SM-TOY-AUTH T7"); }
        }
        transition engage first disengaged then engaged {
            doc /* cruise set: PCM rising edge */
            @Enforcement { kind = Enforcer::envelope; records = ("SM-SELFDRIVED D1", "SM-SELFDRIVED D3", "SM-SELFDRIVED D2", "SM-TOY-AUTH T1"); }
        }
        transition refused first disengaged then disengaged {
            doc /* refused: NO_ENTRY */
            @Enforcement { kind = Enforcer::host; records = ("SM-SELFDRIVED N1", "SM-TOY-AUTH T8"); }
        }
        transition driverDisengage first engaged then disengaged {
            doc /* brake, cancel, cruise off */
            @Enforcement { kind = Enforcer::envelope; records = ("SM-SELFDRIVED X2", "SM-TOY-AUTH T2", "SM-TOY-AUTH T3"); }
        }
        transition envelopeFault first engaged then disengaged {
            doc /* envelope fault (RX, heartbeat) */
            @Enforcement { kind = Enforcer::envelope; records = ("SM-TOY-AUTH T4", "SM-TOY-AUTH T5", "SM-TOY-AUTH T10a", "SM-TOY-AUTH T6a", "SM-TOY-AUTH T10b", "SM-TOY-AUTH T10c", "SM-TOY-AUTH T11", "SM-SELFDRIVED X1"); }
        }
        transition softDisableTimeout first engaged.softDisabling then disengaged {
            doc /* 3 s soft-disable timer runs out */
            @Enforcement { kind = Enforcer::gap16; records = ("SM-SELFDRIVED SD2", "SM-TOY-AUTH T2", "SM-TOY-AUTH T6"); }
        }
        transition immediate first engaged then immediateDisable {
            doc /* IMMEDIATE_DISABLE */
            @Enforcement { kind = Enforcer::host; records = "SM-SELFDRIVED X1"; }
        }
        transition immediateEnd first immediateDisable then disengaged {
            doc /* at once */
            @Enforcement { kind = Enforcer::host; records = ("SM-SELFDRIVED X1", "SM-TOY-AUTH T2", "SM-TOY-AUTH T6"); }
        }
        transition dmLockout first disengaged then lockout {
            doc /* DM non-compliance */
            @Enforcement { kind = Enforcer::host; }
        }
        transition lockoutExpires first lockout then disengaged {
            doc /* expires after 1–30 min */
            @Enforcement { kind = Enforcer::host; }
        }
    }
}
