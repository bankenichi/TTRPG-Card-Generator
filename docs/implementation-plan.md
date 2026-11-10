# Review fixes and direct PDF export

The full-sheet raster PDF approach below was rejected after producing a 2.01 GiB catalog. The PDF design and acceptance criteria are superseded by [the compact PDF correction](compact-pdf-plan.md). Other review fixes remain applicable.

The user authorized all fourteen review fixes, a fresh installation test, and print-layout verification. Direct PDF export must preserve the existing card design and physical dimensions.

## Design and acceptance

- Keep the 2.5 by 3.5 inch cards, rotation, Letter sheets, nine slots, margins, colors, and backgrounds. Use the existing HTML/CSS/fit algorithm as the single renderer. Bundle the exact font files and pin Chromium through Playwright; do not introduce a separate PDF layout implementation.
- Export groups of at most five sheets in a background worker, starting a fresh Chromium process for each group and retrying a transient browser failure once, wait for fonts and card fitting, capture lossless 300-DPI RGB sheets, embed those exact pixels in PDF pages, and stream the sheets into the final PDF. Decode every embedded image and compare its SHA-256 against the HTML render before reporting success. Provide progress, a download, useful errors, and a complete PDF. HTML previews load at most 20 sheets with links between batches; repeated SVG assets share CSS definitions.
- Confine HTTP services to loopback; reject foreign Host/Origin requests and unsafe file paths. Restrict served files and generation inputs to intended assets/data/outputs. Sanitize imported HTML while preserving known formatting.
- Stage Git/ZIP imports and prerelease synchronization, validate tree structure, then replace existing data with rollback on failure.
- Resolve source copy modifications/templates/preserve rules, exact class feature levels, playtest lookup dependencies, feat categories, spell classes, legendary budgets, source CRs, and boolean movement correctly. Preserve distinct item variants as separate cards.

## Execution

1. Add regressions for the security/import and fourteen data-content cases; implement shared HTTP/import/copy helpers and the narrow parser corrections.
2. Add pinned PDF dependencies, local fonts, deterministic fitting completion, bounded HTML previews, and a PDF export job API/UI. Add order, sheet-count, overflow, and asset-deduplication checks.
3. Bootstrap a fresh copy with no Python environment, install requirements and Chromium, exercise setup/import/launch, generate representative and large decks, export PDFs, inspect page geometry and rasterized samples, and record evidence.
4. Run all unit/integration checks, inspect the final diff, request an independent code review, and correct material findings. Leave unrelated user files untouched; do not commit or push unless asked.

The existing eight tests and 29 category/mode generation smoke runs are the baseline. Count changes caused by restored content and removal of invalid condensation are expected; content correctness and page/slot integrity are the acceptance criteria.
