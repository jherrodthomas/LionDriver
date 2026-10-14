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

    view <'V-06'> f01Requirements : RequirementView {
        doc /* System requirements of F-01 lateral control (WP-S-01 §2), their satisfying elements and verification cases. */
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

    view <'V-04'> mechanismAllocation : AllocationView {
        doc /* Safety mechanisms SM-01 to SM-43 against the elements that perform them. */
        expose LionDriverMechanisms::*;
        expose LdSda::**;
        render Views::asElementTable;
    }
}
