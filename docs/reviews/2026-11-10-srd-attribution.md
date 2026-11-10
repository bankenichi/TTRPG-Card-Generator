# SRD attribution page

The required attribution is copied from page 1 of the official English SRD
5.2.1, available through <https://www.dndbeyond.com/srd>. Official PDF SHA-256:
`8974902d109d6e63672d7c490bde9ccf052410503d9cfa768237154fbc5e3d87`.

One shared About & licenses page at `/about` contains the complete prescribed
statement, including the official SRD and CC BY 4.0 legalcode links. Quiet links
from the workbench footer and data setup reach that one page. The statement is
not repeated in those views, on cards, in the deck viewer, or in PDF output.

The desktop and Android copies of `local_http.py`, `workbench_ui.py`, and the
three affected HTML templates are byte-identical. Card engine, parser, fitting,
and splitting files have no changes in this work.

Validation on 2026-11-10:

- Ten desktop workbench/browser and HTTP-boundary tests pass. They check the
  complete exact attribution string, one occurrence, navigation, phone overflow,
  absence from the viewer, and successful HTTP delivery.
- Android `:app:assembleDebug` succeeds. Updated debug APK installed with `-r`,
  preserving the existing full dataset. Pixel 9a / Android 15 navigation through
  Data setup -> About & licenses displays the complete statement once, with
  wrapping links and a working app back link.

This attribution change does not certify the unfinished SRD data projection.
The SRD-only fork/default-download goal remains active until its separate
source-fidelity, installation and publication gates pass.
