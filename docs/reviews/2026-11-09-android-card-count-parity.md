# Desktop / Android card-count audit

## Result

**The deltas are now fixed and verified on the Android emulator.** All 29 independent category/source selections and the complete mixed selection match desktop in card count, entry count, and emitted card-title multiset. Both generate **12,270 cards from 10,183 entries** with every category selected.

The full item catalog remains **2,375 cards / 2,213 items / 265 sheets**. Its four actual-device audit HTML documents are byte-identical before and after these fixes. Seven representative item sheets also have identical text sizes, geometry, and screenshot pixels, including sheets containing long descriptions, tables, artifacts, and the named stress cases.

Both repos were committed and pushed before changes: desktop `2db9f00` (`prerelease-content`) and Android `06070d6` (`master`). The fixes only add Android's existing desktop non-item grouping guard, feature-reference level matching, source-correct legendary header/budget handling, and one controller pass per dataset entry. Desktop engine/parsers were unchanged. Android's layout HTML/CSS, fitting script, text measurement, splitting helpers, item-family grouping branches, and unrelated parser sections are pinned to the pushed checkpoint by regression tests.

The sections below preserve the original audit findings before the fixes.

The audit generated all 17 categories, each available official/playtest selection separately (29 cases), and all categories together. Android generation ran in the installed app on the Pixel_9a Android 15 emulator through Chaquopy, using its production controller and renderer. Desktop used its production controller. Filters were unrestricted on both.

All 638 installed source JSON files are byte-identical to the desktop dataset. Both protected renderer/parser trees still match the SHA-256 baselines recorded before the UI refresh. The shared splitting/estimation helper ASTs are identical across platforms. No renderer or parser was changed for this audit.

## Item catalog: matching before and after

| Selection | Desktop cards | Android cards | Items on each |
| --- | ---: | ---: | ---: |
| Official | 2,264 | 2,264 | 2,104 |
| Playtest | 111 | 111 | 109 |
| Both | 2,375 | 2,375 | 2,213 |

Every emitted item-card title and its multiplicity matches. The combined production controller output has 265 sheets on each platform. The final controller isolates each dataset request directly, so official/playtest separation no longer depends on comparing Android path aliases.

## Original independent selections with different counts

| Selection | Desktop cards | Android cards | Android delta |
| --- | ---: | ---: | ---: |
| Bestiary — official | 4,823 | 4,809 | -14 |
| Classes — playtest | 800 | 804 | +4 |
| Decks — official | 385 | 384 | -1 |
| Psionics — official | 52 | 49 | -3 |
| Races — official | 200 | 196 | -4 |
| Spells — official | 600 | 596 | -4 |

The other 23 independent selections have equal counts. Of all 29 independent cases, 17 also have identical title multisets. Twelve have title differences, including the six count mismatches above.

With **all categories selected in one request**, desktop generates **12,270 cards from 10,183 entries**; Android generates **12,259 cards from 10,158 entries**. This is a separate case: Android's existing controller pools official categories into one engine pass, while desktop isolates each dataset entry. Its result must not be inferred by summing individual category counts.

## Located causes and examples

- Android still applies item-family elemental grouping to non-item entities. The desktop already has a type guard. Examples include merged elemental creatures, `Mastery of Air/Fire/Force/Water`, `Wall of Fire/Force/Water`, and elemental Genasi. Even single variants can acquire labels such as `Spray (Poison Or Poison)`.
- The Classes parsers differ in feature-reference level matching. Playtest Artificer produces 5 cards on desktop and 7 on Android; Expert Sidekick produces 4 versus 5; Warrior Sidekick produces 3 versus 4. The splitting helper itself is unchanged: the enriched content supplied to it differs.
- The Bestiary parsers differ in legendary-action header and related source handling. Tiamat produces 3 cards on desktop and 2 on Android; Draconic Shard produces 2 versus 3. These differences also predate the UI refresh.
- Equal totals are insufficient: Bastions, Feats, Optional Features, Vehicles, and playtest Spells contain title differences despite matching aggregate card counts.

The user subsequently authorized narrowly fixing these deltas. The corrected source content now feeds the same untouched splitting functions. No renderer replacement or layout/fitting change was made.

## Evidence and rerun

- `output/ui-refresh/catalog-delta-fix/verified-deltas.json`: final 30-case native parity check and byte-identical item source checks.
- `output/ui-refresh/catalog-delta-fix/device/`: final actual-device reports and emitted title multisets.
- `output/ui-refresh/catalog-delta-fix/render-preservation/verification.json`: seven exact before/after screenshot comparisons. The harness explicitly loads all bundled font faces and uses fresh pages to avoid font/cache timing differences between repeated navigations.
- Android `tests/test_catalog_deltas.py`: focused behavior checks and strict checkpoint preservation guards.
- Android `FullCatalogParityTest`: now asserts all 30 cases against the checked-in desktop reference fixture, rather than only collecting results.

Original pre-fix evidence:

- `output/ui-refresh/catalog-parity/verified-catalog-parity.json`: complete count comparison, every differing title, installed dataset file hashes, and protected-tree checks.
- `output/ui-refresh/catalog-parity/{desktop,mobile}/catalog-counts.json`: production generation results for each case.
- Corresponding `*.titles.json` files: complete emitted title multisets.
- `output/ui-refresh/count-parity/mobile-counts.json`: item-controller check including 2,375 cards / 2,213 items / 265 sheets.
- Android `CatalogCountParityTest`: item totals and sheet count pass.
- The original Android `FullCatalogParityTest` only recorded all cases. The updated test above now fails on any count, entry-count, or title-multiset difference.

Run instrumentation with `-Pandroid.injected.androidTest.leaveApksInstalledAfterRun=true` so the development installation and imported dataset are retained. Compare the recorded reports rather than treating the instrumentation task's exit status as proof of parity.


## Final checks

- Desktop: 87 tests pass; its renderer/parser tree remains at the pre-fix checkpoint.
- Android: 10 host regressions and two connected instrumentation tests pass.
- All 30 production generation cases match the desktop fixture in counts and complete emitted title multisets.
- All four actual-device item HTML outputs are byte-identical to the pre-fix outputs.
- Seven representative item-sheet raster pairs have zero differing pixels after deterministic font preparation.
- Independent read-only review found no blocking issues and separately verified merge edge cases, preservation guards, recorded device results, and the raster pairs.
- Existing local IDE changes, generated decks, Python caches, and unrelated proof/walkthrough files were preserved outside both commits.
