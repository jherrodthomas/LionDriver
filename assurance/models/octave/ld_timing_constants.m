function k = ld_timing_constants(repo)
  % Read the loop periods and timeouts the timing-loop model uses from the pinned panda and opendbc sources, so the
  % model follows the code. repo: path of the LionDriver checkout (panda and opendbc_repo checked out).
  % Fails if a constant, or a loop rule the model assumes, is not found in the expected form. Times in microseconds.
  cfg  = fileread(fullfile(repo, 'panda', 'board', 'stm32h7', 'stm32h7_config.h'));
  mainc = fileread(fullfile(repo, 'panda', 'board', 'main.c'));
  hbm  = fileread(fullfile(repo, 'panda', 'board', 'drivers', 'heartbeat_monitor.h'));
  wdg  = fileread(fullfile(repo, 'panda', 'board', 'drivers', 'hw_watchdog.h'));
  eps  = fileread(fullfile(repo, 'panda', 'board', 'drivers', 'eps_fault_siren.h'));
  saf  = fileread(fullfile(repo, 'opendbc_repo', 'opendbc', 'safety', 'safety.h'));
  toy  = fileread(fullfile(repo, 'opendbc_repo', 'opendbc', 'safety', 'modes', 'toyota.h'));
  pd   = fileread(fullfile(repo, 'openpilot', 'selfdrive', 'pandad', 'pandad.cc'));

  % loops
  k.task_us = 1e6 / num(cfg, '#define\s+SAFETY_TASK_FREQ\s+(\d+)U');            % 100 Hz safety task (TIM4)
  need(mainc, '// called at 8Hz', 'tick handler no longer documented as 8 Hz');
  k.tick_us = 1e6 / 8;                                                            % 8 Hz tick (TIM12)
  need(mainc, 'set_siren((loop_counter & 1U)', 'speaker no longer driven on every other tick');
  need(mainc, 'loop_counter %= 8U', 'tick counter no longer modulo 8');
  need(mainc, 'if (loop_counter == 0U) {', '1 Hz decimation of the tick changed');
  k.slow_us = 8 * k.tick_us;                                                      % 1 Hz path (every 8th tick)

  % SoC heartbeat (0xf3): sent by pandad at 10 Hz (every 10th frame of its 100 Hz loop)
  need(pd, 'if (rk.frame() % 10 == 0) {', 'pandad heartbeat no longer at 10 Hz');
  k.heartbeat_period_us = 1e5;
  k.hb_timeout_ticks = num(hbm, '#define\s+HEARTBEAT_AUTHORITY_TIMEOUT_TICKS\s+(\d+)U');   % T-06a
  k.hb_silent_cnt_on = num(mainc, '#define\s+HEARTBEAT_IGNITION_CNT_ON\s+(\d+)U');           % T-06 / T-06b

  % RX timeout (TSR-401): reference build 5 periods, strict >, evaluated by the safety task; baseline max(10 periods, 1 s)
  k.rx_periods_ref = num(toy, '#define\s+TOYOTA_RX_TIMEOUT_PERIODS\s+(\d+)U');
  need(saf, 'const uint8_t MAX_MISSED_MSGS = 10U;', 'baseline RX threshold changed');
  need(saf, 'uint32_t lag_threshold = SAFETY_MAX(timestep * MAX_MISSED_MSGS, 1e6);', 'baseline RX threshold changed');
  need(saf, 'return elapsed_time > lag_threshold;', 'RX timeout comparison no longer strict');
  k.rx = struct('addr', {}, 'hz', {});
  for a = {'0xaa', '0x260', '0x262', '0x1D3', '0x1D2', '0x226'}
    t = regexp(toy, ['\{\{\s*' a{1} ',\s*0,\s*8,\s*(\d+)U'], 'tokens', 'once');
    assert(!isempty(t), ['RX check ' a{1} ' not found in modes/toyota.h']);
    k.rx(end + 1) = struct('addr', a{1}, 'hz', str2double(t{1}));
  end

  % SoC command arrival (TSR-408): 0x2E4 timeout, strict >
  k.arrival_lka_us = num(toy, '\{\.addr = 0x2E4U, \.bus = 0U, \.timeout_us = (\d+)U');
  need(saf, '> check->timeout_us) {', 'TX arrival comparison no longer strict');

  % hardware watchdog IWDG1 (TSR-501): timeout = 4 * 2^PR * (RLR + 1) / f_LSI
  k.iwdg_pr  = num(wdg, '#define\s+HW_WATCHDOG_PRESCALER\s+(\d+)U');
  k.iwdg_rlr = num(wdg, '#define\s+HW_WATCHDOG_RELOAD\s+(\d+)U');
  need(wdg, 'Timeout = 4 * 2^PR * (RLR + 1) / f_LSI', 'IWDG timeout formula comment changed');
  k.lsi_nominal_hz = 32000;

  % EPS-fault siren persistence (TSR-516(b), DQ-048)
  k.eps_persist_ticks = num(eps, '#define\s+EPS_FAULT_SIREN_PERSIST_TICKS\s+(\d+)U');
end

function v = num(text, pat)
  t = regexp(text, pat, 'tokens', 'once');
  assert(!isempty(t), ['pattern not found: ' pat]);
  v = str2double(t{1});
end

function need(text, s, msg)
  assert(!isempty(strfind(text, s)), ['timing-loop model: ' msg ' (expected: ' s ')']);
end
