// Crystallyzer touchscreen app. Talks to the bench through a small JSON API.
// A static demo can set window.CRYSTALLYZER_API to answer the same calls without a server.

const $ = (s) => document.querySelector(s);
const el = (tag, attrs = {}, ...kids) => {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k.startsWith('on')) e.addEventListener(k.slice(2), v);
    else if (k === 'text') e.textContent = v;
    else if (v !== false && v !== null && v !== undefined) e.setAttribute(k, v === true ? '' : v);
  }
  for (const k of kids) if (k !== null && k !== undefined && k !== false) e.append(k);
  return e;
};
const SVGNS = 'http://www.w3.org/2000/svg';
const svg = (tag, attrs = {}) => {
  const e = document.createElementNS(SVGNS, tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  return e;
};

async function api(path, body) {
  if (window.CRYSTALLYZER_API) return window.CRYSTALLYZER_API(path, body);
  const res = await fetch(path, body ? { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) } : {});
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || res.statusText);
  return data;
}

const S = { view: 'diffraction', slide: 'hexagonal', crystal: 'quartz', growCrystal: 'alum', library: null, simulated: true, diff: null, pol: null, polIndex: 0 };

// ------------------------------------------------------------ chrome

function go(view) {
  S.view = view;
  $('#app').dataset.view = view;
  try { localStorage.setItem('crystallyzer:view', view); } catch {}
}
document.querySelectorAll('[data-go]').forEach((b) => b.addEventListener('click', () => go(b.dataset.go)));

async function refreshStatus() {
  try {
    const st = await api('/api/status');
    S.simulated = st.simulated;
    const s = st.sensors;
    const fmt = (v, unit, digits = 1) => (v === null || v === undefined ? '–' : `${Number(v).toFixed(digits)} ${unit}`);
    $('#sensors').replaceChildren(
      el('dt', { text: 'Room' }), el('dd', { text: fmt(s.room_c, '°C') }),
      el('dt', { text: 'Humidity' }), el('dd', { text: fmt(s.humidity, '%', 0) }),
      el('dt', { text: 'Pressure' }), el('dd', { text: fmt(s.pressure_hpa, 'hPa', 0) }),
      el('dt', { text: 'Solution' }), el('dd', { text: fmt(s.solution_c, '°C') }),
    );
    const mode = $('#mode');
    mode.className = 'mode' + (st.simulated ? '' : st.problems.length ? ' warn' : ' hw');
    mode.textContent = st.simulated ? 'Simulator: physics, no hardware' : st.problems.length ? `${st.problems.length} part${st.problems.length > 1 ? 's' : ''} need attention` : 'Hardware ready';
    mode.title = st.problems.join('\n');
  } catch (err) {
    $('#mode').textContent = 'Bench not reachable';
  }
}

function picker(host, items, current, onPick) {
  host.replaceChildren(...items.map((it) => el('button', { 'aria-pressed': String(it.id === current), onclick: () => { onPick(it.id); picker(host, items, it.id, onPick); } },
    el('b', { text: it.name }), el('small', { class: it.old ? 'old' : '', text: it.sub }))));
}

// ------------------------------------------------------------ diffraction

const overlay = $('#overlay');
function drawOverlay() {
  const r = S.diff?.reading;
  const size = S.diff?.size || 512;
  const box = overlay.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  overlay.width = box.width * dpr;
  overlay.height = box.height * dpr;
  const ctx = overlay.getContext('2d');
  ctx.clearRect(0, 0, overlay.width, overlay.height);
  if (!r || !$('#show-overlay').checked) return;
  const k = (box.width / size) * dpr;
  const [cx, cy] = r.centre;
  ctx.save();
  ctx.scale(k, k);
  const fold = r.pattern_fold;
  if (fold >= 2) {
    ctx.strokeStyle = 'rgba(127, 211, 255, 0.22)';
    ctx.lineWidth = 1 / k * dpr;
    ctx.setLineDash([4, 6]);
    const base = r.basis_px?.length ? Math.atan2(r.basis_px[0][1], r.basis_px[0][0]) : 0;
    for (let i = 0; i < fold; i++) {
      const a = base + (i * Math.PI * 2) / fold;
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.lineTo(cx + Math.cos(a) * size, cy + Math.sin(a) * size);
      ctx.stroke();
    }
    ctx.setLineDash([]);
  }
  ctx.strokeStyle = 'rgba(127, 211, 255, 0.9)';
  ctx.lineWidth = 1.4 / k * dpr;
  for (const s of r.spots.slice(0, 30)) {
    ctx.beginPath();
    ctx.arc(s.x, s.y, 7, 0, Math.PI * 2);
    ctx.stroke();
  }
  if (r.ring_um) {
    const d = S.library.device;
    const rad = (d.wavelength_nm * 1e-3 * d.distance_mm * d.px_per_mm) / r.ring_um;
    ctx.setLineDash([6, 6]);
    ctx.beginPath();
    ctx.arc(cx, cy, rad, 0, Math.PI * 2);
    ctx.stroke();
    ctx.setLineDash([]);
  }
  for (const [i, v] of (r.basis_px || []).entries()) {
    ctx.strokeStyle = i ? '#ffd27a' : '#ffffff';
    ctx.fillStyle = ctx.strokeStyle;
    ctx.lineWidth = 2.2 / k * dpr;
    const [x, y] = [cx + v[0], cy + v[1]];
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(x, y);
    ctx.stroke();
    const a = Math.atan2(v[1], v[0]);
    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.lineTo(x - 9 * Math.cos(a - 0.4), y - 9 * Math.sin(a - 0.4));
    ctx.lineTo(x - 9 * Math.cos(a + 0.4), y - 9 * Math.sin(a + 0.4));
    ctx.fill();
  }
  ctx.restore();
}
$('#show-overlay').addEventListener('change', drawOverlay);
new ResizeObserver(drawOverlay).observe(overlay);

function rebuild(canvas, r) {
  // The crystal, drawn back from its own diffraction pattern.
  const dpr = window.devicePixelRatio || 1;
  const w = canvas.clientWidth * dpr, h = canvas.clientHeight * dpr;
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = '#0b0f14';
  ctx.fillRect(0, 0, w, h);
  const scale = (h / 4.2) / (r.a_um || 40);
  const g = (r.gamma_deg * Math.PI) / 180;
  const a = [r.a_um * scale, 0];
  const b = [r.b_um * scale * Math.cos(g), r.b_um * scale * Math.sin(g)];
  ctx.fillStyle = '#e8edf4';
  for (let i = -20; i <= 20; i++) for (let j = -20; j <= 20; j++) {
    const x = w / 2 + i * a[0] + j * b[0];
    const y = h / 2 + i * a[1] + j * b[1];
    if (x > -10 && x < w + 10 && y > -10 && y < h + 10) {
      ctx.beginPath();
      ctx.arc(x, y, 3.2 * dpr, 0, Math.PI * 2);
      ctx.fill();
    }
  }
  ctx.strokeStyle = '#7fd3ff';
  ctx.lineWidth = 2 * dpr;
  ctx.beginPath();
  ctx.moveTo(w / 2, h / 2);
  ctx.lineTo(w / 2 + a[0], h / 2 + a[1]);
  ctx.lineTo(w / 2 + a[0] + b[0], h / 2 + a[1] + b[1]);
  ctx.lineTo(w / 2 + b[0], h / 2 + b[1]);
  ctx.closePath();
  ctx.stroke();
}

function renderDiffraction() {
  const d = S.diff;
  const host = $('#d-result');
  if (!d) return host.replaceChildren();
  const r = d.reading;
  $('#pattern').src = d.image;
  $('#pattern').classList.add('on');
  $('#screen-empty').hidden = true;
  const readouts = [['Pattern', `${r.pattern_fold || '∞'}-fold`], ['Slide', r.crystal_fold]];
  if (r.a_um) readouts.push(['a', `${r.a_um} µm`], ['b', `${r.b_um} µm`], ['Angle γ', `${r.gamma_deg}°`]);
  if (r.ring_um) readouts.push(['Typical spacing', `${r.ring_um} µm`]);
  if (r.helix_angle_deg) readouts.push(['X opens', `±${r.helix_angle_deg}°`]);
  const folds = Object.entries(r.symmetry_scores);
  const best = r.pattern_fold;
  const canvas = r.a_um ? el('canvas', { class: 'rebuilt', 'aria-label': 'Lattice rebuilt from the pattern' }) : null;
  host.replaceChildren(
    el('h2', { text: r.headline }),
    el('p', { text: r.explanation }),
    el('div', { class: 'readouts' }, ...readouts.map(([k, v]) => el('div', { class: 'readout' }, el('small', { text: k }), el('span', { text: v })))),
    canvas ? el('small', { class: 'readout-label', text: 'Rebuilt from the pattern alone' }) : null,
    canvas,
    el('div', { class: 'bars', title: 'How alike the pattern is to itself after each turn' },
      ...folds.map(([n, v]) => el('div', {}, el('i', { class: Number(n) === best ? 'hit' : '', style: `height:${Math.max(2, v * 100)}%` }), el('span', { text: `${n}×` })))),
  );
  if (canvas) requestAnimationFrame(() => rebuild(canvas, r));
  drawOverlay();
}

$('#fire').addEventListener('click', async () => {
  const button = $('#fire');
  button.disabled = true;
  $('#screen').classList.remove('firing');
  void $('#screen').offsetWidth;
  $('#screen').classList.add('firing');
  try {
    S.diff = await api('/api/diffraction', { slide: S.slide });
    renderDiffraction();
  } catch (err) {
    $('#d-result').replaceChildren(el('h2', { text: 'The laser did not fire' }), el('p', { text: err.message }));
  } finally {
    button.disabled = false;
  }
});

// ------------------------------------------------------------ polarized light

function chartLight(reading) {
  const host = $('#light-chart');
  host.replaceChildren();
  const W = 600, H = 170, pad = 28;
  const x = (deg) => pad + (deg / 180) * (W - pad - 8);
  const y = (v) => H - 20 - v * (H - 40);
  for (const deg of [0, 45, 90, 135, 180]) {
    host.append(svg('line', { x1: x(deg), x2: x(deg), y1: 10, y2: H - 20, class: 'grid', stroke: 'rgba(220,230,245,.08)' }));
    const t = svg('text', { x: x(deg), y: H - 4, 'text-anchor': 'middle', class: 'axis', fill: '#626e80', 'font-size': 10, 'font-family': 'Martian Mono, monospace' });
    t.textContent = `${deg}°`;
    host.append(t);
  }
  for (const e of reading.extinction_deg) host.append(svg('line', { x1: x(e), x2: x(e), y1: 10, y2: H - 20, stroke: '#ff3d2e', 'stroke-dasharray': '4 4', 'stroke-width': 1.5 }));
  const pts = reading.angles.map((a, i) => [a, reading.light[i]]);
  const path = pts.map(([a, v], i) => `${i ? 'L' : 'M'}${x(a)},${y(v)}`).join(' ');
  host.append(svg('path', { d: path, fill: 'none', stroke: '#7fd3ff', 'stroke-width': 2.2 }));
  for (const [a, v] of pts) host.append(svg('circle', { cx: x(a), cy: y(v), r: 3.5, fill: '#0e1218', stroke: '#7fd3ff', 'stroke-width': 2 }));
}

function chartMichelLevy(reading) {
  const chart = S.library.chart;
  const max = chart[chart.length - 1].nm;
  const canvas = $('#ml');
  const ctx = canvas.getContext('2d');
  const w = canvas.width, h = canvas.height;
  chart.forEach((c, i) => {
    ctx.fillStyle = `rgb(${c.rgb.map((v) => Math.round(v * 255)).join(',')})`;
    ctx.fillRect((i / chart.length) * w, 0, w / chart.length + 1, h);
  });
  const axis = $('#ml-axis');
  axis.replaceChildren(...[0, 550, 1100, 1650].map((nm) => el('span', { style: `left:${(nm / max) * 100}%`, text: nm ? `${nm} nm` : '0' })));
  if (reading?.retardation_nm) {
    const left = (reading.retardation_nm / max) * 100;
    axis.append(el('span', { class: 'mark', style: `left:${left}%` }), el('span', { class: 'mark-label', style: `left:${left}%`, text: `≈ ${reading.retardation_nm} nm` }));
  }
}

function showStage(i) {
  S.polIndex = i;
  const f = S.pol.frames[i];
  $('#stage-big').src = f.image;
  $('#stage-angle').textContent = `${f.angle}°`;
  document.querySelectorAll('#strip button').forEach((b, k) => b.setAttribute('aria-pressed', String(k === i)));
}

function renderPolarization() {
  const p = S.pol;
  const r = p.reading;
  $('#strip').replaceChildren(...p.frames.map((f, i) => el('button', { onclick: () => showStage(i), 'aria-label': `${f.angle}°` }, el('img', { src: f.image, alt: '' }), el('span', { text: `${f.angle}°` }))));
  const brightest = r.light.indexOf(Math.max(...r.light));
  showStage(Math.max(0, brightest));
  chartLight(r);
  chartMichelLevy(r);
  const readouts = [['Modulation', `${Math.round(r.modulation * 100)}%`]];
  if (r.birefringent) readouts.push(['Dark at', r.extinction_deg.map((d) => `${d}°`).join(', ')]);
  if (r.retardation_nm) readouts.push(['Retardation', `≈ ${r.retardation_nm} nm`]);
  if (r.birefringence) readouts.push(['Birefringence', `≈ ${r.birefringence}`]);
  $('#p-result').replaceChildren(
    el('h2', { text: r.headline }),
    el('p', { text: r.explanation }),
    el('div', { class: 'readouts' }, ...readouts.map(([k, v]) => el('div', { class: 'readout' }, el('small', { text: k }), el('span', { text: v })))),
  );
}

$('#turn').addEventListener('click', async () => {
  const button = $('#turn');
  button.disabled = true;
  try {
    S.pol = await api('/api/polarization', { crystal: S.crystal, steps: 12, thickness_um: Number($('#thickness').value) || null });
    renderPolarization();
  } catch (err) {
    $('#p-result').replaceChildren(el('h2', { text: 'The stage did not turn' }), el('p', { text: err.message }));
  } finally {
    button.disabled = false;
  }
});

// ------------------------------------------------------------ growth

function chartGrowth(samples) {
  const host = $('#g-chart');
  host.replaceChildren();
  if (!samples.length) return;
  const W = 900, H = 220, padL = 44, padR = 44;
  const hours = samples.map((s) => s.hours), size = samples.map((s) => s.size_mm), temp = samples.map((s) => s.solution_c);
  const hMax = Math.max(...hours) || 1;
  const [sMin, sMax] = [Math.min(...size), Math.max(...size)];
  const [tMin, tMax] = [Math.min(...temp) - 0.3, Math.max(...temp) + 0.3];
  const x = (v) => padL + (v / hMax) * (W - padL - padR);
  const ys = (v) => H - 24 - ((v - sMin) / (sMax - sMin || 1)) * (H - 44);
  const yt = (v) => H - 24 - ((v - tMin) / (tMax - tMin || 1)) * (H - 44);
  for (let k = 0; k <= 4; k++) {
    const hv = (hMax * k) / 4;
    host.append(svg('line', { x1: x(hv), x2: x(hv), y1: 10, y2: H - 24, stroke: 'rgba(220,230,245,.07)' }));
    const t = svg('text', { x: x(hv), y: H - 6, 'text-anchor': 'middle', fill: '#626e80', 'font-size': 10, 'font-family': 'Martian Mono, monospace' });
    t.textContent = `${hv.toFixed(0)} h`;
    host.append(t);
  }
  const label = (text, xx, yy, colour, anchor) => {
    const t = svg('text', { x: xx, y: yy, 'text-anchor': anchor, fill: colour, 'font-size': 10, 'font-family': 'Martian Mono, monospace' });
    t.textContent = text;
    host.append(t);
  };
  label(`${sMax.toFixed(2)} mm`, padL - 6, ys(sMax) + 4, '#7fd3ff', 'end');
  label(`${sMin.toFixed(2)} mm`, padL - 6, ys(sMin) + 4, '#7fd3ff', 'end');
  label(`${tMax.toFixed(1)}°C`, W - padR + 6, yt(tMax) + 4, '#ffbf5e', 'start');
  label(`${tMin.toFixed(1)}°C`, W - padR + 6, yt(tMin) + 4, '#ffbf5e', 'start');
  const line = (vals, y, colour, width) => host.append(svg('path', { d: vals.map((v, i) => `${i ? 'L' : 'M'}${x(hours[i])},${y(v)}`).join(' '), fill: 'none', stroke: colour, 'stroke-width': width, 'stroke-linejoin': 'round' }));
  line(temp, yt, 'rgba(255,191,94,.75)', 1.6);
  const area = `M${x(hours[0])},${H - 24} ` + size.map((v, i) => `L${x(hours[i])},${ys(v)}`).join(' ') + ` L${x(hours[hours.length - 1])},${H - 24} Z`;
  host.append(svg('path', { d: area, fill: 'rgba(127,211,255,.12)' }));
  line(size, ys, '#7fd3ff', 2.4);
}

function renderGrowth(g) {
  $('#g-hint').textContent = g.simulated ? 'Simulated: a whole day, played at once.' : g.running ? 'Sampling every 5 minutes. Leave it running overnight.' : '';
  $('#g-frames').replaceChildren(...(g.frames || []).map((f) => el('figure', {}, el('img', { src: f.image, alt: `After ${f.hours} hours` }), el('figcaption', { text: `${f.hours} h` }))));
  const r = g.reading;
  if (!r) return $('#g-result').replaceChildren();
  chartGrowth(r.samples);
  const readouts = [['Edge growth', `${r.edge_um_per_h} µm/h`], ['Area growth', `${r.area_mm2_per_h} mm²/h`]];
  if (r.temperature_link !== null) readouts.push(['Speed vs warmth', `r = ${r.temperature_link}`]);
  $('#g-result').replaceChildren(el('h2', { text: r.headline }), el('p', { text: r.explanation }), el('div', { class: 'readouts' }, ...readouts.map(([k, v]) => el('div', { class: 'readout' }, el('small', { text: k }), el('span', { text: v })))));
}

$('#grow').addEventListener('click', async () => {
  const button = $('#grow');
  button.disabled = true;
  try {
    renderGrowth(await api('/api/growth/start', { crystal: S.growCrystal, every_s: 300 }));
  } catch (err) {
    $('#g-result').replaceChildren(el('h2', { text: 'The run did not start' }), el('p', { text: err.message }));
  } finally {
    button.disabled = false;
  }
});

// ------------------------------------------------------------ start

function runButton(id) {
  return new Promise((resolve) => {
    const b = $(id);
    const done = new MutationObserver(() => { if (!b.disabled) { done.disconnect(); resolve(); } });
    done.observe(b, { attributes: true, attributeFilter: ['disabled'] });
    b.click();
  });
}

(async function start() {
  try { go(localStorage.getItem('crystallyzer:view') || location.hash.slice(1) || 'diffraction'); } catch { go('diffraction'); }
  if (['diffraction', 'polarization', 'growth'].includes(location.hash.slice(1))) go(location.hash.slice(1));
  S.library = await api('/api/library');
  const lib = S.library;
  picker($('#slides'), lib.slides.map((s) => ({ id: s.id, name: s.name, sub: s.kind })), S.slide, (id) => { S.slide = id; });
  const crystalItems = lib.crystals.map((c) => ({ id: c.id, name: c.name, sub: c.in_2016 ? '2016 set' : c.formula, old: c.in_2016 }));
  picker($('#crystals'), crystalItems, S.crystal, (id) => { S.crystal = id; $('#thickness').value = lib.crystals.find((c) => c.id === id).flake_um; });
  $('#thickness').value = lib.crystals.find((c) => c.id === S.crystal).flake_um;
  picker($('#g-crystals'), lib.crystals.filter((c) => !['quartz', 'calcite'].includes(c.id)).map((c) => ({ id: c.id, name: c.name, sub: c.formula })), S.growCrystal, (id) => { S.growCrystal = id; });
  chartMichelLevy(null);
  await refreshStatus();
  setInterval(refreshStatus, 5000);
  // Open on a real result rather than an empty screen, one experiment after another.
  for (const id of ['#fire', '#turn', '#grow']) await runButton(id);
})();
