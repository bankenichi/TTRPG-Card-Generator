# Full-database rendering preservation — 2026-11-10

The user's current requirement is exact preservation of full-database card
counts, split boundaries, and existing rendering behavior. No renderer, parser,
fitting, splitting, or grouping implementation was changed for the SRD work.
All 38 protected files match their repository HEAD blobs after Git's existing
line-ending normalization.

The read-only capture uses every currently available official/playtest origin
from the actual workbench catalog: 29 requests across 17 categories, with all
filters unrestricted. It fingerprints all 651 JSON files in the installed data
root before and after generation. No installed or custom data is replaced.

| Platform | Entries | Cards | Letter sheets | Fresh output versus its own baseline |
| --- | ---: | ---: | ---: | --- |
| Desktop | 10,183 | 12,270 | 1,374 | Exact complete HTML, ordered card markup and shell |
| Android host generator | 10,183 | 12,270 | 1,374 | Exact complete HTML, ordered card markup and shell |

Android's existing native `load_master_stats` startup call is reproduced using
the same deity source file in an isolated temporary native-files directory.
The earlier host capture without that initialization produced 12,224 cards and
is invalid as an app comparison. It is retained for diagnosis and superseded
by `android-initialized/` and `android-recheck/`.

Cross-platform ordered titles and part numbers match. Existing platform CSS,
source-label formatting, and 460 card body/element differences mean this is
**not** a claim that Android and desktop render identical content or pixels.
For example, Android includes the existing `canHover True ft.` movement output
on Factol Skall, and includes Kyrilla's alternate lair Challenge label. These
existing behaviors were not changed. Exact regression approval compares each
platform with its own frozen output, without normalizing away differences.

Evidence is under `output/srd-fork/full-database-preservation-baseline/`:

- `verification.json`: reconciled counts, ordered titles, protected code and
  existing cross-platform differences.
- `desktop/baseline.json` and `android-initialized/baseline.json`: complete
  ordered card hashes, shell/HTML hashes and input fingerprints.
- `desktop-recheck/baseline.json` and `android-recheck/baseline.json`: fresh
  captures with a passing exact regression receipt against those baselines.

The fork's `tools/capture_full_database.py --baseline <baseline.json>` is a
repeatable gate. It rejects a different platform, input catalog or input data,
then requires identical counts, sheets, every ordered card's full markup,
shell and whole-document hash. It also reports protected-code changes
separately. Five focused tests reject same-count changed splits, reordering,
layout/document changes and invalid comparisons. An output directory separate
from the baseline is mandatory.

The six explicitly approved portrait flags belong only to the separately
generated SRD dataset. Its agreed total is 1,616 cards rather than 1,610. Its
exact inverse restores all 2,136 source records, and both platforms preserve
the other 1,602 cards byte-for-byte. That authorization does not permit changes
to full-database rendering or its installed source files.

These host checks do not replace native-device or final-PDF visual tests.

## Recheck after the explicit preservation requirement

Fresh captures in `desktop-latest-constraint-recheck/` and
`android-latest-constraint-recheck/` both pass against their original frozen
baselines: 12,270 cards, 10,183 entries and 1,374 sheets per platform. All
ordered card hashes, shell and complete HTML hashes are exact, as are the
protected code hashes. All 651 installed JSON inputs remain unchanged. The
five focused preservation tests also pass, including rejection of a changed
split with an unchanged card count.

Any proposed renderer change must pass this full-database comparison on both
platforms. Matching totals alone cannot approve it: changed grouping, splits,
order, card markup or document layout fails the gate. Do not regenerate a
baseline to absorb such a difference. The six separately approved SRD input
overrides do not relax the installed full-database requirement.
