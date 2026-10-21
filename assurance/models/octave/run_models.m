% LionDriver envelope models in GNU Octave (MATLAB syntax). RR-2026-009 follow-up; WP-P-07 TL-25.
% Usage, from the repository root:  octave-cli --no-gui assurance/models/octave/run_models.m [out_dir]
% Models of the logic, written from the code and DN-01. They are NOT the C code and NOT verification
% evidence. Constants are read from opendbc at the pinned commit (ld_constants.m), so a code change that
% the models do not follow makes this script fail. Exit status 1 if any model check fails.
1;
here = fileparts(mfilename('fullpath'));
addpath(here);
repo = fullfile(here, '..', '..', '..');
args = argv();
if numel(args) >= 1, out_dir = args{end}; else, out_dir = fullfile(tempdir(), 'liondriver-octave'); end
if !exist(out_dir, 'dir'), mkdir(out_dir); end
fails = {};
function fails = check(fails, ok, msg)
  if ok, printf('  pass  %s\n', msg); else, printf('  FAIL  %s\n', msg); fails{end + 1} = msg; end
end

c = ld_constants(repo);
printf('Constants from opendbc: max_torque %d, rate up/down %d/%d, rt delta %d, TX window %.0f ms, revoke after %d rejections, %d TX-rate rows\n', ...
       c.max_torque, c.max_rate_up, c.max_rate_down, c.max_rt_delta, 1000 * c.tx_window_s, c.tx_revoke_n, numel(c.tx_checks));

%% 1. TX-rate supervision (DN-01, SWSR-518), every row of toyota_tx_rate_checks
printf('\n1. TX-rate supervision\n');
for i = 1:numel(c.tx_checks)
  row = c.tx_checks(i);
  nominal = tx_rate_model(c, row.frequency, row.burst, 1, 1.0, 2.0);
  fails = check(fails, all(nominal.accepted), sprintf('%s: no rejection at the nominal %d Hz (budget %d per %.0f ms)', ...
                row.addr, row.frequency, nominal.budget, 1000 * c.tx_window_s));
end
lka = c.tx_checks(strcmp({c.tx_checks.addr}, '0x2E4'));
r2 = tx_rate_model(c, lka.frequency, lka.burst, 2, 0.5, 1.0);
printf('  0x2E4 at 2x from 0.5 s: first rejection %.3f s, revocation %.3f s (%.0f ms after the first rejection, %.0f ms after onset)\n', ...
       r2.first_reject_s, r2.revoke_s, 1000 * (r2.revoke_s - r2.first_reject_s), 1000 * (r2.revoke_s - 0.5));
fails = check(fails, r2.revoke_s - r2.first_reject_s <= 0.1, 'revocation <= 0.1 s after the first rejected frame (SWSR-518 acceptance, model)');
r2e = tx_rate_model(c, lka.frequency, lka.burst, 2, 0.0, 0.5);
printf('  0x2E4 at 2x from an empty window: revocation %.0f ms after onset (DN-01 estimates about 190 ms)\n', 1000 * r2e.revoke_s);

%% 2. Torque envelope (TOYOTA_TORQUE_STEERING_LIMITS)
printf('\n2. Steering torque envelope\n');
req = [zeros(1, 20), 2000 * ones(1, 120), zeros(1, 60)];
te = torque_envelope_model(c, req);
k_max = find(te.out >= c.max_torque, 1);
printf('  step request 2000 raw: %d raw reached after %d frames; released to 0 in %d frames\n', ...
       c.max_torque, k_max - 21, find(te.out(141:end) == 0, 1));
fails = check(fails, max(abs(te.out)) <= c.max_torque, 'permitted torque never exceeds max_torque');
fails = check(fails, all(diff([0 te.out]) <= c.max_rate_up) && all(diff([0 te.out]) >= -c.max_rate_down), 'per-frame change within +rate_up / -rate_down');

%% 3. Authority state machine scenario (state-machines/sm-toy-auth.yaml)
printf('\n3. Authority state machine scenario\n');
sm = fileread(fullfile(repo, 'assurance', '05-software', 'state-machines', 'sm-toy-auth.yaml'));
ev = {1.0, 'T1', 'cruise on'; 3.0, 'T3', 'brake'; 4.0, 'T1', 'cruise on'; 6.3, 'T10a', 'no heartbeat for 0.3 s'};
for i = 1:rows(ev)
  fails = check(fails, !isempty(regexp(sm, ['\{id: ' ev{i, 2} ','], 'once')), sprintf('transition %s exists in sm-toy-auth.yaml', ev{i, 2}));
end
ts = 0:0.01:8; ca = zeros(size(ts)); ca(ts >= 1.0 & ts < 3.0) = 1; ca(ts >= 4.0 & ts < 6.3) = 1;

%% 4. Timing loops (WP-S-04 §3.7, §4): detection and warning times swept over the loop phases
printf('\n4. Timing loops\n');
kt = ld_timing_constants(repo);
tc = timing_loop_model(kt);
for x = tc
  printf('  %-34s FDTI %.4f-%.4f s (budget %.2f)  FHTI <= %.4f s (FTTI %.1f)', x.label, x.fdti_min, x.fdti_max, ...
         x.fdti_budget, x.fhti_max, x.ftti);
  if !isnan(x.warn_max), printf('  warning %.4f-%.4f s (budget %.1f)', x.warn_min, x.warn_max, x.warn_budget); end
  printf('\n');
end
% the model must reproduce the code-derived times of WP-S-04 §4 (within 10 ms; the document rounds up to one task
% period or tick). A disagreement means the model, the code or the document has moved.
doc = {'rx-1d2-ref', 'fdti_max', 0.162, 'T-01 0x1D2 <= 0.162 s'; 'rx-262-ref', 'fdti_max', 0.21, 'T-01 0x262 ~0.21 s'; ...
       'rx-260-base', 'fdti_max', 2.0, 'T-01 baseline 1-2 s (upper)'; 'rx-260-base', 'fdti_min', 1.0, 'T-01 baseline 1-2 s (lower)'; ...
       'hb-ref', 'fdti_max', 0.31, 'T-06a <= 0.31 s'; 'hb-ref', 'warn_max', 0.56, 'T-07a siren ~0.56 s'; ...
       'hb-base', 'fdti_max', 5.0, 'T-06 4-5 s (upper)'; 'hb-base', 'fdti_min', 4.0, 'T-06 4-5 s (lower)'; ...
       'stall-ref', 'fdti_max', 0.06, 'T-34 <= 0.06 s'; 'stall-ref', 'warn_max', 0.31, 'T-34 siren <= 0.31 s'; ...
       'iwdg-nom', 'fdti_max', 0.09, 'T-09a ~90 ms nominal'; 'eps-ref', 'warn_max', 0.96, 'T-28 siren <= 0.96 s'};
for i = 1:rows(doc)
  x = tc(strcmp({tc.id}, doc{i, 1}));
  v = x.(doc{i, 2});
  fails = check(fails, abs(v - doc{i, 3}) <= 0.0101, sprintf('model %s %s = %.4f s agrees with WP-S-04 %s', ...
                doc{i, 1}, doc{i, 2}, v, doc{i, 4}));
end
% the reference-build FDTI overruns are exactly the documented ones: 0x262 at 25 Hz (T-01), the command stall up to one
% task period over 50 ms (T-34), and the IWDG only if the LSI is slower than 10 % (T-09a, OI-2). A new overrun, or one
% that is fixed, fails here so the document is updated
ref = tc(strcmp({tc.build}, 'reference'));
over = sort({ref(arrayfun(@(x) x.fdti_max > x.fdti_budget + 1e-9, ref)).id});
fails = check(fails, isequal(over, sort({'rx-262-ref', 'stall-ref'})), ...
              sprintf('reference-build FDTI overruns are the documented ones (0x262 T-01, stall T-34): %s', strjoin(over, ', ')));
fails = check(fails, abs(tc(strcmp({tc.id}, 'iwdg-slow')).fdti_max - 0.1) <= 1e-6, ...
              'IWDG reaches the 0.1 s budget exactly at a 10 % slow LSI (T-09a, watchdog impact record OI-2)');
fails = check(fails, all(arrayfun(@(x) x.fhti_max <= x.ftti + 1e-9, ref)), 'reference build: every FHTI within its FTTI');
% committed results, read by assurance/models/figures/fig_timing_anim.py
csv = timing_csv(tc);
committed = fullfile(here, 'timing_loop_results.csv');
fid = fopen(fullfile(out_dir, 'timing_loop_results.csv'), 'w'); fputs(fid, csv); fclose(fid);
if strcmp(getenv('LD_TIMING_UPDATE'), '1')
  fid = fopen(committed, 'w'); fputs(fid, csv); fclose(fid); printf('  wrote %s\n', committed);
end
fails = check(fails, exist(committed, 'file') && strcmp(fileread(committed), csv), ...
              'timing_loop_results.csv is current (else: LD_TIMING_UPDATE=1 octave-cli ... run_models.m)');

%% Plots
graphics_toolkit('gnuplot');
set(0, 'defaulttextinterpreter', 'none'); set(0, 'defaultaxesticklabelinterpreter', 'none');
ink = [0.055 0.10 0.17]; gold = [0.66 0.51 0.10]; blue = [0.12 0.43 0.88]; grey = [0.45 0.50 0.58]; red = [0.78 0.2 0.2];
h = figure('visible', 'off', 'position', [0 0 1500 1050]);
subplot(3, 1, 1); hold on;
plot(r2.t(r2.accepted), 1 + 0 * r2.t(r2.accepted), 'o', 'color', blue, 'markerfacecolor', blue, 'markersize', 3);
plot(r2.t(!r2.accepted), 0.5 + 0 * r2.t(!r2.accepted), 'x', 'color', gold, 'markersize', 6, 'linewidth', 1.5);
plot([r2.revoke_s r2.revoke_s], [0 1.5], '-', 'color', red, 'linewidth', 2); plot([0.5 0.5], [0 1.5], '--', 'color', grey);
text(0.02, 1.3, 'accepted (blue) / rejected (gold)', 'color', ink);
text(r2.revoke_s + 0.01, 1.3, sprintf('revoked %.0f ms after first rejection', 1000 * (r2.revoke_s - r2.first_reject_s)), 'color', red);
text(0.51, 0.2, '2x flood starts', 'color', grey); set(gca, 'ytick', []); xlim([0 1]); ylim([0 1.5]);
title(sprintf('TX-rate supervision of 0x2E4: budget %d frames / %.0f ms (DN-01, SWSR-518)', r2.budget, 1000 * c.tx_window_s), 'color', gold); xlabel('time (s)');
subplot(3, 1, 2); hold on; k = (1:numel(req)) / 100;
plot(k, req, '--', 'color', grey, 'linewidth', 1.5); plot(k, te.out, '-', 'color', blue, 'linewidth', 2.5);
plot([0 2], [c.max_torque c.max_torque], ':', 'color', gold, 'linewidth', 1.5); ylim([-100 2200]);
title(sprintf('Steering torque envelope: max %d raw, +%d / -%d raw per frame (TOYOTA_TORQUE_STEERING_LIMITS)', c.max_torque, c.max_rate_up, c.max_rate_down), 'color', gold);
xlabel('time (s)'); ylabel('torque (raw)'); legend({'requested', 'permitted by envelope', 'max torque'}, 'location', 'northeast');
subplot(3, 1, 3); hold on; stairs(ts, ca, '-', 'color', blue, 'linewidth', 2.5);
for i = 1:rows(ev), plot([ev{i, 1} ev{i, 1}], [0 1.25], ':', 'color', grey); text(ev{i, 1} + 0.05, 1.15 - 0.12 * mod(i, 2), [ev{i, 2} ' ' ev{i, 3}], 'color', ink); end
set(gca, 'ytick', [0 1], 'yticklabel', {'NOT ALLOWED', 'ALLOWED'}); ylim([-0.1 1.3]); xlim([0 8]);
title('Authority state machine SM-TOY-AUTH: scripted scenario', 'color', gold); xlabel('time (s)');
png = fullfile(out_dir, 'liondriver-octave-models.png'); print(h, '-dpng', '-r110', png);
printf('\nwrote %s\n', png);

% timing ladder: per case the swept FDTI (every phase as a dot), the FRTI budget after the worst FDTI, the warning
% range and the FTTI, on 0..1.2 s; later times are clipped and printed
teal = [0.06 0.46 0.43]; orange = [0.76 0.25 0.05]; xmax = 1.2;
h2 = figure('visible', 'off', 'position', [0 0 1500 900]); hold on;
n = numel(tc);
for i = 1:n
  x = tc(i); y = n + 1 - i;
  d = min(x.fdti_samples, xmax);
  plot([0 min(x.fdti_max, xmax)], [y y], '-', 'color', teal, 'linewidth', 9);
  plot(d, y + 0 * d, 'o', 'color', ink, 'markersize', 2);
  if x.fdti_max < xmax && isnan(x.warn_max) || (x.fdti_max > 0 && x.fdti_max < xmax)
    plot([x.fdti_max min(x.fhti_max, xmax)], [y y], '-', 'color', orange, 'linewidth', 9);
  end
  if !isnan(x.warn_max)
    plot([min(x.warn_min, xmax) min(x.warn_max, xmax)], [y - 0.28 y - 0.28], '-', 'color', red, 'linewidth', 4);
  end
  plot([x.ftti x.ftti], [y - 0.42 y + 0.42], '-', 'color', ink, 'linewidth', 2.5);
  plot([x.fdti_budget x.fdti_budget], [y - 0.42 y + 0.42], ':', 'color', teal, 'linewidth', 1.5);
  verdict = 'safe state within FTTI'; col = teal;
  if x.fhti_max > x.ftti + 1e-9, verdict = 'FTTI exceeded'; col = red; end
  if x.fdti_max > x.fdti_budget + 1e-9 && x.fhti_max <= x.ftti + 1e-9, verdict = 'FDTI over budget, FTTI met'; col = gold; end
  text(-0.02, y, sprintf('%s · %s', x.label, x.sg), 'horizontalalignment', 'right', 'color', ink);
  text(1.21, y, sprintf('FDTI <= %.3f s · %s', x.fdti_max, verdict), 'color', col);
end
set(gca, 'ytick', [], 'position', [0.25 0.08 0.48 0.84]); xlim([0 xmax]); ylim([0.3 n + 0.7]); xlabel('time from the last valid event (s) · model of the code, not a measurement (WP-S-04 6) · times after 1.2 s clipped');
title('Timing loops: FDTI over all loop phases (dots), FRTI budget (orange), warning (red), FDTI budget (dotted), FTTI (black)', 'color', gold);

png2 = fullfile(out_dir, 'liondriver-timing-loops.png'); print(h2, '-dpng', '-r110', png2);
printf('wrote %s\n', png2);

if isempty(fails)
  printf('OK: all model checks passed (models only; not verification of the C code)\n');
else
  printf('FAILED: %d model checks\n', numel(fails)); exit(1);
end
