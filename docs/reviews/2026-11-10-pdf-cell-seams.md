# PDF-only table-cell seam correction — 2026-11-10

The renderer, domain parsers, fitting, splitting and grouping remain unchanged.
The new `pdf_fills.py` helper operates on native PDF drawing commands after
Chromium prints, within `_render_batch` only. It changes neither generated HTML
nor browser layout and has no Android rendering counterpart.

The complete SRD candidate initially exported, but PDFium's existing 300-DPI
check rejected 43 bestiary pages. Adjacent translucent table-cell rectangles
produced one-pixel darker seams; MuPDF passed. Saved failed reports, source
PDF and diagnosis images remain under
`output/srd-fork/candidate-21-full-export/`.

The correction combines only positive, exactly adjacent horizontal rectangle
fills under the same explicit RGB color and simple Normal transparency state.
Raw decimal tokens establish exact adjacency and width sums, with bounded
token lengths and sufficient local precision. It splices only those rectangle
bytes; all other text, curve, transform, clipping and color bytes remain intact.
An independent parsed-operation comparison rejects misplaced matches inside
strings or inline images. Existing open paths, gaps, overlaps, state changes,
unknown states and unsupported command shapes are preserved. Unchanged pages
retain their original content streams.

The exporter verifies the original native text/hash, saves its hash separately,
applies the guarded PDF-only union, then freezes the final content hash.
Compaction and merged-document hash checks remain unchanged. No overflow,
visual, contrast or glyph tolerance was relaxed.

Independent context-free review found no actionable issues. It reran all nine
focused tests, confirmed clone stream identity on all 186 original pages, and
checked idempotence of all 6,163 joins across 115 changed pages. The complete
workspace suite passes 108 tests, including the ten separate installer-helper
tests which are not part of this PDF change. The scoped committed test modules
plus the new PDF tests pass **98 tests**, with no failures or skips.

The fresh production SRD export contains **1,616 cards / 186 Letter sheets /
19,604,985 bytes**. Its SHA-256 is
`c887c89ccc22874cde804e01b387efc09321b67c42d37f7f9bf5943d5c4a5207`.

- All 186 original native drawing-stream hashes are identical before the
  PDF-only step; all browser glyph layouts, text signatures and card counts
  are also exact matches.
- All 1,001,414 characters match, with zero unmatched glyphs. Maximum
  advance/cross error remains 0.10385 / 1.8035 CSS px.
- All 186 pages pass the unchanged MuPDF and PDFium artifact/contrast checks
  at 300 DPI. Maximum unexpected background pixels are two and zero,
  respectively.
- Six assembled-PDF overviews cover every page; all 14 approved portrait card
  faces were inspected in detailed final-PDF crops.
- 185/186 browser screenshot PNGs are byte-identical between runs. Sheet 45
  has edge rasterization variation with zero unexpected background pixels or
  contrast tiles; its full glyph layout and native drawing stream are exact.
  These checks do not claim literal cross-reader pixel identity.

Evidence: `output/srd-fork/candidate-21-final-export/verification.json`,
`glyph-verification.json`, `graphics-mupdf.json`, `graphics-pdfium.json`,
`browser-boundary.json`, `native-boundary.json`, and `review/`.

Fresh post-fix captures of the full installed 651-JSON database pass exact
per-platform complete HTML/card/shell regression: **12,270 cards / 10,183 entries
/ 1,374 sheets** on desktop and Android's initialized host generator. All 38
protected code files still match their repository HEAD blobs. See
[full-database preservation](2026-11-10-full-database-rendering-preservation.md).

The production PDF-only step was also applied to the frozen previously approved
full-item regression PDF, preserving its **2,375 cards / 265 sheets**. All
1,398,932 glyphs pass with zero unmatched characters. Detailed final-PDF crops
of Rhythm-Maker's Drum, Apparatus of Kwalish, Demonomicon of Iggwilv, Queen
Ehlissa's Marvelous Nightingale and all four Sword of Zariel faces were inspected.
All 265 pages pass both complete visual checks at 300 DPI, with maximum quiet
background differences of three pixels in MuPDF and zero in PDFium. The output
is 23,362,752 bytes, SHA-256
`5747d731455bc0d2253c230a17d24d4c35d576a89c922378f2ee98c1d0a0339c`.
This is a PDF transformation
regression against saved exact renders, not a newly generated full-item HTML
catalog. Evidence: `output/srd-fork/full-item-pdf-fill-regression/`.

The six separately approved SRD data flags retain their specific 1,610→1,616
exception. They do not authorize any renderer or installed full-database change.
This PDF result does not certify the unfinished SRD source audit, release,
default-download integration or Android-native export.
