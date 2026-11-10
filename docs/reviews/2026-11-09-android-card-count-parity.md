# Desktop / Android card-count audit

## Result

**Full parity does not yet hold.** The entire item catalog matches, but six independent category/source selections have different card counts. Equal aggregate counts also conceal different card identities in several other categories.

The audit generated all 17 categories, each available official/playtest selection separately (29 cases), and all categories together. Android generation ran in the installed app on the Pixel_9a Android 15 emulator through Chaquopy, using its production controller and renderer. Desktop used its production controller. Filters were unrestricted on both.

All 638 installed source JSON files are byte-identical to the desktop dataset. Both protected renderer/parser trees still match the SHA-256 baselines recorded before the UI refresh. The shared splitting/estimation helper ASTs are identical across platforms. No renderer or parser was changed for this audit.

## Item catalog: matching

| Selection | Desktop cards | Android cards | Items on each |
| --- | ---: | ---: | ---: |
| Official | 2,264 | 2,264 | 2,104 |
| Playtest | 111 | 111 | 109 |
| Both | 2,375 | 2,375 | 2,213 |

Every emitted item-card title and its multiplicity matches. The combined production controller output has 265 sheets on each platform. The Android controller recognizes canonical Android path aliases (`/data/data` and `/data/user/0`) when distinguishing the two source passes; this does not change card rendering or splitting.

## Independent selections with different counts

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

These protected grouping/parser differences remain unchanged. This audit is evidence of a parity gap, not an approval to replace either renderer or alter splitting.

## Evidence and rerun

- `output/ui-refresh/catalog-parity/verified-catalog-parity.json`: complete count comparison, every differing title, installed dataset file hashes, and protected-tree checks.
- `output/ui-refresh/catalog-parity/{desktop,mobile}/catalog-counts.json`: production generation results for each case.
- Corresponding `*.titles.json` files: complete emitted title multisets.
- `output/ui-refresh/count-parity/mobile-counts.json`: item-controller check including 2,375 cards / 2,213 items / 265 sheets.
- Android `CatalogCountParityTest`: item totals and sheet count pass.
- Android `FullCatalogParityTest`: records all cases on the device. Its successful execution means evidence collection completed; it does **not** mean platform parity passed.

Run instrumentation with `-Pandroid.injected.androidTest.leaveApksInstalledAfterRun=true` so the development installation and imported dataset are retained. Compare the recorded reports rather than treating the instrumentation task's exit status as proof of parity.
