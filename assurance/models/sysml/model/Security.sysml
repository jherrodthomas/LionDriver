package LionDriverSecurity {
    doc
    /*
     * Security architecture of WP-S-07 §3: the security zones Z1 to Z7 and the trust boundaries
     * TB-1 to TB-7, with every column of the two tables (check M10 holds them to WP-S-07 cell by
     * cell). Model elements name their zone with @Zone in LionDriverArchitecture; a zone also
     * keeps the WP-S-07 text of what it holds, which includes things outside the model (signing
     * keys, the release host, the back-end services).
     *
     * Status: draft, AI-assisted (Claude), not reviewed (I0).
     */

    private import LionDriverLibrary::*;

    part <'Z1'> safetyMcuZone : SecurityZone {
        doc /* Safety MCU */
        :>> holds = "panda STM32H7: bootstub (flash sector 0), application firmware, option bytes, opendbc safety code (E-03)";
        :>> trust = "Trusted; the only element that must stay intact under attack (envelope pattern, [WP-M-01 §4](../01-management/WP-M-01-assurance-strategy.md))";
        :>> basis = "CSG-01, CSG-02";
    }
    part <'Z2'> safetyHostZone : SecurityZone {
        doc /* SoC — safety-relevant host */
        :>> holds = "pandad, card/controlsd, selfdrived, modeld, dmonitoringmodeld, plannerd, params store, msgq";
        :>> trust = "QM; **assumed compromisable**; must not be able to defeat Z1";
        :>> basis = "CSG-03, CSG-04";
    }
    part <'Z3'> networkFacingZone : SecurityZone {
        doc /* SoC — network-facing */
        :>> holds = "athenad, uploader, updated, sshd, webrtcd, UI, installer";
        :>> trust = "Untrusted input handlers";
        :>> basis = "CSG-06, CSG-07, CSG-08";
    }
    part <'Z4'> externalNetworkZone : SecurityZone {
        doc /* External network and back end */
        :>> holds = "comma athena/connect, GitHub, LFS store, AGNOS CDN, Wi-Fi/LTE";
        :>> trust = "Untrusted (CA-01, CA-02, CA-04)";
        :>> basis = "CSC-02, CSC-04";
    }
    part <'Z5'> vehicleBusZone : SecurityZone {
        doc /* Vehicle bus */
        :>> holds = "Toyota ECUs, OBD-II port, harness";
        :>> trust = "Untrusted for injection (CA-03)";
        :>> basis = "CSG-05, CSC-01";
    }
    part <'Z6'> releaseZone : SecurityZone {
        doc /* Release environment */
        :>> holds = "LionDriver signing keys (offline), release build host, release record";
        :>> trust = "Trusted, outside the device";
        :>> basis = "CSG-02, CSG-07";
    }
    part <'Z7'> physicalDeviceZone : SecurityZone {
        doc /* Physical device */
        :>> holds = "eMMC/UFS storage, `/persist`, `/data`, debug ports";
        :>> trust = "Owner-controlled (CA-05)";
        :>> basis = "CSG-08";
    }

    part <'TB-1'> commandChannel : TrustBoundary {
        doc /* Z2 → Z1 command channel (SPI/USB) */
        :>> zones = ("Z2", "Z1");
        :>> crossing = "Safety mode/param `0xdc`, alternative experience `0xdf`, bus config `0xdb`/`0xde`, relay debug `0xc5`, softloader `0xd1`, CAN TX frames";
        :>> threats = "TS-02, TS-05, TS-12";
        :>> controls = "CSR-011…CSR-016, CSR-021…CSR-024, CSR-061";
    }
    part <'TB-2'> bootControl : TrustBoundary {
        doc /* Z2 → Z1 boot control (GPIO) */
        :>> zones = ("Z2", "Z1");
        :>> crossing = "Panda boot and reset lines driven by the SoC (details: private record GD-03)";
        :>> threats = "TS-03";
        :>> controls = "CSR-041…CSR-043, CSR-051…CSR-054";
    }
    part <'TB-3'> networkBoundary : TrustBoundary {
        doc /* Z4 ↔ Z3 network */
        :>> zones = ("Z4", "Z3");
        :>> crossing = "athena RPCs, uploads, SSH, git updates, AGNOS images, LFS objects";
        :>> threats = "TS-06, TS-07, TS-08, TS-10";
        :>> controls = "CSR-101…CSR-104, CSR-111…CSR-117, CSR-121…CSR-126, CSR-131…CSR-135";
    }
    part <'TB-4'> localIntegrity : TrustBoundary {
        doc /* Z3 → Z2 local integrity */
        :>> zones = ("Z3", "Z2");
        :>> crossing = "Params, msgq, model files, filesystem";
        :>> threats = "TS-04, TS-09, TS-12";
        :>> controls = "CSR-062…CSR-064, CSR-071…CSR-073, CSR-081…CSR-083";
    }
    part <'TB-5'> vehicleCanBoundary : TrustBoundary {
        doc /* Z1 ↔ Z5 vehicle CAN */
        :>> zones = ("Z1", "Z5");
        :>> crossing = "RX plausibility inputs, TX actuation, PCS forwarding";
        :>> threats = "TS-01";
        :>> controls = "CSR-091…CSR-093";
    }
    part <'TB-6'> releaseBoundary : TrustBoundary {
        doc /* Z6 → device */
        :>> zones = "Z6";
        :>> crossing = "Signed images and manifests; release key material never crosses";
        :>> threats = "TS-05, TS-06, TS-10";
        :>> controls = "CSR-031…CSR-034, CSR-121, CSR-126, CSR-135";
    }
    part <'TB-7'> physicalBoundary : TrustBoundary {
        doc /* Z7 physical */
        :>> zones = "Z7";
        :>> crossing = "Data and keys at rest";
        :>> threats = "TS-11, TS-13";
        :>> controls = "CSR-141…CSR-144, CSR-151, CSR-152";
    }
}
