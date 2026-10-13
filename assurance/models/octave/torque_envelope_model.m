function r = torque_envelope_model(c, req)
  % Model of the Toyota torque rate and magnitude limits (code: opendbc modes/toyota.h
  % TOYOTA_TORQUE_STEERING_LIMITS, lateral.h). One element of req per 10 ms frame.
  % The host is modelled as clipping its own command to what the envelope accepts; the real-time
  % (max_rt_delta) and measured-torque checks are not modelled.
  out = zeros(size(req)); last = 0;
  for k = 1:numel(req)
    d = req(k) - last;
    if d > 0, step = min(d, c.max_rate_up); else, step = max(d, -c.max_rate_down); end
    out(k) = min(max(last + step, -c.max_torque), c.max_torque);
    last = out(k);
  end
  r.out = out;
end
