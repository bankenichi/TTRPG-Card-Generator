# Missing entities: present in Official-only or Playtest-only, absent from Combined

Mechanism: card_engine.get_dataset_items flattens *_combined.json stubs
(_official + _playtest) into one item list for a single dataset. Then
generate_html dedupes by lowercased **name only** at card_engine.py:760-775
(ds_best[name_key]), keeping the higher-priority source (sources.get_source_priority).
UA/playtest sources default to priority 99; many official books are >=99, so UA often wins.
This name-dedupe also exists on main for near-duplicates within official data.

Our combined wiring (single stub file) is what surfaces Official↔Playtest collisions.

## Races
- Official cards: 196
- Playtest cards: 95
- Combined (stub) cards: 228
- Gap (sum - combined): 63
- Exact name overlaps Official∩Playtest: 60
- Missing entity records (name|source|dtype): 64

### Files
- Official: generators/data/data/races.json
- Playtest: ['generators/data/prerelease/generated/races_playtest.json']
- Combined stub: ['generators/data/prerelease/generated/races_combined.json']

### Reason groups

#### A. Engine ds_best name-dedupe (same display name, different source)
One of Official/Playtest wins by source priority; the other is silently dropped.

Overlap outcomes: kept official=25, kept playtest=35.

| Name | Dropped source | Dropped type | Kept source | Kept side | className |
|---|---|---|---|---|---|
| astral elf | AAG | race | UA2021TRAVELERSOFTHEMULTIVERSE | playtest |  |
| autognome | AAG | race | UA2021TRAVELERSOFTHEMULTIVERSE | playtest |  |
| centaur | UACENTAURSMINOTAURS | race | GGR | official |  |
| changeling | UAEBERRON | race | EFA | official |  |
| dhampir | UA2021GOTHICLINEAGES | race | RHW | official |  |
| dragonborn | XUA2022CHARACTEROPTIONS | race | XPHB | official |  |
| dragonborn (chromatic) | UA2021DRACONICOPTIONS | race | FTD | official |  |
| dragonborn (gem) | UA2021DRACONICOPTIONS | race | FTD | official |  |
| dragonborn (metallic) | UA2021DRACONICOPTIONS | race | FTD | official |  |
| dwarf | XUA2022CHARACTEROPTIONS | race | XPHB | official |  |
| dwarf (mark of warding) | ERLW | subrace | UADRAGONMARKS | playtest |  |
| elf | XUA2022CHARACTEROPTIONS | race | XPHB | official |  |
| elf (mark of shadow) | ERLW | subrace | UADRAGONMARKS | playtest |  |
| fairy | MPMM | race | UA2021FOLKOFTHEFEYWILD | playtest |  |
| giff | AAG | race | UA2021TRAVELERSOFTHEMULTIVERSE | playtest |  |
| gith | MTF | race | UAELADRINANDGITH | playtest |  |
| gnome | XUA2022CHARACTEROPTIONS | race | XPHB | official |  |
| gnome (mark of scribing) | ERLW | subrace | UADRAGONMARKS | playtest |  |
| goliath | XUA2022CLERICANDREVISEDSPECIES | race | XPHB | official |  |
| hadozee | AAG | race | UA2021TRAVELERSOFTHEMULTIVERSE | playtest |  |
| half-elf (variant; mark of detection) | ERLW | subrace | UADRAGONMARKS | playtest |  |
| half-elf (variant; mark of storm) | ERLW | subrace | UADRAGONMARKS | playtest |  |
| half-orc (variant; mark of finding) | ERLW | subrace | UADRAGONMARKS | playtest |  |
| halfling | XUA2022CHARACTEROPTIONS | race | XPHB | official |  |
| halfling (mark of healing) | ERLW | subrace | UADRAGONMARKS | playtest |  |
| halfling (mark of hospitality) | ERLW | subrace | UADRAGONMARKS | playtest |  |
| hexblood | UA2021GOTHICLINEAGES | race | RHW | official |  |
| hobgoblin | MPMM | race | UA2021FOLKOFTHEFEYWILD | playtest |  |
| human | XUA2022CHARACTEROPTIONS | race | XPHB | official |  |
| human (mark of handling) | ERLW | subrace | UADRAGONMARKS | playtest |  |
| human (mark of making) | ERLW | subrace | UADRAGONMARKS | playtest |  |
| human (mark of passage) | ERLW | subrace | UADRAGONMARKS | playtest |  |
| human (mark of sentinel) | ERLW | subrace | UADRAGONMARKS | playtest |  |
| kalashtar | UARACESOFEBERRON | race | EFA | official |  |
| kender | UA2022HEROESOFKRYNNREVISITED | race | DSOTDQ | official |  |
| kobold | MPMM | race | UA2021DRACONICOPTIONS | playtest |  |
| kuo-toa | DMG | race | XUA2026UNDERDARKOPTIONS2 | playtest |  |
| loxodon | UARACESOFRAVNICA | race | GGR | official |  |
| minotaur | UACENTAURSMINOTAURS | race | GGR | official |  |
| orc | XUA2022CHARACTEROPTIONS | race | XPHB | official |  |
| plasmoid | AAG | race | UA2021TRAVELERSOFTHEMULTIVERSE | playtest |  |
| reborn | UA2021GOTHICLINEAGES | race | RHW | official |  |
| shifter | UAEBERRON | race | EFA | official |  |
| shifter (beasthide) | ERLW | subrace | UAEBERRON | playtest |  |
| shifter (longtooth) | ERLW | subrace | UAEBERRON | playtest |  |
| shifter (swiftstride) | ERLW | subrace | UARACESOFEBERRON | playtest |  |
| shifter (wildhunt) | ERLW | subrace | UAEBERRON | playtest |  |
| simic hybrid | UARACESOFRAVNICA | race | GGR | official |  |
| thri-kreen | AAG | race | UA2021TRAVELERSOFTHEMULTIVERSE | playtest |  |
| tiefling | XUA2022CHARACTEROPTIONS | race | XPHB | official |  |
| tiefling (baalzebul) | MTF | subrace | UAFIENDISHOPTIONS | playtest |  |
| tiefling (dispater) | MTF | subrace | UAFIENDISHOPTIONS | playtest |  |
| tiefling (fierna) | MTF | subrace | UAFIENDISHOPTIONS | playtest |  |
| tiefling (glasya) | MTF | subrace | UAFIENDISHOPTIONS | playtest |  |
| tiefling (levistus) | MTF | subrace | UAFIENDISHOPTIONS | playtest |  |
| tiefling (mammon) | MTF | subrace | UAFIENDISHOPTIONS | playtest |  |
| tiefling (mephistopheles) | MTF | subrace | UAFIENDISHOPTIONS | playtest |  |
| tiefling (zariel) | MTF | subrace | UAFIENDISHOPTIONS | playtest |  |
| vedalken | UARACESOFRAVNICA | race | GGR | official |  |
| warforged | UAEBERRON | race | EFA | official |  |

#### B. Name-dedupe + post-enrich rename
Collision key is the pre-enrich name; winner is later renamed (e.g. Eladrin → Elf (Eladrin)),
so Combined still has a card but under a different title — official race card is gone.

- **Eladrin** | source=MPMM | dtype=race
- **Githyanki** | source=MPMM | dtype=race
- **Githzerai** | source=MPMM | dtype=race

### Full missing list (JSON-ish)
- Astral Elf | AAG | race | className=None | in_off=True in_pt=False | lost_to=Astral Elf/UA2021TRAVELERSOFTHEMULTIVERSE/race
- Autognome | AAG | race | className=None | in_off=True in_pt=False | lost_to=Autognome/UA2021TRAVELERSOFTHEMULTIVERSE/race
- Eladrin | MPMM | race | className=None | in_off=True in_pt=False | lost_to=None/None/None
- Fairy | MPMM | race | className=None | in_off=True in_pt=False | lost_to=Fairy/UA2021FOLKOFTHEFEYWILD/race
- Giff | AAG | race | className=None | in_off=True in_pt=False | lost_to=Giff/UA2021TRAVELERSOFTHEMULTIVERSE/race
- Gith | MTF | race | className=None | in_off=True in_pt=False | lost_to=Gith/UAELADRINANDGITH/race
- Githyanki | MPMM | race | className=None | in_off=True in_pt=False | lost_to=None/None/None
- Githzerai | MPMM | race | className=None | in_off=True in_pt=False | lost_to=None/None/None
- Hadozee | AAG | race | className=None | in_off=True in_pt=False | lost_to=Hadozee/UA2021TRAVELERSOFTHEMULTIVERSE/race
- Hobgoblin | MPMM | race | className=None | in_off=True in_pt=False | lost_to=Hobgoblin/UA2021FOLKOFTHEFEYWILD/race
- Kobold | MPMM | race | className=None | in_off=True in_pt=False | lost_to=Kobold/UA2021DRACONICOPTIONS/race
- Kuo-Toa | DMG | race | className=None | in_off=True in_pt=False | lost_to=Kuo-Toa/XUA2026UNDERDARKOPTIONS2/race
- Plasmoid | AAG | race | className=None | in_off=True in_pt=False | lost_to=Plasmoid/UA2021TRAVELERSOFTHEMULTIVERSE/race
- Thri-kreen | AAG | race | className=None | in_off=True in_pt=False | lost_to=Thri-kreen/UA2021TRAVELERSOFTHEMULTIVERSE/race
- Dwarf (Mark of Warding) | ERLW | subrace | className=None | in_off=True in_pt=False | lost_to=Dwarf (Mark of Warding)/UADRAGONMARKS/subrace
- Elf (Mark of Shadow) | ERLW | subrace | className=None | in_off=True in_pt=False | lost_to=Elf (Mark of Shadow)/UADRAGONMARKS/subrace
- Gnome (Mark of Scribing) | ERLW | subrace | className=None | in_off=True in_pt=False | lost_to=Gnome (Mark of Scribing)/UADRAGONMARKS/subrace
- Half-Elf (Variant; Mark of Detection) | ERLW | subrace | className=None | in_off=True in_pt=False | lost_to=Half-Elf (Variant; Mark of Detection)/UADRAGONMARKS/subrace
- Half-Elf (Variant; Mark of Storm) | ERLW | subrace | className=None | in_off=True in_pt=False | lost_to=Half-Elf (Variant; Mark of Storm)/UADRAGONMARKS/subrace
- Half-Orc (Variant; Mark of Finding) | ERLW | subrace | className=None | in_off=True in_pt=False | lost_to=Half-Orc (Variant; Mark of Finding)/UADRAGONMARKS/subrace
- Halfling (Mark of Healing) | ERLW | subrace | className=None | in_off=True in_pt=False | lost_to=Halfling (Mark of Healing)/UADRAGONMARKS/subrace
- Halfling (Mark of Hospitality) | ERLW | subrace | className=None | in_off=True in_pt=False | lost_to=Halfling (Mark of Hospitality)/UADRAGONMARKS/subrace
- Human (Mark of Handling) | ERLW | subrace | className=None | in_off=True in_pt=False | lost_to=Human (Mark of Handling)/UADRAGONMARKS/subrace
- Human (Mark of Making) | ERLW | subrace | className=None | in_off=True in_pt=False | lost_to=Human (Mark of Making)/UADRAGONMARKS/subrace
- Human (Mark of Passage) | ERLW | subrace | className=None | in_off=True in_pt=False | lost_to=Human (Mark of Passage)/UADRAGONMARKS/subrace
- Human (Mark of Sentinel) | ERLW | subrace | className=None | in_off=True in_pt=False | lost_to=Human (Mark of Sentinel)/UADRAGONMARKS/subrace
- Shifter (Beasthide) | ERLW | subrace | className=None | in_off=True in_pt=False | lost_to=Shifter (Beasthide)/UAEBERRON/subrace
- Shifter (Longtooth) | ERLW | subrace | className=None | in_off=True in_pt=False | lost_to=Shifter (Longtooth)/UAEBERRON/subrace
- Shifter (Swiftstride) | ERLW | subrace | className=None | in_off=True in_pt=False | lost_to=Shifter (Swiftstride)/UARACESOFEBERRON/subrace
- Shifter (Wildhunt) | ERLW | subrace | className=None | in_off=True in_pt=False | lost_to=Shifter (Wildhunt)/UAEBERRON/subrace
- Tiefling (Asmodeus) | MTF | subrace | className=None | in_off=True in_pt=False | lost_to=Tiefling (Asmodeus)/UAFIENDISHOPTIONS/subrace
- Tiefling (Baalzebul) | MTF | subrace | className=None | in_off=True in_pt=False | lost_to=Tiefling (Baalzebul)/UAFIENDISHOPTIONS/subrace
- Tiefling (Dispater) | MTF | subrace | className=None | in_off=True in_pt=False | lost_to=Tiefling (Dispater)/UAFIENDISHOPTIONS/subrace
- Tiefling (Fierna) | MTF | subrace | className=None | in_off=True in_pt=False | lost_to=Tiefling (Fierna)/UAFIENDISHOPTIONS/subrace
- Tiefling (Glasya) | MTF | subrace | className=None | in_off=True in_pt=False | lost_to=Tiefling (Glasya)/UAFIENDISHOPTIONS/subrace
- Tiefling (Levistus) | MTF | subrace | className=None | in_off=True in_pt=False | lost_to=Tiefling (Levistus)/UAFIENDISHOPTIONS/subrace
- Tiefling (Mammon) | MTF | subrace | className=None | in_off=True in_pt=False | lost_to=Tiefling (Mammon)/UAFIENDISHOPTIONS/subrace
- Tiefling (Mephistopheles) | MTF | subrace | className=None | in_off=True in_pt=False | lost_to=Tiefling (Mephistopheles)/UAFIENDISHOPTIONS/subrace
- Tiefling (Zariel) | MTF | subrace | className=None | in_off=True in_pt=False | lost_to=Tiefling (Zariel)/UAFIENDISHOPTIONS/subrace
- Changeling | UAEBERRON | race | className=None | in_off=False in_pt=True | lost_to=Changeling/EFA/race
- Shifter | UAEBERRON | race | className=None | in_off=False in_pt=True | lost_to=Shifter/EFA/race
- Warforged | UAEBERRON | race | className=None | in_off=False in_pt=True | lost_to=Warforged/EFA/race
- Dragonborn (Chromatic) | UA2021DRACONICOPTIONS | race | className=None | in_off=False in_pt=True | lost_to=Dragonborn (Chromatic)/FTD/race
- Dragonborn (Gem) | UA2021DRACONICOPTIONS | race | className=None | in_off=False in_pt=True | lost_to=Dragonborn (Gem)/FTD/race
- Dragonborn (Metallic) | UA2021DRACONICOPTIONS | race | className=None | in_off=False in_pt=True | lost_to=Dragonborn (Metallic)/FTD/race
- Dragonborn | XUA2022CHARACTEROPTIONS | race | className=None | in_off=False in_pt=True | lost_to=Dragonborn/XPHB/race
- Dwarf | XUA2022CHARACTEROPTIONS | race | className=None | in_off=False in_pt=True | lost_to=Dwarf/XPHB/race
- Elf | XUA2022CHARACTEROPTIONS | race | className=None | in_off=False in_pt=True | lost_to=Elf/XPHB/race
- Gnome | XUA2022CHARACTEROPTIONS | race | className=None | in_off=False in_pt=True | lost_to=Gnome/XPHB/race
- Halfling | XUA2022CHARACTEROPTIONS | race | className=None | in_off=False in_pt=True | lost_to=Halfling/XPHB/race
- Human | XUA2022CHARACTEROPTIONS | race | className=None | in_off=False in_pt=True | lost_to=Human/XPHB/race
- Orc | XUA2022CHARACTEROPTIONS | race | className=None | in_off=False in_pt=True | lost_to=Orc/XPHB/race
- Tiefling | XUA2022CHARACTEROPTIONS | race | className=None | in_off=False in_pt=True | lost_to=Tiefling/XPHB/race
- Kender | UA2022HEROESOFKRYNNREVISITED | race | className=None | in_off=False in_pt=True | lost_to=Kender/DSOTDQ/race
- Goliath | XUA2022CLERICANDREVISEDSPECIES | race | className=None | in_off=False in_pt=True | lost_to=Goliath/XPHB/race
- Centaur | UACENTAURSMINOTAURS | race | className=None | in_off=False in_pt=True | lost_to=Centaur/GGR/race
- Minotaur | UACENTAURSMINOTAURS | race | className=None | in_off=False in_pt=True | lost_to=Minotaur/GGR/race
- Kalashtar | UARACESOFEBERRON | race | className=None | in_off=False in_pt=True | lost_to=Kalashtar/EFA/race
- Loxodon | UARACESOFRAVNICA | race | className=None | in_off=False in_pt=True | lost_to=Loxodon/GGR/race
- Simic Hybrid | UARACESOFRAVNICA | race | className=None | in_off=False in_pt=True | lost_to=Simic Hybrid/GGR/race
- Vedalken | UARACESOFRAVNICA | race | className=None | in_off=False in_pt=True | lost_to=Vedalken/GGR/race
- Dhampir | UA2021GOTHICLINEAGES | race | className=None | in_off=False in_pt=True | lost_to=Dhampir/RHW/race
- Hexblood | UA2021GOTHICLINEAGES | race | className=None | in_off=False in_pt=True | lost_to=Hexblood/RHW/race
- Reborn | UA2021GOTHICLINEAGES | race | className=None | in_off=False in_pt=True | lost_to=Reborn/RHW/race

## Classes
- Official cards: 643
- Playtest cards: 804
- Combined (stub) cards: 1143
- Gap (sum - combined): 304
- Exact name overlaps Official∩Playtest: 87
- Missing entity records (name|source|dtype): 87

### Files
- Official: ['generators/data/data/class/index.json', 'generators/data/data/optionalfeatures.json']
- Playtest: ['generators/data/prerelease/generated/classes_playtest.json']
- Combined stub: ['generators/data/prerelease/generated/classes_combined.json', 'generators/data/data/optionalfeatures.json']

### Reason groups

#### A. Engine ds_best name-dedupe (same display name, different source)
One of Official/Playtest wins by source priority; the other is silently dropped.

Overlap outcomes: kept official=76, kept playtest=11.

| Name | Dropped source | Dropped type | Kept source | Kept side | className |
|---|---|---|---|---|---|
| abjurer | XUA2023PLAYERSHANDBOOKP7 | subclass | XPHB | official | Wizard |
| alchemist | UAARTIFICERREVISITED | subclass | EFA | official | Artificer (Revisited) |
| arcana domain | XUA2025ARCANESUBCLASSES | subclass | AU | official | Cleric |
| arcane archer | XUA2025ARCANESUBCLASSES | subclass | AU | official | Fighter |
| arcane trickster | XUA2023PLAYERSHANDBOOKP6 | subclass | XPHB | official | Rogue |
| artificer | UAARTIFICER | class | EFA | official |  |
| artillerist | UAARTIFICERREVISITED | subclass | EFA | official | Artificer (Revisited) |
| assassin | XUA2023PLAYERSHANDBOOKP6 | subclass | XPHB | official | Rogue |
| barbarian | XUA2023PLAYERSHANDBOOKP5 | class | XPHB | official |  |
| bard | XUA2022EXPERTCLASSES | class | XPHB | official |  |
| battle master | XUA2023PLAYERSHANDBOOKP7 | subclass | XPHB | official | Fighter |
| battle smith | UAARTIFICERREVISITED | subclass | EFA | official | Artificer (Revisited) |
| beast master | XUA2023PLAYERSHANDBOOKP6 | subclass | XPHB | official | Ranger |
| bladesinger | XUA2025FORGOTTENREALMSSUBCLASSES | subclass | FRHOF | official | Wizard |
| cavalier | XGE | subclass | XUA2025SUBCLASSESUPDATE | playtest | Fighter |
| celestial patron | XUA2023PLAYERSHANDBOOKP7 | subclass | XPHB | official | Warlock |
| champion | XUA2023PLAYERSHANDBOOKP5 | subclass | XPHB | official | Fighter |
| circle of spores | TCE | subclass | XUA2026UNDERDARKOPTIONS2 | playtest | Druid |
| circle of the land | XUA2023PLAYERSHANDBOOKP6 | subclass | XPHB | official | Druid |
| circle of the moon | XUA2023DRUIDANDPALADIN | subclass | XPHB | official | Druid |
| circle of the sea | XUA2023PLAYERSHANDBOOKP6 | subclass | XPHB | official | Druid |
| cleric | XUA2022CLERICANDREVISEDSPECIES | class | XPHB | official |  |
| college of dance | XUA2023PLAYERSHANDBOOKP6 | subclass | XPHB | official | Bard |
| college of glamour | XUA2023PLAYERSHANDBOOKP6 | subclass | XPHB | official | Bard |
| college of lore | XUA2022EXPERTCLASSES | subclass | XPHB | official | Bard |
| college of spirits | XUA2025HORRORSUBCLASSES | subclass | RHW | official | Bard |
| college of the moon | XUA2025FORGOTTENREALMSSUBCLASSES | subclass | FRHOF | official | Bard |
| college of valor | XUA2023PLAYERSHANDBOOKP6 | subclass | XPHB | official | Bard |
| conjurer | XUA2025ARCANESUBCLASSES | subclass | AU | official | Wizard |
| diviner | XUA2023PLAYERSHANDBOOKP7 | subclass | XPHB | official | Wizard |
| draconic sorcery | XUA2023PLAYERSHANDBOOKP5 | subclass | XPHB | official | Sorcerer |
| druid | XUA2023DRUIDANDPALADIN | class | XPHB | official |  |
| eldritch knight | XUA2023PLAYERSHANDBOOKP7 | subclass | XPHB | official | Fighter |
| enchanter | XUA2025ARCANESUBCLASSES | subclass | AU | official | Wizard |
| evoker | XUA2023PLAYERSHANDBOOKP5 | subclass | XPHB | official | Wizard |
| expert sidekick | TCE | class | UASIDEKICKS | playtest |  |
| fiend patron | XUA2023PLAYERSHANDBOOKP5 | subclass | XPHB | official | Warlock |
| fighter | XUA2023PLAYERSHANDBOOKP5 | class | XPHB | official |  |
| gloom stalker | XUA2023PLAYERSHANDBOOKP6 | subclass | XPHB | official | Ranger |
| grave domain | XUA2025HORRORSUBCLASSES | subclass | RHW | official | Cleric |
| hollow warden | XUA2025HORRORSUBCLASSES | subclass | RHW | official | Ranger |
| hunter | XUA2022EXPERTCLASSES | subclass | XPHB | official | Ranger |
| illusionist | XUA2023PLAYERSHANDBOOKP7 | subclass | XPHB | official | Wizard |
| knowledge domain | XUA2025FORGOTTENREALMSSUBCLASSES | subclass | FRHOF | official | Cleric |
| life domain | XUA2022CLERICANDREVISEDSPECIES | subclass | XPHB | official | Cleric |
| light domain | XUA2023PLAYERSHANDBOOKP6 | subclass | XPHB | official | Cleric |
| monk | XUA2023PLAYERSHANDBOOKP6 | class | XPHB | official |  |
| necromancer | XUA2025ARCANESUBCLASSES | subclass | AU | official | Wizard |
| oath of devotion | XUA2023DRUIDANDPALADIN | subclass | XPHB | official | Paladin |
| oath of glory | XUA2023PLAYERSHANDBOOKP6 | subclass | XPHB | official | Paladin |
| oath of the ancients | XUA2023PLAYERSHANDBOOKP6 | subclass | XPHB | official | Paladin |
| oath of the noble genies | XUA2025FORGOTTENREALMSSUBCLASSES | subclass | FRHOF | official | Paladin |
| oath of vengeance | XUA2023PLAYERSHANDBOOKP6 | subclass | XPHB | official | Paladin |
| oathbreaker | DMG | subclass | XUA2025SUBCLASSESUPDATE | playtest | Paladin |
| paladin | XUA2023DRUIDANDPALADIN | class | XPHB | official |  |
| path of the berserker | XUA2023PLAYERSHANDBOOKP5 | subclass | XPHB | official | Barbarian |
| path of the storm herald | XGE | subclass | XUA2025SUBCLASSESUPDATE | playtest | Barbarian |
| path of the wild heart | XUA2023PLAYERSHANDBOOKP7 | subclass | XPHB | official | Barbarian |
| path of the world tree | XUA2023PLAYERSHANDBOOKP7 | subclass | XPHB | official | Barbarian |
| path of the zealot | XUA2023PLAYERSHANDBOOKP7 | subclass | XPHB | official | Barbarian |
| phantom | XUA2025HORRORSUBCLASSES | subclass | RHW | official | Rogue |
| ranger | XUA2022EXPERTCLASSES | class | XPHB | official |  |
| reanimator | XUA2025HORRORSUBCLASSES | subclass | RHW | official | Artificer |
| rogue | XUA2022EXPERTCLASSES | class | XPHB | official |  |
| scion of the three | XUA2025FORGOTTENREALMSSUBCLASSES | subclass | FRHOF | official | Rogue |
| shadow sorcery | XUA2025HORRORSUBCLASSES | subclass | RHW | official | Sorcerer |
| sorcerer | XUA2023PLAYERSHANDBOOKP5 | class | XPHB | official |  |
| spellcaster sidekick | TCE | class | UASIDEKICKS | playtest |  |
| spellfire sorcery | XUA2025FORGOTTENREALMSSUBCLASSES | subclass | FRHOF | official | Sorcerer |
| storm sorcery | XGE | subclass | UAWATERBORNEADVENTURES | playtest | Sorcerer |
| swashbuckler | XGE | subclass | UAWATERBORNEADVENTURES | playtest | Rogue |
| the archfey | PHB | subclass | XUA2023PLAYERSHANDBOOKP7 | playtest | Warlock |
| the great old one | PHB | subclass | XUA2023PLAYERSHANDBOOKP7 | playtest | Warlock |
| thief | XUA2022EXPERTCLASSES | subclass | XPHB | official | Rogue |
| transmuter | XUA2025ARCANESUBCLASSES | subclass | AU | official | Wizard |
| trickery domain | XUA2023PLAYERSHANDBOOKP6 | subclass | XPHB | official | Cleric |
| undead patron | XUA2025HORRORSUBCLASSES | subclass | RHW | official | Warlock |
| vestige patron | XUA2026MYSTICSUBCLASSES | subclass | AU | official | Warlock |
| war domain | XUA2023PLAYERSHANDBOOKP6 | subclass | XPHB | official | Cleric |
| warlock | XUA2023PLAYERSHANDBOOKP5 | class | XPHB | official |  |
| warrior of shadow | XUA2023PLAYERSHANDBOOKP6 | subclass | XPHB | official | Monk |
| warrior of the elements | XUA2023PLAYERSHANDBOOKP6 | subclass | XPHB | official | Monk |
| warrior of the mystic arts | XUA2026MYSTICSUBCLASSES | subclass | AU | official | Monk |
| warrior sidekick | TCE | class | UASIDEKICKS | playtest |  |
| wild magic sorcery | XUA2023PLAYERSHANDBOOKP7 | subclass | XPHB | official | Sorcerer |
| winter walker | XUA2025FORGOTTENREALMSSUBCLASSES | subclass | FRHOF | official | Ranger |
| wizard | XUA2023PLAYERSHANDBOOKP5 | class | XPHB | official |  |

### Full missing list (JSON-ish)
- Path of the Storm Herald | XGE | subclass | className=Barbarian | in_off=True in_pt=False | lost_to=Path of the Storm Herald/XUA2025SUBCLASSESUPDATE/subclass
- Circle of Spores | TCE | subclass | className=Druid | in_off=True in_pt=False | lost_to=Circle of Spores/XUA2026UNDERDARKOPTIONS2/subclass
- Cavalier | XGE | subclass | className=Fighter | in_off=True in_pt=False | lost_to=Cavalier/XUA2025SUBCLASSESUPDATE/subclass
- Oathbreaker | DMG | subclass | className=Paladin | in_off=True in_pt=False | lost_to=Oathbreaker/XUA2025SUBCLASSESUPDATE/subclass
- Swashbuckler | XGE | subclass | className=Rogue | in_off=True in_pt=False | lost_to=Swashbuckler/UAWATERBORNEADVENTURES/subclass
- Expert Sidekick | TCE | class | className=None | in_off=True in_pt=False | lost_to=Expert Sidekick/UASIDEKICKS/class
- Spellcaster Sidekick | TCE | class | className=None | in_off=True in_pt=False | lost_to=Spellcaster Sidekick/UASIDEKICKS/class
- Warrior Sidekick | TCE | class | className=None | in_off=True in_pt=False | lost_to=Warrior Sidekick/UASIDEKICKS/class
- Storm Sorcery | XGE | subclass | className=Sorcerer | in_off=True in_pt=False | lost_to=Storm Sorcery/UAWATERBORNEADVENTURES/subclass
- The Archfey | PHB | subclass | className=Warlock | in_off=True in_pt=False | lost_to=The Archfey/XUA2023PLAYERSHANDBOOKP7/subclass
- The Great Old One | PHB | subclass | className=Warlock | in_off=True in_pt=False | lost_to=The Great Old One/XUA2023PLAYERSHANDBOOKP7/subclass
- Artificer | UAARTIFICER | class | className=None | in_off=False in_pt=True | lost_to=Artificer/EFA/class
- Bard | XUA2022EXPERTCLASSES | class | className=None | in_off=False in_pt=True | lost_to=Bard/XPHB/class
- Ranger | XUA2022EXPERTCLASSES | class | className=None | in_off=False in_pt=True | lost_to=Ranger/XPHB/class
- Rogue | XUA2022EXPERTCLASSES | class | className=None | in_off=False in_pt=True | lost_to=Rogue/XPHB/class
- Cleric | XUA2022CLERICANDREVISEDSPECIES | class | className=None | in_off=False in_pt=True | lost_to=Cleric/XPHB/class
- Druid | XUA2023DRUIDANDPALADIN | class | className=None | in_off=False in_pt=True | lost_to=Druid/XPHB/class
- Paladin | XUA2023DRUIDANDPALADIN | class | className=None | in_off=False in_pt=True | lost_to=Paladin/XPHB/class
- Barbarian | XUA2023PLAYERSHANDBOOKP5 | class | className=None | in_off=False in_pt=True | lost_to=Barbarian/XPHB/class
- Fighter | XUA2023PLAYERSHANDBOOKP5 | class | className=None | in_off=False in_pt=True | lost_to=Fighter/XPHB/class
- Sorcerer | XUA2023PLAYERSHANDBOOKP5 | class | className=None | in_off=False in_pt=True | lost_to=Sorcerer/XPHB/class
- Warlock | XUA2023PLAYERSHANDBOOKP5 | class | className=None | in_off=False in_pt=True | lost_to=Warlock/XPHB/class
- Wizard | XUA2023PLAYERSHANDBOOKP5 | class | className=None | in_off=False in_pt=True | lost_to=Wizard/XPHB/class
- Monk | XUA2023PLAYERSHANDBOOKP6 | class | className=None | in_off=False in_pt=True | lost_to=Monk/XPHB/class
- Alchemist | UAARTIFICERREVISITED | subclass | className=Artificer (Revisited) | in_off=False in_pt=True | lost_to=Alchemist/EFA/subclass
- Artillerist | UAARTIFICERREVISITED | subclass | className=Artificer (Revisited) | in_off=False in_pt=True | lost_to=Artillerist/EFA/subclass
- Battle Smith | UAARTIFICERREVISITED | subclass | className=Artificer (Revisited) | in_off=False in_pt=True | lost_to=Battle Smith/EFA/subclass
- College of Lore | XUA2022EXPERTCLASSES | subclass | className=Bard | in_off=False in_pt=True | lost_to=College of Lore/XPHB/subclass
- Hunter | XUA2022EXPERTCLASSES | subclass | className=Ranger | in_off=False in_pt=True | lost_to=Hunter/XPHB/subclass
- Thief | XUA2022EXPERTCLASSES | subclass | className=Rogue | in_off=False in_pt=True | lost_to=Thief/XPHB/subclass
- Life Domain | XUA2022CLERICANDREVISEDSPECIES | subclass | className=Cleric | in_off=False in_pt=True | lost_to=Life Domain/XPHB/subclass
- Circle of the Moon | XUA2023DRUIDANDPALADIN | subclass | className=Druid | in_off=False in_pt=True | lost_to=Circle of the Moon/XPHB/subclass
- Oath of Devotion | XUA2023DRUIDANDPALADIN | subclass | className=Paladin | in_off=False in_pt=True | lost_to=Oath of Devotion/XPHB/subclass
- Champion | XUA2023PLAYERSHANDBOOKP5 | subclass | className=Fighter | in_off=False in_pt=True | lost_to=Champion/XPHB/subclass
- Draconic Sorcery | XUA2023PLAYERSHANDBOOKP5 | subclass | className=Sorcerer | in_off=False in_pt=True | lost_to=Draconic Sorcery/XPHB/subclass
- Evoker | XUA2023PLAYERSHANDBOOKP5 | subclass | className=Wizard | in_off=False in_pt=True | lost_to=Evoker/XPHB/subclass
- Fiend Patron | XUA2023PLAYERSHANDBOOKP5 | subclass | className=Warlock | in_off=False in_pt=True | lost_to=Fiend Patron/XPHB/subclass
- Path of the Berserker | XUA2023PLAYERSHANDBOOKP5 | subclass | className=Barbarian | in_off=False in_pt=True | lost_to=Path of the Berserker/XPHB/subclass
- Arcane Trickster | XUA2023PLAYERSHANDBOOKP6 | subclass | className=Rogue | in_off=False in_pt=True | lost_to=Arcane Trickster/XPHB/subclass
- Assassin | XUA2023PLAYERSHANDBOOKP6 | subclass | className=Rogue | in_off=False in_pt=True | lost_to=Assassin/XPHB/subclass
- Beast Master | XUA2023PLAYERSHANDBOOKP6 | subclass | className=Ranger | in_off=False in_pt=True | lost_to=Beast Master/XPHB/subclass
- Circle of the Land | XUA2023PLAYERSHANDBOOKP6 | subclass | className=Druid | in_off=False in_pt=True | lost_to=Circle of the Land/XPHB/subclass
- Circle of the Sea | XUA2023PLAYERSHANDBOOKP6 | subclass | className=Druid | in_off=False in_pt=True | lost_to=Circle of the Sea/XPHB/subclass
- College of Dance | XUA2023PLAYERSHANDBOOKP6 | subclass | className=Bard | in_off=False in_pt=True | lost_to=College of Dance/XPHB/subclass
- College of Glamour | XUA2023PLAYERSHANDBOOKP6 | subclass | className=Bard | in_off=False in_pt=True | lost_to=College of Glamour/XPHB/subclass
- College of Valor | XUA2023PLAYERSHANDBOOKP6 | subclass | className=Bard | in_off=False in_pt=True | lost_to=College of Valor/XPHB/subclass
- Gloom Stalker | XUA2023PLAYERSHANDBOOKP6 | subclass | className=Ranger | in_off=False in_pt=True | lost_to=Gloom Stalker/XPHB/subclass
- Light Domain | XUA2023PLAYERSHANDBOOKP6 | subclass | className=Cleric | in_off=False in_pt=True | lost_to=Light Domain/XPHB/subclass
- Oath of Glory | XUA2023PLAYERSHANDBOOKP6 | subclass | className=Paladin | in_off=False in_pt=True | lost_to=Oath of Glory/XPHB/subclass
- Oath of the Ancients | XUA2023PLAYERSHANDBOOKP6 | subclass | className=Paladin | in_off=False in_pt=True | lost_to=Oath of the Ancients/XPHB/subclass
- Oath of Vengeance | XUA2023PLAYERSHANDBOOKP6 | subclass | className=Paladin | in_off=False in_pt=True | lost_to=Oath of Vengeance/XPHB/subclass
- Trickery Domain | XUA2023PLAYERSHANDBOOKP6 | subclass | className=Cleric | in_off=False in_pt=True | lost_to=Trickery Domain/XPHB/subclass
- War Domain | XUA2023PLAYERSHANDBOOKP6 | subclass | className=Cleric | in_off=False in_pt=True | lost_to=War Domain/XPHB/subclass
- Warrior of Shadow | XUA2023PLAYERSHANDBOOKP6 | subclass | className=Monk | in_off=False in_pt=True | lost_to=Warrior of Shadow/XPHB/subclass
- Warrior of the Elements | XUA2023PLAYERSHANDBOOKP6 | subclass | className=Monk | in_off=False in_pt=True | lost_to=Warrior of the Elements/XPHB/subclass
- Abjurer | XUA2023PLAYERSHANDBOOKP7 | subclass | className=Wizard | in_off=False in_pt=True | lost_to=Abjurer/XPHB/subclass
- Battle Master | XUA2023PLAYERSHANDBOOKP7 | subclass | className=Fighter | in_off=False in_pt=True | lost_to=Battle Master/XPHB/subclass
- Celestial Patron | XUA2023PLAYERSHANDBOOKP7 | subclass | className=Warlock | in_off=False in_pt=True | lost_to=Celestial Patron/XPHB/subclass
- Diviner | XUA2023PLAYERSHANDBOOKP7 | subclass | className=Wizard | in_off=False in_pt=True | lost_to=Diviner/XPHB/subclass
- Eldritch Knight | XUA2023PLAYERSHANDBOOKP7 | subclass | className=Fighter | in_off=False in_pt=True | lost_to=Eldritch Knight/XPHB/subclass
- Illusionist | XUA2023PLAYERSHANDBOOKP7 | subclass | className=Wizard | in_off=False in_pt=True | lost_to=Illusionist/XPHB/subclass
- Path of the Wild Heart | XUA2023PLAYERSHANDBOOKP7 | subclass | className=Barbarian | in_off=False in_pt=True | lost_to=Path of the Wild Heart/XPHB/subclass
- Path of the World Tree | XUA2023PLAYERSHANDBOOKP7 | subclass | className=Barbarian | in_off=False in_pt=True | lost_to=Path of the World Tree/XPHB/subclass
- Path of the Zealot | XUA2023PLAYERSHANDBOOKP7 | subclass | className=Barbarian | in_off=False in_pt=True | lost_to=Path of the Zealot/XPHB/subclass
- Wild Magic Sorcery | XUA2023PLAYERSHANDBOOKP7 | subclass | className=Sorcerer | in_off=False in_pt=True | lost_to=Wild Magic Sorcery/XPHB/subclass
- Arcana Domain | XUA2025ARCANESUBCLASSES | subclass | className=Cleric | in_off=False in_pt=True | lost_to=Arcana Domain/AU/subclass
- Arcane Archer | XUA2025ARCANESUBCLASSES | subclass | className=Fighter | in_off=False in_pt=True | lost_to=Arcane Archer/AU/subclass
- Conjurer | XUA2025ARCANESUBCLASSES | subclass | className=Wizard | in_off=False in_pt=True | lost_to=Conjurer/AU/subclass
- Enchanter | XUA2025ARCANESUBCLASSES | subclass | className=Wizard | in_off=False in_pt=True | lost_to=Enchanter/AU/subclass
- Necromancer | XUA2025ARCANESUBCLASSES | subclass | className=Wizard | in_off=False in_pt=True | lost_to=Necromancer/AU/subclass
- Transmuter | XUA2025ARCANESUBCLASSES | subclass | className=Wizard | in_off=False in_pt=True | lost_to=Transmuter/AU/subclass
- Bladesinger | XUA2025FORGOTTENREALMSSUBCLASSES | subclass | className=Wizard | in_off=False in_pt=True | lost_to=Bladesinger/FRHOF/subclass
- College of the Moon | XUA2025FORGOTTENREALMSSUBCLASSES | subclass | className=Bard | in_off=False in_pt=True | lost_to=College of the Moon/FRHOF/subclass
- Knowledge Domain | XUA2025FORGOTTENREALMSSUBCLASSES | subclass | className=Cleric | in_off=False in_pt=True | lost_to=Knowledge Domain/FRHOF/subclass
- Oath of the Noble Genies | XUA2025FORGOTTENREALMSSUBCLASSES | subclass | className=Paladin | in_off=False in_pt=True | lost_to=Oath of the Noble Genies/FRHOF/subclass
- Scion of the Three | XUA2025FORGOTTENREALMSSUBCLASSES | subclass | className=Rogue | in_off=False in_pt=True | lost_to=Scion of the Three/FRHOF/subclass
- Spellfire Sorcery | XUA2025FORGOTTENREALMSSUBCLASSES | subclass | className=Sorcerer | in_off=False in_pt=True | lost_to=Spellfire Sorcery/FRHOF/subclass
- Winter Walker | XUA2025FORGOTTENREALMSSUBCLASSES | subclass | className=Ranger | in_off=False in_pt=True | lost_to=Winter Walker/FRHOF/subclass
- College of Spirits | XUA2025HORRORSUBCLASSES | subclass | className=Bard | in_off=False in_pt=True | lost_to=College of Spirits/RHW/subclass
- Grave Domain | XUA2025HORRORSUBCLASSES | subclass | className=Cleric | in_off=False in_pt=True | lost_to=Grave Domain/RHW/subclass
- Hollow Warden | XUA2025HORRORSUBCLASSES | subclass | className=Ranger | in_off=False in_pt=True | lost_to=Hollow Warden/RHW/subclass
- Phantom | XUA2025HORRORSUBCLASSES | subclass | className=Rogue | in_off=False in_pt=True | lost_to=Phantom/RHW/subclass
- Reanimator | XUA2025HORRORSUBCLASSES | subclass | className=Artificer | in_off=False in_pt=True | lost_to=Reanimator/RHW/subclass
- Shadow Sorcery | XUA2025HORRORSUBCLASSES | subclass | className=Sorcerer | in_off=False in_pt=True | lost_to=Shadow Sorcery/RHW/subclass
- Undead Patron | XUA2025HORRORSUBCLASSES | subclass | className=Warlock | in_off=False in_pt=True | lost_to=Undead Patron/RHW/subclass
- Vestige Patron | XUA2026MYSTICSUBCLASSES | subclass | className=Warlock | in_off=False in_pt=True | lost_to=Vestige Patron/AU/subclass
- Warrior of the Mystic Arts | XUA2026MYSTICSUBCLASSES | subclass | className=Monk | in_off=False in_pt=True | lost_to=Warrior of the Mystic Arts/AU/subclass
