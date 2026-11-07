/* Pure logic for the rent estimator (no DOM). Works in the browser (window.RentCore) and in node (module.exports) for testing. */
(function (root) {
  'use strict';

  const FLOOR_BANDS = { any: null, low: [0, 3], mid: [4, 10], high: [11, 9999] };
  const SIZE_BANDS = { any: null, small: [0, 30], medium: [31, 120], large: [121, 99999] };
  const MIN_COMPARABLES = 20;
  // order in which filters are dropped when too few comparables match
  const RELAX_ORDER = ['size', 'floor', 'radius', 'baths', 'type', 'suburb'];
  const RELAX_LABEL = { size: 'building size', floor: 'floor level', radius: 'map radius', baths: 'bathrooms', type: 'property type', suburb: 'suburb' };

  function decode(data) {
    const C = {};
    data.cols.forEach((c, k) => { C[c] = new Array(data.rows.length); });
    data.rows.forEach((r, i) => data.cols.forEach((c, k) => { C[c][i] = r[k]; }));
    C.n = data.rows.length;
    C.suburbs = data.suburbs; C.suburbLabels = data.suburbLabels; C.types = data.types; C.meta = data.meta;
    C._lower = null;
    return C;
  }

  function titleCase(s) {
    return s.toLowerCase().replace(/\b([a-z])/g, (m) => m.toUpperCase()).replace(/\b(Nsw)\b/g, 'NSW');
  }

  function haversine(lat1, lng1, lat2, lng2) {
    const R = 6371000, rad = Math.PI / 180;
    const dLat = (lat2 - lat1) * rad, dLng = (lng2 - lng1) * rad;
    const a = Math.sin(dLat / 2) ** 2 + Math.cos(lat1 * rad) * Math.cos(lat2 * rad) * Math.sin(dLng / 2) ** 2;
    return 2 * R * Math.asin(Math.sqrt(a));
  }

  function quantile(sorted, q) {
    if (!sorted.length) return NaN;
    const pos = (sorted.length - 1) * q, lo = Math.floor(pos), hi = Math.ceil(pos);
    return sorted[lo] + (sorted[hi] - sorted[lo]) * (pos - lo);
  }

  function stats(values) {
    const s = values.slice().sort((a, b) => a - b);
    return { n: s.length, min: s[0], p10: quantile(s, 0.1), p25: quantile(s, 0.25), median: quantile(s, 0.5), p75: quantile(s, 0.75), p90: quantile(s, 0.9), max: s[s.length - 1], sorted: s };
  }

  function bedsMatch(v, want) { return want < 0 ? true : want >= 4 ? v >= 4 : v === want; }
  function bathsMatch(v, want) { return want < 0 ? true : want >= 3 ? v >= 3 : v === want; }

  /* f = {suburb:-1|idx, type:-1|idx, beds:-1..4, baths:-1..3, floor:'any'|'low'|'mid'|'high', size:'any'|'small'|'medium'|'large', center:{lat,lng}|null, radius:meters}
     Returns indices of matching flats, widening the filters (in RELAX_ORDER) until at least MIN_COMPARABLES match. */
  function match(C, f, minN) {
    minN = minN || MIN_COMPARABLES;
    const active = { size: f.size !== 'any', floor: f.floor !== 'any', radius: !!(f.center && f.radius > 0), baths: f.baths >= 0, type: f.type >= 0, suburb: f.suburb >= 0 };
    const relaxed = [];
    const run = () => {
      const out = [];
      const fl = FLOOR_BANDS[f.floor], sz = SIZE_BANDS[f.size];
      for (let i = 0; i < C.n; i++) {
        if (active.suburb && C.sub[i] !== f.suburb) continue;
        if (active.type && C.type[i] !== f.type) continue;
        if (!bedsMatch(C.beds[i], f.beds)) continue;
        if (active.baths && !bathsMatch(C.baths[i], f.baths)) continue;
        if (active.floor && !(C.floor[i] >= fl[0] && C.floor[i] <= fl[1])) continue;
        if (active.size && !(C.bsize[i] >= sz[0] && C.bsize[i] <= sz[1])) continue;
        if (active.radius && haversine(f.center.lat, f.center.lng, C.lat[i], C.lng[i]) > f.radius) continue;
        out.push(i);
      }
      return out;
    };
    let idx = run();
    for (const k of RELAX_ORDER) {
      if (idx.length >= minN) break;
      if (active[k]) { active[k] = false; relaxed.push(k); idx = run(); }
    }
    return { idx, relaxed, relaxedLabels: relaxed.map((k) => RELAX_LABEL[k]) };
  }

  function rentOf(C, i, parking) { return parking === 'with' ? C.rw[i] : C.ro[i]; }

  function estimate(C, f, parking) {
    const m = match(C, f);
    const vals = m.idx.map((i) => rentOf(C, i, parking));
    const st = stats(vals);
    const prem = stats(m.idx.map((i) => C.rw[i] - C.ro[i]));
    const spread = st.n ? (st.p75 - st.p25) / st.median : 1;
    const confidence = st.n >= 60 && spread < 0.3 ? 'High' : st.n >= MIN_COMPARABLES && spread < 0.5 ? 'Medium' : 'Low';
    return { ...m, parking, stats: st, premium: prem.median, confidence, spread };
  }

  function typicalError(C, beds) {
    const e = C.meta.errByBeds; const key = String(Math.max(0, Math.min(3, beds < 0 ? 1 : beds)));
    return e[key] != null ? e[key] : C.meta.medianError;
  }

  function search(C, query, limit) {
    limit = limit || 10;
    if (!C._lower) C._lower = C.addr.map((a) => a.toLowerCase());
    const toks = query.toLowerCase().split(/[\s,]+/).filter(Boolean);
    if (!toks.length) return [];
    const hits = [];
    for (let i = 0; i < C.n; i++) {
      const a = C._lower[i]; let ok = true;
      for (const t of toks) {
        if (a.indexOf(t) >= 0) continue;
        if (/^\d+$/.test(t)) {   // a street number inside a range such as 24-30
          const n = +t, re = /(\d+)-(\d+)/g; let m, inRange = false;
          while ((m = re.exec(a))) { if (+m[1] <= n && n <= +m[2]) { inRange = true; break; } }
          if (inRange) continue;
        }
        ok = false; break;
      }
      if (ok) { hits.push(i); if (hits.length >= 400) break; }
    }
    hits.sort((a, b) => C.addr[a].length - C.addr[b].length);
    return hits.slice(0, limit);
  }

  function nearest(C, lat, lng, filterFn, k) {
    const arr = [];
    for (let i = 0; i < C.n; i++) { if (filterFn(i)) arr.push([haversine(lat, lng, C.lat[i], C.lng[i]), i]); }
    arr.sort((a, b) => a[0] - b[0]);
    return arr.slice(0, k).map(([d, i]) => ({ i, d }));
  }

  /* median rent per suburb for the given type/beds/parking (ignoring suburb), for the ranking chart */
  function suburbMedians(C, f, parking) {
    const groups = C.suburbs.map(() => []);
    for (let i = 0; i < C.n; i++) {
      if (f.type >= 0 && C.type[i] !== f.type) continue;
      if (!bedsMatch(C.beds[i], f.beds)) continue;
      groups[C.sub[i]].push(rentOf(C, i, parking));
    }
    return groups.map((g, s) => ({ sub: s, n: g.length, median: g.length >= 5 ? quantile(g.sort((a, b) => a - b), 0.5) : NaN }));
  }

  function medianByBeds(C, f, parking) {
    const groups = [[], [], [], [], []];
    for (let i = 0; i < C.n; i++) {
      if (f.suburb >= 0 && C.sub[i] !== f.suburb) continue;
      if (f.type >= 0 && C.type[i] !== f.type) continue;
      const b = C.beds[i]; if (b < 0) continue;
      groups[Math.min(4, b)].push(rentOf(C, i, parking));
    }
    return groups.map((g, b) => ({ beds: b, n: g.length, median: g.length >= 5 ? quantile(g.sort((a, c) => a - c), 0.5) : NaN }));
  }

  function histogram(sorted, bins) {
    if (!sorted.length) return [];
    const lo = quantile(sorted, 0.01), hi = quantile(sorted, 0.99), w = (hi - lo) / bins || 1;
    const out = Array.from({ length: bins }, (_, k) => ({ x0: lo + k * w, x1: lo + (k + 1) * w, c: 0 }));
    for (const v of sorted) { const k = Math.min(bins - 1, Math.max(0, Math.floor((v - lo) / w))); out[k].c++; }
    return out;
  }

  /* Rent heat map: median predicted rent per square grid cell (about cellM metres wide) over the given flats. */
  function heatCells(C, idx, parking, cellM) {
    const dLat = cellM / 110540, dLng = cellM / (111320 * Math.cos(-33.88 * Math.PI / 180));
    const cells = new Map();
    for (const i of idx) {
      const ky = Math.floor(C.lat[i] / dLat), kx = Math.floor(C.lng[i] / dLng), key = ky + ':' + kx;
      let c = cells.get(key); if (!c) { c = { lat0: ky * dLat, lat1: (ky + 1) * dLat, lng0: kx * dLng, lng1: (kx + 1) * dLng, vals: [] }; cells.set(key, c); }
      c.vals.push(rentOf(C, i, parking));
    }
    const out = [];
    cells.forEach((c) => { if (c.vals.length >= 2) { c.vals.sort((a, b) => a - b); out.push({ lat0: c.lat0, lat1: c.lat1, lng0: c.lng0, lng1: c.lng1, n: c.vals.length, median: quantile(c.vals, 0.5) }); } });
    const meds = out.map((c) => c.median).sort((a, b) => a - b);
    return { cells: out, lo: quantile(meds, 0.05), hi: quantile(meds, 0.95) };
  }

  const api = { heatCells, decode, titleCase, haversine, quantile, stats, match, estimate, typicalError, search, nearest, suburbMedians, medianByBeds, histogram, rentOf, MIN_COMPARABLES, FLOOR_BANDS, SIZE_BANDS };
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else root.RentCore = api;
})(typeof window !== 'undefined' ? window : globalThis);
