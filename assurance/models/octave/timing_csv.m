function s = timing_csv(cases)
  % Results of timing_loop_model.m as CSV text (seconds, 4 decimals). Deterministic, so CI can compare it with the
  % committed timing_loop_results.csv that assurance/models/figures/fig_timing_anim.py draws.
  %   fdti_ok   worst FDTI within the §3.7 FDTI budget
  %   ftti_ok   worst FDTI + FRTI budget (FHTI) within the FTTI: safe state within the FTTI
  %   warn_ok   worst warning time within its budget (empty when the case has no warning)
  s = ['id,label,sg,build,ftti_s,fdti_budget_s,frti_budget_s,warn_budget_s,fdti_min_s,fdti_max_s,fhti_max_s,' ...
       'warn_min_s,warn_max_s,fdti_ok,ftti_ok,warn_ok,samples,rule' "\n"];
  for c = cases
    ok = @(v) num2str(double(v));
    warn_ok = ''; if !isnan(c.warn_budget), warn_ok = ok(c.warn_max <= c.warn_budget + 1e-9); end
    s = [s sprintf('%s,"%s",%s,"%s",%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%d,"%s"\n', c.id, c.label, c.sg, c.build, ...
         f(c.ftti), f(c.fdti_budget), f(c.frti_budget), f(c.warn_budget), f(c.fdti_min), f(c.fdti_max), ...
         f(c.fhti_max), f(c.warn_min), f(c.warn_max), ok(c.fdti_max <= c.fdti_budget + 1e-9), ...
         ok(c.fhti_max <= c.ftti + 1e-9), warn_ok, c.samples, c.rule)];
  end
end

function t = f(v)
  if isnan(v), t = ''; else, t = sprintf('%.4f', v); end
end
