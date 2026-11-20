/* TuneCore: compare a student's recording with the speaker's, chunk by chunk, entirely in the browser.
   Same file runs in Node for testing (module.exports) and in the page (window.TuneCore).

   Steps
   1. trim()        cut the silence round a recording
   2. pitchTrack()  semitones every 10 ms (the page's own autocorrelation tracker, 16 kHz, 70-400 Hz)
   3. mfcc()        13 numbers per 10 ms that describe WHAT sound is being made
   4. dtw()         line the two recordings up by sound, so "where is the student's 'from'?" has an answer
   5. classify5()   the tone of a stretch from its pitch: fall, rise, fall-rise, rise-fall, flat (pitch_check.py port)
   6. scoreLine()   per chunk: speaker tone (measured) vs student tone, plus how wide each voice moved
*/
(function (root) {
  'use strict';
  const HOP = 0.01;

  /* ---------- 1. trim (same rule as the page) ---------- */
  function trim(d, sr) {
    const win = Math.floor(sr * .02), rms = [];
    let peak = 0;
    for (let i = 0; i + win <= d.length; i += win) {
      let s = 0; for (let j = i; j < i + win; j++) s += d[j] * d[j];
      const v = Math.sqrt(s / win); rms.push(v); if (v > peak) peak = v;
    }
    if (peak < .004) return null;
    const thr = Math.max(peak * .035, .0015);
    const a = rms.findIndex(v => v > thr), b = rms.length - 1 - [...rms].reverse().findIndex(v => v > thr);
    const step = win / sr, dur = d.length / sr;
    const start = Math.max(0, a * step - .08), end = Math.min(dur, (b + 1) * step + .25);
    return { start, end, peak };
  }

  /* downsample to ~16 kHz by block averaging, cut to the trimmed segment */
  function prepare(d0, sr0, tr) {
    const k = Math.max(1, Math.round(sr0 / 16000)), sr = sr0 / k;
    const a0 = Math.floor(tr.start * sr0), n = Math.floor((Math.floor(tr.end * sr0) - a0) / k), d = new Float32Array(n);
    for (let i = 0; i < n; i++) { let s = 0; for (let j = 0; j < k; j++) s += d0[a0 + i * k + j] || 0; d[i] = s / k; }
    return { d, sr };
  }

  /* ---------- 2. pitch ---------- */
  function pitchTrack(d, sr) {
    const n = d.length, win = Math.round(.04 * sr), hop = Math.round(HOP * sr), minL = Math.floor(sr / 400), maxL = Math.ceil(sr / 70);
    const starts = [], rms = [];
    for (let s = 0; s + win + maxL < n; s += hop) {
      let e = 0; for (let i = s; i < s + win; i++) e += d[i] * d[i];
      starts.push(s); rms.push(Math.sqrt(e / win));
    }
    const peak = Math.max(0, ...rms), st = [];
    starts.forEach((s, fi) => {
      if (rms[fi] < peak * .08) { st.push(null); return; }
      let e0 = 0; for (let i = s; i < s + win; i++) e0 += d[i] * d[i];
      const rs = new Float32Array(maxL + 2); let best = 0;
      for (let L = minL; L <= maxL + 1; L++) {
        let c = 0, e1 = 0;
        for (let i = s; i < s + win; i++) { const b = d[i + L]; c += d[i] * b; e1 += b * b; }
        rs[L] = c / Math.sqrt(e0 * e1 || 1); if (L <= maxL && rs[L] > best) best = rs[L];
      }
      if (best < .55) { st.push(null); return; }
      let bl = 0;
      for (let L = minL + 1; L <= maxL; L++) if (rs[L] >= best * .9 && rs[L] >= rs[L - 1] && rs[L] >= rs[L + 1]) { bl = L; break; }
      if (!bl) { st.push(null); return; }
      const p = rs[bl - 1], q = rs[bl], u = rs[bl + 1], den = p - 2 * q + u, lag = den ? bl + .5 * (p - u) / den : bl;
      st.push(12 * Math.log2(sr / lag));
    });
    const med = st.map((v, i) => {
      if (v === null) return null;
      const w = st.slice(Math.max(0, i - 2), i + 3).filter(x => x !== null).sort((a, b) => a - b);
      return w[w.length >> 1];
    });
    for (let i = 1; i < med.length; i++) if (med[i] !== null && med[i - 1] !== null && Math.abs(med[i] - med[i - 1]) > 2.5) med[i] = null;
    for (let i = 0; i < med.length;) {
      if (med[i] === null) { i++; continue; }
      let j = i; while (j < med.length && med[j] !== null) j++;
      if (j - i < 4) for (let q = i; q < j; q++) med[q] = null;
      i = j;
    }
    return med;
  }

  /* ---------- 3. mfcc ---------- */
  function fft(re, im) {
    const n = re.length;
    for (let i = 1, j = 0; i < n; i++) {
      let bit = n >> 1; for (; j & bit; bit >>= 1) j ^= bit; j ^= bit;
      if (i < j) { let t = re[i]; re[i] = re[j]; re[j] = t; t = im[i]; im[i] = im[j]; im[j] = t; }
    }
    for (let len = 2; len <= n; len <<= 1) {
      const ang = -2 * Math.PI / len, wr = Math.cos(ang), wi = Math.sin(ang);
      for (let i = 0; i < n; i += len) {
        let cr = 1, ci = 0;
        for (let k = 0; k < len / 2; k++) {
          const a = i + k, b = a + len / 2;
          const xr = re[b] * cr - im[b] * ci, xi = re[b] * ci + im[b] * cr;
          re[b] = re[a] - xr; im[b] = im[a] - xi; re[a] += xr; im[a] += xi;
          const t = cr * wr - ci * wi; ci = cr * wi + ci * wr; cr = t;
        }
      }
    }
  }
  const hz2mel = f => 2595 * Math.log10(1 + f / 700), mel2hz = m => 700 * (Math.pow(10, m / 2595) - 1);
  let FB = null;
  function filterbank(sr, nfft, nf) {
    if (FB && FB.sr === sr) return FB.fb;
    const lo = hz2mel(80), hi = hz2mel(Math.min(7600, sr / 2 - 100)), pts = [];
    for (let i = 0; i < nf + 2; i++) pts.push(Math.floor((nfft + 1) * mel2hz(lo + (hi - lo) * i / (nf + 1)) / sr));
    const fb = [];
    for (let m = 1; m <= nf; m++) {
      const f = new Float32Array(nfft / 2 + 1);
      for (let k = pts[m - 1]; k < pts[m]; k++) f[k] = (k - pts[m - 1]) / ((pts[m] - pts[m - 1]) || 1);
      for (let k = pts[m]; k < pts[m + 1]; k++) f[k] = (pts[m + 1] - k) / ((pts[m + 1] - pts[m]) || 1);
      fb.push(f);
    }
    FB = { sr, fb }; return fb;
  }
  function mfcc(d, sr) {
    const nfft = 512, nf = 26, nc = 13, wl = Math.round(.025 * sr), hp = Math.round(HOP * sr), fb = filterbank(sr, nfft, nf);
    const win = new Float32Array(wl); for (let i = 0; i < wl; i++) win[i] = .54 - .46 * Math.cos(2 * Math.PI * i / (wl - 1));
    const dct = []; for (let c = 0; c < nc; c++) { const r = new Float32Array(nf); for (let m = 0; m < nf; m++) r[m] = Math.cos(Math.PI * c * (m + .5) / nf); dct.push(r); }
    const frames = [], re = new Float32Array(nfft), im = new Float32Array(nfft), le = new Float32Array(nf);
    for (let s = 0; s + wl <= d.length; s += hp) {
      re.fill(0); im.fill(0);
      for (let i = 0; i < wl; i++) re[i] = (d[s + i] - (i ? d[s + i - 1] : 0) * .97) * win[i];
      fft(re, im);
      for (let m = 0; m < nf; m++) { let e = 0; const f = fb[m]; for (let k = 0; k <= nfft / 2; k++) if (f[k]) e += f[k] * (re[k] * re[k] + im[k] * im[k]); le[m] = Math.log(e + 1e-9); }
      const v = new Float32Array(nc);
      for (let c = 0; c < nc; c++) { let x = 0; for (let m = 0; m < nf; m++) x += dct[c][m] * le[m]; v[c] = x; }
      frames.push(v);
    }
    /* per-recording mean and variance normalisation: removes the microphone and most of the voice difference */
    for (let c = 0; c < nc; c++) {
      let m = 0; frames.forEach(v => m += v[c]); m /= frames.length || 1;
      let q = 0; frames.forEach(v => q += (v[c] - m) * (v[c] - m)); q = Math.sqrt(q / (frames.length || 1)) || 1;
      frames.forEach(v => v[c] = (v[c] - m) / q);
    }
    return frames;
  }

  /* ---------- 4. dtw ---------- */
  function dtw(A, B) {
    const N = A.length, M = B.length, nc = A[0].length;
    const D = new Float32Array((N + 1) * (M + 1)).fill(Infinity), bp = new Uint8Array((N + 1) * (M + 1));
    const W = M + 1; D[0] = 0;
    for (let i = 1; i <= N; i++) {
      const a = A[i - 1];
      for (let j = 1; j <= M; j++) {
        const b = B[j - 1]; let s = 0; for (let c = 0; c < nc; c++) { const x = a[c] - b[c]; s += x * x; }
        const d = Math.sqrt(s);
        const dg = D[(i - 1) * W + j - 1] + 2 * d, up = D[(i - 1) * W + j] + d, lf = D[i * W + j - 1] + d;
        if (dg <= up && dg <= lf) { D[i * W + j] = dg; bp[i * W + j] = 0; }
        else if (up <= lf) { D[i * W + j] = up; bp[i * W + j] = 1; }
        else { D[i * W + j] = lf; bp[i * W + j] = 2; }
      }
    }
    const path = []; let i = N, j = M;
    while (i > 0 && j > 0) { path.push([i - 1, j - 1]); const b = bp[i * W + j]; if (b === 0) { i--; j--; } else if (b === 1) i--; else j--; }
    path.reverse();
    return { path, cost: D[N * W + M] / (N + M) };
  }
  /* for every frame of A: the first and last frame of B it was lined up with */
  function mapRange(path, N) {
    const lo = new Int32Array(N).fill(-1), hi = new Int32Array(N).fill(-1);
    path.forEach(([i, j]) => { if (lo[i] < 0 || j < lo[i]) lo[i] = j; if (j > hi[i]) hi[i] = j; });
    return { lo, hi };
  }

  /* ---------- 5. tone ---------- */
  const median = a => { const s = a.slice().sort((x, y) => x - y); return s.length ? (s.length & 1 ? s[s.length >> 1] : (s[s.length / 2 - 1] + s[s.length / 2]) / 2) : NaN; };
  function arraySplit(v, n) { const out = [], base = Math.floor(v.length / n), extra = v.length % n; let k = 0; for (let i = 0; i < n; i++) { const m = base + (i < extra ? 1 : 0); out.push(v.slice(k, k + m)); k += m; } return out; }
  /* st: semitone values (null = no pitch) of a nucleus-plus-tail stretch, relative to the whole recording's median */
  function classify5(st, lead) {
    const v = st.filter(x => x !== null);
    if (v.length < 6) {
      /* creaky or very short: if a clearly higher lead-in sits just before it and what is left is low, it is a fall */
      const lv = (lead || []).filter(x => x !== null);
      if (v.length >= 2 && lv.length >= 3 && Math.max(...lv) - median(v) >= 2.5 && median(v) <= -1) return { tone: '↘', p: [] };
      return { tone: '?', p: [] };
    }
    const p = arraySplit(v, 5).map(median);
    const drop = Math.max(p[0], p[1]) - Math.min(p[2], p[3], p[4]);
    const riseEnd = p[4] - Math.min(p[1], p[2], p[3]);
    let tone = '?';
    if (p[2] >= Math.max(p[1], p[3]) && p[2] - p[0] >= 3 && p[2] - p[4] >= 3) tone = '↗↘';
    else if (drop >= 2 && riseEnd >= 1.5) tone = '↘↗';
    else if (drop >= 2) tone = '↘';
    else if (p[4] - Math.min(p[0], p[1]) >= 2) tone = '↗';
    else if (Math.max(...p) - Math.min(...p) < 1.5) tone = '→';
    /* a stretch sitting low after a higher lead-in is the end of a fall that began just before the window */
    if ((tone === '→' || tone === '?') && lead && lead.length) {
      const lv = lead.filter(x => x !== null);
      if (lv.length && Math.max(...lv) - median(v) >= 2 && median(v) <= -1.5) tone = '↘';
    }
    return { tone, p };
  }
  const span = v => { const s = v.filter(x => x !== null).sort((a, b) => a - b); return s.length < 6 ? 0 : s[Math.floor(s.length * .95)] - s[Math.floor(s.length * .05)]; };

  /* ---------- 6. score ---------- */
  const NAME = { '↘': 'goes down', '↗': 'goes up', '↘↗': 'goes down, then up', '↗↘': 'goes up, then down', '→': 'stays flat', '?': '' };
  const NEAR = { '↘': ['↘↗', '↗↘'], '↘↗': ['↘', '↗'], '↗': ['↘↗'], '↗↘': ['↘'], '→': [] };

  /* analyse(): everything we need from one recording, once. */
  function analyse(d0, sr0) {
    const tr = trim(d0, sr0); if (!tr) return null;
    const { d, sr } = prepare(d0, sr0, tr);
    const st = pitchTrack(d, sr), mf = mfcc(d, sr);
    const voiced = st.filter(x => x !== null);
    const mid = voiced.length ? median(voiced) : 0;
    return { tr, sr, st, mf, rel: st.map(x => x === null ? null : x - mid), voicedShare: voiced.length / Math.max(1, st.length), dur: d.length / sr };
  }

  /* Compare the two voices over a stretch of the speaker's recording. Every speaker frame is paired with the
     student frame the alignment chose; only frames where BOTH voices have a measured pitch are used (so a
     creaky ending that one tracker lost and the other found cannot fake a difference). Each voice is measured
     against its own average, so a deep voice is never marked down for being deep.
     Returns {n, d, spkRange, youRange}: d = how far apart the two shapes are, in semitones (root mean square). */
  function compareStretch(spk, stu, mr, a, b) {
    const S = [], Y = [];
    for (let i = a; i <= b && i < spk.rel.length; i++) {
      if (mr.lo[i] < 0) continue;
      const j = Math.round((mr.lo[i] + mr.hi[i]) / 2), x = spk.rel[i], z = stu.rel[j];
      if (typeof x === 'number' && typeof z === 'number') { S.push(x); Y.push(z); }
    }
    if (S.length < 8) return { n: S.length, d: null };
    const ms = S.reduce((p, q) => p + q, 0) / S.length, my = Y.reduce((p, q) => p + q, 0) / Y.length;
    let q = 0, sxy = 0, sxx = 0, syy = 0;
    for (let i = 0; i < S.length; i++) { q += ((S[i] - ms) - (Y[i] - my)) ** 2; sxy += (S[i] - ms) * (Y[i] - my); sxx += (S[i] - ms) ** 2; syy += (Y[i] - my) ** 2; }
    /* r: do the two go up and down together? 1 = yes, 0 = unrelated, -1 = one rises where the other falls */
    return { n: S.length, d: Math.sqrt(q / S.length), r: sxx > 0 && syy > 0 ? sxy / Math.sqrt(sxx * syy) : 0, spkRange: span(S), youRange: span(Y) };
  }
  const SAME = 2.0, NEARLY = 3.5;   /* semitones; chosen on known-difference test recordings, see test-synth.js */

  /* spk, stu: analyse() results.  line: {units:[{w:[a,b],nuc}], voices:{x:{tones,words}}}, voice: key. */
  function scoreLine(line, voice, spk, stu, opts) {
    const same = opts && opts.same || SAME, nearly = opts && opts.nearly || NEARLY;
    const V = line.voices[voice], res = { units: [], ok: true, notes: [] };
    if (!stu || stu.voicedShare < .12) { res.ok = false; res.notes.push('quiet'); return res; }
    const al = dtw(spk.mf, stu.mf), mr = mapRange(al.path, spk.mf.length);
    res.match = al.cost; res.mr = mr;
    const toF = t => Math.max(0, Math.min(spk.mf.length - 1, Math.round((t - spk.tr.start) / HOP)));
    line.units.forEach((u, ui) => {
      const tn = V.words[u.nuc][1] - .08, tu = V.words[u.w[0]][1] - .02;
      const t1 = ui + 1 < line.units.length ? V.words[line.units[ui + 1].w[0]][1] : spk.tr.end;
      const a = toF(tn), b = toF(t1), au = toF(tu);
      const cn = compareStretch(spk, stu, mr, a, b), cu = compareStretch(spk, stu, mr, au, b);
      const c = cn.d !== null ? cn : cu;
      const ja = mr.lo[a] >= 0 ? mr.lo[a] : 0, jb = mr.hi[b] >= 0 ? mr.hi[b] : stu.st.length - 1;
      const spkT = classify5(spk.rel.slice(a, b + 1), spk.rel.slice(Math.max(0, a - 30), a + 10));
      const youT = classify5(stu.rel.slice(ja, jb + 1), stu.rel.slice(Math.max(0, ja - 30), ja + 10));
      const r = { unit: ui, word: line.plainWords ? line.plainWords[u.nuc] : null, d: c.d, dUnit: cu.d, n: c.n,
        ref: spkT.tone, you: youT.tone, refPraat: V.tones[ui], spkRange: c.spkRange, youRange: c.youRange, a, b };
      if (c.d === null) r.verdict = 'unclear';
      else if (c.d <= same) r.verdict = 'same';
      else if (c.d <= nearly) r.verdict = 'near';
      else r.verdict = 'try';
      r.r = c.r;
      r.flat = c.d !== null && c.spkRange >= 3 && c.youRange < Math.max(1.5, .35 * c.spkRange);
      /* going the wrong way is never "the same tune", however small the distance */
      if (c.d !== null && c.spkRange >= 3) { if (c.r < -.2 && r.verdict !== 'try') r.verdict = 'try'; else if (c.r < .2 && r.verdict === 'same') r.verdict = 'near'; }
      /* a voice that barely moves is not "the same tune", even if the few small movements line up */
      if (r.flat && r.verdict === 'same') r.verdict = 'near';
      res.units.push(r);
    });
    return res;
  }

  const api = { HOP, SAME, NEARLY, trim, prepare, pitchTrack, mfcc, dtw, mapRange, classify5, analyse, scoreLine, compareStretch, span, NAME, NEAR };
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else root.TuneCore = api;
})(typeof window !== 'undefined' ? window : globalThis);
