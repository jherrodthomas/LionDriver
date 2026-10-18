package LionDriverLibrary {
    doc
    /*
     * Definitions shared by the LionDriver architecture model: integrity attribution,
     * element classes, port and interface kinds, safety mechanisms and the metadata
     * that ties each model element back to the work product it comes from.
     *
     * Status: draft, AI-assisted (Claude), not reviewed. The work products named in
     * the Source metadata stay the documents of record (assurance/models/sysml/README.md).
     */

    private import ScalarValues::*;

    // ------------------------------------------------------------------ attribution

    enum def Integrity {
        doc /* Integrity attribution of an element, in the notation of WP-S-02 §2.1. */
        enum QM;
        enum QMBsup;
        enum B;
        enum BDagger;
        enum C;
        enum AoU;
        enum Untrusted;
    }

    enum def Scope {
        doc /* Whether an element belongs to the item (WP-C-01 §3). */
        enum inside;
        enum outside;
        enum excluded;
    }

    enum def Build {
        doc /* Which firmware build carries the element (WP-W-03 §3.1, column Build). */
        enum both;
        enum reference;
    }

    metadata def Safety {
        doc /* Integrity attribution; label is the text the work product uses. */
        attribute integrity : Integrity;
        attribute label : String;
    }

    metadata def Boundary {
        doc /* Position of an element relative to the item boundary. */
        attribute scope : Scope;
    }

    metadata def Source {
        doc /* The work product, and the clause in it, that this element is copied from. */
        attribute workProduct : String;
        attribute clause : String;
        attribute paths : String[0..*];
    }

    metadata def Unit {
        doc /* Software unit of WP-W-06 §2 that an element belongs to, and its build scope. */
        attribute id : String;
        attribute build : Build;
    }

    metadata def InterfaceId {
        doc
        /*
         * Identifier of the work-product interface (IF-nn) a connection realises. One
         * interface can be realised by several connections, so the identifier is
         * metadata rather than the short name.
         */
        attribute id : String;
        attribute route : String[0..*];
        attribute tsr : String[0..*];
    }

    metadata def FfiClaim {
        doc /* Freedom-from-interference claims (WP-S-03 §7) that this connection crosses. */
        attribute claims : String[1..*];
    }

    // ------------------------------------------------------------------ element classes

    part def Element {
        doc /* Any element of ISO 26262-1:2018 3.39 (system, component, hardware part, software unit). */
    }
    part def HardwareElement :> Element;
    part def SoftwareElement :> Element;
    part def MlElement :> Element;
    part def ExternalElement :> Element {
        doc /* Existing vehicle element or environment outside the item. */
    }
    part def Person :> ExternalElement;

    // ------------------------------------------------------------------ ports

    port def CanPort { doc /* Attachment to a CAN bus. */ }
    port def SpiPort { doc /* SPI link between the SoC and the safety MCU. */ }
    port def GpioPort { doc /* Discrete control line. */ }
    port def ImagePort { doc /* Camera image stream. */ }
    port def HmiPort { doc /* Visual or audible information exchanged with the driver. */ }
    port def PowerPort { doc /* 12 V supply and ignition sense. */ }
    port def NetworkPort { doc /* Wi-Fi or LTE network attachment. */ }
    port def SensorPort { doc /* Sensor message stream. */ }

    // ------------------------------------------------------------------ interfaces

    interface def CanLink {
        doc /* A CAN connection; direction is from source to target. */
        end port source : CanPort;
        end port target : CanPort;
    }
    interface def SpiLink {
        end port host : SpiPort;
        end port device : SpiPort;
    }
    interface def GpioLink {
        end port driver : GpioPort;
        end port receiver : GpioPort;
    }
    interface def ImageLink {
        end port source : ImagePort;
        end port target : ImagePort;
    }
    interface def HmiLink {
        end port source : HmiPort;
        end port target : HmiPort;
    }
    interface def PowerLink {
        end port supply : PowerPort;
        end port load : PowerPort;
    }
    interface def NetworkLink {
        end port device : NetworkPort;
        end port peer : NetworkPort;
    }
    interface def SensorLink {
        end port source : SensorPort;
        end port target : SensorPort;
    }

    connection def DataFlow {
        doc /* A cereal service from its publisher to one subscriber (WP-S-03 §9). */
        end part publisher : Element;
        end part subscriber : Element;
        attribute service : String;
        attribute rateHz : Real;
    }

    // ------------------------------------------------------------------ safety mechanisms

    action def SafetyMechanism {
        doc /* A safety mechanism of the WP-S-03 §6 catalogue; elements perform it. */
        attribute covers : String;
        attribute dcTarget : String;
        attribute tsr : String[0..*];
    }

    // ------------------------------------------------------------------ views

    view def ContextView {
        doc /* The item, its boundary and the elements outside it (WP-C-01 §3). */
    }
    view def DecompositionView {
        doc /* Item, system, components, parts and units (ISO 26262-1 3.39). */
    }
    view def InterconnectionView {
        doc /* Parts, ports and the interfaces between them. */
    }
    view def AllocationView {
        doc /* Which element performs which safety mechanism. */
    }
    view def ThreadView {
        doc /* One requirement with everything related to it: what it derives from, what satisfies it, the mechanisms that cite it and the cases that verify it. */
    }
    view def RequirementView {
        doc /* The requirements of one function with their satisfying elements and verification cases. */
    }
    view def RequirementMatrixView {
        doc /* Requirements against the elements that satisfy them and the cases that verify them. */
    }
}
