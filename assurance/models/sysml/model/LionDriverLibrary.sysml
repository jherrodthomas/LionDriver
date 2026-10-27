package LionDriverLibrary {
    doc
    /*
     * Definitions shared by the LionDriver architecture model: integrity attribution,
     * element classes, port and interface kinds, safety mechanisms and the metadata
     * that ties each model element back to the work product it comes from.
     *
     * Status: draft, AI-assisted (Claude), not reviewed. The model is to become the record
     * of the architecture tables (SY-05, DQ-186); until its review (OI-8) the work products
     * named in the Source metadata stay the record and tools/gen_tables.py checks that the
     * tables they hold are the tables the model generates (assurance/models/sysml/README.md).
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
        // the row of WP-S-03 §3.3, on the first connection of each interface (SY-05)
        attribute label : String[0..1];
        attribute name : String[0..1];
        attribute between : String[0..1];
        attribute content : String[0..1];
        attribute relevance : String[0..1];
        attribute detail : String[0..1];
    }

    metadata def Catalogue {
        doc
        /*
         * The text columns of the element's row in an architecture table generated from the
         * model (SY-05): WP-S-03 §3.1 (name, description, main sources) or WP-W-03 §3.1
         * (name when it is more than the short name, responsibility, files, a note to the build
         * column, ASIL attribution when it says more than the integrity label).
         */
        attribute name : String[0..1];
        attribute description : String;
        attribute sources : String;
        attribute attribution : String[0..1];
        attribute buildNote : String[0..1];
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
        // the other columns of its WP-S-03 §6 row (SY-05)
        attribute element : String;
        attribute status : String;
        attribute latent : String;
    }

    // ------------------------------------------------------------------ functions
    action def ItemFunction {
        doc /* A function of the item (WP-C-01 §2.1), decomposed into the steps of its functional chain. */
    }
    enum def Stage {
        doc /* Position of a step on the functional chain, from sensing to acting on the vehicle or the driver. */
        enum sense;
        enum perceive;
        enum plan;
        enum control;
        enum command;
        enum envelope;
        enum act;
    }
    action def FunctionStep {
        doc /* One step of a function; the element that performs it is where the step runs. */
        attribute stage : Stage;
    }
    // ------------------------------------------------------------------ security architecture
    part def SecurityZone {
        doc /* A security zone of WP-S-07 §3.1: what it holds, its trust level and the goals or claims it rests on. */
        attribute holds : String;
        attribute trust : String;
        attribute basis : String;
    }
    part def TrustBoundary {
        doc /* A trust boundary of WP-S-07 §3.2 between zones, with what crosses it, its threats and its controls. */
        attribute zones : String[1..*];
        attribute crossing : String;
        attribute threats : String;
        attribute controls : String;
    }
    metadata def Zone {
        doc /* The security zone (WP-S-07 §3.1) an element and, unless they name their own, its parts belong to. */
        attribute id : String;
    }
    // ------------------------------------------------------------------ integration
    action def IntegrationStep {
        doc /* A system integration step of WP-S-08 §3.1, with the elements it adds and the interfaces it exercises. */
        attribute elements : String;
        attribute interfaces : String;
        attribute stimulus : String;
        attribute purpose : String;
        attribute integrates : String[0..*];
        attribute exercises : String[0..*];
    }
    // ------------------------------------------------------------------ life cycle
    action def LifecyclePhase {
        doc /* A phase of the installed item's life (WP-S-06 §3); section is the section that lists its requirements. */
        attribute section : String;
    }
    action def ProcedureStep {
        doc /* What the procedures of a phase must achieve to meet one production or operation requirement TSR-8nn. */
        attribute tsr : String;
        attribute asil : String;
        attribute parent : String;
        attribute steps : String;
        attribute record : String;
        attribute status : String;
        attribute statusNote : String;
    }
    // ------------------------------------------------------------------ behaviour
    metadata def ModeRow {
        doc /* The WP-C-01 §4 row of an operating mode, and the record states (machine and state) it stands for. */
        attribute description : String;
        attribute actuation : String;
        attribute host : String[0..*];
        attribute panda : String[0..*];
    }
    metadata def ModeConfigurations {
        doc /* WP-C-01 §4 rows that select a configuration rather than name a mode. */
        attribute rows : String[0..*];
    }
    enum def Enforcer {
        doc /* Who enforces a mode transition (WP-C-01 Figure 4-1). */
        enum envelope;
        enum host;
        enum gap16;
    }
    metadata def Enforcement {
        doc /* Who enforces a transition, and the record transitions (machine and ID) it stands for. */
        attribute kind : Enforcer;
        attribute records : String[0..*];
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
    view def SecurityView {
        doc /* Security zones, the elements in them and the trust boundaries between them. */
    }
    view def IntegrationView {
        doc /* The integration steps in order, with what each adds and exercises and the cases that run at it. */
    }
    view def StateView {
        doc /* A state machine: states, transitions, and who enforces each transition. */
    }
    view def FunctionalView {
        doc /* Functions along their functional chain, each step on the element that performs it. */
    }
    view def UseCaseView {
        doc /* Use cases of the item with their subject and actors. */
    }
    view def ParametricView {
        doc /* Constraints with their parameters bound to value properties of the model. */
    }
    view def ActivityView {
        doc /* An action flow: the actions, the successions between them and what each action carries. */
    }
    view def SequenceView {
        doc /* A sequence of messages between lifelines that stand for elements of the architecture. */
    }
    view def NeedsView {
        doc /* Stakeholder needs and actors against the use cases that serve them, with the requirements that refine each need. */
    }
}
