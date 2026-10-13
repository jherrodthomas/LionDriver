function c = ld_constants(repo)
  % Read the envelope constants the models use from the opendbc source, so the models follow the pinned code.
  % repo: path of the LionDriver checkout (opendbc_repo must be checked out).
  % Fails if a constant or the TX-rate budget formula cannot be found in the expected form.
  saf = fileread(fullfile(repo, 'opendbc_repo', 'opendbc', 'safety', 'safety.h'));
  toy = fileread(fullfile(repo, 'opendbc_repo', 'opendbc', 'safety', 'modes', 'toyota.h'));

  lim = regexp(toy, 'TOYOTA_TORQUE_STEERING_LIMITS\s*=\s*\{(.*?)\};', 'tokens', 'once');
  assert(!isempty(lim), 'TOYOTA_TORQUE_STEERING_LIMITS not found in modes/toyota.h');
  c.max_torque    = field(lim{1}, 'max_torque');
  c.max_rate_up   = field(lim{1}, 'max_rate_up');
  c.max_rate_down = field(lim{1}, 'max_rate_down');
  c.max_rt_delta  = field(lim{1}, 'max_rt_delta');

  c.tx_window_s  = num(saf, '#define\s+TX_RATE_WINDOW_US\s+(\d+)U') / 1e6;
  c.tx_revoke_n  = num(saf, '#define\s+TX_RATE_REVOKE_REJECTED\s+(\d+)U');
  % the model's budget formula must be the code's: ceil(f * 0.25 s * 1.2) + 1 + burst
  assert(!isempty(strfind(saf, '((((uint32_t)check->frequency * 3U) + 9U) / 10U) + 1U + (uint32_t)check->burst')), ...
         'TX-rate budget formula in safety.h changed: update tx_rate_model.m');

  rows = regexp(toy, '\{\.addr = (0x[0-9A-Fa-f]+)U, \.bus = (\d+)U, \.frequency = (\d+)U, \.burst = (\d+)U\}', 'tokens');
  assert(!isempty(rows), 'toyota_tx_rate_checks not found in modes/toyota.h');
  c.tx_checks = struct('addr', {}, 'frequency', {}, 'burst', {});
  for i = 1:numel(rows)
    c.tx_checks(i).addr = rows{i}{1};
    c.tx_checks(i).frequency = str2double(rows{i}{3});
    c.tx_checks(i).burst = str2double(rows{i}{4});
  end
end

function v = field(block, name)
  t = regexp(block, ['\.' name '\s*=\s*(\d+)'], 'tokens', 'once');
  assert(!isempty(t), ['field ' name ' not found']);
  v = str2double(t{1});
end

function v = num(text, pat)
  t = regexp(text, pat, 'tokens', 'once');
  assert(!isempty(t), ['pattern not found: ' pat]);
  v = str2double(t{1});
end
