# Included SRD library

Fresh setup offers **Use included SRD 5.2.1** first. The library is packaged
with the app and works offline. Custom GitHub repository downloads and ZIP
imports remain available. An existing library is kept until you explicitly
choose to replace it.

Both apps include the same small data-only archive (about 433 KiB), pinned
by SHA-256 in `verified_srd.py`. Each of its 40 JSON files is checked against
the manifest before installation. Failed verification preserves existing data.
The package contains 2,136 SRD records plus its manifest, README, attribution
and data license. No external database, repository URL or upstream metadata is
included. Official SRD source citations and attribution are retained.

To reproduce the bundle from reviewed data, use
`tools/package_bundled_srd.py --source <reviewed-data-folder> --out <archive.zip>`
in the desktop repository. It copies game data without changing any bytes.

Renderer, fitting, grouping and splitting code are unchanged. The previously
approved six SRD-only orientation settings remain in the data. The SRD notice
appears once in About & licenses; the short privacy policy is available there,
in Data setup, and in the workbench footer.
