# PPTX Patterns — MOEF Design System (pptxgenjs)

Copy helper functions verbatim. Adapt slide functions to match the script content.

---

## Boilerplate Header

```js
'use strict';
const PptxGenJS = require('../../IR_ppt/node_modules/pptxgenjs');
const zlib      = require('zlib');

// Gradient PNG matching HTML: linear-gradient(160deg, #243478 0%, #1B2D60 40%, #121C48 100%)
// pptxgenjs v4 has no gradient shape API — embed a PNG as slide background instead.
function makeGradientPNG(w, h) {
  const stops = [
    { pos: 0.0, r: 0x24, g: 0x34, b: 0x78 },
    { pos: 0.4, r: 0x1B, g: 0x2D, b: 0x60 },
    { pos: 1.0, r: 0x12, g: 0x1C, b: 0x48 },
  ];
  const dx = Math.sin(160 * Math.PI / 180);
  const dy = -Math.cos(160 * Math.PI / 180);
  const projs = [[0,0],[1,0],[0,1],[1,1]].map(([x,y]) => dx*(x-0.5)+dy*(y-0.5));
  const minP = Math.min(...projs), range = Math.max(...projs) - Math.min(...projs);
  function colorAt(t) {
    t = Math.max(0, Math.min(1, t));
    let s0 = stops[0], s1 = stops[1];
    for (let i = 0; i < stops.length - 1; i++) {
      if (t <= stops[i+1].pos) { s0 = stops[i]; s1 = stops[i+1]; break; }
    }
    const f = s0.pos === s1.pos ? 0 : (t - s0.pos) / (s1.pos - s0.pos);
    return [Math.round(s0.r+f*(s1.r-s0.r)), Math.round(s0.g+f*(s1.g-s0.g)), Math.round(s0.b+f*(s1.b-s0.b))];
  }
  const rows = [];
  for (let y = 0; y < h; y++) {
    const row = [0];
    for (let x = 0; x < w; x++) {
      const nx = w > 1 ? x/(w-1) : 0.5, ny = h > 1 ? y/(h-1) : 0.5;
      const [r,g,b] = colorAt((dx*(nx-0.5)+dy*(ny-0.5)-minP)/range);
      row.push(r, g, b);
    }
    rows.push(Buffer.from(row));
  }
  const compressed = zlib.deflateSync(Buffer.concat(rows), { level: 1 });
  const crcT = new Uint32Array(256);
  for (let i = 0; i < 256; i++) { let c=i; for (let k=0;k<8;k++) c=(c&1)?(0xEDB88320^(c>>>1)):(c>>>1); crcT[i]=c; }
  function crc32(buf) { let c=0xFFFFFFFF; for (const b of buf) c=(crcT[(c^b)&0xFF]^(c>>>8))>>>0; return((c^0xFFFFFFFF)>>>0); }
  function chunk(type, data) {
    const tb=Buffer.from(type,'ascii'), lb=Buffer.alloc(4), cb=Buffer.alloc(4);
    lb.writeUInt32BE(data.length); cb.writeUInt32BE(crc32(Buffer.concat([tb,data])));
    return Buffer.concat([lb,tb,data,cb]);
  }
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(w,0); ihdr.writeUInt32BE(h,4); ihdr[8]=8; ihdr[9]=2;
  return Buffer.concat([Buffer.from([137,80,78,71,13,10,26,10]), chunk('IHDR',ihdr), chunk('IDAT',compressed), chunk('IEND',Buffer.alloc(0))]);
}
const BG_PNG_DATA = 'data:image/png;base64,' + makeGradientPNG(160, 90).toString('base64');

const C = {
  bg:           '243478',
  bgDark:       '121848',
  textPrimary:  'FFFFFF',
  textMuted:    'C0D2E8',
  lineYellow:   'E4E020',
  lineBlue:     '74C0FC',
  lineWhite:    'FFFFFF',
  barMid:       '8AAED0',
  barGold:      'E8B93C',      // 2nd bar series in clustered multi-bar charts
  accentTeal:   '00BFFF',
  gridLine:     '3A5280',
  // Matches HTML's T.zeroLine (rgba(255,255,255,0.28)) blended over the navy gradient
  // background — PPTX axis-line color has no alpha channel, so this is the flattened
  // equivalent: white at 28% opacity over the gradient's middle stop (#1B2D60).
  xAxisLine:    '5B688D',
  // Matches HTML's dual-chart divider (rgba(192,210,232,0.12)) flattened the same way.
  divider:      '2F4170',
  // Matches HTML's legend panel (rgba(18,28,72,0.72)) flattened over the background.
  legendBg:     '1A2550',
  cardBlue:     '1E3F88',
};

/*  Axis label format rules:
 *  Yearly    : "'YY"     e.g. "'21"
 *  Quarterly : "YY.NQ"   e.g. "22.1Q"
 *  Monthly   : "YY.M"    e.g. "22.1"
 *  Do NOT insert empty labels if data doesn't start from Jan/1Q.
 */

// CRITICAL: pptxgenjs/PowerPoint reference fonts by exact installed family name — there is
// no CSS-style "font-weight" concept. 'Pretendard' alone resolves to whatever weight that
// family name's default installed variant is (NOT guaranteed to be Medium/500). The verified
// working value is the literal family name of the Medium weight's own font file/install:
const FONT  = 'Pretendard Medium';
const FONTB = 'Pretendard Black';
const W = 13.33, H = 7.5, M = 0.5;
```

---

## Helper Functions (copy VERBATIM)

```js
function box(s, x, y, w, h, fill, border, radius) {
  const o = { x, y, w, h, fill: { color: fill }, rectRadius: radius || 0 };
  if (border) o.line = { color: border, pt: 1 };
  s.addShape('rect', o);
}

function txt(s, text, x, y, w, h, opts) {
  opts = opts || {};
  s.addText(text, { x, y, w, h, fontFace: FONT, valign: 'middle', wrap: true, ...opts });
}

/** Adds section title (Black 32pt) + 3pt teal underline.
 *  Returns y where content area begins (0.94 in). */
function sectionHeader(s, title) {
  txt(s, title, M, 0.28, W - 2 * M, 0.56, {
    fontFace: FONTB, fontSize: 32, bold: false, color: C.textPrimary,
  });
  box(s, M, 0.88, W - 2 * M, 0.042, C.accentTeal);
  return 0.94;
}

/** Slide number — bottom-right corner */
function pn(s, n) {
  txt(s, String(n), W - 0.9, H - 0.38, 0.36, 0.24, {
    fontSize: 12, bold: false, color: C.textMuted, align: 'right',
  });
}

/** Custom overlay legend — drawn as shapes/text INSIDE the chart's own bounding box,
 *  matching HTML's SVG-drawn legend exactly. pptxgenjs's native showLegend/legendPos only
 *  supports preset positions ('tr','b','l','r','t') that reserve a whole SEPARATE column
 *  outside the chart frame (shrinking the plot area) — verified via slide screenshot export
 *  that this produces a legend floating in the slide's blank margin beside the chart, not
 *  "in the upper-right corner of the chart" as intended. Every addChart call must therefore
 *  set showLegend:false and call this instead, immediately after addChart().
 *  frameX/frameY/frameW are the SAME (x,y,w) passed to addChart for that chart.
 *  items: [{ name, color, type: 'line' | 'bar' }] */
function legend(s, frameX, frameY, frameW, items) {
  const itemH  = 0.19;
  const boxW   = 1.7;
  const boxH   = items.length * itemH + 0.08;
  const boxX   = frameX + frameW - boxW - 0.08;
  const boxY   = frameY + 0.08;
  box(s, boxX, boxY, boxW, boxH, C.legendBg);
  items.forEach((item, i) => {
    const iy = boxY + 0.06 + i * itemH;
    if (item.type === 'bar') {
      box(s, boxX + 0.08, iy + 0.01, 0.14, 0.09, item.color);
    } else {
      box(s, boxX + 0.08, iy + 0.045, 0.14, 0.018, item.color);
    }
    txt(s, item.name, boxX + 0.28, iy - 0.03, boxW - 0.34, itemH, {
      fontSize: 9, color: C.textMuted, align: 'left', valign: 'middle', wrap: false,
    });
  });
}

/** Base MOEF chart style.
 *  CRITICAL: valAxisLineShow is false (no y-axis line) but catAxisLineShow is TRUE with an
 *  explicit color/size — this draws the visible x-axis floor line that matches HTML's added
 *  floor line (see html_patterns.md). Do NOT set catAxisLineShow:false — that was an old/wrong
 *  pattern that predates the floor-line fix.
 *  Tick marks are explicitly suppressed on both axes — pptxgenjs otherwise draws a dense row
 *  of per-category tick marks that HTML never shows.
 *  Gridlines are SOLID (not dashed) — must match the HTML fix on the other side.
 *  plotArea/chartArea have NO fill (→ <a:noFill/>) so the slide gradient shows through.
 *  showLegend is always false — legend is drawn separately via legend() above.
 *  Callers needing an x-axis crossing value MUST use valAxisCrossesAt (controls where the
 *  CATEGORY axis's line sits along the value axis) — NOT catAxisCrossesAt (that confusingly-
 *  named option actually controls the VALUE axis's own crossing position among categories;
 *  passing a raw data value into it can silently flip the y-axis to the wrong side). See the
 *  "Bar-baseline coupling" and "falsy-zero crossesAt" rows in Common Errors below before
 *  setting this on any chart containing a bar series. */
function moefCS(overrides) {
  overrides = overrides || {};
  return {
    plotArea:             {},                              // no fill → transparent
    chartArea:            {},                              // no fill → transparent
    catGridLine:          { style: 'none' },
    valGridLine:          { style: 'solid', color: C.gridLine, size: 0.5 },
    catAxisLineShow:      true,
    catAxisLineColor:     C.xAxisLine,
    catAxisLineSize:      1,
    catAxisMajorTickMark: 'none',
    catAxisMinorTickMark: 'none',
    valAxisMajorTickMark: 'none',
    valAxisMinorTickMark: 'none',
    valAxisLineShow:      false,
    catAxisLabelFontFace: FONT,
    catAxisLabelFontSize: 10,
    catAxisLabelColor:    C.textMuted,
    valAxisLabelFontFace: FONT,
    valAxisLabelFontSize: 10,
    valAxisLabelColor:    C.textMuted,
    showTitle:            false,
    showLegend:           false,
    ...overrides,
  };
}
```

---

## Slide Function: COVER

```js
function s_Cover(pptx) {
  const s = pptx.addSlide();
  s.background = { data: BG_PNG_DATA }; // gradient PNG (matches HTML gradient)

  txt(s, '[Title]', 1.0, 2.18, 11.33, 1.10, {
    fontFace: FONTB, fontSize: 38, bold: false,  // 38pt matches HTML 38px
    color: C.textPrimary, align: 'center', valign: 'middle',
  });
  txt(s, '[English subtitle]', 1.0, 3.52, 11.33, 0.36, {
    fontSize: 12, color: C.textMuted, align: 'center',
  });
  txt(s, '[Date]  ·  [Organization]', 1.0, 3.96, 11.33, 0.36, {
    fontSize: 12, color: C.textMuted, align: 'center',
  });
  pn(s, 1);
}
```

---

## Slide Function: CHART_SINGLE

```js
function s_ChartSingle(pptx, slideNum) {
  const s = pptx.addSlide();
  s.background = { data: BG_PNG_DATA }; // gradient PNG (matches HTML gradient)

  // No leading zero in section number: "1." not "01."
  const cy = sectionHeader(s, '[N]. [Title]');
  pn(s, slideNum);

  const chartY = cy + 0.28;
  const chartH = H - chartY - M;

  // Unit label: placed ABOVE the chart frame (at cy, same row as section header content
  // start) — NOT at chartY (that overlaps the chart's own topmost axis number).
  // No source citation (출처) anywhere.
  txt(s, '(%)', M, cy, 0.4, 0.28, { fontSize: 10, color: C.textMuted, wrap: false });

  // x-axis labels: first-of-year only, others '' (empty string)
  const LBLS = [/* '24.1','','','','','','','','','','','','25.1',... */];

  // CRITICAL: pptxgenjs v4 multi-type addChart() IGNORES per-type opts (except the
  // secondaryValAxis/secondaryCatAxis flags — see the dual-axis variant below).
  // All other options (chartColors, lineDataSymbol, lineSize, barGapWidthPct, barDir,
  // barGrouping) MUST go in the top-level moefCS overrides — NOT in the per-type opts objects.
  // Per-type objects: only { type, data } — no opts.
  // Use this multi-type ARRAY form only when combining DIFFERENT chart types (bar + line).
  // For 2+ series of the SAME type that must cluster, use the single-type form instead
  // (see "Clustered multi-bar" example below) — the array form gives each same-type entry
  // its own separate wrapper, which overlaps instead of clustering in PowerPoint.
  s.addChart(
    [
      { type: pptx.ChartType.bar,  data: [{ name: '[Bar series]',     labels: LBLS, values: [/* ... */] }] },
      { type: pptx.ChartType.line, data: [{ name: '[Primary line]',   labels: LBLS, values: [/* ... */] }] },
      // Optional second line: { type: pptx.ChartType.line, data: [{ name: '[Secondary line]', labels: LBLS, values: [/* ... */] }] },
    ],
    moefCS({
      x: M, y: chartY, w: W - 2 * M, h: chartH,
      // chartColors: order matches series order (bar first, then lines)
      chartColors: [C.barMid, C.lineYellow],         // 3 series: [C.barMid, C.lineYellow, C.lineWhite]
      barDir: 'col', barGrouping: 'clustered', barGapWidthPct: 50,
      lineDataSymbol: 'none', lineSize: 1.5,          // 'none' = no circle markers on lines
      showLegend: false,                              // legend drawn separately below
      valAxisLabelFormatCode: '#,##0.0',              // NOT valAxisNumFmt — that option name is silently ignored
      valAxisMinVal: /* yMin */, valAxisMaxVal: /* yMax */,
      valAxisMajorUnit: /* step — same value as HTML opts.step */,
      // Only set valAxisCrossesAt if yMin===0 or this chart has no bar series — see the
      // "Bar-baseline coupling" Common Error below. Omit entirely for negative-floor bar charts.
      valAxisCrossesAt: /* yMin, only if safe per the rule above */,
    })
  );
  legend(s, M, chartY, W - 2 * M, [
    { name: '[Bar series]',   color: C.barMid,    type: 'bar' },
    { name: '[Primary line]', color: C.lineYellow, type: 'line' },
  ]);
}
```

### Variant: Clustered multi-bar (2+ bar series, same axis, must sit side by side)

```js
// Single-type call (NOT the multi-type array combo form) — the array form emits one
// SEPARATE <c:barChart> wrapper per entry, and two independent bar-chart wrappers do not
// cluster against each other in PowerPoint: both series render at the same x-position and
// visually overlap instead of sitting side by side. Passing both series in one `data` array
// under a single chart-type call produces ONE <c:barChart> wrapper with two <c:ser>
// elements, which is what PowerPoint's clustering actually operates on.
s.addChart(
  pptx.ChartType.bar,
  [
    { name: '[Bar series A]', labels: LBLS, values: [/* ... */] },
    { name: '[Bar series B]', labels: LBLS, values: [/* ... */] },
  ],
  moefCS({
    x: M, y: chartY, w: W - 2 * M, h: chartH,
    chartColors: [C.barMid, C.barGold],
    barDir: 'col', barGrouping: 'clustered', barGapWidthPct: 50,
    showLegend: false,
    valAxisLabelFormatCode: '0,"k"', // when values are in the thousands, matches HTML's "k" abbreviation
    valAxisMinVal: /* yMin */, valAxisMaxVal: /* yMax */, valAxisMajorUnit: /* step */,
    // Deliberately NO valAxisCrossesAt here if yMin < 0 — see "Bar-baseline coupling" below.
  })
);
legend(s, M, chartY, W - 2 * M, [
  { name: '[Bar series A]', color: C.barMid,  type: 'bar' },
  { name: '[Bar series B]', color: C.barGold, type: 'bar' },
]);
```

### Variant: Secondary (right) y-axis — ONE chart, two very-different-scale series

```js
// Series that belongs on the right axis needs BOTH flags in its own `options` — omitting
// secondaryCatAxis leaves the auto-added secondary category axis unreferenced by any series
// ("orphaned axis"), which PowerPoint rejects outright (COM 0x80070570) even though the XML
// is well-formed. Legend/series names get an English " (Left)"/" (Right)" suffix.
s.addChart(
  [
    { type: pptx.ChartType.bar,  data: [{ name: '[Bar series] (Left)',  labels: LBLS, values: [/* ... */] }], options: {} },
    { type: pptx.ChartType.line, data: [{ name: '[Line series] (Right)', labels: LBLS, values: [/* ... */] }], options: { secondaryValAxis: true, secondaryCatAxis: true } },
  ],
  moefCS({
    x: M, y: chartY, w: W - 2 * M, h: chartH,
    chartColors: [C.barMid, C.lineYellow],
    barDir: 'col', barGrouping: 'clustered', barGapWidthPct: 50,
    lineDataSymbol: 'none', lineSize: 1.5,
    showLegend: false,
    valAxisLabelFormatCode: '0', valAxisMinVal: /* left yMin */, valAxisMaxVal: /* left yMax */, valAxisMajorUnit: /* left step */,
    // valAxes[0] = left/primary axis opts, valAxes[1] = right/secondary axis opts.
    // Give the secondary axis its own gridline: {style:'none'} — HTML only draws gridlines
    // from the left scale, so a second gridline set would double up and look wrong.
    valAxes: [
      { valAxisMinVal: /* left yMin */,  valAxisMaxVal: /* left yMax */,  valAxisMajorUnit: /* left step */,  valAxisLabelFormatCode: '0' },
      { valAxisMinVal: /* right yMin */, valAxisMaxVal: /* right yMax */, valAxisMajorUnit: /* right step */, valAxisLabelFormatCode: '0', valGridLine: { style: 'none' } },
    ],
    // catAxes[1] MUST be declared (even just {catAxisHidden:true}) — REQUIRED alongside
    // secondaryCatAxis:true above, or pptxgenjs writes a crossAx reference to an axis ID
    // that's never defined and PowerPoint rejects the file.
    catAxes: [ {}, { catAxisHidden: true } ],
    // Only set a crossing value here if this chart has NO bar series, or yMin===0 for the
    // bar series — see "Bar-baseline coupling" in Common Errors. Decks with a negative-floor
    // bar series should omit any crossing value entirely (leave PowerPoint's default autoZero).
  })
);
legend(s, M, chartY, W - 2 * M, [
  { name: '[Bar series] (Left)',   color: C.barMid,    type: 'bar' },
  { name: '[Line series] (Right)', color: C.lineYellow, type: 'line' },
]);
```

---

## Slide Function: CHART_DUAL

```js
function s_ChartDual(pptx, slideNum) {
  const s = pptx.addSlide();
  s.background = { data: BG_PNG_DATA }; // gradient PNG (matches HTML gradient)

  // No leading zero in section number: "1." not "01."
  const cy = sectionHeader(s, '[N]. [Title]');
  pn(s, slideNum);

  // x-axis labels: first-of-year only, others '' (empty string)
  const LBLS   = [/* '24.1','','','','','','','','','','','','25.1',... */];
  const gap    = 1.0;                    // 1in gap between charts
  const gw     = (W - 2 * M - gap) / 2; // each chart width (~5.67in)
  const titleH = 0.42;
  const chartY = cy + titleH;
  const gh     = H - chartY - M;

  // Chart titles: 18pt Pretendard Black (900), centered — txt() defaults to FONT (Medium),
  // so fontFace: FONTB must be explicit here.
  txt(s, '[Left chart title]', M, cy, gw, titleH, {
    fontFace: FONTB, fontSize: 18, color: C.textPrimary, align: 'center', valign: 'middle',
  });
  txt(s, '[Right chart title]', M + gw + gap, cy, gw, titleH, {
    fontFace: FONTB, fontSize: 18, color: C.textPrimary, align: 'center', valign: 'middle',
  });

  // Unit labels: same row as the title (left-aligned, before the centered title text) so it
  // doesn't overlap the chart's own topmost axis number. BOTH charts get one; no 출처 anywhere.
  txt(s, '(%)', M,              cy, 0.4, titleH, { fontSize: 10, color: C.textMuted, wrap: false });
  txt(s, '(%)', M + gw + gap,   cy, 0.4, titleH, { fontSize: 10, color: C.textMuted, wrap: false });

  // CRITICAL: pptxgenjs v4 multi-type addChart() IGNORES per-type opts.
  // chartColors, lineDataSymbol, lineSize, barGapWidthPct MUST be in the top-level moefCS.
  // Left chart
  s.addChart(
    [
      { type: pptx.ChartType.bar,  data: [{ name: '[Bar series]',  labels: LBLS, values: [/* ... */] }] },
      { type: pptx.ChartType.line, data: [{ name: '[Line series]', labels: LBLS, values: [/* ... */] }] },
    ],
    moefCS({
      x: M, y: chartY, w: gw, h: gh,
      chartColors: [C.barMid, C.lineYellow],
      barDir: 'col', barGrouping: 'clustered', barGapWidthPct: 50,
      lineDataSymbol: 'none', lineSize: 1.5,
      showLegend: false,
      valAxisLabelFormatCode: '0', // NOT valAxisNumFmt — silently ignored
      valAxisMinVal: /* yMin */, valAxisMaxVal: /* yMax */,
      valAxisMajorUnit: /* step — same value as HTML opts.step */,
      valAxisCrossesAt: /* yMin, only if safe per "Bar-baseline coupling" rule */,
    })
  );
  legend(s, M, chartY, gw, [
    { name: '[Bar series]',  color: C.barMid,    type: 'bar' },
    { name: '[Line series]', color: C.lineYellow, type: 'line' },
  ]);

  // Right chart
  s.addChart(
    [
      { type: pptx.ChartType.bar,  data: [{ name: '[Bar series]',  labels: LBLS, values: [/* ... */] }] },
      { type: pptx.ChartType.line, data: [{ name: '[Line series]', labels: LBLS, values: [/* ... */] }] },
    ],
    moefCS({
      x: M + gw + gap, y: chartY, w: gw, h: gh,
      chartColors: [C.barMid, C.lineYellow],
      barDir: 'col', barGrouping: 'clustered', barGapWidthPct: 50,
      lineDataSymbol: 'none', lineSize: 1.5,
      showLegend: false,
      valAxisLabelFormatCode: '0',
      valAxisMinVal: /* yMin */, valAxisMaxVal: /* yMax */,
      valAxisMajorUnit: /* step — same value as HTML opts.step */,
      valAxisCrossesAt: /* yMin, only if safe per "Bar-baseline coupling" rule */,
    })
  );
  legend(s, M + gw + gap, chartY, gw, [
    { name: '[Bar series]',  color: C.barMid,    type: 'bar' },
    { name: '[Line series]', color: C.lineYellow, type: 'line' },
  ]);

  // Vertical divider centered in the gap (present in HTML as a faint line) — spans from the
  // chart titles down to the bottom margin.
  box(s, M + gw + gap / 2 - 0.005, cy, 0.01, H - cy - M, C.divider);
}
```

---

## Slide Function: STRATEGY_CARDS

```js
function s_StrategyCards(pptx, slideNum) {
  const s = pptx.addSlide();
  s.background = { data: BG_PNG_DATA }; // gradient PNG (matches HTML gradient)

  const cy = sectionHeader(s, '[Section tag]. [Title]');
  pn(s, slideNum);

  // All cards use the same cardBlue — no alternating teal/purple
  const CARDS = [
    { title: '① [Title]', body: '• [bullet1]\n• [bullet2]\n• [bullet3]' },
    { title: '② [Title]', body: '• [bullet1]\n• [bullet2]\n• [bullet3]' },
    { title: '③ [Title]', body: '• [bullet1]\n• [bullet2]\n• [bullet3]' },
    { title: '④ [Title]', body: '• [bullet1]\n• [bullet2]\n• [bullet3]' },
    // Use 2–4 cards; adjust CARDS array length accordingly
  ];

  const gap = 0.16;
  const cw  = (W - 2 * M - (CARDS.length - 1) * gap) / CARDS.length;
  const ch  = H - cy - M;

  CARDS.forEach(function(card, i) {
    const x = M + i * (cw + gap);
    box(s, x, cy, cw, ch, C.cardBlue, null, 0.11);  // 8pt radius

    txt(s, card.title, x + 0.16, cy + 0.16, cw - 0.32, 0.52, {
      fontFace: FONTB, fontSize: 16, bold: false, color: C.textPrimary, valign: 'top',
    });

    box(s, x + 0.16, cy + 0.72, cw - 0.32, 0.007, '4A7A9A');

    txt(s, card.body, x + 0.16, cy + 0.84, cw - 0.32, ch - 1.00, {
      fontSize: 14, bold: false, color: C.textPrimary, valign: 'top', lineSpacingMultiple: 1.7,
    });
  });
}
```

---

## Slide Function: TEXT_ONLY

```js
function s_TextOnly(pptx, slideNum) {
  const s = pptx.addSlide();
  s.background = { data: BG_PNG_DATA }; // gradient PNG (matches HTML gradient)

  const cy = sectionHeader(s, '[Section tag]. [Title]');
  pn(s, slideNum);

  // 2-column layout (extend to 3 columns by splitting colW into thirds)
  const colW = (W - 2 * M - 0.40) / 2;
  const ch   = H - cy - M;

  // Column headings: 16pt yellow
  txt(s, '[Heading 1]', M,               cy + 0.08, colW, 0.36, { fontSize: 16, color: C.lineYellow });
  txt(s, '[Heading 2]', M + colW + 0.40, cy + 0.08, colW, 0.36, { fontSize: 16, color: C.lineYellow });

  // Vertical separator
  box(s, M + colW + 0.19, cy, 0.007, ch, '3A5A7A');

  // Body text: 16pt white (larger than chart text — text-only slides get bigger font)
  txt(s, '• [bullet1]\n• [bullet2]\n• [bullet3]\n• [bullet4]',
    M, cy + 0.52, colW, ch - 0.52,
    { fontSize: 16, color: C.textPrimary, valign: 'top', lineSpacingMultiple: 1.8 }
  );
  txt(s, '• [bullet1]\n• [bullet2]\n• [bullet3]\n• [bullet4]',
    M + colW + 0.40, cy + 0.52, colW, ch - 0.52,
    { fontSize: 16, color: C.textPrimary, valign: 'top', lineSpacingMultiple: 1.8 }
  );
}
```

---

## main() Boilerplate

```js
async function main() {
  const pptx = new PptxGenJS();
  pptx.layout = 'LAYOUT_WIDE';

  s_Cover(pptx);
  // call each slide function in presentation order

  // Write to a _build.pptx temp name, then run the REQUIRED JSZip post-processing block
  // (bar gradients, per-series line colors, Korean legend font, crossesAt/autoZero fix, AND
  // the embedded-workbook data-editability fix — see SKILL.md Step 4b for the full, current
  // regex block) before renaming to the final filename. Do NOT skip this step and do NOT rely
  // on manual PowerPoint formatting — the gradient/colors/font/data-editability are all
  // applied programmatically, not by hand. The embedded-workbook fix in particular is silent
  // if skipped: the file opens and renders perfectly, and only fails when the USER clicks
  // Edit Data — so there is no rendering-based signal that it was missed.
  await pptx.writeFile({ fileName: '[presentation-title]_build.pptx' });
  // ... JSZip post-processing block goes here (see SKILL.md Step 4b) ...
  console.log('✓  [title].pptx generated');
  console.log('   Edit chart data: right-click any chart → Edit Data');
}

main().catch(err => { console.error(err); process.exit(1); });
```

---

## Common Errors

| Error | Cause | Fix |
|---|---|---|
| Colors render as black | 8-digit hex (e.g., `'FFFFFF55'`) | 6-digit only — never append opacity |
| `Cannot find module` | Wrong require path | Must be `../../IR_ppt/node_modules/pptxgenjs` |
| Chart blank or crash | `null` in values array | Every `values[i]` must be a number |
| Y-axis line still visible | Missing `valAxisLineShow: false` | Must be in `moefCS` base — never omit |
| Legend floats outside the chart in the slide margin | Used native `showLegend: true, legendPos: 'tr'` | Native legend reserves a separate column outside the plot area, not an inside-corner overlay. Set `showLegend: false` and call the custom `legend()` helper instead. |
| `valAxisNumFmt` has no effect | Not a real pptxgenjs option (silently ignored) | Use `valAxisLabelFormatCode` instead |
| Bars stretch from a negative floor instead of from zero | `valAxisCrossesAt` set to the chart's negative `yMin` on a bar-containing chart | Only set `valAxisCrossesAt` for `yMin===0` or pure-line charts; leave negative-floor bar charts on default `autoZero` |
| Y-axis silently flips to the wrong side | Passed a raw data value into `catAxisCrossesAt` instead of `valAxisCrossesAt` | `valAxisCrossesAt` controls where the category axis's line sits along the value axis; `catAxisCrossesAt` controls something else entirely — don't confuse them |
| PowerPoint says "there's content it cannot read" on open, but the XML is well-formed | (a) `valAxisCrossesAt: 0` on any chart without the Step 4b `crossesAt`/`autoZero` regex fix — pptxgenjs's own `opts.valAxisCrossesAt \|\| 'autoZero'` treats literal `0` as falsy and emits invalid XML; (b) a secondary-value-axis chart missing `secondaryCatAxis: true` on the secondary series' `options`, leaving the secondary category axis "orphaned" (unreferenced) | (a) apply the crossesAt regex fix in Step 4b; (b) always pass both `secondaryValAxis: true` AND `secondaryCatAxis: true` together, plus `catAxes: [{}, {catAxisHidden:true}]` in moefCS. Verify via real PowerPoint/COM automation, not regex/XSD checks — both bugs are schema-legal XML that only PowerPoint's own parser rejects. |
| Two same-type series (e.g., two bar series) overlap instead of clustering side by side | Used the multi-type array form `addChart([{type,data},{type,data}], opts)` for two series of the SAME type — pptxgenjs emits a separate wrapper per entry | Use the single-type form instead: `addChart(pptx.ChartType.bar, [series1, series2], opts)` — one wrapper, multiple `<c:ser>`, which is what PowerPoint actually clusters |
| Dense per-category tick marks along an axis that HTML doesn't show | Tick marks not suppressed | Set `catAxisMajorTickMark/catAxisMinorTickMark/valAxisMajorTickMark/valAxisMinorTickMark: 'none'` in `moefCS` |
| PPTX saves in wrong place | Path prefix in `writeFile` | Use `{ fileName: 'name.pptx' }` only — no path |
| PowerPoint says "연결된 파일을 사용할 수 없습니다" (linked file cannot be used) when clicking Edit Data on a chart — even though the data is embedded, not linked, and the file opens/renders fine | pptxgenjs's embedded-workbook shared-string cell references are assigned via a naive counter that doesn't dedupe, so repeated category-label text (e.g. the blank `''` entries in every sparse yearly/quarterly/monthly axis label array this skill mandates) makes cells reference shared-string indices that don't exist in the table. Excel can't load a workbook with out-of-range references. This passes every XML well-formedness/schema check and even a clean PowerPoint open — it only breaks Edit Data specifically. | Apply the embedded-workbook data-editability fix in SKILL.md Step 4b (MANDATORY on every deck, not just ones with visibly "unusual" charts) — rewrites the header row and category column as inline strings sourced from each chart's own cache. Verify with the out-of-bounds shared-string scan in Step 6, not `ChartData.Workbook` COM automation (unreliable — see Step 6). |
