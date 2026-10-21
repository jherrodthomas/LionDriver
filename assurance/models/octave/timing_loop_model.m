function cases = timing_loop_model(k)
  % Timing-loop model of the panda fault detection and warning paths (WP-S-04 §3.7, §4 T-01, T-06, T-06a, T-07a,
  % T-09a, T-28, T-34). For each fault class it sweeps the phase of the fault against every loop that can delay the
  % detection or the warning: the 100 Hz safety task, the 8 Hz tick and its speaker parity (the speaker sounds only on
  % every other tick), the 1 Hz path of the original baseline and the LSI tolerance of the hardware watchdog.
  % t = 0 is the last valid event before the fault (last frame, last heartbeat, last watchdog feed, first EPS fault
  % frame), as WP-S-04 §4 states its times; that is the worst case for the detection time.
  % The reaction after detection (FRTI) is the §3.7 budget: the EPS and PCM response is not modelled (M-02).
  % k: constants from ld_timing_constants.m. Times are integer microseconds inside, seconds in the result.
  % A model of the logic, written from the code; not the C code and not verification evidence.
  T = k.task_us; TK = k.tick_us; S = k.slow_us;
  TP = (1:20) * T / 20;          % first safety-task run after t = 0
  KP = (1:25) * TK / 25;         % first 8 Hz tick after t = 0
  SP = (1:200) * S / 200;        % first 1 Hz pass after t = 0 (baseline)
  PAR = [0 1];                   % parity of that first tick (the speaker sounds on odd ticks)
  cases = struct([]);

  % --- RX loss (TSR-401): reference build, 5 periods, evaluated by the safety task
  for a = {'0x1D2', '0x262'}
    m = k.rx(strcmp({k.rx.addr}, a{1}));
    thr = k.rx_periods_ref * floor(1e6 / m.hz);
    fd = arrayfun(@(p) first_after(thr, p, T), TP);
    cases = add(cases, ['rx-' lower(a{1}(3:end)) '-ref'], sprintf('RX loss %s (%d Hz)', a{1}, m.hz), 'SG-01', ...
                'reference', 0.5, 0.2, 0.1, NaN, fd, [], ...
                sprintf('threshold %d x %.1f ms, strict >, checked by the 100 Hz safety task', ...
                        k.rx_periods_ref, floor(1e6 / m.hz) / 1000));
  end
  % --- RX loss, original baseline: max(10 periods, 1 s), checked in the 1 Hz path
  m = k.rx(strcmp({k.rx.addr}, '0x260'));
  thr = max(10 * floor(1e6 / m.hz), 1e6);
  fd = arrayfun(@(p) first_after(thr, p, S), SP);
  cases = add(cases, 'rx-260-base', sprintf('RX loss 0x260 (%d Hz), baseline', m.hz), 'SG-01', 'baseline 8b8c6ae', ...
              0.5, 0.2, 0.1, NaN, fd, [], 'threshold max(10 periods, 1 s), checked once per second');

  % --- SoC heartbeat loss (TSR-407): revoked at the 30th safety-task run after the last 0xf3; siren (TSR-516(a))
  [fd, wn] = deal([]);
  for p = TP
    det = p + (k.hb_timeout_ticks - 1) * T;
    for q = KP, for par = PAR, fd(end + 1) = det; wn(end + 1) = siren(det, q, par, TK); end, end
  end
  cases = add(cases, 'hb-ref', 'SoC heartbeat loss', 'SG-01', 'reference', 0.5, 0.3, 0.1, 1.0, fd, wn, ...
              sprintf('revoked at the %dth safety-task run; siren on the next odd 8 Hz tick', k.hb_timeout_ticks));
  % --- heartbeat loss, original baseline: counter in the 1 Hz path, SILENT at 5 with ignition on
  fd = SP + (k.hb_silent_cnt_on - 1) * S;
  cases = add(cases, 'hb-base', 'SoC heartbeat loss, baseline', 'SG-01', 'baseline 8b8c6ae', 0.5, 0.3, 0.1, NaN, fd, [], ...
              sprintf('SILENT when the 1 Hz counter reaches %d', k.hb_silent_cnt_on));

  % --- SoC command stall (TSR-408): 0x2E4 older than the timeout, strict >, checked by the safety task; siren
  [fd, wn] = deal([]);
  for p = TP
    det = first_after(k.arrival_lka_us, p, T);
    for q = KP, for par = PAR, fd(end + 1) = det; wn(end + 1) = siren(det, q, par, TK); end, end
  end
  cases = add(cases, 'stall-ref', 'SoC command stall (0x2E4)', 'SG-01', 'reference', 0.5, 0.05, 0.1, 1.0, fd, wn, ...
              sprintf('0x2E4 older than %.0f ms; the revocation sounds the siren (DQ-404 A)', k.arrival_lka_us / 1000));

  % --- MCU hang (TSR-501): IWDG timeout after the last feed, at nominal LSI and 10 % slow
  for f = [1.0 0.9]
    hz = f * k.lsi_nominal_hz;
    fd = round(4 * 2 ^ k.iwdg_pr * (k.iwdg_rlr + 1) / hz * 1e6);
    tag = 'nominal'; if f < 1, tag = 'LSI 10 % slow'; end
    cases = add(cases, sprintf('iwdg-%s', ifelse(f < 1, 'slow', 'nom')), sprintf('MCU hang, IWDG (%s)', tag), 'SG-07', ...
                'reference', 0.2, 0.1, 0.1, NaN, fd, [], sprintf('4 x (%d + 1) / %.1f kHz, hang right after a feed', ...
                k.iwdg_rlr, hz / 1000));
  end

  % --- EPS fault (TSR-110, TSR-516(b)): LKA refused on receipt; siren after 70 safety-task runs of persistence
  [fd, wn] = deal([]);
  for p = TP
    req = p + (k.eps_persist_ticks - 1) * T;
    for q = KP, for par = PAR, fd(end + 1) = 0; wn(end + 1) = siren(req, q, par, TK); end, end
  end
  cases = add(cases, 'eps-ref', 'EPS fault -> siren', 'SG-02', 'reference', 1.0, 0.5, 0.5, 1.0, fd, wn, ...
              sprintf('refused on the first fault frame; siren after %d task runs, next odd tick', k.eps_persist_ticks));
end

function v = first_after(t, phase, P)
  % first time phase + n * P (n >= 0) strictly after t
  if phase > t, v = phase; else, v = phase + (floor((t - phase) / P) + 1) * P; end
end

function v = siren(req, phase, par, TK)
  % first 8 Hz tick strictly after req on which the speaker sounds (odd tick counter)
  m = 0; if phase <= req, m = floor((req - phase) / TK) + 1; end
  if mod(par + m, 2) == 0, m = m + 1; end
  v = phase + m * TK;
end

function cases = add(cases, id, label, sg, build, ftti, fdti_b, frti_b, warn_b, fd_us, wn_us, rule)
  c.id = id; c.label = label; c.sg = sg; c.build = build; c.rule = rule;
  c.ftti = ftti; c.fdti_budget = fdti_b; c.frti_budget = frti_b; c.warn_budget = warn_b;
  c.fdti_min = min(fd_us) / 1e6; c.fdti_max = max(fd_us) / 1e6;
  c.fhti_max = c.fdti_max + frti_b;
  if isempty(wn_us), c.warn_min = NaN; c.warn_max = NaN; else, c.warn_min = min(wn_us) / 1e6; c.warn_max = max(wn_us) / 1e6; end
  c.samples = numel(fd_us);
  c.fdti_samples = fd_us / 1e6;
  if isempty(cases), cases = c; else, cases(end + 1) = c; end
end

function r = ifelse(c, a, b)
  if c, r = a; else, r = b; end
end
