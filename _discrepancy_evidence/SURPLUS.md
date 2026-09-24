# Combined card-count surplus (Official+Playtest dual-dataset)

## Root cause
When Official and Playtest were submitted as two `datasets[]` entries in **one** `generate_html` call,
`card_engine.generate_html` kept a **shared `raw_dict`** across both passes (and shared `all_raw_global` for enrich).
Playtest entities that `_copy` / reference official parents then resolved with more text than in a playtest-only run,
which produced **extra page-splits** (and one race card that playtest-alone dropped for empty/unresolved content).

This is **not** duplicate `name|source` entities. Isolating each dataset into its own `generate_html` pass
(controller `generate_html_isolated`) makes Combined card count equal Official + Playtest.

Engine / renderer / parsers were **not** modified.

## Races
- Official: **196**
- Playtest: **95**
- Sum: **291**
- Combined BEFORE (shared raw_dict): **300** (surplus **+9**)
- Combined AFTER (isolated passes): **291** (delta vs sum **+0**)
- Missing vs union after fix: **0**

### Every surplus card before fix (17)
| Name | Source | Type | Page-split | Reason |
|---|---|---|---|---|
| Elf (Mark of Shadow) 1/2 | UADRAGONMARKS p.6 | Subrace | 1/2 | extra_page_split_from_shared_raw_dict |
| Elf (Mark of Shadow) 2/2 | UADRAGONMARKS p.6 | Subrace | 2/2 | extra_page_split_from_shared_raw_dict |
| Half-Orc (Variant; Mark of Finding) 1/2 | UADRAGONMARKS p.2 | Subrace | 1/2 | extra_page_split_from_shared_raw_dict |
| Half-Orc (Variant; Mark of Finding) 2/2 | UADRAGONMARKS p.2 | Subrace | 2/2 | extra_page_split_from_shared_raw_dict |
| Tiefling (Asmodeus) | UAFIENDISHOPTIONS p.1 | Subrace | — | card_only_with_shared_raw_dict |
| Tiefling (Abyssal) 1/2 | UATHATOLDBLACKMAGIC p.1 | Subrace | 1/2 | extra_page_split_from_shared_raw_dict |
| Tiefling (Abyssal) 2/2 | UATHATOLDBLACKMAGIC p.1 | Subrace | 2/2 | extra_page_split_from_shared_raw_dict |
| Elf (High; Aereni) 1/2 | UAWAYFINDERSGUIDETOEBERRON p.73 | Subrace | 1/2 | extra_page_split_from_shared_raw_dict |
| Elf (High; Aereni) 2/2 | UAWAYFINDERSGUIDETOEBERRON p.73 | Subrace | 2/2 | extra_page_split_from_shared_raw_dict |
| Elf (High; Valenar) 1/2 | UAWAYFINDERSGUIDETOEBERRON p.73 | Subrace | 1/2 | extra_page_split_from_shared_raw_dict |
| Elf (High; Valenar) 2/2 | UAWAYFINDERSGUIDETOEBERRON p.73 | Subrace | 2/2 | extra_page_split_from_shared_raw_dict |
| Elf (Wood; Aereni) 1/2 | UAWAYFINDERSGUIDETOEBERRON p.73 | Subrace | 1/2 | extra_page_split_from_shared_raw_dict |
| Elf (Wood; Aereni) 2/2 | UAWAYFINDERSGUIDETOEBERRON p.73 | Subrace | 2/2 | extra_page_split_from_shared_raw_dict |
| Elf (Wood; Valenar) 1/2 | UAWAYFINDERSGUIDETOEBERRON p.73 | Subrace | 1/2 | extra_page_split_from_shared_raw_dict |
| Elf (Wood; Valenar) 2/2 | UAWAYFINDERSGUIDETOEBERRON p.73 | Subrace | 2/2 | extra_page_split_from_shared_raw_dict |
| Elf (Eladrin) 1/2 | UAELADRINANDGITH p.1 | Subrace | 1/2 | extra_page_split_from_shared_raw_dict |
| Elf (Eladrin) 2/2 | UAELADRINANDGITH p.1 | Subrace | 2/2 | extra_page_split_from_shared_raw_dict |

### Split deltas (base entity page counts)
| Base name | Source | Type | Off pages | Pt pages | Expected | Dual pages | Delta |
|---|---|---|---:|---:|---:|---:|---:|
| elf (eladrin) | uaeladrinandgith p.1 | subrace | 0 | 1 | 1 | 2 | +1 |
| elf (high; aereni) | uawayfindersguidetoeberron p.73 | subrace | 0 | 1 | 1 | 2 | +1 |
| elf (high; valenar) | uawayfindersguidetoeberron p.73 | subrace | 0 | 1 | 1 | 2 | +1 |
| elf (mark of shadow) | uadragonmarks p.6 | subrace | 0 | 1 | 1 | 2 | +1 |
| elf (wood; aereni) | uawayfindersguidetoeberron p.73 | subrace | 0 | 1 | 1 | 2 | +1 |
| elf (wood; valenar) | uawayfindersguidetoeberron p.73 | subrace | 0 | 1 | 1 | 2 | +1 |
| half-orc (variant; mark of finding) | uadragonmarks p.2 | subrace | 0 | 1 | 1 | 2 | +1 |
| tiefling (abyssal) | uathatoldblackmagic p.1 | subrace | 0 | 1 | 1 | 2 | +1 |
| tiefling (asmodeus) | uafiendishoptions p.1 | subrace | 0 | 0 | 0 | 1 | +1 |

## Classes
- Official: **643**
- Playtest: **804**
- Sum: **1447**
- Combined BEFORE (shared raw_dict): **1454** (surplus **+7**)
- Combined AFTER (isolated passes): **1447** (delta vs sum **+0**)
- Missing vs union after fix: **0**

### Every surplus card before fix (26)
| Name | Source | Type | Page-split | Reason |
|---|---|---|---|---|
| Ranger (Spell-less) 1/7 | UAMODIFYINGCLASSES p.5 | Class Overview | 1/7 | extra_page_split_from_shared_raw_dict |
| Ranger (Spell-less) 2/7 | UAMODIFYINGCLASSES p.5 | Class Overview | 2/7 | extra_page_split_from_shared_raw_dict |
| Ranger (Spell-less) 3/7 | UAMODIFYINGCLASSES p.5 | Class Overview | 3/7 | extra_page_split_from_shared_raw_dict |
| Ranger (Spell-less) 4/7 | UAMODIFYINGCLASSES p.5 | Class Overview | 4/7 | extra_page_split_from_shared_raw_dict |
| Ranger (Spell-less) 5/7 | UAMODIFYINGCLASSES p.5 | Class Overview | 5/7 | extra_page_split_from_shared_raw_dict |
| Ranger (Spell-less) 6/7 | UAMODIFYINGCLASSES p.5 | Class Overview | 6/7 | extra_page_split_from_shared_raw_dict |
| Ranger (Spell-less) 7/7 | UAMODIFYINGCLASSES p.5 | Class Overview | 7/7 | extra_page_split_from_shared_raw_dict |
| Ranger (Revised) 1/6 | UATHERANGERREVISED p.1 | Class Overview | 1/6 | extra_page_split_from_shared_raw_dict |
| Ranger (Revised) 2/6 | UATHERANGERREVISED p.1 | Class Overview | 2/6 | extra_page_split_from_shared_raw_dict |
| Ranger (Revised) 3/6 | UATHERANGERREVISED p.1 | Class Overview | 3/6 | extra_page_split_from_shared_raw_dict |
| Ranger (Revised) 4/6 | UATHERANGERREVISED p.1 | Class Overview | 4/6 | extra_page_split_from_shared_raw_dict |
| Ranger (Revised) 5/6 | UATHERANGERREVISED p.1 | Class Overview | 5/6 | extra_page_split_from_shared_raw_dict |
| Ranger (Revised) 6/6 | UATHERANGERREVISED p.1 | Class Overview | 6/6 | extra_page_split_from_shared_raw_dict |
| Battle Master 1/4 | XUA2023PLAYERSHANDBOOKP7 p.73 | Fighter Subclass | 1/4 | extra_page_split_from_shared_raw_dict |
| Battle Master 2/4 | XUA2023PLAYERSHANDBOOKP7 p.73 | Fighter Subclass | 2/4 | extra_page_split_from_shared_raw_dict |
| Battle Master 3/4 | XUA2023PLAYERSHANDBOOKP7 p.73 | Fighter Subclass | 3/4 | extra_page_split_from_shared_raw_dict |
| Battle Master 4/4 | XUA2023PLAYERSHANDBOOKP7 p.73 | Fighter Subclass | 4/4 | extra_page_split_from_shared_raw_dict |
| Arcane Archer (UA) 1/3 | UAFIGHTER p.1 | Fighter Subclass | 1/3 | extra_page_split_from_shared_raw_dict |
| Arcane Archer (UA) 2/3 | UAFIGHTER p.1 | Fighter Subclass | 2/3 | extra_page_split_from_shared_raw_dict |
| Arcane Archer (UA) 3/3 | UAFIGHTER p.1 | Fighter Subclass | 3/3 | extra_page_split_from_shared_raw_dict |
| Arcane Archer v2 (UA) 1/3 | UAREVISEDSUBCLASSES p.2 | Fighter Subclass | 1/3 | extra_page_split_from_shared_raw_dict |
| Arcane Archer v2 (UA) 2/3 | UAREVISEDSUBCLASSES p.2 | Fighter Subclass | 2/3 | extra_page_split_from_shared_raw_dict |
| Arcane Archer v2 (UA) 3/3 | UAREVISEDSUBCLASSES p.2 | Fighter Subclass | 3/3 | extra_page_split_from_shared_raw_dict |
| Arcane Archer 1/3 | XUA2025ARCANESUBCLASSES p.2 | Fighter Subclass | 1/3 | extra_page_split_from_shared_raw_dict |
| Arcane Archer 2/3 | XUA2025ARCANESUBCLASSES p.2 | Fighter Subclass | 2/3 | extra_page_split_from_shared_raw_dict |
| Arcane Archer 3/3 | XUA2025ARCANESUBCLASSES p.2 | Fighter Subclass | 3/3 | extra_page_split_from_shared_raw_dict |

### Split deltas (base entity page counts)
| Base name | Source | Type | Off pages | Pt pages | Expected | Dual pages | Delta |
|---|---|---|---:|---:|---:|---:|---:|
| arcane archer | xua2025arcanesubclasses p.2 | fighter subclass | 0 | 3 | 3 | 4 | +1 |
| arcane archer (ua) | uafighter p.1 | fighter subclass | 0 | 3 | 3 | 4 | +1 |
| arcane archer v2 (ua) | uarevisedsubclasses p.2 | fighter subclass | 0 | 3 | 3 | 4 | +1 |
| battle master | xua2023playershandbookp7 p.73 | fighter subclass | 0 | 3 | 3 | 5 | +2 |
| ranger (revised) | uatherangerrevised p.1 | class overview | 0 | 8 | 8 | 9 | +1 |
| ranger (spell-less) | uamodifyingclasses p.5 | class overview | 0 | 8 | 8 | 9 | +1 |

