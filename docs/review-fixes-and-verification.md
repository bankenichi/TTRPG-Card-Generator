# PDF export verification - 2026-11-09

This report supersedes the earlier five-sheet native export reports and their catalog counts. Those files contained mask artifacts despite passing text checks.

The current controller-generated catalog contains **2,213 grouped items, 2,375 cards, and 265 Letter sheets**. The complete PDF is **23,326,715 bytes (23.3 MB)**. All 76 tests pass with no failures, errors, or skipped tests.

## Surgical renderer boundary

The sole new card-layout change is restricted to the exact name **Queen Ehlissa's Marvelous Nightingale**, source **AU**, with the existing two-column/two-chunk layout. Complete preceding sections move into the spare first column so the spell table fits. Entry order and one-card output are preserved. The shared splitter, thresholds, CSS, fitting script, and text helper remain unchanged.

The full controller catalog was compared with the untouched reference engine and parsers, using the same source-label formatting pass. **Only card 1296, sheet 144, changes; the other 2,374 cards have identical HTML.** A source other than AU and another item name do not trigger the exception. No other cards have visible-content overflow in the complete scan.

Earlier authorized grouping safeguards remain: ordinary bonus families still combine; different printed bonus rules are retained; non-items cannot enter item-family grouping. Rhythm-Maker's Drum remains one card, Apparatus of Kwalish two, Demonomicon of Iggwilv two, and Sword of Zariel four.

## Export correction

Chromium can paint opaque mask rectangles when a native print call spans several physical sheets. The same failing five-sheet sample passes both independent PDF rasterizers when each sheet is printed separately. The exporter now enforces **one physical sheet per short-lived worker job**, with at most four concurrent workers, then merges and deduplicates resources into **one complete PDF**. No automatic split PDF downloads are generated. Vector text and lossless graphics are retained.

The exporter serves the original Open Sans import from bundled fonts and reruns the original fitting callback after fonts are ready. Its overflow guard checks actual flow blocks, including bullet/indented divs and table borders, rather than counting empty trailing margins. The document parser also accepts the original script-free card-back HTML; the back renderer was not changed.

## Final-file verification

All checks run against the assembled PDF, not just worker parts:

- **265/265 sheets** pass graphics comparison at **300 DPI** in both MuPDF and PDFium.
- **1,398,932 characters** match; **zero unmatched glyphs**. Maximum advance error is **0.10385 CSS px** (limit 0.2); cross-axis font-box error is **1.9754 CSS px** (limit 2).
- Every saved fitted layout matches a fresh, hash-bound scan of the exact controller HTML. No source-content overflow is reported.
- Background checks exclude three-pixel sharp-edge neighborhoods and flag channel differences above 16. An additional 8-pixel tile contrast check catches covered text that extracted-text checks cannot detect. Regression tests reject both solid colored rectangles and covered text. These checks permit antialiasing differences; they do not claim literal pixel identity.
- All pages were inspected in contact sheets, with detailed crops for long tables/artifacts, including the requested difficult items. Default card backs also pass both rasterizers.

The engine stress export freshly printed all 264 packed sheets with normal guards. The controller retains the pre-existing official/playtest sheet boundary, producing 265 sheets for the same cards. Its first 251 sheets are identical to the fresh stress output and were reused; the remaining 14 controller sheets were rendered separately. **All 265 final controller sheets were checked again after assembly.**

The seven obsolete tests had asserted engine changes that were rolled back to preserve rendering. They now exercise retained helpers and supported original behavior: standalone prose sanitization, import-path protection, prerelease copy materialization, loaded-parent subrace inheritance, and original title/table/badge formatting. They do not assert that removed engine features remain installed. No tests were skipped or marked as expected failures.

## Evidence

- [Complete PDF](../output/pdf-revalidation/controller/entire-item-catalog.pdf)
- [Combined verification summary](../output/pdf-revalidation/final-verification.json)
- [Controller card parity](../output/pdf-revalidation/controller/generation.json)
- [Text and glyph positions](../output/pdf-revalidation/controller/glyph-verification.json)
- [MuPDF graphics](../output/pdf-revalidation/controller/mupdf-visual-verification.json)
- [PDFium graphics](../output/pdf-revalidation/controller/pdfium-visual-verification.json)
- [Hash-bound layout and overflow scan](../output/pdf-revalidation/controller/bound-layout-preflight.json)
- [Tests](../output/pdf-revalidation/tests.json)

PDF SHA-256: `64030b2161217d18404557e0ca46f3076b1ea916fc0cb6a416d12cbda955c891`.
