# Work product versions

Every work product of the [assurance record](../assurance/README.md) with its current version, status and the date
it last changed. Versions here: {{LEDGER_SOURCE}}.

Nobody types these numbers. Each version is computed by the [change ledger](../assurance/07-supporting/ledger/README.md)
from the merged changes, in the form **X.Y.Z**:

| Part | Goes up when | Resets |
|---|---|---|
| **X** | A gate approves the work product (recorded in [gate-approvals.yaml](../assurance/07-supporting/ledger/gate-approvals.yaml)). 0 means not yet approved | Y and Z |
| **Y** | A merged change alters its content | Z |
| **Z** | A merged change only fixes wording, links or layout (label `editorial`) | |

The ledger started from the version each header carried at the time (0.68 became 0.68.0), so a work product with
X above 0 that no gate has approved kept that number from before the ledger. A version shown as `0.68.0+1` has one
change the ledger has not recorded yet; it catches up at the next ledger run.

The same version is printed on every exported copy of a work product, with a footer on each page and its revision
history ([how to export](../assurance/07-supporting/ledger/README.md#exporting-a-work-product)). The status is the one
in the work product's own header.

{{WP_VERSIONS}}

Built at `{{SYNC_COMMIT}}`, {{SYNC_DATE}}.
