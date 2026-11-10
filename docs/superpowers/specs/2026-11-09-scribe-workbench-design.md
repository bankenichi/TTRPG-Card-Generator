# Approved Scribe workbench and engraved icon design

Approved by the user: A / Scribe workbench with stronger engraved icons, subject to the individual icon exceptions below. Both renderer/parser trees are frozen against output/ui-refresh/renderer-baselines.json.

## Order and boundaries

1. Desktop setup, installer, generator, and continuous deck viewer.
2. Review and refresh the card-type SVG set, adding missing assets and explicit type coverage.
3. Bring Android UI and user workflows to parity using platform adapters.

Both existing rendering engines and domain parsers are frozen. Android will not receive a replacement desktop renderer. Existing selection/filter semantics, grouping, split rules, sizing, fitting, fonts, and rendered content stay under their current contracts. The separately approved icon changes are limited to glyph assets and mappings; their canvas and mask contract remain the same.

## Approved desktop direction

Scribe's workbench: a warm neutral surface, forest-green actions, a characterful serif display face, and a restrained sans-serif for controls. A searchable category rail, focused filter panels, persistent selection summary, and clear generation/export status replace the long checkbox wall. Empty filters retain their existing unrestricted meaning. Card counts are shown after generation; the UI does not fabricate live count estimates.

The alternative directions are Night workshop (dark and compact) and Clean ledger (neutral and dense). The mockups illustrate the intended structure rather than implementing new backend behavior.

## Flow

Import/manage data -> choose categories and filters -> adjust appearance if desired -> generate -> continuous preview or export. The viewer loads unchanged rendered sheets progressively without visible batch navigation. Export keeps one complete downloadable PDF and actual progress. Existing paper and card sizes remain unchanged.

## Icons

Audit covers all 37 current card-type glyphs, every supported category/subtype mapping, silhouette clarity, consistent visual weight, safe bounds, and legibility at compact sizes. Known gaps include the missing optionalfeatures.svg and the monster/card/disease/upgrade fallbacks. Approved replacements use the existing 80x80 viewBox, transparent background, monochrome alpha geometry, and no filters or embedded raster images. Backgrounds, watermarks, dividers, and card backs are excluded.

## Android

Reuse the approved responsive UI and icon assets, with native dataset/file import, document saving/sharing, lifecycle-safe progress, and an Android export adapter. Verify each platform against its own unchanged renderer baseline. Native Android export must be tested against its rendered sheets; the desktop Chromium subprocess is not portable to Android. Existing Android Studio workspace settings remain untouched.

## Verification

Protect both renderer/parser trees with recorded SHA-256 baselines. Test UI keyboard/focus behavior, phone/desktop layouts, filter payload parity, SVG uploads, continuous loading, progress, complete PDF downloads, and setup/recovery states. Re-run the existing desktop suite and rendered-card comparisons. Build Android and exercise import/generation/preview/export on the available Pixel_9a emulator through the device tools.

## User icon revisions

Restore the exact original Barbarian, Bard, Bestiary, Classes, Druid, Feats, Psionics, Races, Rogue, Skills, and Warlock assets. Classes keeps its original stroke weights as well as its original graph. Keep the new Fighter sword and remove its two flanking arcs. Paladin retains the shield with a different central emblem instead of another sword. Redesign Sidekick; redesign Wizard around a staff and book. The current revised proposals use a lantern for Sidekick and a radiant diamond within Paladin's shield.

The user approved the revised Fighter, Paladin, and Sidekick assets and Wizard option A (open book with an orb staff). Those choices are final for this pass.
