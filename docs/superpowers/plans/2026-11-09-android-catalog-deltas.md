# Android Catalog Delta Implementation Plan

> **For agentic workers:** Execute inline, one cause and verification gate at a time. Preserve the checkpoint commits before changes.

**Goal:** Match desktop card identities and counts for all 29 category/source cases and the complete mixed selection, without changing layout or splitting algorithms.

**Architecture:** Use the verified desktop behavior as the reference for narrowly scoped Android grouping and source-reference corrections. Keep the Android renderer's existing HTML/CSS, text measurement, splitting and fit script intact. Isolate controller input passes only where the existing desktop controller already does so.

**Tech Stack:** Python, unittest, Chaquopy/Android instrumentation, existing catalog audit, Playwright screenshot comparisons.

**Spec:** docs/reviews/2026-11-09-android-card-count-parity.md and the user's explicit authorization to fix those deltas carefully after checkpointing both repos.

## Global Constraints

- Checkpoint desktop `2db9f000709394b13b9b5f09717e699c8204dd68` and Android `06070d6f1885f72aaad6aac4178c4d3ce47dad79` are pushed and remotely verified before fixes.
- Desktop engine/parsers remain unchanged.
- Android `flatten_entries`, `estimate_lines`, `estimate_row_lines`, `split_item_by_lines`, parser_utils.py and generated HTML/CSS/fit script remain unchanged.
- Item-family grouping stays unchanged; the full item catalog remains 2,375 cards / 2,213 items / 265 sheets.
- No PDF codec, icon, UI design, dependency, or unrelated parser cleanup in this pass.
- Retain the development app and imported data after instrumentation.

### Task 1: Reproduce and freeze boundaries

- [x] Add regression checks for non-item elemental collisions, class feature level references, source-specified monster headers, and mixed-category controller isolation.
- [x] Pin preservation checks to the pushed Android checkpoint, comparing unapproved function and renderer sections via AST/source rather than replacing hash expectations.
- [x] Generate pre-fix Android reference HTML for the full item catalog and representative unaffected short, long and table cards.

### Task 2: Correct only demonstrated input/grouping causes

- [x] In Android card_engine.py, add the existing desktop non-item type guard around family-name extraction and grouping keys; leave item grouping branches byte-identical.
- [x] In Android parser_classes.py, match feature-reference level alongside the existing name/class/source fields at the three established lookup sites.
- [x] In Android parser_monsters.py, use the source's legendary header/budget instead of invented common prose, only after verifying this explains the named split differences.
- [x] In Android card_controller.py, generate each dataset entry separately and concatenate unchanged pages in requested order, matching desktop controller isolation. Preserve style resources from every pass.
- [x] After each correction run its failing regression check and compare generated catalog evidence before adding another fix.

### Task 3: Verify whole-catalog parity and preservation

- [x] Run all 29 category/source cases and all categories together on the actual Android emulator.
- [x] Require exact card counts, entry counts, and emitted card-title multisets per case; require 12,270 cards / 10,183 entries for the complete selection.
- [x] Require the item-catalog source output to match its pre-fix Android document, including split boundaries and HTML/CSS.
- [x] Compare all unaffected card content from before/after audits and raster-check representative unchanged cards at the same viewport with bundled fonts.
- [x] Run desktop tests, Android build/instrumentation, and preservation guards.
- [x] Update audit documentation, commit only this fix scope, push both branches as applicable, and verify local/remote hashes.
