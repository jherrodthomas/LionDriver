# Vehicle compatibility

<p align="center">
  <img src="../assets/liondriver/assurance/ecosystem.svg" width="100%" alt="Vehicle ecosystem card generated from the assurance records: the number of upstream-compatible car models, the number of LionDriver-evaluated configurations and the number of assurance-supported configurations.">
</p>

LionDriver keeps the vehicle support of the openpilot version it pins. The authoritative list is [`docs/CARS.md`](../CARS.md), which upstream generates from the car ports in `opendbc`. LionDriver does not edit it.

> **Vehicle compatibility does not imply independent safety assurance.**
> A car that openpilot supports has not, by that fact, been analysed, verified or reviewed by LionDriver, and no vehicle is approved for unsupervised operation.

## Three classifications

| Classification | Meaning | How a configuration gets there |
|---|---|---|
| **Upstream Compatible** | Supported by the inherited openpilot integration | Listed in `docs/CARS.md` at the pinned upstream version |
| **LionDriver Evaluated** | Undergoing or completed documented engineering evaluation | A configuration record in [`assurance/case-records/configurations/`](../../assurance/case-records/configurations/) with an item definition and an impact analysis against the platform assumptions |
| **Assurance Supported** | Defined configuration with accepted evidence for specific safety claims | At least one claim for that configuration accepted through a recorded review; the validator refuses the classification otherwise |

The counts on this page and in the README are generated from those sources by [`generate_dashboard.py`](../../assurance/case-records/tools/generate_dashboard.py), so they cannot drift from the records.

## Current configurations

| ID | Configuration | Classification | State |
|---|---|---|---|
| [CFG-001](../../assurance/case-records/configurations/cfg-001-toyota-corolla-e210.yaml) | Corolla E210 · ZRE212 · US: Toyota Corolla sedan, US, model years 2020–2022, 1.8 L CVT, Toyota Safety Sense 2.0 ([register](vehicles/README.md#cfg-001--corolla-e210--zre212--us)) | LionDriver Evaluated | Evaluation in progress; no accepted claims |

The Corolla is the reference configuration for the first assurance work. It is a starting point, not a limit on the vehicles LionDriver supports.

The exact vehicles a configuration covers (model years, model code, powertrain, trims, ECU firmware) and what it excludes are recorded in the [vehicle register](vehicles/README.md), which the assurance records cite by ID.

## Adding a configuration

1. Copy [`cfg-001-toyota-corolla-e210.yaml`](../../assurance/case-records/configurations/cfg-001-toyota-corolla-e210.yaml) to a new `CFG-nnn` record with `classification: liondriver-evaluated` and `evaluation_state: in-progress`.
2. Add the vehicle facts to the [vehicle register](vehicles/vehicles.yaml) under the same ID (codename, model years, model code, powertrain, firmware set, exclusions), then run `python3 tools/vehicles/vehicle_register.py`.
3. Record the configuration baseline: car platform, brand safety mode and parameters, each with its source in the pinned upstream code.
4. Write the [impact analysis](../../assurance/01-management/WP-M-12-impact-analysis.md): which assumptions of use hold for this vehicle, which differ, and what evidence each needs.
5. Run `python3 assurance/case-records/tools/validate.py` and `python3 assurance/case-records/tools/generate_dashboard.py`, then open a pull request.

Upstream car-port changes arrive through submodule updates and are handled by the [upstream management](../../assurance/01-management/WP-M-11-upstream-and-supplier-management.md) process, not edited in this repository.
