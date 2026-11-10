# SRD download delivery

The pruned fork and its data-only release are published:
<https://github.com/bankenichi/5etools-srd/releases/tag/srd-5.2.1-r1>.
Both app setup flows now offer the pinned SRD download first. Existing installed
libraries are not switched automatically; custom repository/ZIP choices remain.
Desktop manual SRD imports skip prerelease enrichment as well.

After implementation and publication, both actual setup HTTP endpoints downloaded
the public archive into isolated fresh roots. All 40 data files match the fork;
no prerelease content was merged. Both generators produced 1,616 cards / 1,488
entries, with all 14 HTML files per platform byte-identical to candidate 24.
The ten runtime installer/rollback tests pass.

Fresh full-database captures on both platforms retain 12,270 cards / 10,183
entries / 1,374 sheets, including exact ordered card markup, splits, shell and
whole HTML. All 38 protected renderer/parser files and all 651 installed JSON
inputs remain unchanged. The existing final PDF certificate remains applicable
to the identical HTML; this is not a newly rendered PDF or native PDF claim.

Android `assembleDebug` succeeds. The updated APK was installed with data kept,
and the native UI showed the existing library ready plus the new SRD download
option under Manage data source. The existing device library was not replaced.
Fresh public-download tests used each app's production HTTP handlers on the host.

Evidence and the APK are under `output/srd-fork/delivery/`.

## Historical foundation notes

The notes below predate delivery and retain the original implementation context.

`verified_srd.py` is identical in desktop and Android. It performs no work on
import and is not connected to UI/endpoints or a release configuration yet.
Source verification and publication must finish before the SRD default is
enabled. Existing installed catalogs, custom imports and current defaults are
unchanged.

The helper streams an HTTPS archive, requires an externally pinned SHA-256,
checks SRD version/source/PDF identity, checks the full data-file manifest and
checksums, requires attribution/license documents, and rejects unexpected
payloads. It stages and validates the entire package before calling the existing
atomic replacement routine. It never invokes playtest enrichment.

This separate path is necessary because desktop's current generic repository
and ZIP imports call `sync_prerelease_content`. The future built-in SRD route
must call this verified helper directly. When integrating manual SRD imports,
also preserve the restriction rather than silently enriching the archive.
Custom full-database imports must keep their existing behavior.

Independent review reproduced two gaps in the first helper version: unexpected
siblings outside a selected wrapper escaped validation, and an HTTPS redirect
could issue an HTTP request. Both are fixed. Every extracted file must belong
to the selected package, and the redirect handler rejects/cleans up a downgrade
before following it. The regression suite uses a real urllib redirect chain
with in-memory transport, without external network access.

Ten tests pass against each Python copy. They cover exact fresh/wrapped install
bytes, requested-destination scope, archive/file integrity, malformed JSON,
unsafe/duplicate paths, wrapper siblings, HTTPS redirects, interrupted download,
and preservation of existing data on failure. Fixtures are synthetic installer
tests, not SRD source certificates or final app/device tests.

A fresh candidate-23 probe now installs the current 44 package files exactly
through both helper copies in separate isolated roots. Each generator produces
1,616 cards / 1,488 entries and all fourteen HTML files per platform are
byte-identical to its original candidate output. The private archive is 880,333
bytes. Ten runtime-only tests also pass against each helper copy with `-s`.
Existing full-catalog files and all 38 protected parser/renderer files remain
unchanged. Evidence is under `output/srd-fork/candidate-23-install-probe/`.
These are host helper/generator checks, not real public-network, setup-UI or
native-device checks. The archive remains an unpublished fixture while source
verification and publication are incomplete.

Candidate 24 repeats the same fresh-install check after the single Druidic
Focus class-list correction. All 44 package files and all 28 HTML outputs again
match exactly, retaining 1,616 / 1,488 on both platforms. Its unpublished fixture
is 881,650 bytes; current evidence is under
`output/srd-fork/candidate-24-install-probe/`. The helper code remains unchanged.

The earlier private probe installed candidate-18 data into
two isolated roots under `output/srd-fork/candidate-18-install-probe/`. All 44
package files match their inputs byte-for-byte. Both existing generators produce
1,610 cards / 1,488 entries from those installs, with equal counts and titles.
The unpublished 870,099-byte archive is a test fixture, not a release for users.

Still required: finish source/omission verification; publish the data-only
release; pin its real URL/hash; wire the recommended SRD option into both setup
flows while preserving ready/custom state; test real network install and
Android UI/build/device behavior; complete final full-catalog PDF verification.
