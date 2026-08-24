---
name: moef-ppt
description: >
  Generates a MOEF (Ministry of Economy and Finance Korea) styled presentation
  (HTML preview + editable PPTX) from a user-provided script and design system.
  Creates a timestamped project folder with both outputs.

  Use this skill whenever the user:
  - Provides slide content/script and mentions MOEF, government PPT, or Korean economic presentation
  - Says "make MOEF PPT", "create slides with MOEF design", "MOEF 스타일 PPT 만들어"
  - Provides a structured slide script (COVER:, CHART_SINGLE:, etc.) with MOEF context
  - Asks to generate, rebuild, or update a MOEF-style deck

  Always generate HTML first, then PPTX, then verify both match visually.
---

# moef-ppt

Creates HTML preview + editable PPTX in the MOEF (기획재정부) design system.

## Working Context

- **Output root:** `C:\Users\kmshi\Desktop\Claude_workspace\moef_ppt\`
- **pptxgenjs:** `C:\Users\kmshi\Desktop\Claude_workspace\IR_ppt\node_modules\pptxgenjs`
  - From subfolder (1 level under moef_ppt root): `require('../../IR_ppt/node_modules/pptxgenjs')`
- **Font files:** `C:\Users\kmshi\Desktop\Claude_workspace\IR_ppt\Pretendard-fonts\public\static\alternative\`
  - From subfolder: `../../IR_ppt/Pretendard-fonts/public/static/alternative/`
- **Design system:** `C:\Users\kmshi\Desktop\Claude_workspace\moef_ppt\moef_ppt_design.txt`
- **Reference implementation (base patterns):** `C:\Users\kmshi\Desktop\Claude_workspace\moef_ppt\2026-06-22_moef-design-demo\` (build.js + preview.html)
- **Reference implementation (custom legend, clustered multi-bar, secondary/dual y-axis, all bug fixes below):** `C:\Users\kmshi\Desktop\Claude_workspace\moef_ppt\2026-07-22_ir-economic-indicators\` (build.js + gen_preview.js-generated preview.html) — this is the source of truth for every pattern in `references/*.md` that isn't in the 06-22 demo. When in doubt about exact working code, read this project's `build.js` directly.

---

## Supported Slide Types

| Type | Description |
|---|---|
| COVER | Centered title, subtitle, date, organization |
| CHART_SINGLE | Section header + one combo chart (bars + lines), centered |
| CHART_DUAL | Section header + two side-by-side charts (each its own single y-axis) |
| STRATEGY_CARDS | Section header + 2–4 column card grid, text only |
| TEXT_ONLY | Section header + 2–3 column text blocks, no charts |

**Variants within CHART_SINGLE (not separate types — same slide shape, different chart engine call):**
- **Clustered multi-bar:** 2+ bar series that must sit side-by-side sharing one axis (e.g., two comparable-scale bar series). Use `renderChartMultiBar()` (HTML) / the single-type `addChart(pptx.ChartType.bar, [series...], opts)` form (PPTX) — not the base `renderChart()`/multi-type-array form, which stacks/overlaps same-type series instead of clustering them.
- **Secondary (right) y-axis, ONE chart:** two series with very different units/scales in a single chart (not two side-by-side charts — that's CHART_DUAL). Use `renderChartDual()` (HTML) and the `valAxes`/`catAxes` dual-axis pattern (PPTX) — see `pptx_patterns.md` and `html_patterns.md`. Legend/series names get an English ` (Left)` / ` (Right)` suffix per the MOEF reference convention.

---

## Step 1 · Parse the Script

Accept both structured and freeform input. Map to slide type + content.

**Structured format:**
```
COVER: [Title] | [Subtitle] | [Date] | [Organization]

CHART_SINGLE: [Section tag] | [Slide title]
  bars: [Series name] | [label:value, label:value, ...]
  line1: [Series name] | [label:value, ...]   (yellow)
  line2: [Series name] | [label:value, ...]   (white, optional)
  yMin: -2 | yMax: 6 | unit: (%)

CHART_DUAL: [Section tag] | [Slide title]
  LEFT:
    title: [Chart title]
    bars: [Series] | [label:value, ...]
    line1: [Series] | [label:value, ...]
    yMin: 0 | yMax: 10 | unit: (%)
  RIGHT:
    title: [Chart title]
    bars: [Series] | [label:value, ...]
    line1: [Series] | [label:value, ...]
    yMin: 0 | yMax: 10

STRATEGY_CARDS: [Section tag] | [Slide title]
  - [Card header] | [bullet1] / [bullet2] / [bullet3]
  - ...  (2 to 4 cards)

TEXT_ONLY: [Section tag] | [Slide title]
  COL1: [Column heading] | [bullet1] / [bullet2] / [bullet3] / [bullet4]
  COL2: [Column heading] | [bullet1] / [bullet2] / [bullet3] / [bullet4]
  COL3: [Column heading] | ...  (optional)
```

**Axis label format rules (CRITICAL — always follow):**
- Yearly data: `'YY` (e.g., `'21`, `'22`) — show EVERY year, apostrophe prefix
- Quarterly data: `YY.1Q` at Q1 only (e.g., `23.1Q`, `24.1Q`). All Q2/Q3/Q4 positions must be `''`:
  ```
  // Q1 2021 – Q1 2026 (21 quarters):
  ['21.1Q','','','','22.1Q','','','','23.1Q','','','','24.1Q','','','','25.1Q','','','','26.1Q']
  ```
- Monthly data: `YY.1` at January only (e.g., `24.1`, `25.1`). All other months must be `''`:
  ```
  // Monthly May 2021 – Apr 2026 (60 points, Jan of each year at positions 8,20,32,44,56):
  ['','','','','','','','','22.1','','','','','','','','','','','','23.1','','','','','','','','','','','','24.1','','','','','','','','','','','','25.1','','','','','','','','','','','','26.1','','','']
  ```
- Count the array length against the data series length — they MUST match. Use `node -e "console.log([...].length)"` to verify.
- **Line colors (CRITICAL when multiple lines):** First line = `lineYellow` (#E4E020). Second line = `lineBlue` (#74C0FC). Third line = `lineWhite` (#FFFFFF). NEVER assign the same color to two lines in one chart.

**Data completeness rule (CRITICAL):**
- Default: use ALL available data from the source (Excel, CSV, etc.) — never truncate to recent periods only.
- If Excel has data from 2021–2026, all ~60 data points go in the chart, not just 2024–2025.
- Set axis yMin/yMax/step to accommodate the full data range, not just recent values.
- **Override:** if the user explicitly requests a time window (e.g., "use only the last 5 years"), that instruction wins — trim with `slice(-N)` on the positionally-derived series (see below), not by re-parsing row labels.
- **Deriving dates positionally:** raw sheet row labels are often inconsistent (`"01.1"`, `"2"`, Excel date serials, `"2021/06"`). Do not parse them directly. Instead, take the sheet's first row as a known start month/year and increment by one period per row — verify no gaps/dupes across the full column first. Trim with `.slice(-N)` only after building the full positional series.
- **Dual-axis need shrinks with a shorter window:** two series that need a secondary axis over full history may fall into comparable scale once trimmed to a short window — check yMin/yMax on the actual trimmed slice before deciding a chart needs `CHART_DUAL`/secondary-axis treatment, don't assume from the full-history shape.

---

## Step 2 · Create Project Folder

```powershell
$ts   = Get-Date -Format 'yyyy-MM-dd'
$slug = "<sanitized-title>"   # lowercase, hyphens, no spaces
$dir  = "C:\Users\kmshi\Desktop\Claude_workspace\moef_ppt\${ts}_${slug}"
New-Item -ItemType Directory -Path $dir -Force
```

All output files go inside `$dir`.

---

## Step 3 · Generate `preview.html`

Read `references/html_patterns.md` for:
- Complete CSS shell (gradient background, @font-face, base styles)
- Complete `renderChart()` SVG engine (copy verbatim — do not simplify)
- HTML markup pattern for each slide type

**Key requirements:**
- Each slide: `<div class="slide">` at **960 × 540 px**
- Scale: 1 PPTX inch = 72 px → margin 0.5in = 36px
- **Standalone fonts (REQUIRED):** Embed Pretendard as base64 data URIs in @font-face — do NOT use relative file paths. Read TTF files at build time and inline them:
  ```js
  // In a Node.js build script that also writes the HTML:
  const medB64 = require('fs').readFileSync('...Pretendard-Medium.ttf').toString('base64');
  const blkB64 = require('fs').readFileSync('...Pretendard-Black.ttf').toString('base64');
  // In the CSS @font-face src: url('data:font/truetype;base64,<medB64>') format('truetype')
  ```
  Or, generate HTML with path-based fonts then replace with a post-processing step.
  The resulting HTML will be ~7MB but is fully standalone — fonts render correctly on any device.
- Background gradient: `linear-gradient(160deg, #243478 0%, #1B2D60 40%, #121C48 100%)`
- NEVER draw a vertical axis line in SVG (labels float beside gridlines only)
- Legend: always vertical stacking (one row per series, 16px apart); line legend icons are plain lines (no dots)
- Dual-chart gap: 96px between the two chart plot areas
- **Slideshow mode:** Include the slideshow CSS + HTML controls + JS engine (see `references/html_patterns.md` → "Slideshow Mode" section). Keyboard: ←/→/Space navigate, Escape exits, F fullscreen.

---

## Step 4 · Generate `build.js`

Read `references/pptx_patterns.md` for:
- pptxgenjs require path and color/font constants
- Complete helper functions (box, txt, sectionHeader, pn, moefCS) — copy verbatim
- Slide function pattern for each slide type

**Key requirements:**
- `require('../../IR_ppt/node_modules/pptxgenjs')` (two levels up from project subfolder)
- `valAxisLineShow: false` (no visible y-axis line) but `catAxisLineShow: true` with `catAxisLineColor: C.xAxisLine` and `catAxisLineSize: 1` — this draws the visible x-axis floor line that matches HTML's added floor line. Do NOT set `catAxisLineShow: false`; that was an old/wrong pattern.
- **Tick marks:** always set `catAxisMajorTickMark: 'none'`, `catAxisMinorTickMark: 'none'`, `valAxisMajorTickMark: 'none'`, `valAxisMinorTickMark: 'none'` in `moefCS`. Without this, pptxgenjs draws a dense row of per-category tick marks along the x-axis that HTML never shows.
- **Gridlines are SOLID, not dashed:** `valGridLine: { style: 'solid', color: C.gridLine, size: 0.5 }`. Matches the HTML fix (see html_patterns.md) — both sides must agree.
- Dual-chart gap: 1.0in between chart bounding boxes
- Dual-chart titles: 18pt white Pretendard Black, centered above each chart
- Card body: 14pt; Text-only body: 16pt; Chart labels: 10pt; Section title: 32pt Black
- All card colors: `#1E3F88` (single blue — no teal/purple alternating)
- **Legend is a custom overlay, never pptxgenjs's native legend:** always set `showLegend: false` in `moefCS`. `legendPos: 'tr'` (or any preset) reserves a separate column OUTSIDE the chart plot area and shrinks the chart — it cannot replicate an inside-corner floating legend. Instead call the `legend(s, frameX, frameY, frameW, items)` helper (see `pptx_patterns.md`) after `addChart()`, passing the same `x/y/w` used for the chart frame. Legend font: 9pt, color `C.textMuted` (smaller than 10pt chart labels to avoid overlap).
- pptxgenjs color format: **6-digit hex WITHOUT `#`** (never 8-digit — will silently break)
- `await pptx.writeFile({ fileName: '<title>.pptx' })` — no path prefix, saves in cwd
- **CRITICAL — pptxgenjs multi-type chart opts are IGNORED:** For `addChart([{type, data}, ...], opts)`, pptxgenjs v4 reads ALL styling from the second argument (top-level opts), NOT from per-type `opts` (except the `secondaryValAxis`/`secondaryCatAxis` flags — see below). Place `chartColors`, `lineDataSymbol`, `lineSize`, `barDir`, `barGrouping`, `barGapWidthPct` in the top-level `moefCS({...})` call. `chartColors` must be ordered to match series (bars first, then lines).
- **CRITICAL — multi-type array does NOT cluster same-type series:** `addChart([{type:bar,...},{type:bar,...}], opts)` makes pptxgenjs emit one SEPARATE `<c:barChart>` XML wrapper per array entry — two independent bar wrappers do not cluster in PowerPoint, they overlap at the same x-position. When two-or-more series share the SAME chart type and must cluster (e.g., two bar series side by side), use the single-type call form instead: `addChart(pptx.ChartType.bar, [series1, series2], opts)` — one wrapper, two `<c:ser>` elements, which is what PowerPoint actually clusters against. Reserve the multi-type array form for genuinely different chart types (bar + line combo).
- **All line series:** `lineDataSymbol: 'none'` (in top-level moefCS opts) — no circle markers on lines
- **Unit labels:** place `txt()` in the same row as the section title / chart-title text (at `y = cy`, i.e. ABOVE the chart frame), not at `chartY` (inside the frame). Placing it at `chartY` overlaps the chart's own topmost axis number. No source citations (출처) anywhere.
- **Dual-axis (secondary value axis) charts — REQUIRED wiring, or the file corrupts:** when one series needs a secondary right-hand axis, that series' `options` must set BOTH `secondaryValAxis: true` AND `secondaryCatAxis: true` — omitting `secondaryCatAxis` leaves the auto-added secondary category axis unreferenced by any series ("orphaned axis"), which PowerPoint's file parser rejects outright (COM error `0x80070570`, "file is corrupted and unreadable") even though the XML is well-formed and schema-legal by XSD alone. Also pass `valAxes: [leftAxisOpts, rightAxisOpts]` and `catAxes: [{}, { catAxisHidden: true }]` in the top-level `moefCS` call — see `pptx_patterns.md` for the full pattern. This class of bug is NOT caught by regex tag-balancing or XML well-formedness checks; only real PowerPoint (ideally via COM automation, see Step 6) or opening the file will reveal it.
- **Bar-baseline coupling caveat:** do NOT set `valAxisCrossesAt` (or the equivalent on `catAxes[0]`) to a chart's true negative floor for any chart containing a bar series — PowerPoint anchors bar baselines to wherever the category axis crosses the value axis, so forcing the crossing to a negative floor stretches every bar from that floor upward instead of from zero, breaking bar rendering. Only set an explicit `valAxisCrossesAt` for charts with `yMin = 0` or pure-line charts; leave bar-containing charts with a negative range on PowerPoint's default `autoZero` crossing (accepting that the x-axis floor line then sits at value=0 instead of the chart's true bottom for that one chart).
- **pptxgenjs falsy-zero bug:** internally pptxgenjs does `opts.valAxisCrossesAt || 'autoZero'`, which treats a legitimate crossing value of exactly `0` as falsy and emits invalid XML (`<c:crossesAt val="autoZero"/>` — a numeric element holding a non-numeric string), corrupting the whole file. If any chart legitimately crosses at 0, this needs the Step 4b post-processing regex fix — see below.
- **Slide background:** Use `BG_PNG_DATA` (gradient PNG generated by `makeGradientPNG(160,90)` — copy verbatim from `pptx_patterns.md`). Set `s.background = { data: BG_PNG_DATA }` on every slide. This replicates the HTML gradient (`linear-gradient(160deg, #243478 0%, #1B2D60 40%, #121C48 100%)`).
- **Chart transparency:** `moefCS` must have NO `plotArea.fill` and NO `chartArea.fill` color → pptxgenjs outputs `<a:noFill/>` so charts are transparent over the gradient background
- **Cover title:** `fontSize: 38` (matches HTML 38px)
- **Gridlines:** Add `valAxisMajorUnit` to every chart equal to the HTML `opts.step` value — keeps gridline count to <8
- **Color constants:** `C.lineBlue = '74C0FC'` (second line), `C.lineYellow = 'E4E020'` (first line), `C.barGold = 'E8B93C'` (second bar series, for multi-bar charts). All must be in the `C` object and used in `chartColors` and HTML's `T` object.

---

## Step 4b · Post-Processing (JSZip — REQUIRED)

pptxgenjs generates PPTX XML with several limitations. Apply this post-processing block **every time** after `pptx.writeFile()`:

**Why needed:**
1. Bar fills default to flat `#8AAED0`; we replace with top-to-bottom gradient
2. `<c:dPt>` per-data-point color overrides in barChart override series-level fills — must remove them
3. Line series colors are all assigned from `chartColors[0]` (a pptxgenjs v4 bug) — must post-assign per-series
4. Legend font (`legendFontFace`, `legendFontColor`) is silently ignored by pptxgenjs for Korean text — must replace `<c:txPr>` in XML
5. **`<c:crossesAt val="autoZero"/>` fix (only if any chart sets `valAxisCrossesAt: 0`):** add `xml = xml.replace(/<c:crossesAt val="autoZero"\/>/g, '<c:crossesAt val="0"\/>');` — fixes pptxgenjs's falsy-zero bug (see Step 4). Without this, PowerPoint reports the file as corrupted on open.
6. **Embedded workbook data-editability fix (MANDATORY, every chart, every deck — see below):** without this, "Edit Data" in PowerPoint fails with "연결된 파일을 사용할 수 없습니다" (the linked file cannot be used), even though the data is genuinely embedded. This is NOT an edge case — it is triggered by this skill's OWN mandated sparse axis-label pattern (blank `''` entries for non-shown periods), so every multi-period chart this skill produces is affected unless this fix is applied.

**Counter scope — GLOBAL per chart XML file, never per-wrapper or per-match:** pptxgenjs emits chart XML in two different shapes depending on how `addChart()` was called — (a) the multi-type array form emits one SEPARATE `<c:barChart>`/`<c:lineChart>` wrapper per series, each with one `<c:ser>`; (b) the single-type multi-series form emits ONE wrapper with multiple `<c:ser>` elements. Both shapes need per-series color cycling in the SAME order (bar colors array, then line colors array), so the replace-callback's color-index counter must be declared OUTSIDE the wrapper-matching regex (once per chart XML file) and incremented across every match, not reset at the start of each `<c:barChart>`/`<c:lineChart>` block — otherwise a chart using the separate-wrapper shape gets the same color assigned to every series. See `pptx_patterns.md` for the exact working regex.

**Write to temp file, rename to avoid EBUSY file lock:**
```js
const finalFname = '파일명.pptx';
const buildFname = '파일명_build.pptx';
await pptx.writeFile({ fileName: buildFname });
```

**Post-processing block (copy verbatim):**
```js
const JSZip = require('../../IR_ppt/node_modules/jszip');
const fs = require('fs');

const solidFill = '<a:solidFill><a:srgbClr val="8AAED0"/></a:solidFill>';
const gradFill  = '<a:gradFill><a:gsLst><a:gs pos="0"><a:srgbClr val="DCEEFF"/></a:gs><a:gs pos="100000"><a:srgbClr val="5070A8"/></a:gs></a:gsLst><a:lin ang="16200000" scaled="0"/></a:gradFill>';

const zip = await JSZip.loadAsync(fs.readFileSync(buildFname));
for (const [chartPath, file] of Object.entries(zip.files)) {
  if (/^ppt\/charts\/chart\d+\.xml$/.test(chartPath)) {
    let xml = await file.async('string');

    // (a) Bar series: gradient fill + remove per-data-point color overrides
    xml = xml.replace(/(<c:barChart>)([\s\S]*?)(<\/c:barChart>)/g, (_, o, c, cl) => {
      c = c.replaceAll(solidFill, gradFill);
      c = c.replace(/<c:dPt>[\s\S]*?<\/c:dPt>\s*/g, '');
      return o + c + cl;
    });

    // (b) Line series: noFill for series fill, correct stroke color per series order
    const lineColors = ['E4E020', '74C0FC', 'FFFFFF'];
    xml = xml.replace(/(<c:lineChart>)([\s\S]*?)(<\/c:lineChart>)/g, (_, o, c, cl) => {
      let n = 0;
      c = c.replace(
        /<c:spPr><a:solidFill><a:srgbClr val="[0-9A-Fa-f]{6}"\/><\/a:solidFill>(<a:ln[^>]*>)<a:solidFill><a:srgbClr val="[0-9A-Fa-f]{6}"\/><\/a:solidFill>/g,
        (_, lnTag) => {
          const lc = lineColors[n++ % lineColors.length];
          return `<c:spPr><a:noFill/>${lnTag}<a:solidFill><a:srgbClr val="${lc}"/></a:solidFill>`;
        }
      );
      return o + c + cl;
    });

    // (c) Legend font: complete <c:txPr> replacement (Korean text needs <a:ea>)
    const legendTxPr = [
      '<c:txPr><a:bodyPr/><a:lstStyle/><a:p><a:pPr>',
      '<a:defRPr sz="1000" b="0" i="0" u="none" strike="noStrike">',
      '<a:solidFill><a:srgbClr val="FFFFFF"/></a:solidFill>',
      '<a:latin typeface="Pretendard Medium"/>',
      '<a:ea typeface="Pretendard Medium"/>',
      '<a:cs typeface="Pretendard Medium"/>',
      '</a:defRPr></a:pPr>',
      '<a:endParaRPr lang="ko-KR">',
      '<a:solidFill><a:srgbClr val="FFFFFF"/></a:solidFill>',
      '<a:latin typeface="Pretendard Medium"/>',
      '<a:ea typeface="Pretendard Medium"/>',
      '<a:cs typeface="Pretendard Medium"/>',
      '</a:endParaRPr></a:p></c:txPr>',
    ].join('');
    xml = xml.replace(
      /(<c:legend>[\s\S]*?)<c:txPr>[\s\S]*?<\/c:txPr>([\s\S]*?<\/c:legend>)/g,
      (_, pre, post) => pre + legendTxPr + post
    );

    zip.file(chartPath, xml);
  }
}

// ── Embedded workbook data-editability fix (MANDATORY — see "Why needed" #6 above) ──
// Root cause (found via isolated testing across many pptxgenjs chart variants + real
// PowerPoint COM automation, since this corruption class passes every XML well-formedness /
// schema check): pptxgenjs's embedded-workbook shared-string TABLE (xl/sharedStrings.xml) is
// correctly deduplicated, but the CELL REFERENCES pointing into it (xl/worksheets/sheet1.xml)
// are assigned via a naive sequential counter that does not check for duplicates. Any chart
// with repeated text among its category labels — which includes every yearly/quarterly/
// monthly sparse axis-label pattern mandated above (blank '' entries repeat constantly) — ends
// up with cells referencing shared-string indices that don't exist in the table (e.g. cells
// reference index 19 while the table only has 12 entries). Excel cannot resolve an
// out-of-range shared-string index, so it fails to load the embedded workbook; PowerPoint
// surfaces this as "linked file cannot be used" when the user clicks Edit Data — even though
// the workbook is genuinely embedded, not linked. A second, harmless-on-its-own defect
// co-occurs: xl/tables/table1.xml's `ref` attribute gets a stray trailing apostrophe (e.g.
// `ref="A1:G14'"`) — schema-invalid; fixed below too since it's free.
//
// Fix: rewrite the header row (series names) and category column (axis labels) as INLINE
// strings, read directly out of each chart's OWN cached values (already sitting in the `xml`
// this loop just finished patching above) — that cache is unaffected by the bug, so no
// hand-maintained data map is needed; this derives the correct values automatically for any
// chart shape.
function decodeXmlEntities(s) {
  return s.replace(/&apos;/g, "'").replace(/&quot;/g, '"').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&');
}
function encodeXmlEntities(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
function colLetter(n) { // 1-indexed: 1->A, 2->B, ...
  let s = '';
  while (n > 0) { const m = (n - 1) % 26; s = String.fromCharCode(65 + m) + s; n = Math.floor((n - 1) / 26); }
  return s;
}
function extractChartSeriesAndCategories(chartXml) {
  const seriesNames = [...chartXml.matchAll(/<c:ser>[\s\S]*?<c:tx>[\s\S]*?<c:v>([^<]*)<\/c:v>[\s\S]*?<\/c:tx>/g)]
    .map(m => decodeXmlEntities(m[1]));
  const catMatch = chartXml.match(/<c:cat>([\s\S]*?)<\/c:cat>/);
  let categoryLabels = [];
  if (catMatch) {
    const ptCountMatch = catMatch[1].match(/<c:ptCount val="(\d+)"/);
    const ptCount = ptCountMatch ? parseInt(ptCountMatch[1], 10) : 0;
    categoryLabels = new Array(ptCount).fill('');
    for (const m of catMatch[1].matchAll(/<c:pt idx="(\d+)"><c:v>([^<]*)<\/c:v><\/c:pt>/g)) {
      categoryLabels[parseInt(m[1], 10)] = decodeXmlEntities(m[2]);
    }
  }
  return { seriesNames, categoryLabels };
}
function fixEmbeddedWorkbookLabels(sheetXml, categoryLabels, seriesNames) {
  let xml = sheetXml;
  seriesNames.forEach((name, i) => {
    const cellRef = `${colLetter(2 + i)}1`; // row 1, col B onward (col A is the corner header)
    const re = new RegExp(`<c r="${cellRef}"[^>]*>(?:<v>\\d+</v>)?</c>`);
    xml = xml.replace(re, `<c r="${cellRef}" t="inlineStr"><is><t xml:space="preserve">${encodeXmlEntities(name)}</t></is></c>`);
  });
  categoryLabels.forEach((label, i) => {
    const cellRef = `A${2 + i}`; // col A, row 2 onward
    const re = new RegExp(`<c r="${cellRef}"[^>]*>(?:<v>\\d+</v>)?</c>`);
    xml = xml.replace(re, `<c r="${cellRef}" t="inlineStr"><is><t xml:space="preserve">${encodeXmlEntities(label)}</t></is></c>`);
  });
  return xml;
}

for (const [chartPath, chartFile] of Object.entries(zip.files)) {
  if (!/^ppt\/charts\/chart\d+\.xml$/.test(chartPath)) continue;
  const chartXml = await zip.file(chartPath).async('string'); // already-patched by the loop above
  const relsPath = chartPath.replace('charts/', 'charts/_rels/') + '.rels';
  const relsFile = zip.file(relsPath);
  if (!relsFile) continue;
  const relsXml = await relsFile.async('string');
  const relMatch = relsXml.match(/Target="[^"]*\/([^"/]+\.xlsx)"/);
  if (!relMatch) continue; // this chart has no embedded workbook
  const embPath = `ppt/embeddings/${relMatch[1]}`;
  const embFile = zip.file(embPath);
  if (!embFile) continue;

  const { seriesNames, categoryLabels } = extractChartSeriesAndCategories(chartXml);
  const embBuf = await embFile.async('nodebuffer');
  const embZip = await JSZip.loadAsync(embBuf);
  let fixedAny = false;
  for (const [innerPath, innerFile] of Object.entries(embZip.files)) {
    if (innerFile.dir || !/\.xml$/.test(innerPath)) continue;
    let innerXml = await innerFile.async('string');
    let patched = innerXml.replace(/ref="([A-Z]+\d+(?::[A-Z]+\d+)?)'"/g, 'ref="$1"');
    if (/^xl\/worksheets\/sheet\d+\.xml$/.test(innerPath)) {
      patched = fixEmbeddedWorkbookLabels(patched, categoryLabels, seriesNames);
    }
    if (/^xl\/sharedStrings\.xml$/.test(innerPath)) {
      const actualCount = (patched.match(/<si>/g) || []).length;
      patched = patched.replace(/count="\d+" uniqueCount="\d+"/, `count="${actualCount}" uniqueCount="${actualCount}"`);
    }
    if (patched !== innerXml) { embZip.file(innerPath, patched); fixedAny = true; }
  }
  if (fixedAny) {
    const fixedEmbBuf = await embZip.generateAsync({ type: 'nodebuffer', compression: 'DEFLATE' });
    zip.file(embPath, fixedEmbBuf);
  }
}

const outBuf = await zip.generateAsync({ type: 'nodebuffer', compression: 'DEFLATE' });
fs.writeFileSync(buildFname, outBuf);

// Rename to final (works even if PowerPoint has it open — PowerPoint will prompt to reload)
try {
  if (fs.existsSync(finalFname)) fs.unlinkSync(finalFname);
  fs.renameSync(buildFname, finalFname);
} catch (e) {
  console.log(`⚠  Saved as ${buildFname} — close PowerPoint and rename to ${finalFname}`);
}
```

**Key notes:**
- Chart XML path in PPTX ZIP is `ppt/charts/chart*.xml` (NOT `xl/charts/` — that's Excel)
- `ang="16200000"` = 270° = top-to-bottom gradient in OOXML (angles are in 1/60000 degree units)
- `<c:dPt>` removal is essential — pptxgenjs cycles `chartColors` per bar and generates per-point overrides that cover the series-level gradient
- Legend `legendFontFace`/`legendFontColor` props in pptxgenjs are silently ignored for Korean (hangul falls back to theme font). Full `<c:txPr>` replacement with `<a:ea>` is the only fix.
- Embedded workbook path in PPTX ZIP is `ppt/embeddings/*.xlsx` (one per chart, resolved via that chart's own `ppt/charts/_rels/chart*.xml.rels` — do not assume a fixed naming/numbering scheme, always resolve through the relationship)
- The embedded-workbook fix must run over the SAME `zip` object as the chart-XML fixes above (after that loop, before `zip.generateAsync`) since it reads each chart's already-patched XML to source the correct label/series text

---

## Step 5 · Run the Build

```bash
cd "<project-dir>"
node build.js
```

If it fails:
1. Read the error — most common causes: wrong require path, 8-digit hex color, null chart value, label array length mismatch
2. Fix `build.js` and retry
3. Never use `--no-verify` or skip errors — fix the root cause
4. **EBUSY error:** PPTX is open in PowerPoint. Use `_build.pptx` temp + rename pattern (see Step 4b)

---

## Step 6 · Verify HTML + PPTX

```powershell
Start-Process "<project-dir>\preview.html"
```

**HTML checklist** (use slideshow mode: click "슬라이드쇼 시작 ▶", or use ←/→ keyboard):
- [ ] All slides render without blank content
- [ ] Text content matches the input script exactly
- [ ] Teal underline appears below every section title
- [ ] Section numbers have no leading zeros (e.g., "1." not "01.")
- [ ] Charts: bars visible, lines WITHOUT circle markers, correct axis labels
- [ ] Gridlines are SOLID (not dashed); x-axis floor line visible and bright, matching the zero line style
- [ ] X-axis: only first period of each year labeled (24.1, 25.1, 26.1 etc.); others blank
- [ ] Unit label appears above the chart frame at top-left, not overlapping the topmost axis number, not in legend or series names
- [ ] No source citations (출처) anywhere in the slides
- [ ] Y-axis: fewer than 8 gridlines per chart
- [ ] All-positive charts (yMin > 0): bars start from chart bottom, not from y=0
- [ ] Multi-bar charts (2+ clustered bar series): bars sit SIDE BY SIDE, not overlapping at the same x-position
- [ ] Legend: floating panel with background, inside the chart's own top-right corner (not in a separate reserved column outside the chart)
- [ ] Dual charts (CHART_DUAL layout): clear gap, 18pt centered titles above each chart, unit labels on both sides
- [ ] Dual-axis charts (single chart, secondary y-axis): left AND right axis tick labels both visible and distinct; legend entries suffixed ` (Left)` / ` (Right)`
- [ ] No text overflow outside the 960×540 px slide bounds
- [ ] Cards: all same navy blue, text not clipped
- [ ] Slideshow mode works: click "슬라이드쇼 시작 ▶" actually activates fullscreen single-slide view (not just a no-op), ←/→ navigate, Escape exits, counter shows N/total. If it doesn't activate, check the CSS — a `display:none` ancestor (`.slide-wrap`) will hide a `.show-active` descendant regardless of the descendant's own `display` value; the fix is `visibility: hidden`/`visibility: visible` instead (see `html_patterns.md`).

**PPTX/HTML alignment** — open both side-by-side and compare slide by slide.
HTML is the reference. Verify PPTX matches on:
- [ ] Section title font weight and size
- [ ] Teal underline position
- [ ] Chart layout and axis label positions
- [ ] Gridlines solid, tick marks absent (no dense per-category tick row on either axis)
- [ ] Legend position, panel background, and font size match the HTML overlay legend
- [ ] Unit label position (above chart frame, not overlapping axis numbers)
- [ ] Dual-axis charts: right-axis numbers visible and distinct from left; file actually opens without a "repair" prompt
- [ ] Background color (PPTX uses flat `#243478`; HTML uses gradient — closest match achievable)
- [ ] **Every chart's embedded workbook has no out-of-bounds shared-string references** (see script below) — this is the automatable proxy for "Edit Data works in PowerPoint" and MUST be run every time, not just for charts that "look" structurally new

Bar gradient (DCEEFF → 5070A8, top-to-bottom) is applied automatically via JSZip post-processing (Step 4b) — no manual PowerPoint steps needed.

**Do not trust visual inspection alone for "does the PPTX actually open."** Regex-based tag-balance checks, cross-reference resolution checks, and XML well-formedness checks can all pass on a file that PowerPoint still rejects as corrupted — several of the bugs above (falsy-zero `crossesAt`, orphaned secondary axis) are schema-legal XML that PowerPoint's own parser rejects for semantic reasons no XSD validator catches. For any dual-axis or otherwise structurally new chart, verify by actually launching PowerPoint via COM automation and opening the file programmatically (`New-Object -ComObject PowerPoint.Application`, `.Presentations.Open()`), catching and printing the real COM error if it fails, then `.Close()` without saving. This is the same code path the user's PowerPoint uses, so it reproduces (or rules out) the "content cannot be read" repair prompt authoritatively — unlike any custom regex/schema check. Likewise, verify HTML slideshow interactivity with a real click (e.g. via `claude-in-chrome`) rather than a synthetic dispatched `.click()`/`KeyboardEvent`, which can bypass real hit-testing/event-pipeline bugs.

**"Does Edit Data actually work" needs its own check — a clean PowerPoint open does NOT prove this.** A chart can render perfectly and the file can open with zero repair prompt while its embedded workbook is still unreadable by Excel (the out-of-bounds shared-string bug fixed in Step 4b is exactly this: invisible to rendering, breaks the moment the user clicks Edit Data). Two verification layers, in order of reliability:
1. **Automated, always run this** — after Step 4b, scan every embedded workbook for out-of-bounds shared-string references:
   ```js
   const embPaths = Object.keys(zip.files).filter(p => /^ppt\/embeddings\/.*\.xlsx$/.test(p));
   for (const p of embPaths) {
     const inner = await JSZip.loadAsync(await zip.file(p).async('nodebuffer'));
     const sst = await inner.file('xl/sharedStrings.xml').async('string');
     const siCount = (sst.match(/<si>/g) || []).length;
     for (const [sp, sf] of Object.entries(inner.files)) {
       if (sf.dir || !/^xl\/worksheets\/sheet\d+\.xml$/.test(sp)) continue;
       const sheet = await sf.async('string');
       const maxIdx = Math.max(-1, ...[...sheet.matchAll(/t="s"><v>(\d+)<\/v>/g)].map(m => parseInt(m[1], 10)));
       if (maxIdx >= siCount) console.log(`OUT OF BOUNDS in ${p}: max index ${maxIdx} >= ${siCount} entries`);
     }
   }
   ```
   This alone would have caught the bug fixed in Step 4b — it is cheap, deterministic, and does not depend on PowerPoint being installed.
2. **`ChartData.Workbook` / extracted-xlsx COM automation is UNRELIABLE for this check — do not trust it, in either direction.** Testing showed `Shape.Chart.ChartData.Workbook` returns an object with `Worksheets.Count = 0` even for files later confirmed to work correctly for the end user, and even for other already-shipped decks — this is a limitation of driving OLE/Excel activation headlessly, not a signal about the file. Do not use it to declare a file broken OR to declare it fixed. If PowerPoint isn't available for a real interactive test, treat check #1 passing as sufficient evidence; if it's available, a real click-through Edit Data test by the user remains the only fully authoritative confirmation.

Fix any issues before reporting done.

---

## Step 7 · Report

Tell the user:
1. **Folder:** full path
2. **Files:** `preview.html`, `build.js`, `<title>.pptx`
3. **Slides:** count and type list
4. **To edit chart data in PowerPoint:** right-click any chart → Edit Data — confirmed editable (out-of-bounds shared-string check from Step 6 passed for every chart)
5. **To regenerate PPTX:** `node build.js` from the project folder
