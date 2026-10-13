function r = tx_rate_model(c, f, burst, factor, onset_s, t_end_s)
  % Model of the per-ID TX-rate check (DN-01, SWSR-518; code: opendbc safety.h tx_rate_check).
  % Frames arrive at f Hz until onset_s, then at factor * f Hz. Authority is granted at t = 0.
  % Returns the budget, accepted mask, frame times, first rejection and revocation time.
  r.budget = ceil(f * c.tx_window_s * 1.2) + 1 + burst;
  t = [0:1/f:onset_s - 1e-9, onset_s:1/(factor * f):t_end_s];
  half = c.tx_window_s / 2;
  msgs = 0; prev = 0; rej = 0; tlast = 0; allowed = true;
  r.revoke_s = NaN; acc = false(size(t));
  for k = 1:numel(t)
    el = t(k) - tlast;
    if el >= half - 1e-12
      if el >= c.tx_window_s - 1e-12, prev = 0; else, prev = msgs; end
      msgs = 0; rej = 0; tlast = t(k);
    end
    if msgs + prev >= r.budget
      rej = rej + 1;
      if allowed && rej >= c.tx_revoke_n, allowed = false; r.revoke_s = t(k); end
    else
      msgs = msgs + 1; acc(k) = true;
    end
  end
  r.t = t; r.accepted = acc;
  i = find(!acc, 1);
  if isempty(i), r.first_reject_s = NaN; else, r.first_reject_s = t(i); end
end
