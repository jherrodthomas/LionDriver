package LionDriverViews {
    doc
    /*
     * The views drawn from the model. Each view says what it exposes and how it is
     * rendered; tools/render_views.py draws it with the layout of the same name in
     * views/layout.toml. A figure is never edited by hand: change the model or the
     * layout and regenerate.
     */

    private import LionDriverLibrary::*;
    private import LionDriverArchitecture::*;
    private import LionDriverMechanisms::*;

    view <'V-01'> itemContext : ContextView {
        doc /* LD-SDA, its components and the vehicle elements, people and networks outside it. */
        expose OperationalContext::*;
        expose LdSda::*;
        render Views::asInterconnectionDiagram;
    }

    view <'V-02'> elementHierarchy : DecompositionView {
        doc /* Item, components, parts and software units with their integrity attribution. */
        expose LdSda::**;
        render Views::asTreeDiagram;
    }

    view <'V-03'> systemInterconnection : InterconnectionView {
        doc /* Technical safety architecture: QM partition, safety envelope, interfaces IF-01 to IF-10. */
        expose LdSda::**;
        expose OperationalContext::*;
        render Views::asInterconnectionDiagram;
    }

    view <'V-05'> requirementThread : ThreadView {
        doc /* TSR-407 (heartbeat loss) from its safety goals to its verification cases. */
        expose LionDriverRequirements::tsr_407;
        render Views::asTreeDiagram;
    }

    view <'V-06'> functionRequirements : RequirementView {
        doc /* One requirement diagram per function F-01 to F-09: its system requirements (WP-S-01 §2–§9), the needs they derive from, their satisfying elements and verification cases. */
        expose LionDriverRequirements::*;
        expose LionDriverSatisfaction::*;
        expose LionDriverVerification::*;
        render Views::asTreeDiagram;
    }

    view <'V-07'> systemRequirementMatrix : RequirementMatrixView {
        doc /* All system requirements of WP-S-01 against satisfying elements and verification cases. */
        expose LionDriverRequirements::*;
        expose LionDriverSatisfaction::*;
        expose LionDriverVerification::*;
        render Views::asElementTable;
    }

    view <'V-08'> interfaceN2 : InterconnectionView {
        doc /* N2 chart: which component or outside element sends to which, over which interface (IF-01 to IF-10). */
        expose LdSda::**;
        expose OperationalContext::*;
        render Views::asElementTable;
    }

    view <'V-09'> verificationMatrix : RequirementMatrixView {
        doc /* Verification cross-reference matrix: SYS, TSR and CSR requirements by verification method and by the level of the cases that verify them. */
        expose LionDriverRequirements::*;
        expose LionDriverVerification::*;
        render Views::asElementTable;
    }

    view <'V-04'> mechanismAllocation : AllocationView {
        doc /* Safety mechanisms SM-01 to SM-43 against the elements that perform them. */
        expose LionDriverMechanisms::*;
        expose LdSda::**;
        render Views::asElementTable;
    }

    view <'V-10'> functionalArchitecture : FunctionalView {
        doc /* Functional architecture: the functions F-01 to F-09 along their functional chain, each step on the element that performs it. */
        expose LionDriverFunctions::**;
        expose LdSda::**;
        render Views::asElementTable;
    }

    view <'V-11'> securityZones : SecurityView {
        doc /* Security zones Z1 to Z7 of WP-S-07 §3.1 with the model elements in them, and the trust boundaries TB-1 to TB-7 of §3.2. */
        expose LionDriverSecurity::*;
        expose LdSda::**;
        render Views::asElementTable;
    }

    view <'V-12'> integrationBuildUp : IntegrationView {
        doc /* System integration build-up: the steps I-1 to I-4 of WP-S-08 §3.1, the elements each adds, the interfaces it exercises and the cases that run at it. */
        expose LionDriverIntegration::*;
        expose LionDriverVerification::*;
        expose LdSda::**;
        render Views::asElementTable;
    }

    view <'V-13'> systemModes : StateView {
        doc /* System modes: the operating modes of WP-C-01 §4 as a state machine, each transition with the record transitions it stands for and who enforces it. */
        expose LionDriverBehaviour::**;
        render Views::asInterconnectionDiagram;
    }

    view <'V-14'> needsUseCases : NeedsView {
        doc /* Stakeholder needs SN-01 to SN-12 and actors of WP-S-01 §1.2 and §1.3 against the use cases UC-01 to UC-11 of §1.4, the requirements that refine each need and the functions each use case performs. */
        expose LionDriverNeeds::*;
        expose LionDriverRequirements::*;
        expose LionDriverFunctions::*;
        render Views::asElementTable;
    }

    view <'V-15'> endToEndThread : ThreadView {
        doc /* SN-01 end to end: stakeholder, need, use case, functions and the elements that perform them; system requirements, satisfying elements and verification cases. */
        expose LionDriverNeeds::sn_01;
        expose LionDriverNeeds::uc_01;
        expose LionDriverRequirements::*;
        expose LionDriverSatisfaction::*;
        expose LionDriverVerification::*;
        expose LionDriverFunctions::**;
        expose LdSda::**;
        render Views::asTreeDiagram;
    }

    view <'V-16'> stateMachineRecords : StateView {
        doc /* The state-machine records of WP-W-05 §5 (SM-SAFETY-MODE, SM-TOY-AUTH, SM-SELFDRIVED): states, record transitions, status and SWSRs. */
        expose LionDriverStateRecords::**;
        render Views::asElementTable;
    }

    view <'V-17'> startupSequence : SequenceView {
        doc /* The start-up and engagement sequence of WP-S-03 §4.1 (Table 4-1): lifelines, steps, conditions and the states they lead to. */
        expose LionDriverSequences::**;
        expose LdSda::**;
        render Views::asInterconnectionDiagram;
    }

    view <'V-18'> timingBudgets : AllocationView {
        doc /* The FTTI budgets of WP-S-04 §3.7: FDTI and FRTI against the FTTI per safety goal and fault class, with the elements their TSRs are allocated to. */
        expose LionDriverTiming::*;
        expose LionDriverRequirements::*;
        expose LionDriverSatisfaction::*;
        render Views::asElementTable;
    }

    view <'V-19'> hsiSignals : InterconnectionView {
        doc /* The safety-relevant signals of WP-S-05 §11 with their owner elements, protection, TSRs and test cases. */
        expose LionDriverSignals::*;
        expose LdSda::**;
        render Views::asElementTable;
    }

    view <'V-20'> hsiResponsibilities : InterconnectionView {
        doc /* The hardware and software responsibilities of WP-S-05 §11.4 per interface: what each side provides and must do, their owner elements, who detects a failure and the reaction. */
        expose LionDriverSignals::*;
        expose LdSda::**;
        render Views::asElementTable;
    }

    view <'V-21'> useCases : UseCaseView {
        doc /* Use case diagram: LD-SDA as the subject, the use cases UC-01 to UC-11 of WP-S-01 §1.4 and the actors that take part in them. */
        expose LionDriverNeeds::*;
        render Views::asInterconnectionDiagram;
    }

    view <'V-22'> tsrBlocks : RequirementView {
        doc /* One requirement diagram per TSR block of WP-S-02: each TSR with the FSRs it derives from, its satisfying elements, the mechanisms that cite it and its verification cases. */
        expose LionDriverRequirements::*;
        expose LionDriverSatisfaction::*;
        expose LionDriverVerification::*;
        expose LionDriverMechanisms::*;
        render Views::asTreeDiagram;
    }
}
