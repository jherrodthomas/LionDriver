# How LionDriver works

The other pages explain how LionDriver is assured. This one explains the product they are about: how the device
connects to the car, how one steering command travels from the camera to the steering motor, and what the safety
envelope on the panda checks on the way. It explains and links. The engineering record is the
[architecture, WP-S-03](../assurance/03-system/WP-S-03-technical-safety-concept-architecture.md), the
[technical safety requirements, WP-S-02](../assurance/03-system/WP-S-02-technical-safety-requirements.md) and the
[timing analysis, WP-S-04](../assurance/03-system/WP-S-04-timing-ftti-budget.md); the car is the
[reference vehicle](Reference-vehicle.md).

> [!IMPORTANT]
> LionDriver is a supervised driver-assistance system. The driver must stay attentive and in control at all
> times. The figures show how the system is designed to behave; nothing here is verified on the car yet.

Every figure is drawn at each wiki sync by [`tools/wiki/how_animations.py`](../tools/wiki/how_animations.py). The
envelope limits are read from the calibration record ([WP-W-09](../assurance/05-software/WP-W-09-configuration-calibration-data.md)
CD-02), the stall times and the forwarding rule from WP-S-02, the FTTI from WP-S-04 §3.7 and the status of each
requirement from the [TSR list](../assurance/03-system/requirements/tsr-list.md). Every other phrase is checked
against its record, and the limits against the panda code when it is checked out. When a record changes, the build
fails instead of showing old text.

## 1. How it connects to the car

![Animated: the stock camera talking to the car over one cable; the harness splitting that cable into a camera side and a car side; the panda blocking the camera's steering frames and forwarding PCS braking and everything else; openpilot's steering going out through the panda](how-hookup.svg)

On the reference car, the forward camera behind the mirror does Toyota's own lane keeping and pre-collision
braking (PCS), and talks to the rest of the car over one connector. The harness plugs in at that connector and
splits it: the camera on one side (bus 2), the car on the other (bus 0). The panda, the safety microcontroller in
the comma device, sits between them. It forwards everything the camera says except its steering, lane-display and cruise
commands, so the car's own PCS braking keeps working, and sends openpilot's steering in their place. If the device
faults or is unplugged, a relay in the harness drops and the camera is connected straight to the car again.

## 2. The life of one steering command

![Animated: a camera frame flowing through the driving model, planner, controls and car interface to the panda and the steering motor; then a clock showing when the panda revokes authority if the chain stalls, against the FTTI](how-one-command.svg)

The main computer (the SoC) runs openpilot: the driving model reads the camera, the planner picks a path, the
controls turn it into a steering torque, and the car interface packs it into a CAN message. None of that is
safety-rated (QM). The panda is: it checks every message before the car sees it. If the chain stalls, the panda
does not wait for the SoC to notice. It counts the time since the last good message and takes authority back well
before the **FTTI**, the time after which a fault could first lead to a hazardous drift.

## 3. The panda: the gate every command passes

![Animated: five steering commands meeting the panda's per-frame checks; one passes and four are blocked: over the torque cap, too fast a rise, not engaged and driver braking](how-envelope.svg)

Each steering frame must pass every check, every time. A blocked frame never reaches the steering motor. The
limits are fixed numbers in the firmware; the figure also says which planned checks are not implemented yet, read
from the TSR list. [Hardware safety and interference](Hardware-safety-and-interference.md) explains why the panda
can be trusted when the SoC cannot, and [From hazard to test](From-hazard-to-test.md) follows one of these limits
from the hazard it answers to the test that checks it.

## See also

- [Reference vehicle](Reference-vehicle.md): the car, the device and what the configuration fixes.
- [Integrated standards](Integrated-standards.md): what each standard asks of the same envelope.
- [Glossary](Glossary.md) for the work product and ID codes.
