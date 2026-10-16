// LionDriver L2 steering plant: a two-inertia column EPS model of the reference Corolla (assurance/sim README §3.5).
// Plain Modelica, no library. Every parameter is an assumption until measured (M-02): see ../column.py.
model SteeringColumn
  // inputs
  input Real T_d(unit = "N.m") "driver torque at the steering wheel";
  input Real T_cmd(unit = "N.m") "LKA motor torque command, referred to the column";
  // parameters
  parameter Real J_sw(unit = "kg.m2") = 0.04 "steering wheel and upper column inertia";
  parameter Real c_sw(unit = "N.m.s/rad") = 0.2 "steering wheel viscous damping";
  parameter Real k_tb(unit = "N.m/rad") = 130 "torsion bar stiffness (the torque sensor)";
  parameter Real c_tb(unit = "N.m.s/rad") = 0.1 "torsion bar damping";
  parameter Real J_l(unit = "kg.m2") = 0.2 "lower column, reflected motor and rack inertia";
  parameter Real c_l(unit = "N.m.s/rad") = 1.0 "lower column and rack viscous damping";
  parameter Real k_r(unit = "N.m/rad") = 200 "rack and tyre aligning stiffness, referred to the column";
  parameter Real tau_m(unit = "s") = 0.12 "motor torque lag (steerActuatorDelay as a first-order lag, as in L1)";
  parameter Real T_m_max(unit = "N.m") = 3.0 "motor torque limit, referred to the column";
  // outputs
  output Real T_tb(unit = "N.m") "torsion bar torque: what the EPS reports as driver torque";
  output Real th_sw(unit = "rad", start = 0, fixed = true) "steering wheel angle";
  output Real th_l(unit = "rad", start = 0, fixed = true) "pinion angle (road wheel angle times the steering ratio)";
  output Real T_m(unit = "N.m", start = 0, fixed = true) "motor torque at the column";
  Real w_sw(unit = "rad/s", start = 0, fixed = true);
  Real w_l(unit = "rad/s", start = 0, fixed = true);
equation
  der(T_m) = (max(-T_m_max, min(T_m_max, T_cmd)) - T_m) / tau_m;
  T_tb = k_tb * (th_sw - th_l) + c_tb * (w_sw - w_l);
  der(th_sw) = w_sw;
  J_sw * der(w_sw) = T_d - T_tb - c_sw * w_sw;
  der(th_l) = w_l;
  J_l * der(w_l) = T_tb + T_m - k_r * th_l - c_l * w_l;
end SteeringColumn;
