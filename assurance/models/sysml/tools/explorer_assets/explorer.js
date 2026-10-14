const D = JSON.parse(document.getElementById('model-data').textContent);
const E = D.elements, C = D.connections, M = D.mechanisms;
const $ = (s, r = document) => r.querySelector(s), $$ = (s, r = document) => [...r.querySelectorAll(s)];
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
const LABEL = {BDagger: 'B‡', B: 'ASIL B', QMBsup: 'QM (B-sup)', QM: 'QM', AoU: 'AoU', Untrusted: 'untrusted'};
const store = { get(k) { try { return localStorage.getItem(k) } catch { return null } }, set(k, v) { try { localStorage.setItem(k, v) } catch {} } };
let current = null, sel = null;

function dotClass(e) {
  if (e.scope !== 'inside') return 'out';
  if (e.classes.includes('MlElement')) return 'ml';
  return e.integrity || 'QM';
}
function isCode(e) { return e.short && /^(host|panda)\./.test(e.short) }
function within(path, root) { return path === root || path.startsWith(root + '.') }

// ---------------------------------------------------------------- tree
const open = new Set(['context', 'context.ldsda']);
function renderTree() {
  const q = $('#q').value.trim().toLowerCase();
  const out = [];
  const match = e => !q || [e.ident, e.name, e.title, e.doc, e.unit].some(v => v && String(v).toLowerCase().includes(q));
  const keep = new Map();
  const visit = p => { const e = E[p]; let k = match(e); for (const c of e.children) k = visit(c) || k; keep.set(p, k); return k };
  visit('context');
  const walk = (p, depth) => {
    const e = E[p];
    if (!keep.get(p)) return;
    const kids = e.children.length > 0, isOpen = q ? true : open.has(p);
    const name = isCode(e) ? e.short : (e.short && /^E-0/.test(e.short) ? e.title : (e.short && !isCode(e) && !/^E-0/.test(e.short) ? e.title : e.title));
    out.push(`<div class="row${isCode(e) ? ' mono' : ''}${sel === p ? ' sel' : ''}" role="treeitem" tabindex="0" data-p="${p}" style="padding-left:${8 + depth * 14}px" aria-expanded="${kids ? isOpen : ''}">
      <span class="tw">${kids ? (isOpen ? '▾' : '▸') : ''}</span><span class="dot ${dotClass(e)}"></span>
      ${e.short && !isCode(e) ? `<span class="id">${esc(e.short)}</span>` : ''}<span class="nm">${esc(name)}</span></div>`);
    if (kids && isOpen) for (const c of e.children) walk(c, depth + 1);
  };
  walk('context', 0);
  $('#tree').innerHTML = out.join('');
}
$('#tree').addEventListener('click', ev => {
  const r = ev.target.closest('.row'); if (!r) return;
  const p = r.dataset.p;
  if (ev.target.classList.contains('tw')) { open.has(p) ? open.delete(p) : open.add(p); renderTree(); return }
  select(p, true);
});
$('#tree').addEventListener('keydown', ev => { if (ev.key === 'Enter' || ev.key === ' ') { const r = ev.target.closest('.row'); if (r) { ev.preventDefault(); select(r.dataset.p, true) } } });
$('#q').addEventListener('input', renderTree);

// ---------------------------------------------------------------- views, pan and zoom
let zoom = 1, ox = 0, oy = 0;
function apply() { $('#sheet').style.transform = `translate(${ox}px, ${oy}px) scale(${zoom})` }
function fit() {
  const vp = $('#vp'), svg = $('#sheet svg'); if (!svg) return;
  const w = +svg.getAttribute('width'), h = +svg.getAttribute('height');
  zoom = Math.min((vp.clientWidth - 24) / w, (vp.clientHeight - 24) / h, 1.4);
  ox = (vp.clientWidth - w * zoom) / 2; oy = Math.max(12, (vp.clientHeight - h * zoom) / 2); apply();
}
function zoomAt(f, cx, cy) { const nz = Math.min(4, Math.max(0.2, zoom * f)); ox = cx - (cx - ox) * nz / zoom; oy = cy - (cy - oy) * nz / zoom; zoom = nz; apply() }
function show(vid) {
  current = vid;
  $$('.tab').forEach(t => t.setAttribute('aria-selected', t.dataset.v === vid));
  $('#sheet').innerHTML = $('#svg-' + vid).innerHTML;
  $('#sheet svg').classList.add('fig');
  $('#cap').textContent = D.views[vid].doc;
  store.set('ld-view', vid);
  if (location.hash.slice(1) !== vid) history.replaceState(null, '', '#' + vid);
  fit(); highlight();
}
$$('.tab').forEach(t => t.addEventListener('click', () => show(t.dataset.v)));
$('#zin').onclick = () => zoomAt(1.25, $('#vp').clientWidth / 2, $('#vp').clientHeight / 2);
$('#zout').onclick = () => zoomAt(0.8, $('#vp').clientWidth / 2, $('#vp').clientHeight / 2);
$('#zfit').onclick = fit;
const vp = $('#vp');
vp.addEventListener('wheel', ev => { ev.preventDefault(); const r = vp.getBoundingClientRect(); zoomAt(ev.deltaY < 0 ? 1.12 : 0.89, ev.clientX - r.left, ev.clientY - r.top) }, {passive: false});
let drag = null, moved = false;
vp.addEventListener('pointerdown', ev => { drag = {x: ev.clientX, y: ev.clientY, ox, oy}; moved = false; vp.setPointerCapture(ev.pointerId) });
vp.addEventListener('pointermove', ev => { if (!drag) return; const dx = ev.clientX - drag.x, dy = ev.clientY - drag.y; if (Math.abs(dx) + Math.abs(dy) > 3) { moved = true; vp.classList.add('drag') } ox = drag.ox + dx; oy = drag.oy + dy; apply() });
vp.addEventListener('pointerup', ev => {
  vp.classList.remove('drag'); const wasDrag = moved; drag = null;
  if (wasDrag) return;
  vp.releasePointerCapture(ev.pointerId);
  const hit = document.elementsFromPoint(ev.clientX, ev.clientY);
  for (const node of hit) {
    const sm = node.closest && node.closest('[data-sm]'); if (sm) { selectMech(sm.dataset.sm); return }
    const g = node.closest && node.closest('[data-el]'); if (g && $('#sheet').contains(g)) { select(g.dataset.el, false); return }
  }
  select(null);
});
window.addEventListener('resize', fit);

// ---------------------------------------------------------------- highlight
function highlight() {
  const svg = $('#sheet svg'); if (!svg) return;
  $$('[data-el], [data-edge], [data-sm]', svg).forEach(n => n.classList.remove('hit', 'near'));
  svg.classList.toggle('focus', !!sel);
  if (!sel) return;
  if (sel.startsWith('SM-')) {
    $$(`[data-sm="${sel}"]`, svg).forEach(n => n.classList.add('hit'));
    for (const p of M[sel].by) $$('[data-el]', svg).forEach(n => { if (within(p, n.dataset.el) || within(n.dataset.el, p)) n.classList.add('hit') });
    return;
  }
  const drawn = $$('[data-el]', svg).map(n => n.dataset.el);
  // the drawn node that stands for the selection: itself, else its nearest drawn ancestor
  let anchor = sel; while (anchor && !drawn.includes(anchor)) anchor = anchor.includes('.') ? anchor.slice(0, anchor.lastIndexOf('.')) : null;
  $$('[data-el]', svg).forEach(n => { if (n.dataset.el === anchor || within(n.dataset.el, sel)) n.classList.add('hit') });
  $$('[data-el]', svg).forEach(n => { if (anchor && within(anchor, n.dataset.el) && n.dataset.el !== anchor) n.classList.add('near') });
  $$('[data-edge]', svg).forEach(g => {
    const a = g.dataset.a, b = g.dataset.b;
    if (anchor && (a === anchor || b === anchor)) {
      g.classList.add('hit');
      $$('[data-el]', svg).forEach(n => { if (n.dataset.el === (a === anchor ? b : a)) n.classList.add('near') });
    }
  });
  $$('[data-sm]', svg).forEach(n => { if (E[sel] && E[sel].performs.includes(n.dataset.sm)) n.classList.add('hit') });
}

// ---------------------------------------------------------------- inspector
function name(p) { const e = E[p]; return e ? (isCode(e) ? e.short : (e.short ? e.short + ' ' + e.title : e.title)) : p }
function interfacesOf(p) {
  return C.filter(c => c.def !== 'DataFlow' && c.kind !== 'connect' && (within(c.a, p) || within(c.b, p)) && !(within(c.a, p) && within(c.b, p)))
    .map(c => ({c, out: within(c.a, p), other: within(c.a, p) ? c.b : c.a}));
}
function flowsOf(p) { return C.filter(c => c.def === 'DataFlow' && (c.a === p || c.b === p)) }
function asilBar(reqs) {
  const order = ['D', 'C', 'B', 'A', 'QM'], n = {};
  for (const r of reqs) { const a = (r.asil.match(/[ABCD]/) || ['QM'])[0]; n[a] = (n[a] || 0) + 1 }
  const tot = reqs.length || 1;
  return `<div class="bar" role="img" aria-label="ASIL mix">${order.filter(a => n[a]).map(a => `<i class="${a}" style="width:${100 * n[a] / tot}%" title="${a}: ${n[a]}"></i>`).join('')}</div>
    <div class="legend">${order.filter(a => n[a]).map(a => `<span><span class="dot sw-${a}"></span>${a === 'QM' ? 'QM' : 'ASIL ' + a} ${n[a]}</span>`).join('')}</div>`;
}
function chipFor(e) {
  const i = e.integrity; if (!i) return '';
  const cls = i === 'BDagger' ? 'env' : i === 'B' ? 'b' : '';
  return `<span class="chip ${cls}" title="${esc(e.label)}">${LABEL[i] || i}</span>`;
}
let reqLimit = 12;
function inspect(p) {
  const e = E[p];
  const all = [];
  for (const q of Object.keys(E)) if (within(q, p)) for (const r of E[q].reqs) if (!all.some(x => x.id === r.id)) all.push(r);
  const own = e.reqs;
  const ifs = interfacesOf(p), flows = flowsOf(p);
  const sms = [...new Set(Object.keys(E).filter(q => within(q, p)).flatMap(q => E[q].performs))].sort();
  const kids = e.children;
  const html = [];
  html.push(`<div class="kicker">${e.short ? `<span class="chip">${esc(e.short)}</span>` : ''}${chipFor(e)}${e.classes.includes('MlElement') ? '<span class="chip ml">ML</span>' : ''}${e.scope !== 'inside' ? `<span class="chip">${e.scope === 'excluded' ? 'excluded' : 'outside the item'}</span>` : ''}${e.build === 'reference' ? '<span class="chip">reference build</span>' : ''}</div>`);
  html.push(`<h3>${esc(isCode(e) ? e.short : e.title)}</h3>`);
  if (e.doc) html.push(`<p class="doc">${esc(e.doc)}</p>`);
  const kv = [['SysML', `<span class="code">part ${esc(e.name)} : ${esc(e.def || '—')}</span>`]];
  if (e.label) kv.push(['Integrity', esc(e.label)]);
  if (e.unit) kv.push(['Unit', `<span class="code">${esc(e.unit)}</span>`]);
  if (e.source) kv.push(['Source', `${esc(e.source.wp)} ${esc(e.source.clause || '')}${e.source.paths.length ? `<br><span class="code">${e.source.paths.map(esc).join('<br>')}</span>` : ''}`]);
  if (e.parent) kv.push(['Part of', `<a href="#" data-go="${e.parent}">${esc(name(e.parent))}</a>`]);
  if (e.ports.length) kv.push(['Ports', `<span class="code">${e.ports.map(esc).join(', ')}</span>`]);
  html.push(`<dl class="kv">${kv.map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join('')}</dl>`);
  if (ifs.length) {
    html.push(`<div class="sect"><h4>Interfaces <span>${ifs.length}</span></h4><ul class="list">${ifs.map(({c, out, other}) => {
      const k = c.def === 'CanLink' ? (c.id === 'IF-01' ? '' : 'teal') : (c.def === 'SpiLink' || c.def === 'GpioLink' && c.id === 'IF-04b') ? 'vio' : c.def === 'PowerLink' ? '' : 'teal';
      return `<li class="link" data-go="${E[other] ? other : other.slice(0, other.lastIndexOf('.'))}"><span class="k ${k}">${esc(c.id || c.def.replace('Link', ''))}</span><span class="t">${out ? '→' : '←'} ${esc(name(E[other] ? other : other.slice(0, other.lastIndexOf('.'))))}<small>${esc(c.def)}${c.ffi.length ? ' · FFI ' + c.ffi.join(', ') : ''}${c.doc ? ' · ' + esc(c.doc) : ''}</small></span></li>`
    }).join('')}</ul></div>`);
  }
  if (flows.length) {
    html.push(`<div class="sect"><h4>Cereal services <span>${flows.length}</span></h4><ul class="list">${flows.map(c => {
      const out = c.a === p, other = out ? c.b : c.a;
      return `<li class="link" data-go="${other}"><span class="k mut">${out ? 'pub' : 'sub'}</span><span class="t">${esc(c.service)} ${out ? '→' : '←'} ${esc(name(other))}<small>${c.rate ? c.rate + ' Hz' : ''}</small></span></li>`
    }).join('')}</ul></div>`);
  }
  if (sms.length) {
    html.push(`<div class="sect"><h4>Safety mechanisms <span>${sms.length}</span></h4><ul class="list">${sms.map(s => `<li class="link" data-sm="${s}"><span class="k">${s}</span><span class="t">${esc(M[s].doc || M[s].name)}<small>DC ${esc(M[s].dc)} · ${esc(M[s].tsr.join(', '))}</small></span></li>`).join('')}</ul></div>`);
  }
  if (all.length) {
    const shown = all.slice(0, reqLimit);
    html.push(`<div class="sect"><h4>Allocated requirements <span>${all.length}${own.length !== all.length ? ` · ${own.length} here` : ''}</span></h4>${asilBar(all)}
      <ul class="list">${shown.map(r => `<li><span class="k ${r.kind === 'tsr' ? '' : 'mut'}">${esc(r.id)}</span><span class="t">${esc(r.text)}<small>${esc(r.asil || '—')} · ${r.via === 'satisfy' ? 'satisfy' : 'allocated_to'}: ${esc(r.alloc || '—')}${r.via === 'satisfy' ? ` · ${r.cases.length ? 'verified by ' + esc(r.cases.join(', ')) : 'no verification case'}` : ''}</small></span></li>`).join('')}</ul>
      ${all.length > shown.length ? `<button class="more" id="more">Show all ${all.length}</button>` : ''}</div>`);
  }
  if (kids.length) {
    html.push(`<div class="sect"><h4>Parts <span>${kids.length}</span></h4><ul class="list">${kids.map(c => `<li class="link" data-go="${c}"><span class="dot ${dotClass(E[c])}" style="align-self:center"></span><span class="t">${esc(name(c))}</span></li>`).join('')}</ul></div>`);
  }
  $('#insp').innerHTML = html.join('');
  const more = $('#more'); if (more) more.onclick = () => { reqLimit = 9999; inspect(p) };
}
function inspectMech(s) {
  const m = M[s];
  $('#insp').innerHTML = `<div class="kicker"><span class="chip env">${s}</span><span class="chip">DC ${esc(m.dc)}</span></div>
    <h3>${esc(m.doc || m.name)}</h3><p class="doc">Covers: ${esc(m.covers)}</p>
    <dl class="kv"><dt>SysML</dt><dd><span class="code">action ${esc(m.name)} : SafetyMechanism</span></dd><dt>TSRs</dt><dd class="code">${esc(m.tsr.join(', '))}</dd></dl>
    <div class="sect"><h4>Performed by <span>${m.by.length}</span></h4><ul class="list">${m.by.map(p => `<li class="link" data-go="${p}"><span class="dot ${dotClass(E[p])}" style="align-self:center"></span><span class="t">${esc(name(p))}</span></li>`).join('')}</ul></div>`;
}
function emptyInspector() {
  $('#insp').innerHTML = `<div class="empty"><p><strong>Select an element</strong> in a view or in the model tree to see its integrity, source, interfaces, safety mechanisms and the requirements allocated to it.</p>
    <p>Try <a href="#" data-go="context.ldsda.safetyFirmware.safetyLayer">E-03a Safety layer</a>, <a href="#" data-go="context.ldsda.socSoftware.pandad">host.pandad</a> or <a href="#" data-sm="SM-15">SM-15</a>.</p></div>`;
}
$('#insp').addEventListener('click', ev => {
  const g = ev.target.closest('[data-go]'), s = ev.target.closest('[data-sm]');
  if (g) { ev.preventDefault(); select(g.dataset.go, true) } else if (s) { ev.preventDefault(); selectMech(s.dataset.sm) }
});
function select(p, fromTree) {
  sel = p; reqLimit = 12;
  if (p) { let q = p; while (q.includes('.')) { q = q.slice(0, q.lastIndexOf('.')); open.add(q) } inspect(p) } else emptyInspector();
  renderTree(); highlight();
  if (p && fromTree !== false) { const r = $(`.row[data-p="${p}"]`); if (r) r.scrollIntoView({block: 'nearest'}) }
}
function selectMech(s) { sel = s; inspectMech(s); renderTree(); highlight() }

// ---------------------------------------------------------------- start
const first = [location.hash.slice(1), store.get('ld-view'), 'V-03'].find(v => v && D.views[v]);
renderTree(); emptyInspector(); show(first);
