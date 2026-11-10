# Scribe Workbench Implementation Plan

> For agentic workers: execute this plan task-by-task in the current session. Preserve the approved renderer boundaries.

**Goal:** Deliver the approved desktop workbench and engraved card-type icons, then Android UI/feature parity.

**Architecture:** A shared, self-contained HTML/CSS/JavaScript controller is rendered by a small Python template adapter. Desktop HTTP and Android native integration adapt platform capabilities; generated card documents remain isolated and unchanged. The continuous viewer lazily mounts individual unmodified sheets, while existing PDF assembly consumes those sheet files.

**Tech Stack:** Python standard library HTTP/template adapters, vanilla HTML/CSS/JavaScript, SVG, existing Playwright/pypdf desktop export; Kotlin/Compose/WebView/Chaquopy with native Android document export.

**Spec:** docs/superpowers/specs/2026-11-09-scribe-workbench-design.md

## Global Constraints

- Both card_engine.py files and all parser_*.py files must match recorded SHA-256 baselines.
- Classes retains the existing node-and-branch symbol. Retouch only; no shield replacement.
- Card-type assets retain 80x80 viewBox and alpha-mask geometry; backgrounds, watermarks, backs, and dividers are unchanged.
- Filter payload semantics, official/playtest isolation, card dimensions, splitting, and fitting stay unchanged.
- Desktop is completed and verified before Android integration. Preserve existing Android Studio workspace edits.

### Task 1: Shared controller and desktop shell

Files: workbench_ui.py; ui/workbench.html.template; ui/workbench.css; ui/workbench.js; ui/shell.css; ui/setup.html.template; ui/setup.js; ui/installer.html.template; ui/installer.js; card_controller.py; launcher.py; gui_installer.py.

Interfaces: render_workbench(datasets_json, svg_options_json, platform='desktop') -> str; render_setup(ready, platform='desktop', in_generator=False) -> str; render_installer() -> str. Existing POST payload schemas remain unchanged. JSON generation responses add card_count, item_count, type_counts, sheet_count, preview, and kind when Accept requests application/json; legacy HTML remains supported.

- [ ] Implement shared template adapter with safe inline bootstrap JSON and local UI styles/scripts.
- [ ] Build searchable category rail, focused filters, appearance controls, sticky summary, persistent selections, generation/export states, keyboard focus, phone layout, and accessible status.
- [ ] Preserve exact payload behavior for empty/all filters and official/playtest origin files; check resulting payloads against the old controller logic.
- [ ] Route desktop setup/installer through the same visual shell; keep data/installation operations intact.
- [ ] Exercise desktop and phone widths, SVG uploads, reset/restore, generation, backs, export, and error recovery in the shared browser.

### Task 2: Continuous viewer and immutable export sheets

Files: deck_output.py; ui/viewer.html.template; ui/viewer.css; ui/viewer.js; test_http_and_pdf.py; test_workbench.py.

Interface: write_batches(path, sheets_per_batch=20) keeps its callable signature and returns files/sheet_count plus viewer metadata. The files list contains private sheet documents; path becomes the continuous UI viewer. render_pdf continues to consume manifest files in order.

- [ ] Split only outer .page blocks and write each original head/sheet/tail without modifying renderer markup/styles/scripts.
- [ ] Use placeholder sheets and a bounded IntersectionObserver iframe window; show one continuous deck without batch navigation.
- [ ] Preserve original 856x1096 screen document viewport and scale only the outer frame for phone/desktop display.
- [ ] Verify reassembled source pages equal the original pages and PDF source order remains unchanged.

### Task 3: Engraved icon set and coverage

Files: icons/*.svg (card-type glyphs only); icons.py; icon_catalog.json; test_icon_contract.py.

Interfaces: existing SVG basenames and resolve_card_icon_name signature/precedence remain; add explicit missing dtype aliases and assets. Classes keeps its original graph identity.

- [ ] Redraw current card-type glyphs with consistent engraved outlines and solid accents; preserve transparent safe bounds and no filter/raster effects.
- [ ] Add optionalfeatures.svg and explicit monster, card, disease/status, upgrade, language/deity/deck alias coverage.
- [ ] Add distinct missing class/subtype glyphs where the supported catalog requires them; keep existing unrelated resolution rules.
- [ ] Inspect all glyphs at 34px/14px and in actual cards. Test XML safety, viewBox, asset existence, alias coverage, and unchanged non-icon assets.
- [ ] Re-run renderer hashes, full desktop tests, card text/layout parity excluding approved icon alpha, and representative final PDF raster checks.

### Task 4: Android parity outside its renderer

Files: Android app/src/main/python/workbench_ui.py and ui/* (shared copies); Android icons assets/mappings; Android card_controller.py, android_server.py, dataset_service.py; native MainActivity.kt and focused integration classes; app/build.gradle.kts and sharing resources as required.

Interfaces: the same frontend bootstrap/payload schemas; Android export uses a native platform adapter and emits the same job progress/download state shape. Dataset import uses app-private storage and staged replacement. Native document save/share is exposed only for validated generated outputs.

- [ ] Bring shared UI, icon assets, catalog metadata, source-label formatting, and continuous viewer to Android without copying or editing the engine/parsers.
- [ ] Preserve Android engine input semantics and adapt new content modes outside it; stream ZIP imports off the UI thread with safe staging and progress callbacks.
- [ ] Implement bounded one-sheet WebView-native PDF jobs, merge output with pypdf, and integrate native save/share/file selection.
- [ ] Build debug APK and run unit/instrumented checks. Open Pixel_9a through device tools and exercise import, filtering, generation, preview, backs, PDF save/share, rotation/back navigation, and errors.
- [ ] Assert both renderer trees remain byte-identical and the shared UI/assets match. Persist test/build/PDF evidence and APK paths.
