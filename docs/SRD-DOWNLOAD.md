# Default SRD library

Fresh setup offers **Download SRD 5.2.1** first. It downloads the data-only
[SRD release](https://github.com/bankenichi/5etools-srd/releases/tag/srd-5.2.1-r1)
without requiring Git or a repository URL. Custom repository and ZIP imports
remain available below it. Existing installed libraries are not downloaded
over or switched automatically.

The archive is pinned by URL and SHA-256 in `verified_srd.py`. Every data file
is checked against its manifest before installation. Failed downloads or
verification preserve the current library. SRD imports do not fetch or merge
prerelease/playtest content.

The pruned source repository is
[bankenichi/5etools-srd](https://github.com/bankenichi/5etools-srd). It contains
40 data JSON files and 2,136 records. The 881,728-byte release archive contains
only data, manifest, attribution, data license and README.

Desktop and Android use the same release and checksum. The existing renderer,
fitting, grouping and splitting implementations are unchanged. The previously
approved six SRD-only orientation settings remain in the data. The app's SRD
notice is in About & licenses, once per app.
