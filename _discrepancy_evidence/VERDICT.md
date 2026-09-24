# Verdict

## Reproduced counts (prerelease-content)

### Before dual-dataset fix (combined stub — historical)
| Category | Official | Playtest | Combined (stub) | Sum | Gap |
|---|---:|---:|---:|---:|---:|
| Races | 196 | 95 | 228 | 291 | 63 |
| Classes | 643 | 804 | 1143 | 1447 | 304 |

### After dual-dataset wiring, before raw_dict isolation
| Category | Official | Playtest | Combined (shared raw_dict) | Sum | Surplus |
|---|---:|---:|---:|---:|---:|
| Races | 196 | 95 | 300 | 291 | +9 |
| Classes | 643 | 804 | 1454 | 1447 | +7 |

### After controller isolation fix
| Category | Official | Playtest | Combined (isolated) | Sum | Delta |
|---|---:|---:|---:|---:|---:|
| Races | 196 | 95 | 291 | 291 | +0 |
| Classes | 643 | 804 | 1447 | 1447 | +0 |

## Root cause of surplus (+9 / +7)
Shared `raw_dict` across Official + Playtest passes in one `generate_html` call filled more `_copy` / parent-race content for playtest entities, producing extra page-splits (and one race card only present with shared context). See `SURPLUS.md` for every surplus card. Not silent name|source drops.

## Fix
`card_controller.generate_html_isolated`: when `payload.datasets` has more than one entry, run `generate_html` once per dataset and merge `.page` HTML. `/generate` uses this helper. Engine / renderer / parsers untouched.

## Evidence
- `_discrepancy_evidence/SURPLUS.md`
- `_discrepancy_evidence/verify_after_isolation.json`
- `_discrepancy_evidence/surplus_verify.json`

## Engine touched?
**No.**
