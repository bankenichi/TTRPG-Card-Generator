# Bundled SRD and API 36 delivery

November 10, 2026

Both apps now offer **Use included SRD 5.2.1**. The offline archive is
443,357 bytes and contains 40 unchanged game-data files, plus a clean manifest,
README, attribution and license. Its SHA-256 is
`e7f0fe67bd30f4db125478c0e6cba54046c535a96a60d6594bf37bffebd75524`.
No external database names, links, build inputs or development receipts are
included in distribution metadata. The data repository's current metadata and
builder output use the same clean manifest. Historical Git objects are separate.

Generic repository downloads and ZIP imports remain functional. Existing
libraries are replaced only after an explicit successful import. No renderer,
parser, grouping, fitting, splitting or export implementation changed.

Android targets API 36. Both apps expose a 138-word privacy policy through
Data setup, About & licenses and the workbench footer. `PRIVACY.md` contains
the same text for public hosting and the Play Console privacy-policy URL.

## Verification

- 12 installer tests and 10 HTTP/export boundary tests pass.
- 18 database projection tests pass, including deterministic rebuilds.
- Production HTTP setup succeeds with external networking blocked on both
  platforms. Custom repository and ZIP import paths also pass.
- Every game-data byte matches the reviewed database. A recursive decoded
  JSON/document scan finds no removed external database references.
- All 14 SRD HTML outputs per platform exactly match the previous delivery:
  1,616 cards / 1,488 entries.
- Fresh full-catalog captures on both platforms exactly match their frozen
  counts, sheets, card markup/order, page shell and whole HTML: 12,270 cards /
  10,183 entries / 1,374 sheets. All 38 protected engine/parser files are unchanged.
- Android debug build and actual packaged-resource installation test pass on
  Pixel 9a / Android 15. The APK declares target SDK 36 and contains the exact
  same archive. The privacy page was opened and inspected on the emulator.
- Android 16-specific platform behavior has not been device-tested.

Detailed local receipts are under `output/srd-fork/bundled-delivery/`.

## Remaining Play publication work

The debug APK is for testing. Play publication still requires a correctly
signed release App Bundle, Play Console declarations and the public policy URL.
The previous data fork retains old non-SRD upstream Git history; cleaning its
current metadata does not remove that history. Retire that public distribution
history separately before promoting it. The apps no longer link to that fork.
