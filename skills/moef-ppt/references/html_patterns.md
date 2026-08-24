# HTML Patterns — MOEF Design System

Copy these patterns verbatim. Do not simplify or modify the renderChart engine.

---

## CSS Shell

```html
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>MOEF — [Presentation Title]</title>
<style>
@font-face {
  font-family: 'Pretendard';
  src: url('../../IR_ppt/Pretendard-fonts/public/static/alternative/Pretendard-Medium.ttf') format('truetype');
  font-weight: 500;
}
@font-face {
  font-family: 'Pretendard';
  src: url('../../IR_ppt/Pretendard-fonts/public/static/alternative/Pretendard-Black.ttf') format('truetype');
  font-weight: 900;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: #0a1020; padding: 48px 40px; font-family: 'Pretendard', 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif; }
.slide-label { color: #445; font-size: 11px; font-family: monospace; letter-spacing: 0.08em; margin-bottom: 8px; }
.slide-wrap  { margin-bottom: 52px; }
.slide {
  width: 960px; height: 540px;
  position: relative; overflow: hidden;
  box-shadow: 0 12px 40px rgba(0,0,0,0.8);
  background: linear-gradient(160deg, #243478 0%, #1B2D60 40%, #121C48 100%);
}
.slide-title  { font-family:'Pretendard',sans-serif; font-weight:900; font-size:32px; color:#FFFFFF; line-height:1.25; }
.body-text    { font-family:'Pretendard',sans-serif; font-weight:500; font-size:12px; color:#FFFFFF; line-height:1.6; }
.muted-text   { font-family:'Pretendard',sans-serif; font-weight:500; font-size:11px; color:rgba(192,210,232,0.75); }
.title-underline { height:3px; background:#00BFFF; margin-top:8px; }
.slide-header { position:absolute; top:28px; left:36px; right:36px; }

/* ── Slideshow mode ── */
body.show-mode { background: #000 !important; overflow: hidden; }
/* CRITICAL: use visibility, NOT display, to hide/show slides here.
   .slide is nested inside .slide-wrap. display:none on an ANCESTOR always hides its
   descendants regardless of the descendant's own display value — so display:none on
   .slide-wrap would hide every .slide inside it too, including the one with .show-active,
   and the slideshow button would appear to do nothing (only the black background + counter,
   which live outside .slide-wrap, would render). visibility does not have this problem:
   a descendant's visibility:visible DOES override an ancestor's visibility:hidden. */
body.show-mode .slide-wrap,
body.show-mode .slide-label { visibility: hidden; }
body.show-mode .slide.show-active {
  visibility: visible;
  position: fixed; top: 50%; left: 50%;
  z-index: 100;
  box-shadow: 0 0 80px rgba(0,0,0,0.95);
}
#show-btn {
  position: fixed; top: 18px; right: 24px; z-index: 9998;
  background: rgba(0,191,255,0.12); border: 1px solid rgba(0,191,255,0.45);
  color: #00BFFF; font-family: 'Pretendard', sans-serif; font-size: 13px;
  padding: 8px 20px; border-radius: 6px; cursor: pointer; transition: background 0.2s;
}
#show-btn:hover { background: rgba(0,191,255,0.28); }
#show-nav { display: none; }
body.show-mode #show-nav { display: block; }
#show-prev, #show-next {
  position: fixed; top: 50%; transform: translateY(-50%);
  background: rgba(255,255,255,0.07); border: none; color: rgba(255,255,255,0.8);
  font-size: 26px; width: 50px; height: 80px; cursor: pointer;
  border-radius: 4px; z-index: 201; opacity: 0; transition: opacity 0.2s, background 0.15s;
}
#show-nav:hover #show-prev,
#show-nav:hover #show-next { opacity: 1; }
#show-prev:hover, #show-next:hover { background: rgba(255,255,255,0.18); }
#show-prev { left: 12px; }
#show-next { right: 12px; }
#show-counter {
  position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%);
  color: rgba(192,210,232,0.65); font-size: 13px;
  font-family: 'Pretendard', sans-serif; z-index: 201; pointer-events: none;
}
#show-exit {
  position: fixed; top: 18px; right: 24px; z-index: 201;
  background: rgba(255,255,255,0.07); border: 1px solid rgba(255,255,255,0.2);
  color: rgba(255,255,255,0.8); font-family: 'Pretendard', sans-serif; font-size: 13px;
  padding: 8px 18px; border-radius: 6px; cursor: pointer; transition: background 0.15s;
}
#show-exit:hover { background: rgba(255,255,255,0.18); }
</style>
</head>
<body>
<!-- SLIDES GO HERE -->

<!-- Slideshow controls (place after last slide-wrap, before <script>) -->
<button id="show-btn">슬라이드쇼 시작 ▶</button>
<div id="show-nav">
  <button id="show-prev">&#8592;</button>
  <button id="show-next">&#8594;</button>
  <div id="show-counter">1 / N</div>
  <button id="show-exit">✕ 종료</button>
</div>

<script>
/* CHART ENGINE — copy verbatim */
</script>
</body>
</html>
```

---

## renderChart Engine (copy VERBATIM — do not modify)

```js
const T = {
  lineYellow: '#E4E020',
  lineBlue:   '#74C0FC',
  lineWhite:  '#FFFFFF',
  barGradTop: '#DCEEFF',
  barGradBot: '#5070A8',
  barGoldTop: '#FFFA9E',   // 2nd bar series in clustered multi-bar charts (renderChartMultiBar)
  barGoldBot: '#D6CE00',
  gridLine:   'rgba(192,210,232,0.15)',
  zeroLine:   'rgba(255,255,255,0.28)',
  axisText:   'rgba(192,210,232,0.75)',
};
const NS = 'http://www.w3.org/2000/svg';

function el(tag, attrs) {
  const e = document.createElementNS(NS, tag);
  Object.entries(attrs || {}).forEach(([k, v]) => e.setAttribute(k, v));
  return e;
}
function lbl(svg, x, y, text, opts) {
  opts = opts || {};
  const t = el('text', {
    x, y,
    'font-family': 'Pretendard,sans-serif',
    'font-size': opts.size || 10,
    'font-weight': 500,
    fill: opts.color || T.axisText,
    'text-anchor': opts.anchor || 'middle',
  });
  t.textContent = text;
  svg.appendChild(t);
}

// topColor/botColor optional — defaults to the standard blue bar gradient. Pass
// T.barGoldTop/T.barGoldBot (or any other pair) for a second distinct bar-series gradient,
// e.g. in renderChartMultiBar() where 2+ bar series need visually distinct fills.
function addGrad(svg, id, topColor, botColor) {
  let defs = svg.querySelector('defs');
  if (!defs) { defs = el('defs'); svg.insertBefore(defs, svg.firstChild); }
  const g  = el('linearGradient', { id, x1:'0', y1:'0', x2:'0', y2:'1' });
  const s1 = el('stop', { offset:'0%'   }); s1.style.stopColor = topColor || T.barGradTop;
  const s2 = el('stop', { offset:'100%' }); s2.style.stopColor = botColor || T.barGradBot;
  g.appendChild(s1); g.appendChild(s2); defs.appendChild(g);
}

/*  renderChart(svgId, cx, cy, cw, ch, xLabels, bars, lines, yMin, yMax, gradId, opts)

    opts.step      — gridline interval. Pick so total gridlines < 8.
                     Examples: range 0–20k → step=3000 (7 lines); range 55–95 → step=10 (4 lines)
    opts.unit      — unit string (e.g. '(%)') rendered inside SVG at top-left of chart.
                     Placed 14px above the topmost gridline, right-aligned at cx-8
                     (same right-edge and 8px gap to gridlines as all y-axis numbers).
                     Do NOT repeat the unit in series names or legend text.
    opts.labelSize — x-axis label font size (default 9).

    BAR FLOOR RULE:
      baseVal = max(yMin, min(0, yMax))
      All-positive charts (yMin > 0): bars grow from yMin (chart bottom) upward.
      Mixed charts (yMin < 0):        bars grow from the zero line.
      This prevents bars from filling the entire chart height when all data > 0.

    X-AXIS LABEL RULE:
      Pass ONLY first-of-year periods as non-empty strings; all others = ''.
      renderChart() skips '' so only year-start ticks render.
      Monthly (Jan 2024–Feb 2026, 26 pts):
        ['24.1','','','','','','','','','','','','25.1','','','','','','','','','','','','26.1','']
      Quarterly (Q1 2023–Q4 2025, 12 pts):
        ['23.1Q','','','','24.1Q','','','','25.1Q','','','']                               */
function renderChart(svgId, cx, cy, cw, ch, xLabels, bars, lines, yMin, yMax, gid, opts) {
  opts = opts || {};
  const svg  = document.getElementById(svgId);
  addGrad(svg, gid);

  const n     = xLabels.length;
  const range = yMax - yMin;
  const sc    = ch / range;
  const slotW = cw / n;
  const bw    = slotW * 0.44;
  const boff  = (slotW - bw) / 2;

  // Bar floor: clamp 0 to [yMin, yMax]
  const baseVal = Math.max(yMin, Math.min(0, yMax));

  // Gridline bounds
  const step     = opts.step || 1;
  const vStart   = Math.ceil(yMin / step) * step;
  const vEnd     = Math.floor(yMax / step) * step;
  const topGridY = cy + (yMax - vEnd) * sc;

  // Unit label: 14px above topmost gridline, right-aligned at cx-8
  if (opts.unit) {
    lbl(svg, cx - 8, topGridY - 14, opts.unit, { anchor: 'end', size: 10 });
  }

  // Gridlines (step-spaced; always < 8 per chart). SOLID, not dashed — the earlier dashed
  // style ('3 3') was changed to solid per design direction; keep both HTML and PPTX
  // (valGridLine: {style:'solid',...} in pptx_patterns.md) in agreement.
  for (let v = vStart; v <= vEnd + 1e-9; v = Math.round((v + step) * 1e9) / 1e9) {
    if (v > yMax + 1e-9) break;
    const gy = cy + (yMax - v) * sc;
    svg.appendChild(el('line', {
      x1: cx, y1: gy, x2: cx + cw, y2: gy,
      stroke: Math.abs(v) < 1e-9 ? T.zeroLine : T.gridLine,
      'stroke-width': Math.abs(v) < 1e-9 ? 1 : 0.7,
      'stroke-dasharray': '0',
    }));
    const fmt = step >= 1000
      ? (v / 1000).toFixed(0) + 'k'
      : step < 1 ? v.toFixed(1) : v.toFixed(0);
    lbl(svg, cx - 8, gy + 4, fmt, { anchor: 'end', size: 10 });
  }

  // X-axis line: always drawn at the chart floor (yMin), using the same bright/solid style
  // as the zero-gridline. Charts with yMin=0 already get this for free since their floor
  // coincides with v=0 above; charts whose floor isn't 0 previously showed only a dim regular
  // gridline (or nothing) at the floor — this line makes every chart's x-axis look consistent,
  // without altering any other gridline drawn above. Mirror this in PPTX via
  // catAxisLineShow:true + catAxisLineColor (see pptx_patterns.md's moefCS()).
  svg.appendChild(el('line', {
    x1: cx, y1: cy + ch, x2: cx + cw, y2: cy + ch,
    stroke: T.zeroLine, 'stroke-width': 1, 'stroke-dasharray': '0',
  }));

  // Bars: draw from baseVal to v (no stretch-to-bottom on all-positive charts)
  bars.forEach(s => {
    xLabels.forEach((_, i) => {
      const v      = s.values[i];
      const topVal = Math.max(v, baseVal);
      const botVal = Math.min(v, baseVal);
      const bx     = cx + boff + i * slotW;
      const bh     = (topVal - botVal) * sc;
      const by     = cy + (yMax - topVal) * sc;
      svg.appendChild(el('rect', {
        x: bx, y: by,
        width: Math.max(bw, 1), height: Math.max(bh, 1),
        fill: 'url(#' + gid + ')', rx: 1,
      }));
    });
  });

  // Lines — NO circle markers
  lines.forEach(s => {
    const pts = xLabels.map((_, i) => {
      const px = cx + boff + bw / 2 + i * slotW;
      const py = cy + (yMax - s.values[i]) * sc;
      return px.toFixed(1) + ',' + py.toFixed(1);
    });
    svg.appendChild(el('polyline', {
      points: pts.join(' '),
      stroke: s.color, 'stroke-width': 2,
      fill: 'none', 'stroke-linejoin': 'round', 'stroke-linecap': 'round',
    }));
  });

  // X-axis: only non-empty labels
  const labelSize = opts.labelSize || 9;
  xLabels.forEach((txt, i) => {
    if (!txt) return;
    lbl(svg, cx + slotW / 2 + i * slotW, cy + ch + 16, txt, { size: labelSize });
  });

  // Legend: stacked vertically, top-right; line icons are plain lines (no dots)
  const allS = [
    ...bars.map(s  => ({ name: s.name, color: T.barGradBot, isBar: true })),
    ...lines.map(s => ({ name: s.name, color: s.color, isBar: false })),
  ];
  const legX = cx + cw - 120;
  allS.forEach((s, i) => {
    const lx = legX;
    const ly = cy + 12 + i * 16;
    if (s.isBar) {
      svg.appendChild(el('rect', { x: lx, y: ly - 6, width: 11, height: 9,
        fill: 'url(#' + gid + ')', rx: 1 }));
    } else {
      svg.appendChild(el('line', { x1: lx, y1: ly - 1, x2: lx + 11, y2: ly - 1,
        stroke: s.color, 'stroke-width': 2 }));
    }
    lbl(svg, lx + 14, ly + 4, s.name, { anchor: 'start', size: 9, color: T.axisText });
  });
}

/* renderChartMultiBar — extension for slides needing 2+ CLUSTERED bar series on one axis.
   renderChart()'s bar loop draws every bar series at the SAME x position (i.e. stacked/
   overlapping) — that's correct for the common 1-bar+line combo, but wrong for pure
   multi-bar comparisons (e.g. two comparable-scale bar series side by side). Each series
   gets its own gradient id (series.gid) so they can be visually distinguished; pass
   series.gradTop/gradBot to give each its own two-stop gradient (e.g. T.barGradTop/Bot for
   the first series, T.barGoldTop/Bot for the second). Copy verbatim alongside renderChart(). */
function renderChartMultiBar(svgId, cx, cy, cw, ch, xLabels, bars, yMin, yMax, gid, opts) {
  opts = opts || {};
  const svg = document.getElementById(svgId);
  bars.forEach((s, si) => addGrad(svg, s.gid || (gid + si), s.gradTop, s.gradBot));

  const n     = xLabels.length;
  const range = yMax - yMin;
  const sc    = ch / range;
  const slotW = cw / n;
  const nS    = bars.length;
  const bw    = (slotW * 0.72) / nS;
  const groupOff = (slotW - bw * nS) / 2;

  const baseVal = Math.max(yMin, Math.min(0, yMax));

  const step     = opts.step || 1;
  const vStart   = Math.ceil(yMin / step) * step;
  const vEnd     = Math.floor(yMax / step) * step;
  const topGridY = cy + (yMax - vEnd) * sc;

  if (opts.unit) lbl(svg, cx - 8, topGridY - 14, opts.unit, { anchor: 'end', size: 10 });

  for (let v = vStart; v <= vEnd + 1e-9; v = Math.round((v + step) * 1e9) / 1e9) {
    if (v > yMax + 1e-9) break;
    const gy = cy + (yMax - v) * sc;
    svg.appendChild(el('line', {
      x1: cx, y1: gy, x2: cx + cw, y2: gy,
      stroke: Math.abs(v) < 1e-9 ? T.zeroLine : T.gridLine,
      'stroke-width': Math.abs(v) < 1e-9 ? 1 : 0.7,
      'stroke-dasharray': '0',
    }));
    const fmt = step >= 1000 ? (v / 1000).toFixed(0) + 'k' : step < 1 ? v.toFixed(1) : v.toFixed(0);
    lbl(svg, cx - 8, gy + 4, fmt, { anchor: 'end', size: 10 });
  }

  // X-axis line: always at the chart floor (yMin), bright/solid, matching renderChart().
  svg.appendChild(el('line', {
    x1: cx, y1: cy + ch, x2: cx + cw, y2: cy + ch,
    stroke: T.zeroLine, 'stroke-width': 1, 'stroke-dasharray': '0',
  }));

  bars.forEach((s, si) => {
    xLabels.forEach((_, i) => {
      const v      = s.values[i];
      const topVal = Math.max(v, baseVal);
      const botVal = Math.min(v, baseVal);
      const bx     = cx + i * slotW + groupOff + si * bw;
      const bh     = (topVal - botVal) * sc;
      const by     = cy + (yMax - topVal) * sc;
      svg.appendChild(el('rect', {
        x: bx, y: by, width: Math.max(bw - 1, 1), height: Math.max(bh, 1),
        fill: 'url(#' + (s.gid || (gid + si)) + ')', rx: 1,
      }));
    });
  });

  const labelSize = opts.labelSize || 9;
  xLabels.forEach((txt, i) => {
    if (!txt) return;
    lbl(svg, cx + slotW / 2 + i * slotW, cy + ch + 16, txt, { size: labelSize });
  });

  // Legend: upper-right corner, WITH a background panel — unlike renderChart()'s legend, this
  // one needs a panel because this chart type's data can have tall bars reaching into the
  // top-right region, and unlike PPTX's native legend (which auto-shrinks the plot area to
  // make room), this hand-drawn SVG legend has no such reflow — the panel is what keeps it
  // readable instead of visually blending into a bar.
  const legPanelW = 160;
  const legPanelH = bars.length * 16 + 10;
  const legPanelX = cx + cw - legPanelW;
  const legPanelY = cy + 2;
  svg.appendChild(el('rect', {
    x: legPanelX, y: legPanelY, width: legPanelW, height: legPanelH,
    fill: 'rgba(18,28,72,0.72)', rx: 4,
  }));

  const legX = legPanelX + 12;
  bars.forEach((s, i) => {
    const lx = legX, ly = legPanelY + 16 + i * 16;
    svg.appendChild(el('rect', { x: lx, y: ly - 6, width: 11, height: 9, fill: 'url(#' + (s.gid || (gid + i)) + ')', rx: 1 }));
    lbl(svg, lx + 14, ly + 4, s.name, { anchor: 'start', size: 9, color: T.axisText });
  });
}

/* renderChartDual — extension for slides needing a secondary (right) Y-axis in a SINGLE
   chart (not two side-by-side charts — that's the CHART_DUAL slide TYPE, a different thing).
   barsLeft/linesLeft map through yMin/yMax (left scale). linesRight maps through yMin2/yMax2
   (right scale) over the SAME pixel rect. Gridlines are drawn from the LEFT scale only —
   drawing a second gridline set from the right scale would double up and look wrong; the
   right scale gets its own tick labels (own step2) mirrored at the right edge instead.
   Legend suffixes ' (Left)' / ' (Right)' are expected to already be in each series' name
   (matches the MOEF reference capture's English-suffix convention). Copy verbatim. */
function renderChartDual(svgId, cx, cy, cw, ch, xLabels, barsLeft, linesLeft, yMin, yMax, linesRight, yMin2, yMax2, gid, opts) {
  opts = opts || {};
  const svg  = document.getElementById(svgId);
  addGrad(svg, gid, opts.barGradTop, opts.barGradBot);

  const n     = xLabels.length;
  const range = yMax - yMin;
  const sc    = ch / range;
  const range2 = yMax2 - yMin2;
  const sc2   = ch / range2;
  const slotW = cw / n;
  const bw    = slotW * 0.44;
  const boff  = (slotW - bw) / 2;

  const baseVal = Math.max(yMin, Math.min(0, yMax));

  const step     = opts.step || 1;
  const vStart   = Math.ceil(yMin / step) * step;
  const vEnd     = Math.floor(yMax / step) * step;
  const topGridY = cy + (yMax - vEnd) * sc;

  if (opts.unitLeft) {
    lbl(svg, cx - 8, topGridY - 14, opts.unitLeft, { anchor: 'end', size: 10 });
  }
  if (opts.unitRight) {
    lbl(svg, cx + cw + 8, topGridY - 14, opts.unitRight, { anchor: 'start', size: 10 });
  }

  // Gridlines from LEFT scale only
  for (let v = vStart; v <= vEnd + 1e-9; v = Math.round((v + step) * 1e9) / 1e9) {
    if (v > yMax + 1e-9) break;
    const gy = cy + (yMax - v) * sc;
    svg.appendChild(el('line', {
      x1: cx, y1: gy, x2: cx + cw, y2: gy,
      stroke: Math.abs(v) < 1e-9 ? T.zeroLine : T.gridLine,
      'stroke-width': Math.abs(v) < 1e-9 ? 1 : 0.7,
      'stroke-dasharray': '0',
    }));
    const fmt = step >= 1000 ? (v / 1000).toFixed(0) + 'k' : step < 1 ? v.toFixed(1) : v.toFixed(0);
    lbl(svg, cx - 8, gy + 4, fmt, { anchor: 'end', size: 10 });
  }

  // X-axis line: always at the LEFT axis's floor (yMin), bright/solid, matching renderChart().
  svg.appendChild(el('line', {
    x1: cx, y1: cy + ch, x2: cx + cw, y2: cy + ch,
    stroke: T.zeroLine, 'stroke-width': 1, 'stroke-dasharray': '0',
  }));

  // Right-axis tick labels — own step, mirrored at right edge, no gridlines
  const step2   = opts.step2 || 1;
  const vStart2 = Math.ceil(yMin2 / step2) * step2;
  const vEnd2   = Math.floor(yMax2 / step2) * step2;
  for (let v = vStart2; v <= vEnd2 + 1e-9; v = Math.round((v + step2) * 1e9) / 1e9) {
    if (v > yMax2 + 1e-9) break;
    const gy = cy + (yMax2 - v) * sc2;
    const fmt = step2 < 1 ? v.toFixed(1) : v.toFixed(0);
    lbl(svg, cx + cw + 8, gy + 4, fmt, { anchor: 'start', size: 10 });
  }

  barsLeft.forEach(s => {
    xLabels.forEach((_, i) => {
      const v      = s.values[i];
      const topVal = Math.max(v, baseVal);
      const botVal = Math.min(v, baseVal);
      const bx     = cx + boff + i * slotW;
      const bh     = (topVal - botVal) * sc;
      const by     = cy + (yMax - topVal) * sc;
      svg.appendChild(el('rect', {
        x: bx, y: by,
        width: Math.max(bw, 1), height: Math.max(bh, 1),
        fill: 'url(#' + gid + ')', rx: 1,
      }));
    });
  });

  linesLeft.forEach(s => {
    const pts = xLabels.map((_, i) => {
      const px = cx + boff + bw / 2 + i * slotW;
      const py = cy + (yMax - s.values[i]) * sc;
      return px.toFixed(1) + ',' + py.toFixed(1);
    });
    svg.appendChild(el('polyline', {
      points: pts.join(' '), stroke: s.color, 'stroke-width': 2,
      fill: 'none', 'stroke-linejoin': 'round', 'stroke-linecap': 'round',
    }));
  });

  linesRight.forEach(s => {
    const pts = xLabels.map((_, i) => {
      const px = cx + boff + bw / 2 + i * slotW;
      const py = cy + (yMax2 - s.values[i]) * sc2;
      return px.toFixed(1) + ',' + py.toFixed(1);
    });
    svg.appendChild(el('polyline', {
      points: pts.join(' '), stroke: s.color, 'stroke-width': 2,
      fill: 'none', 'stroke-linejoin': 'round', 'stroke-linecap': 'round',
    }));
  });

  const labelSize = opts.labelSize || 9;
  xLabels.forEach((txt, i) => {
    if (!txt) return;
    lbl(svg, cx + slotW / 2 + i * slotW, cy + ch + 16, txt, { size: labelSize });
  });

  const allS = [
    ...barsLeft.map(s  => ({ name: s.name, isBar: true })),
    ...linesLeft.map(s => ({ name: s.name, color: s.color, isBar: false })),
    ...linesRight.map(s => ({ name: s.name, color: s.color, isBar: false })),
  ];
  const legX = cx + cw - 160;
  allS.forEach((s, i) => {
    const lx = legX;
    const ly = cy + 12 + i * 16;
    if (s.isBar) {
      svg.appendChild(el('rect', { x: lx, y: ly - 6, width: 11, height: 9, fill: 'url(#' + gid + ')', rx: 1 }));
    } else {
      svg.appendChild(el('line', { x1: lx, y1: ly - 1, x2: lx + 11, y2: ly - 1, stroke: s.color, 'stroke-width': 2 }));
    }
    lbl(svg, lx + 14, ly + 4, s.name, { anchor: 'start', size: 9, color: T.axisText });
  });
}
```

### Slide markup + call pattern: clustered multi-bar (2+ bar series, one axis)

Same slide HTML shell as CHART_SINGLE (see below) — only the `<script>` call differs:

```js
renderChartMultiBar('s[N]svg', 78, 112, 844, 380, LBLS,
  [
    { name: '[Bar series A]', gid: 'g[N]a', gradTop: T.barGradTop, gradBot: T.barGradBot, values: [/* ... */] },
    { name: '[Bar series B]', gid: 'g[N]b', gradTop: T.barGoldTop, gradBot: T.barGoldBot, values: [/* ... */] },
  ],
  yMin, yMax, 'g[N]',
  { step: /* choose so lines < 8 */, unit: '(%)', labelSize: 9 }
);
```

### Slide markup + call pattern: secondary (right) y-axis, ONE chart

Same slide HTML shell as CHART_SINGLE — only the `<script>` call differs. Series destined for
the right axis get an English ` (Right)` suffix in `name`; left-axis series get ` (Left)`,
matching the MOEF reference capture convention:

```js
renderChartDual('s[N]svg', 78, 112, 844, 380, LBLS,
  [{ name: '[Bar series] (Left)', values: [/* ... */] }],   // barsLeft
  [],                                                        // linesLeft (empty if bar-only on the left)
  leftYMin, leftYMax,
  [{ name: '[Line series] (Right)', color: T.lineYellow, values: [/* ... */] }],  // linesRight
  rightYMin, rightYMax,
  'g[N]',
  { step: /* left step */, step2: /* right step */, unitLeft: '(천명)', unitRight: '(%)', labelSize: 9 }
);
```

---

## Slide Type: COVER

```html
<div class="slide-wrap">
<div class="slide-label">Slide N · COVER</div>
<div class="slide">
  <div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);text-align:center;width:820px;">
    <div class="slide-title" style="font-size:38px;">[Title]</div>
    <div class="muted-text" style="margin-top:22px;font-size:13px;">[English subtitle]</div>
    <div class="muted-text" style="margin-top:10px;font-size:13px;">[Date] · [Organization]</div>
  </div>
</div>
</div>
```

---

## Slide Type: CHART_SINGLE

```html
<div class="slide-wrap">
<div class="slide-label">Slide N · CHART_SINGLE — [title]</div>
<div class="slide">
  <div class="slide-header">
    <div class="slide-title">[N]. [Title]</div>  <!-- No leading zero: "1." not "01." -->
    <div class="title-underline"></div>
  </div>
  <!-- No separate unit div — unit is rendered inside SVG via opts.unit -->
  <svg id="s[N]svg" width="960" height="540" style="position:absolute;top:0;left:0;"></svg>
</div>
</div>

<!-- In <script>: -->
renderChart('s[N]svg',
  78, 112, 844, 380,    // cx=78 (y-label area), cy=112, cw=844 (centered), ch=380
  [/* x-axis labels — first-of-year only, others '' */],
  [{ name: '[Bar series]', values: [/* ... */] }],
  [{ name: '[Line series]', color: T.lineYellow, values: [/* ... */] }],
  yMin, yMax, 'g[N]',
  { step: /* choose so lines < 8 */, unit: '(%)', labelSize: 9 }
);
```

Chart geometry for single chart:
- cx=78, cy=112, cw=844, ch=380
- x-labels at cy+ch+16 = 508px (fits in 540px)
- Unit rendered in SVG 14px above topmost gridline, right-aligned at cx-8=70

---

## Slide Type: CHART_DUAL

```html
<div class="slide-wrap">
<div class="slide-label">Slide N · CHART_DUAL — [title]</div>
<div class="slide">
  <div class="slide-header">
    <div class="slide-title">[N]. [Title]</div>  <!-- No leading zero: "1." not "01." -->
    <div class="title-underline"></div>
  </div>
  <!-- Chart titles: 18px bold white, centered above each chart -->
  <div style="position:absolute;top:90px;left:78px;width:375px;
       font-family:Pretendard,sans-serif;font-weight:900;font-size:18px;color:#FFFFFF;text-align:center;">
    [Left chart title]</div>
  <div style="position:absolute;top:90px;left:549px;width:375px;
       font-family:Pretendard,sans-serif;font-weight:900;font-size:18px;color:#FFFFFF;text-align:center;">
    [Right chart title]</div>
  <!-- No separate unit divs — units rendered inside SVG via opts.unit on BOTH charts -->
  <svg id="s[N]svg" width="960" height="540" style="position:absolute;top:0;left:0;"></svg>
</div>
</div>

<!-- In <script>: -->
// Geometry: left cx=78 cw=375; gap=96px; right cx=549 cw=375; right edge=924, margin=36 ✓
const LBLS = [/* x-axis labels — first-of-year only, others '' */];
const DCY  = 120;   // chart start y (below 18pt title at top:90)
const DCH  = 370;   // chart height → bottom 490, x-labels 506

renderChart('s[N]svg',
  78, DCY, 375, DCH,
  LBLS,
  [{ name: '[Bar series]', values: [/* ... */] }],
  [{ name: '[Line series]', color: T.lineYellow, values: [/* ... */] }],
  leftYMin, leftYMax, 'g[N]L',
  { step: /* choose so lines < 8 */, unit: '(%)', labelSize: 9 }
);

renderChart('s[N]svg',
  549, DCY, 375, DCH,
  LBLS,
  [{ name: '[Bar series]', values: [/* ... */] }],
  [{ name: '[Line series]', color: T.lineYellow, values: [/* ... */] }],
  rightYMin, rightYMax, 'g[N]R',
  { step: /* choose so lines < 8 */, unit: '(%)', labelSize: 9 }
  // Both charts get their own unit label via opts.unit
);

// Vertical divider in the gap
document.getElementById('s[N]svg').appendChild(
  el('line', { x1:511, y1:88, x2:511, y2:505, stroke:'rgba(192,210,232,0.12)', 'stroke-width':1 })
);
```

---

## Slide Type: STRATEGY_CARDS

```html
<div class="slide-wrap">
<div class="slide-label">Slide N · STRATEGY_CARDS — [title]</div>
<div class="slide">
  <div class="slide-header">
    <div class="slide-title">[Section tag]. [Title]</div>
    <div class="title-underline"></div>
  </div>
  <div style="position:absolute;top:110px;left:36px;right:36px;bottom:20px;display:flex;gap:12px;">

    <div style="flex:1;background:#1E3F88;border-radius:8px;padding:18px 14px;">
      <div style="font-family:Pretendard;font-weight:900;font-size:16px;color:#FFFFFF;margin-bottom:12px;line-height:1.3;">[① Card title]</div>
      <div style="font-family:Pretendard;font-weight:500;font-size:14px;color:rgba(255,255,255,0.90);line-height:1.9;">
        • [bullet1]<br>• [bullet2]<br>• [bullet3]
      </div>
    </div>

    <!-- Repeat <div style="flex:1;..."> for each card (2–4 total) -->

  </div>
</div>
</div>
```

All cards use the **same color** `#1E3F88`. No alternating teal/purple.

---

## Slide Type: TEXT_ONLY

```html
<div class="slide-wrap">
<div class="slide-label">Slide N · TEXT_ONLY — [title]</div>
<div class="slide">
  <div class="slide-header">
    <div class="slide-title">[Section tag]. [Title]</div>
    <div class="title-underline"></div>
  </div>
  <div style="position:absolute;top:110px;left:36px;right:36px;bottom:20px;display:flex;gap:0;">

    <!-- Column 1 -->
    <div style="flex:1;padding-right:18px;">
      <div style="font-family:Pretendard;font-weight:500;font-size:16px;color:#E4E020;margin-bottom:16px;">[Column heading]</div>
      <div style="font-family:Pretendard;font-weight:500;font-size:16px;color:#FFFFFF;line-height:2.0;">
        • [bullet1]<br>• [bullet2]<br>• [bullet3]<br>• [bullet4]
      </div>
    </div>

    <!-- Column separator -->
    <div style="width:1px;background:rgba(192,210,232,0.20);flex-shrink:0;"></div>

    <!-- Column 2 -->
    <div style="flex:1;padding-left:18px;">
      <div style="font-family:Pretendard;font-weight:500;font-size:16px;color:#E4E020;margin-bottom:16px;">[Column heading]</div>
      <div style="font-family:Pretendard;font-weight:500;font-size:16px;color:#FFFFFF;line-height:2.0;">
        • [bullet1]<br>• [bullet2]<br>• [bullet3]<br>• [bullet4]
      </div>
    </div>

    <!-- Add Column 3 if needed (same pattern, with separator before it) -->

  </div>
</div>
</div>
```

Font sizes for text-only slides: **16px** for both column headings (yellow) and body bullets (white).

---

## Slideshow Mode JS (add at end of `<script>`, after all renderChart calls)

```js
// ── Slideshow engine ──
(function() {
  const slides = Array.from(document.querySelectorAll('.slide'));
  const total  = slides.length;
  let cur = 0, active = false;

  function applyScale() {
    const k = Math.min(window.innerWidth / 960, window.innerHeight / 540);
    slides[cur].style.transform = 'translate(-50%, -50%) scale(' + k + ')';
  }

  function show(i) {
    slides[cur].classList.remove('show-active');
    slides[cur].style.transform = '';
    cur = ((i % total) + total) % total;
    slides[cur].classList.add('show-active');
    applyScale();
    document.getElementById('show-counter').textContent = (cur + 1) + ' / ' + total;
  }

  function enter() {
    active = true;
    document.body.classList.add('show-mode');
    slides[cur].classList.add('show-active');
    applyScale();
    document.getElementById('show-counter').textContent = (cur + 1) + ' / ' + total;
  }

  function exit() {
    active = false;
    slides[cur].classList.remove('show-active');
    slides[cur].style.transform = '';
    document.body.classList.remove('show-mode');
    if (document.fullscreenElement) document.exitFullscreen();
  }

  document.getElementById('show-btn').addEventListener('click', enter);
  document.getElementById('show-exit').addEventListener('click', exit);
  document.getElementById('show-prev').addEventListener('click', function() { show(cur - 1); });
  document.getElementById('show-next').addEventListener('click', function() { show(cur + 1); });
  window.addEventListener('resize', function() { if (active) applyScale(); });

  document.addEventListener('keydown', function(e) {
    if (!active) return;
    if (e.key === 'ArrowRight' || e.key === ' ') { e.preventDefault(); show(cur + 1); }
    else if (e.key === 'ArrowLeft') { e.preventDefault(); show(cur - 1); }
    else if (e.key === 'Escape') exit();
    else if (e.key === 'f' || e.key === 'F') {
      if (!document.fullscreenElement) document.documentElement.requestFullscreen();
      else document.exitFullscreen();
    }
  });
})();
```
