# MOEF Design Tokens

All tokens confirmed from `example_ppt_format.pdf` screenshots and iterative user feedback.

---

## Colors (6-digit hex, no `#` — for pptxgenjs)

```js
const C = {
  bg:          '1E3264',  // dark navy base (background gradient center)
  bgDark:      '121848',  // darker navy (gradient edge)
  textPrimary: 'FFFFFF',
  textMuted:   'C0D2E8',  // light blue-white for muted labels, axis text, legends
  lineYellow:  'E4E020',  // primary chart line (YoY, key metric) — vivid yellow
  lineBlue:    '74C0FC',  // second line series
  lineWhite:   'FFFFFF',  // third line series (also used as 2nd line when only 2 lines total)
  barMid:      '8AAED0',  // solid mid-tone for bars (no gradient support in pptxgenjs — gradient applied via JSZip post-processing)
  barGold:     'E8B93C',  // 2nd bar series color, for clustered multi-bar charts (2+ bar series on one axis)
  accentTeal:  '00BFFF',  // section title underlines ONLY
  gridLine:    '3A5280',  // subtle horizontal grid lines
  xAxisLine:   '5B688D',  // visible x-axis floor line — flattened equivalent of HTML's rgba(255,255,255,0.28) zero-line over the gradient's middle stop
  divider:     '2F4170',  // dual-chart vertical divider — flattened equivalent of HTML's rgba(192,210,232,0.12)
  legendBg:    '1A2550',  // custom overlay legend panel fill — flattened equivalent of HTML's rgba(18,28,72,0.72)
  cardBlue:    '1E3F88',  // strategy card fill — extracted from screenshot_4.png
                          // All cards use this SAME color — no alternating teal/purple
};
```

**CSS hex equivalents (with `#` — for HTML/CSS):**
```css
--bg:          #1E3264;
--bg-dark:     #121848;
--text:        #FFFFFF;
--muted:       #C0D2E8;  /* or rgba(192,210,232,0.75) for axis labels */
--yellow:      #E4E020;
--teal:        #00BFFF;
--bar-top:     #DCEEFF;  /* HTML gradient top */
--bar-bot:     #5070A8;  /* HTML gradient bottom (same midpoint as barMid) */
--card:        #1E3F88;
--grid:        rgba(58,82,128,0.6);
```

---

## Typography

| Context | Font | Weight | Size (pt) | Size (px HTML) |
|---|---|---|---|---|
| Slide section title | Pretendard Black | 900 | 32 | 32px |
| Dual-chart sub-title | Pretendard | 500 | 18 | 18px |
| Strategy card title | Pretendard Black | 900 | 16 | 16px |
| Text-only column heading | Pretendard | 500 | 16 | 16px |
| Text-only body | Pretendard | 500 | 16 | 16px |
| Strategy card body | Pretendard | 500 | 14 | 14px |
| Chart axis labels | Pretendard | 500 | 12 | 11px |
| Chart legend | Pretendard | 500 | 10 | 10px |
| Unit labels `(%)` | Pretendard | 500 | 12 | 11px |
| Slide number | Pretendard | 500 | 12 | — |

Font files (available at `C:\Users\kmshi\Desktop\Claude_workspace\IR_ppt\Pretendard-fonts\public\static\alternative\`):
- `Pretendard-Medium.ttf` → font-weight 500, family name `'Pretendard'`
- `Pretendard-Black.ttf`  → font-weight 900, family name `'Pretendard'`

In pptxgenjs:
```js
const FONT  = 'Pretendard';        // Medium — all body text, axis, legend
const FONTB = 'Pretendard Black';  // Black (900) — section titles only (32pt)
```

---

## Slide Dimensions

| Property | PPTX | HTML |
|---|---|---|
| Width | 13.33 in | 960 px |
| Height | 7.5 in | 540 px |
| Margin | 0.5 in | 36 px |
| 1 inch | — | 72 px |
| 1 pt | — | 1 px (approx) |

In pptxgenjs: `const W = 13.33, H = 7.5, M = 0.5;`

Section header returns content-safe `cy`:
- Title at y=0.28, height=0.56 → underline at y=0.88 (3pt teal) → `cy = 0.94`

---

## Spacing & Layout

| Token | PPTX (in) | HTML (px) |
|---|---|---|
| Side margin (M) | 0.5 | 36 |
| Dual-chart gap | 1.0 | 96 |
| Card corner radius | 0.11 (≈8pt) | 8px |
| Title underline height | 0.042 | 3px |
| Section title y | 0.28 | 20px (top:20 inside .slide-header) |
| Content area start | 0.94 | ~97px |

---

## Chart Style Rules

- **Y-axis**: no line (`valAxisLineShow: false`), numbers visible
- **X-axis**: visible floor line (`catAxisLineShow: true`, color `xAxisLine`) — NOT `false`. In HTML, a matching solid line is drawn at the chart floor (`yMin`) in `renderChart()`/`renderChartMultiBar()`/`renderChartDual()`. This floor line was added after the design was first drafted; earlier notes calling for `catAxisLineShow: false` are superseded.
- **Grid lines**: horizontal only, SOLID (not dashed), color `#3A5280`. Both HTML (`stroke-dasharray:'0'`) and PPTX (`valGridLine: {style:'solid',...}`) must agree — dashed was the original spec but was changed to solid per design direction.
- **Zero line**: solid, slightly brighter than gridline
- **Legend**: a custom floating overlay panel drawn inside the chart's own top-right corner (background panel + swatches + text) — NOT pptxgenjs's native `showLegend`/`legendPos`, which reserves a separate column outside the plot area and cannot replicate an inside-corner floating legend. See `pptx_patterns.md`'s `legend()` helper and `html_patterns.md`'s in-SVG legend blocks.
- **Bar fill**: solid `#8AAED0` in PPTX, replaced with a top-to-bottom gradient via mandatory JSZip post-processing (not a manual PowerPoint step); SVG gradient in HTML
- **Primary line**: `#E4E020` (yellow), 2pt, **no markers** (`lineDataSymbol: 'none'` in PPTX; plain `<polyline>` with no `<circle>` elements in HTML) — a line-only stroke, not circle markers.
- **Secondary line**: `#74C0FC` (blue) or `#FFFFFF` (white) depending on series count, 2pt, **no markers** — same rule as the primary line.
- **Axis label format**:
  - Yearly: `'YY` (e.g., `'21`)
  - Quarterly: `YY.NQ` (e.g., `22.1Q`)
  - Monthly: `YY.M` (e.g., `22.1`)
