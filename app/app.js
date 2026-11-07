/* DOM layer for the rent estimator. Logic lives in core.js. */
(function () {
  'use strict';
  const R = window.RentCore;
  const C = R.decode(window.RENT_DATA);
  const $ = (id) => document.getElementById(id);
  const money = (x) => (isFinite(x) ? '$' + Math.round(x).toLocaleString('en-AU') : 'n/a');
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const label = (i) => R.titleCase(C.addr[i]);

  const state = {
    mode: 'find', flat: -1, parking: 'without', layer: 'heat', cell: 200,
    f: { suburb: -1, type: -1, beds: 2, baths: -1, floor: 'any', size: 'any', center: null, radius: 0 },
  };
  const defaultSuburb = C.suburbLabels.indexOf('Surry Hills');
  state.f.suburb = defaultSuburb;

  // ---------- controls
  function seg(el, options, get, set) {
    const root = $(el);
    const draw = () => {
      root.innerHTML = '';
      options.forEach((o) => {
        const b = document.createElement('button');
        b.textContent = o.label; b.className = get() === o.v ? 'on' : '';
        b.onclick = () => { set(o.v); draw(); render(); };
        root.appendChild(b);
      });
    };
    draw();
    return draw;
  }
  const typeOpts = [{ v: -1, label: 'Any' }].concat(C.types.map((t, i) => ({ v: i, label: R.titleCase(t) })));
  seg('segType', typeOpts, () => state.f.type, (v) => { state.f.type = v; });
  seg('segBeds', [{ v: -1, label: 'Any' }, { v: 0, label: 'Studio' }, { v: 1, label: '1' }, { v: 2, label: '2' }, { v: 3, label: '3' }, { v: 4, label: '4+' }], () => state.f.beds, (v) => { state.f.beds = v; });
  seg('segBaths', [{ v: -1, label: 'Any' }, { v: 1, label: '1' }, { v: 2, label: '2' }, { v: 3, label: '3+' }], () => state.f.baths, (v) => { state.f.baths = v; });
  seg('segFloor', [{ v: 'any', label: 'Any' }, { v: 'low', label: 'Ground-3' }, { v: 'mid', label: '4-10' }, { v: 'high', label: '11+' }], () => state.f.floor, (v) => { state.f.floor = v; });
  seg('segSize', [{ v: 'any', label: 'Any' }, { v: 'small', label: 'Small (up to 30 flats)' }, { v: 'medium', label: 'Medium (31-120)' }, { v: 'large', label: 'Large (120+)' }], () => state.f.size, (v) => { state.f.size = v; });
  const drawRadius = seg('segRadius', [{ v: 0, label: 'Off' }, { v: 250, label: '250 m' }, { v: 500, label: '500 m' }, { v: 1000, label: '1 km' }], () => state.f.radius, (v) => { state.f.radius = v; });
  seg('segLayer', [{ v: 'heat', label: 'Rent heat map' }, { v: 'flats', label: 'Flats' }, { v: 'both', label: 'Both' }], () => state.layer, (v) => { state.layer = v; });
  seg('segCell', [{ v: 150, label: '150 m' }, { v: 200, label: '200 m' }, { v: 400, label: '400 m' }, { v: 800, label: '800 m' }], () => state.cell, (v) => { state.cell = v; });
  const drawParking = seg('segParking', [{ v: 'without', label: 'Without car space' }, { v: 'with', label: 'With car space' }], () => state.parking, (v) => { state.parking = v; });

  const sel = $('suburb');
  sel.innerHTML = '<option value="-1">Any suburb</option>' + C.suburbLabels.map((l, i) => [l, i]).sort((a, b) => a[0].localeCompare(b[0])).map(([l, i]) => `<option value="${i}">${esc(l)}</option>`).join('');
  sel.value = String(defaultSuburb);
  sel.onchange = () => { state.f.suburb = +sel.value; render(); };

  function setMode(m) {
    state.mode = m;
    $('tabFind').className = m === 'find' ? 'on' : ''; $('tabDescribe').className = m === 'describe' ? 'on' : '';
    $('paneFind').classList.toggle('hide', m !== 'find'); $('paneDescribe').classList.toggle('hide', m !== 'describe');
    render();
    if (map) setTimeout(() => map.invalidateSize(), 50);
  }
  $('tabFind').onclick = () => setMode('find'); $('tabDescribe').onclick = () => setMode('describe');

  // ---------- address search
  const q = $('q'), sug = $('suggest');
  q.oninput = () => {
    const hits = q.value.trim().length < 3 ? [] : R.search(C, q.value, 10);
    sug.innerHTML = hits.map((i) => `<li data-i="${i}">${esc(label(i))}</li>`).join('');
    sug.classList.toggle('hide', !hits.length);
  };
  sug.onclick = (e) => { const li = e.target.closest('li'); if (li) pickFlat(+li.dataset.i); };
  function pickFlat(i) {
    state.flat = i; setMode('find'); q.value = label(i); sug.classList.add('hide');
    state.parking = C.car[i] > 0 ? 'with' : 'without'; drawParking();
    state.f.suburb = C.sub[i]; sel.value = String(C.sub[i]);
    render();
  }

  // ---------- map
  let map = null, layer = null, heat = null, ring = null, centerMarker = null;
  if (window.L) {
    map = L.map('map').setView([-33.8808, 151.2061], 13);
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19, attribution: '&copy; OpenStreetMap contributors' }).addTo(map);
    heat = L.layerGroup().addTo(map); layer = L.layerGroup().addTo(map);
    map.on('click', (e) => {
      if (state.mode !== 'describe') return;
      state.f.center = { lat: e.latlng.lat, lng: e.latlng.lng };
      if (!state.f.radius) { state.f.radius = 500; drawRadius(); }
      render();
    });
  } else {
    $('mapWrap').innerHTML = '<div class="nomap">Map needs an internet connection (OpenStreetMap tiles). Everything else works offline.</div>';
  }

  // ---------- charts
  function histSvg(sorted, value) {
    if (sorted.length < 3) return '<div class="hint">Not enough comparable flats.</div>';
    const bins = R.histogram(sorted, 24), W = 520, H = 200, L0 = 10, B = 30, T = 14;
    const mx = Math.max(...bins.map((b) => b.c)), lo = bins[0].x0, hi = bins[bins.length - 1].x1, bw = (W - 2 * L0) / bins.length;
    const X = (v) => L0 + ((v - lo) / (hi - lo)) * (W - 2 * L0);
    const bars = bins.map((b, k) => { const h = (b.c / mx) * (H - B - T); return `<rect x="${L0 + k * bw + 1}" y="${H - B - h}" width="${bw - 2}" height="${h}" fill="var(--bar)"><title>${money(b.x0)} to ${money(b.x1)}: ${b.c} flats</title></rect>`; }).join('');
    const vx = Math.max(L0, Math.min(W - L0, X(value)));
    return `<svg viewBox="0 0 ${W} ${H}" width="100%" role="img" aria-label="Distribution of predicted rents for similar flats">${bars}
      <line x1="${vx}" x2="${vx}" y1="${T - 6}" y2="${H - B}" stroke="var(--accent)" stroke-width="2.5"/>
      <text x="${Math.min(vx + 6, W - 120)}" y="${T}" fill="var(--accent)" style="fill:var(--accent);font-weight:600">${money(value)}</text>
      <text class="mut" x="${L0}" y="${H - 10}">${money(lo)}</text><text class="mut" x="${W / 2}" y="${H - 10}" text-anchor="middle">${money((lo + hi) / 2)}</text><text class="mut" x="${W - L0}" y="${H - 10}" text-anchor="end">${money(hi)}</text></svg>
      <div class="hint">${sorted.length.toLocaleString()} similar flats, predicted rent per week</div>`;
  }
  function bedsSvg(rows, hlBeds) {
    const W = 520, H = 210, B = 38, T = 22, mx = Math.max(...rows.map((r) => r.median || 0), 1), bw = 62, gap = (W - 5 * bw) / 6;
    return `<svg viewBox="0 0 ${W} ${H}" width="100%" role="img" aria-label="Median predicted rent by bedrooms">` + rows.map((r, k) => {
      const x = gap + k * (bw + gap), name = r.beds === 0 ? 'Studio' : r.beds === 4 ? '4+ bed' : r.beds + ' bed';
      if (!isFinite(r.median)) return `<text class="mut" x="${x + bw / 2}" y="${H - B + 16}" text-anchor="middle">${name}</text><text class="mut" x="${x + bw / 2}" y="${H - B - 6}" text-anchor="middle">n/a</text>`;
      const h = (r.median / mx) * (H - B - T), hl = r.beds === hlBeds || (hlBeds >= 4 && r.beds === 4);
      return `<rect x="${x}" y="${H - B - h}" width="${bw}" height="${h}" fill="${hl ? 'var(--accent)' : 'var(--bar)'}"><title>${name}: median ${money(r.median)} (${r.n} flats)</title></rect><text x="${x + bw / 2}" y="${H - B - h - 5}" text-anchor="middle">${money(r.median)}</text><text class="mut" x="${x + bw / 2}" y="${H - B + 16}" text-anchor="middle">${name}</text>`;
    }).join('') + '</svg>';
  }
  function rankSvg(rows, hlSub) {
    const data = rows.filter((r) => isFinite(r.median)).sort((a, b) => b.median - a.median), rh = 20, W = 520, L0 = 130, H = data.length * rh + 6, mx = data[0] ? data[0].median : 1;
    return `<svg viewBox="0 0 ${W} ${H}" width="100%" role="img" aria-label="Median predicted rent by suburb">` + data.map((r, k) => {
      const w = (r.median / mx) * (W - L0 - 60), y = 3 + k * rh, hl = r.sub === hlSub;
      return `<text x="${L0 - 6}" y="${y + 13}" text-anchor="end" ${hl ? 'style="font-weight:700"' : ''}>${esc(C.suburbLabels[r.sub])}</text><rect x="${L0}" y="${y + 2}" width="${w}" height="14" fill="${hl ? 'var(--accent)' : 'var(--bar)'}"><title>${esc(C.suburbLabels[r.sub])}: ${money(r.median)} (${r.n} flats)</title></rect><text class="mut" x="${L0 + w + 5}" y="${y + 13}">${money(r.median)}</text>`;
    }).join('') + '</svg>';
  }

  // ---------- map + table
  const RAMP = ['#ffffb2', '#fecc5c', '#fd8d3c', '#f03b20', '#bd0026'];
  function rampColor(t) {
    t = Math.max(0, Math.min(1, t)); const x = t * (RAMP.length - 1), k = Math.min(RAMP.length - 2, Math.floor(x)), u = x - k;
    const a = RAMP[k].match(/\w\w/g).map((h) => parseInt(h, 16)), b = RAMP[k + 1].match(/\w\w/g).map((h) => parseInt(h, 16));
    return 'rgb(' + a.map((v, n) => Math.round(v + (b[n] - v) * u)).join(',') + ')';
  }
  function drawHeat(heatIdx) {
    heat.clearLayers();
    if (state.layer === 'flats') { $('legend').innerHTML = ''; return null; }
    const H = R.heatCells(C, heatIdx, state.parking, state.cell), span = Math.max(1, H.hi - H.lo);
    H.cells.forEach((c) => {
      const col = rampColor((c.median - H.lo) / span);
      L.rectangle([[c.lat0, c.lng0], [c.lat1, c.lng1]], { weight: 0, fillColor: col, fillOpacity: state.layer === 'both' ? 0.5 : 0.7, interactive: true })
        .bindTooltip(`${money(c.median)} / week median · ${c.n} flats`, { sticky: true }).addTo(heat);
    });
    $('legend').innerHTML = H.cells.length ? `<div style="display:flex;align-items:center;gap:8px;font-size:12px;color:var(--muted)"><span>${money(H.lo)}</span><span style="flex:1;height:10px;border-radius:5px;background:linear-gradient(90deg,${RAMP.join(',')})"></span><span>${money(H.hi)}</span></div><div class="hint">Median predicted weekly rent per ${state.cell} m square (${H.cells.length.toLocaleString()} squares with 2+ flats; colour scale = 5th to 95th percentile).</div>` : '<div class="hint">Not enough flats for a heat map with these filters.</div>';
    return H;
  }
  function drawMap(idx, flatI, estValue, heatIdx) {
    if (!map) return;
    layer.clearLayers();
    const H = drawHeat(heatIdx || idx);
    const pts = state.layer === 'heat' ? [] : idx.length > 350 ? idx.filter((_, k) => k % Math.ceil(idx.length / 350) === 0) : idx;
    pts.forEach((i) => {
      const v = R.rentOf(C, i, state.parking);
      const m = L.circleMarker([C.lat[i], C.lng[i]], { radius: 4, weight: 1, color: '#fff', fillColor: v > estValue * 1.1 ? '#d9480f' : v < estValue * 0.9 ? '#1c7ed6' : '#868e96', fillOpacity: 0.85 });
      m.bindPopup(`${esc(label(i))}<br><b>${money(v)}</b> / week · ${C.beds[i]} bed ${C.baths[i]} bath`);
      m.on('dblclick', () => pickFlat(i)); layer.addLayer(m);
    });
    if (flatI >= 0) L.circleMarker([C.lat[flatI], C.lng[flatI]], { radius: 9, weight: 3, color: '#2563eb', fillColor: '#2563eb', fillOpacity: 0.4 }).addTo(layer).bindPopup(esc(label(flatI)));
    if (ring) { map.removeLayer(ring); ring = null; }
    if (centerMarker) { map.removeLayer(centerMarker); centerMarker = null; }
    const c = state.f.center;
    if (state.mode === 'describe' && c) {
      centerMarker = L.marker([c.lat, c.lng]).addTo(map);
      if (state.f.radius) ring = L.circle([c.lat, c.lng], { radius: state.f.radius, color: '#2563eb', weight: 1, fillOpacity: 0.05 }).addTo(map);
    }
    const focusPts = pts.length ? pts : (H ? H.cells.slice(0, 1).map((c) => null) : []);
    const focus = flatI >= 0 ? [C.lat[flatI], C.lng[flatI]] : c ? [c.lat, c.lng] : (pts.length ? [C.lat[pts[0]], C.lng[pts[0]]] : null);
    if (state.mode === 'describe' && !c && (pts.length || (H && H.cells.length))) {
      const b = pts.length ? L.latLngBounds(pts.map((i) => [C.lat[i], C.lng[i]])) : L.latLngBounds(H.cells.map((k) => [(k.lat0 + k.lat1) / 2, (k.lng0 + k.lng1) / 2]));
      map.fitBounds(b.pad(0.1), { maxZoom: 15 });
    }
    else if (focus) map.setView(focus, flatI >= 0 || c ? 15 : 13);
  }
  function compsTable(list) {
    if (!list.length) return '<div class="hint">No comparable flats found.</div>';
    return `<table><thead><tr><th>Address</th><th>Type</th><th class="r">Bed</th><th class="r">Bath</th><th class="r">Floor</th><th class="r">Predicted rent</th></tr></thead><tbody>` +
      list.map((i) => `<tr class="click" data-i="${i}"><td>${esc(label(i))}</td><td>${esc(R.titleCase(C.types[C.type[i]]))}</td><td class="r">${C.beds[i]}</td><td class="r">${C.baths[i]}</td><td class="r">${C.floor[i] >= 0 ? C.floor[i] : '-'}</td><td class="r">${money(R.rentOf(C, i, state.parking))}</td></tr>`).join('') + '</tbody></table><div class="hint">Click a row to look up that flat.</div>';
  }
  $('comps').onclick = (e) => { const tr = e.target.closest('tr.click'); if (tr) pickFlat(+tr.dataset.i); };

  // ---------- result card
  function resultCard(o) {
    const err = o.err;
    return `<div class="result"><div>
      <div class="hint">${esc(o.kicker)}</div>
      <div class="big">${money(o.value)} <small>/ week</small></div>
      <div class="range">${esc(o.rangeLabel)} <b>${money(o.lo)} to ${money(o.hi)}</b> a week</div>
      <div class="range">${money(o.value * 52 / 12)} a month · ${money(o.value * 52)} a year</div>
      ${o.notice ? `<div class="notice">${o.notice}</div>` : ''}
    </div><div class="kv">${o.rows.map(([k, v]) => `<span>${esc(k)}</span><span>${v}</span>`).join('')}</div></div>`;
  }

  function render() {
    const P = state.parking;
    let value, idxForCharts, comps = [], hlBeds = state.f.beds, hlSub = state.f.suburb, flatI = -1, card;
    const errLine = (beds) => `Typical miss for this size: about ±${money(R.typicalError(C, beds))} a week (half of predictions are closer than this).`;
    if (state.mode === 'find') {
      if (state.flat < 0) {
        $('resultCard').innerHTML = '<div class="hint" style="padding:30px 6px;font-size:15px">Search for an address on the left to get our model\'s rent prediction for that flat, or switch to <b>Describe a property</b> to estimate a rent from filters.</div>';
        ['chartHist', 'chartBeds', 'chartRank', 'comps'].forEach((id) => { $(id).innerHTML = ''; }); $('compTitle').textContent = 'Comparable flats';
        if (layer) layer.clearLayers(); return;
      }
      flatI = state.flat; const i = flatI, err = R.typicalError(C, C.beds[i]);
      value = R.rentOf(C, i, P);
      const f = { suburb: C.sub[i], type: C.type[i], beds: C.beds[i], baths: -1, floor: 'any', size: 'any', center: { lat: C.lat[i], lng: C.lng[i] }, radius: 600 };
      const est = R.estimate(C, f, P); idxForCharts = est.idx.filter((k) => k !== i);
      const sorted = est.stats.sorted; const below = sorted.filter((v) => v < value).length / Math.max(1, sorted.length);
      hlBeds = C.beds[i]; hlSub = C.sub[i];
      card = resultCard({
        kicker: `${label(i)}, ${C.suburbLabels[C.sub[i]]}`, value, lo: value - err, hi: value + err, rangeLabel: 'Likely range:', err,
        notice: esc(errLine(C.beds[i])) + (C.car[i] < 0 ? ' Parking for this flat is not recorded, so check both options below.' : ''),
        rows: [['Without car space', money(C.ro[i])], ['With car space', money(C.rw[i])], ['Car space adds', money(C.rw[i] - C.ro[i])],
          ['Type', esc(R.titleCase(C.types[C.type[i]]))], ['Bedrooms / baths', `${C.beds[i]} / ${C.baths[i]}`], ['Car spaces recorded', C.car[i] >= 0 ? C.car[i] : 'unknown'],
          ['Floor', C.floor[i] >= 0 ? C.floor[i] : 'unknown'], ['Flats in building', C.bsize[i]],
          ['Vs similar flats nearby', `${money(est.stats.median)} median · dearer than ${Math.max(1, Math.min(99, Math.round(below * 100)))}%`]],
      });
      comps = R.nearest(C, C.lat[i], C.lng[i], (k) => k !== i && C.beds[k] === C.beds[i] && C.type[k] === C.type[i], 10).map((o) => o.i);
      $('compTitle').textContent = 'Nearest similar flats (same type and bedrooms)';
      $('resultCard').innerHTML = card;
      $('chartHist').innerHTML = histSvg(sorted, value);
      $('mapHint').textContent = 'Heat squares use all flats of the same type and bedrooms across the city. Blue ring = your flat; in Flats view orange dots rent for more, blue for less.';
      drawMap(idxForCharts, flatI, value, R.match(C, { suburb: -1, type: C.type[i], beds: C.beds[i], baths: -1, floor: 'any', size: 'any', center: null, radius: 0 }, 1).idx);
    } else {
      const f = state.f, est = R.estimate(C, f, P); value = est.stats.median; idxForCharts = est.idx;
      const err = R.typicalError(C, f.beds), conf = est.confidence;
      const notice = est.relaxed.length ? `Too few exact matches, so I widened the search: ignored ${esc(est.relaxedLabels.join(', '))}.` : '';
      card = resultCard({
        kicker: 'Estimate for a flat matching your filters', value, lo: est.stats.p25, hi: est.stats.p75, rangeLabel: 'Middle half of similar flats:', err,
        notice: [notice, esc(errLine(f.beds))].filter(Boolean).join('<br>'),
        rows: [['Comparable flats', est.stats.n.toLocaleString()], ['Confidence', `<span class="pill ${conf}">${conf}</span>`], ['Lowest to highest (10-90%)', `${money(est.stats.p10)} to ${money(est.stats.p90)}`],
          ['Car space adds', money(est.premium)], ['Without car space', money(R.stats(est.idx.map((k) => C.ro[k])).median)], ['With car space', money(R.stats(est.idx.map((k) => C.rw[k])).median)]],
      });
      const centre = f.center, ref = est.stats.median;
      comps = centre ? R.nearest(C, centre.lat, centre.lng, (k) => est.idx.indexOf(k) >= 0, 10).map((o) => o.i)
        : est.idx.slice().sort((a, b) => Math.abs(R.rentOf(C, a, P) - ref) - Math.abs(R.rentOf(C, b, P) - ref)).slice(0, 10);
      $('compTitle').textContent = centre ? 'Nearest matching flats to your map point' : 'Matching flats closest to the estimate';
      $('centerNote').textContent = f.center ? `Centre set (${f.center.lat.toFixed(4)}, ${f.center.lng.toFixed(4)}). Click again to move it.` : 'No map point chosen.';
      $('resultCard').innerHTML = card;
      $('chartHist').innerHTML = histSvg(est.stats.sorted, value);
      $('mapHint').textContent = 'Click the map to centre a search radius. In Flats view, orange dots rent for more than the estimate, blue for less.';
      drawMap(idxForCharts, -1, value, R.match(C, Object.assign({}, f, { center: null, radius: 0 })).idx);
    }
    const f2 = { suburb: state.mode === 'find' ? C.sub[state.flat] : state.f.suburb, type: state.mode === 'find' ? C.type[state.flat] : state.f.type, beds: state.mode === 'find' ? C.beds[state.flat] : state.f.beds };
    $('chartBeds').innerHTML = bedsSvg(R.medianByBeds(C, f2, P), hlBeds);
    $('chartRank').innerHTML = rankSvg(R.suburbMedians(C, f2, P), hlSub);
    $('comps').innerHTML = compsTable(comps);
  }

  $('subtitle').textContent = `Weekly rent for ${C.n.toLocaleString()} City of Sydney flats · ${C.meta.model} · aimed at ${C.meta.targetPeriod}`;
  $('foot').innerHTML = `Held-out check on June-July 2026 adverts: median error about $${C.meta.medianError} a week, ${C.meta.within100}% of estimates within $100, R² ${C.meta.r2}. These are model estimates, not valuations. ` +
    'Estimates in <b>Describe a property</b> are the middle of our model\'s predictions for real flats that match your filters; the exact-address lookup is the model\'s prediction for that flat. Predictions use only information dated by 31 Jul 2026. Built for the Microburbs hackathon (team d4data); estimates are not financial advice.';
  render();
})();
