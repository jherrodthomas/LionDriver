package LionDriverIntegration {
    doc
    /*
     * System integration of WP-S-08 §3.1: the steps I-1 to I-4, bottom-up, each with every column
     * of its row (check M11 holds them to WP-S-08 cell by cell). integrates names the model
     * elements a step adds (a step keeps what the steps before it integrated); exercises names
     * the interfaces it tests. The test cases that run at a step say so in LionDriverVerification
     * (steps), from the Step column of WP-S-08 §6.
     *
     * Status: draft, AI-assisted (Claude), not reviewed (I0). The element and interface lists are
     * read from the row text and are new here.
     */

    private import LionDriverLibrary::*;

    action <'I-1'> envelopeOnTarget : IntegrationStep {
        doc /* Envelope on the target MCU */
        :>> elements = "E-03 panda firmware (release build) on the reference device MCU, SoC running a **test host** (`panda` Python library) instead of openpilot";
        :>> interfaces = "IF-01, IF-02, IF-03 (via bench CAN), IF-04 (SPI, scripted), relay (E-05)";
        :>> stimulus = "Scripted CAN frames and Corolla log replay on bus 0/2; scripted host commands";
        :>> purpose = "Envelope behaviour on target hardware, independent of the QM stack";
        :>> integrates = ("E-03", "E-04a", "E-05");
        :>> exercises = ("IF-01", "IF-02", "IF-03", "IF-04", "IF-10");
    }
    action <'I-2'> socWithEnvelope : IntegrationStep {
        doc /* SoC software with the envelope */
        :>> elements = "I-1 + full openpilot on the SoC (pandad, card, controlsd, selfdrived, ui/soundd), camera inputs from recorded video or covered (no model credit)";
        :>> interfaces = "IF-04 real traffic, IF-07 HMI";
        :>> stimulus = "Open-loop Corolla log replay on the CAN side; process faults injected on the SoC";
        :>> purpose = "SoC ↔ envelope integration, fault reactions, warnings, heartbeat";
        :>> integrates = ("E-01", "E-04b");
        :>> exercises = ("IF-04", "IF-07");
    }
    action <'I-3'> closedLoopBench : IntegrationStep {
        doc /* Closed loop with a plant model */
        :>> elements = "I-2 in closed loop with a vehicle model (Corolla lateral/longitudinal plant on the bench PC, producing `0x260`, `0xAA`, `0x1D2`, `0x226` responses to `0x2E4`/`0x343`)";
        :>> interfaces = "Closed control loop through the panda";
        :>> stimulus = "Scenario scripts";
        :>> purpose = "Dynamic behaviour at limits; FTTI-relevant timing with plant response";
        :>> exercises = ("IF-01", "IF-02");
    }
    action <'I-4'> stationaryVehicle : IntegrationStep {
        doc /* Stationary in the reference vehicle */
        :>> elements = "Device + harness installed in the reference vehicle, **stationary** (engine on, wheels on ground or lifted per [WP-V-07](../06-validation/WP-V-07-vehicle-test-operations.md))";
        :>> interfaces = "All IF incl. real EPS/PCM/camera";
        :>> stimulus = "Engagement attempts, stalk/brake/gas inputs, relay checks, PCS message capture";
        :>> purpose = "Integration with existing vehicle elements before driving; hand-over to WP-S-09";
        :>> integrates = ("E-02", "EXT-EPS", "EXT-PCM", "EXT-CLU", "forwardCamera");
        :>> exercises = ("IF-01", "IF-02", "IF-03", "IF-04", "IF-04b", "IF-05", "IF-06", "IF-07", "IF-08", "IF-09", "IF-10");
    }
}
