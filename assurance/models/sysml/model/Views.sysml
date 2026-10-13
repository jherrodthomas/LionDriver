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

    view <'V-04'> mechanismAllocation : AllocationView {
        doc /* Safety mechanisms SM-01 to SM-43 against the elements that perform them. */
        expose LionDriverMechanisms::*;
        expose LdSda::**;
        render Views::asElementTable;
    }
}
