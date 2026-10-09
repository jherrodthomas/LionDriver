# Vehicle configurations

Each folder is one vehicle, checked against the [platform's assumptions](../platform/README.md#assumptions-register-first-entries). A vehicle enters LionDriver's assured scope only through a configuration with an impact analysis and its own evidence.

| Configuration | Brand safety mode | Lateral | Longitudinal | Status |
|---|---|---|---|---|
| [Toyota Corolla 2020 LE (U.S.)](toyota-corolla-2020/) | `toyota`, parameter `73` | Torque | openpilot | 🟡 Drafting · first evidence on the safety mode |

## Adding a configuration

1. Copy the structure of an existing configuration.
2. Record the baseline: platform, safety mode, parameters and limits, each with its source in the pinned upstream code.
3. Check every platform assumption and record the result, with evidence.
4. Write the impact analysis: what differs from the platform's worst case, and why it is still covered.
5. Open a pull request. It goes through the [safety change workflow](../README.md#change-workflow).
