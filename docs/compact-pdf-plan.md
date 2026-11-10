# Compact PDF correction

> Historical plan. The five-sheet native method and earlier renderer changes described below were superseded. See [current verification](review-fixes-and-verification.md) for the isolated-sheet exporter and the single authorized AU Nightingale correction.

The full-sheet raster design failed the practical requirement: a 2.01 GiB catalog cannot be treated as a successful printable export. Replacing it is within the already authorized export work.

## Design

Use Chromium's native PDF renderer on the same fitted HTML, with screen media, bundled fonts, exact colors, Letter dimensions, zero extra margins, and scale 1. Each five-sheet job runs in its own short-lived Python/Chromium process; up to four jobs run concurrently according to CPU count. This releases renderer/parser memory at each process exit. Retain completed parts and logs on failure. Deduplicate identical PDF resources to a fixed point both within jobs and when merging jobs; embed repeated texture images once. Text stays searchable and vector sharp. Retain optional smaller print downloads, but the complete catalog PDF must be usable on its own.

Alternatives considered: JPEG/lower-DPI full-sheet images reduce size by degrading text; lossless screenshot layers still repeat content pixels and keep text rasterized. Native vector output with shared resources preserves the original HTML layout and produces a compact document. It cannot promise byte-identical screenshot pixels because PDF and browser glyph rasterizers differ. Validation must explicitly distinguish unchanged layout/content from raster equality.

## Implementation and acceptance

1. Prototype representative native PDFs including Apparatus of Kwalish, Sword of Zariel, long artifacts, tables, first/last pages; inspect PDF resource duplication and rendered pages.
2. Replace `pdf_export.py` screenshot embedding/stream merger with native PDF generation and fixed-point resource deduplication. Retain input snapshots, retries, overflow/card geometry checks, background jobs, and safe HTTP download boundaries.
3. Record each card's HTML text and word positions before printing. Assert printing does not change the fitted DOM. Independently inspect the PDF text, positions, physical page bounds, and rendered samples. Never expose the previous `pixel_identical` claim for vector output.
4. Add regression tests that repeated nested image/mask resources share objects and that merged PDFs keep content, ordering, and dimensions. Update the controller status, README, and verification report.
5. Export all 322 catalog sheets as a complete file in the tens of MiB; inspect every sheet for text/position integrity and rasterize the difficult samples. Test PDF loading in the shared browser and verify a download. Run the complete regression suite. Leave changes uncommitted and preserve unrelated files. The initial 25 MiB estimate was slightly low: the final lossless-resource/vector-text document is 27.3 MiB. Browser loading and complete content/layout verification are the usability and fidelity gates.

The first whole-catalog native run correctly stopped at sheet 313: Priest's Pack had a long source code clipped in its HTML header. The old overflow sweep checked only card bodies. The shared metadata CSS now wraps long tokens within shrinkable flex spans, and the export guard also checks headers and footers. The corrected sheet independently passes every text/symbol and glyph-position check. All catalog HTML is being rendered again with this shared correction.

The user subsequently requested shorter UA labels while expressing reluctance to change the rendering engine. `source_labels.py` therefore applies the data's supplied abbreviations to source spans after generation in the controller, with full source titles and original IDs in tooltips. Card sizing, splitting, fitting, selection, and source IDs are unchanged. The complete catalog was rendered and independently checked again after this formatting pass.
