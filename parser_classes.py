import copy
import json

from parser_utils import (
    BYPASS_EXCLUDED_SOURCES_DTYPES,
    PRE_FILTER_HOOKS,
    META_ONLY_DTYPES,
)

# ---------------------------------------------------------------------------
# META-ONLY REGISTRATION
# classFeature and subclassFeature are reference data consumed by the class
# enrichers.  They must never be rendered as standalone cards.
# ---------------------------------------------------------------------------
META_ONLY_DTYPES.update({'classFeature', 'subclassFeature'})


# ---------------------------------------------------------------------------
# BYPASS EXCLUDED SOURCES
# Classes and subclasses should always pass through the global source filter.
# ---------------------------------------------------------------------------
BYPASS_EXCLUDED_SOURCES_DTYPES.update({'class', 'subclass'})


# ---------------------------------------------------------------------------
# ARCHETYPE & TAG HELPERS
# ---------------------------------------------------------------------------

def determine_class_archetypes(item, all_raw):
    """Dynamically determines if a class is a Spellcaster, Half-Caster, Martial, or Gish."""
    archetypes = []
    has_spell_cols = False
    has_9th_level = False

    # 1. Check Table Columns
    for group in item.get('classTableGroups', []):
        for lbl in group.get('colLabels', []):
            lbl_str = str(lbl if not isinstance(lbl, dict) else lbl.get('name', '')).lower()
            if 'spell' in lbl_str or 'cantrip' in lbl_str or 'slot' in lbl_str:
                has_spell_cols = True
            if '9th' in lbl_str or 'level=9' in lbl_str:
                has_9th_level = True

    # 2. Check explicitly declared progressions
    prog = item.get('casterProgression', '')
    if prog in ('full', 'pact'):
        has_spell_cols = True
        has_9th_level = True
    elif prog in ('half', 'artificer'):
        has_spell_cols = True

    # 3. Assign Archetypes
    if has_9th_level:
        archetypes.append("Spellcaster")
    elif has_spell_cols:
        archetypes.append("Half-Caster")
    else:
        # It's a Martial class. Let's see if it has Gish (Spellcasting) subclasses.
        has_caster_subclass = False
        class_name = str(item.get('name', '')).lower().strip()
        if all_raw:
            for f in all_raw:
                if f.get('_data_type') == 'subclass' and str(f.get('className', '')).lower().strip() == class_name:
                    if f.get('casterProgression') or 'spellcastingAbility' in f:
                        has_caster_subclass = True
                        break
                    # Check subclass tables as a fallback
                    for sg in f.get('subclassTableGroups', []):
                        for lbl in sg.get('colLabels', []):
                            lbl_str = str(lbl if not isinstance(lbl, dict) else lbl.get('name', '')).lower()
                            if 'spell' in lbl_str or 'cantrip' in lbl_str or 'slot' in lbl_str:
                                has_caster_subclass = True
                                break
                        if has_caster_subclass:
                            break
                if has_caster_subclass:
                    break

        archetypes.append("Martial")
        if has_caster_subclass:
            archetypes.append("Gish / Subclass Caster")

    return archetypes


def determine_subclass_archetypes(item, all_raw):
    """Subclasses inherit the parent class archetype, but can add Gish if they grant casting."""
    archetypes = []
    class_name = str(item.get('className', '')).lower().strip()

    # 1. Get Parent Class
    parent_class = next((f for f in all_raw if f.get('_data_type') == 'class' and str(f.get('name', '')).lower().strip() == class_name), None)
    parent_archetypes = determine_class_archetypes(parent_class, []) if parent_class else ["Martial"]

    # 2. Check if this specific subclass grants spellcasting
    has_sub_casting = bool(item.get('casterProgression') or 'spellcastingAbility' in item)
    if not has_sub_casting:
        for sg in item.get('subclassTableGroups', []):
            for lbl in sg.get('colLabels', []):
                lbl_str = str(lbl if not isinstance(lbl, dict) else lbl.get('name', '')).lower()
                if 'spell' in lbl_str or 'cantrip' in lbl_str or 'slot' in lbl_str:
                    has_sub_casting = True
                    break
            if has_sub_casting:
                break

    # 3. Assign Inherited Archetypes
    if "Spellcaster" in parent_archetypes:
        archetypes.append("Spellcaster")
    elif "Half-Caster" in parent_archetypes:
        archetypes.append("Half-Caster")
    else:
        archetypes.append("Martial")
        if has_sub_casting:
            archetypes.append("Gish / Subclass Caster")

    return archetypes


# ---------------------------------------------------------------------------
# PRE-FILTER HOOK
# Injects 'archetype' and normalises 'className' for subclasses so that both
# fields are available during the filter pass before enrichment runs.
# Also handles the subclass-parent name filter: a subclass passes a name filter
# if its own name OR its parent className matches, so we inject a
# 'filter_class_name' field the engine can check uniformly via the generic
# list-value path rather than needing dtype-specific branching.
# ---------------------------------------------------------------------------
def _class_pre_filter_hook(norm_item: dict, primary_file: str, all_raw: list) -> None:
    dtype = norm_item.get('_data_type', '')

    if dtype == 'class':
        norm_item['archetype'] = determine_class_archetypes(norm_item, all_raw)
        # For the name filter, classes match on their own name.
        norm_item['filter_class_name'] = [norm_item.get('name', '')]

    elif dtype == 'subclass':
        norm_item['archetype'] = determine_subclass_archetypes(norm_item, all_raw)
        # For the name filter, subclasses match on their own name OR their parent className.
        own_name = norm_item.get('name', '')
        parent_name = norm_item.get('className', '')
        names = [n for n in [own_name, parent_name] if n]
        norm_item['filter_class_name'] = names

for _dt in ('class', 'subclass'):
    PRE_FILTER_HOOKS[_dt] = _class_pre_filter_hook


# ---------------------------------------------------------------------------
# OPTIONAL FEATURE HELPERS
# ---------------------------------------------------------------------------

def build_optional_feature_index(all_raw):
    """
    Indexes all optionalfeature items from all_raw by (name.lower, source.upper).
    Also indexes by name.lower alone as a fallback.
    """
    index = {}
    for f in all_raw:
        if f.get('_data_type') in ('optionalfeature', 'optionalfeatures'):
            name = f.get('name', '').lower().strip()
            source = f.get('source', '').upper().strip()
            index[(name, source)] = f
            if name not in index:
                index[name] = f
    return index


def format_optional_feature_prereqs(prereqs):
    """
    Translates a list of prerequisite dicts into a human-readable string.
    """
    parts = []
    for p in prereqs:
        if 'level' in p:
            lvl = p['level']
            if isinstance(lvl, dict):
                cls_name = lvl.get('class', {}).get('name', '')
                parts.append(f"Level {lvl.get('level')} {cls_name}".strip())
            else:
                parts.append(f"Level {lvl}")
        if 'pact' in p:
            parts.append(f"Pact of the {p['pact']}")
        if 'spell' in p:
            spells = [s.split('|')[0].replace('#c', '') for s in p['spell'] if isinstance(s, str)]
            if spells:
                parts.append(f"Spell: {', '.join(spells)}")
        if 'item' in p:
            parts.append(f"Item: {', '.join(p['item'])}")
        if 'feat' in p:
            feats = [f.split('|')[0] for f in p['feat'] if isinstance(f, str)]
            if feats:
                parts.append(f"Feat: {', '.join(feats)}")
        if 'otherSummary' in p:
            summary = p['otherSummary'].get('entrySummary', '')
            if summary:
                parts.append(summary)
        if 'other' in p and isinstance(p['other'], str):
            parts.append(p['other'])
    return ', '.join(part for part in parts if part)


def resolve_ref_optional_feature(ref_str, opt_index):
    """
    Resolves a 'Name|SOURCE' reference string to an optionalfeature dict.
    e.g. 'Agonizing Blast|XPHB'
    """
    parts = ref_str.split('|')
    name = parts[0].strip().lower()
    source = parts[1].strip().upper() if len(parts) > 1 else ''
    return opt_index.get((name, source)) or opt_index.get(name)


def extract_repeatable(entries):
    """
    Finds and removes any 'Repeatable' named entry block from a feature's entries list.
    The pattern in the data is a double-nested wrapper:
        {type: entries, entries: [{type: entries, name: Repeatable, entries: [...text...]}]}

    Returns (cleaned_entries, repeatable_text) where repeatable_text is None if not found.
    Works for any optionalfeature that uses this pattern, not just Warlock invocations.
    """
    cleaned = []
    repeatable_text = None

    for entry in entries:
        if not isinstance(entry, dict):
            cleaned.append(entry)
            continue

        # Look for the unnamed wrapper block that contains the Repeatable named block
        if entry.get('type') == 'entries' and 'name' not in entry:
            inner_entries = entry.get('entries', [])
            non_repeatable = []
            for inner in inner_entries:
                if (isinstance(inner, dict) and
                        inner.get('type') == 'entries' and
                        inner.get('name', '').strip().lower() == 'repeatable'):
                    # Extract all text from the Repeatable block
                    texts = [t for t in inner.get('entries', []) if isinstance(t, str)]
                    repeatable_text = ' '.join(texts)
                else:
                    non_repeatable.append(inner)

            # Only keep the wrapper if it still has non-repeatable content
            if non_repeatable:
                new_entry = copy.deepcopy(entry)
                new_entry['entries'] = non_repeatable
                cleaned.append(new_entry)
            # If the wrapper only contained Repeatable, drop it entirely
        else:
            cleaned.append(entry)

    return cleaned, repeatable_text


def build_optional_feature_entry(opt):
    """
    Converts a single optionalfeature item into an entry dict for
    embedding inside a class feature's entries list.

    Prerequisites are shown in italics at the top.
    Repeatable notes are extracted from the nested structure and shown
    in italics at the bottom, clearly attached to their parent option.
    """
    prereqs = opt.get('prerequisite', [])
    prereq_str = format_optional_feature_prereqs(prereqs)

    raw_entries = list(opt.get('entries', []))
    cleaned_entries, repeatable_text = extract_repeatable(raw_entries)

    sub_entries = []
    if prereq_str:
        sub_entries.append(f"<i>Prerequisites: {prereq_str}</i>")
    sub_entries.extend(cleaned_entries)
    if repeatable_text:
        sub_entries.append(f"<i>Repeatable: {repeatable_text}</i>")

    return {
        "type": "item",
        "name": opt.get('name', 'Unknown'),
        "entries": sub_entries
    }


def resolve_feature_entries(entries, opt_index, all_features=None):
    """
    Recursively walks a feature's entries list and resolves:
    1. 'type: options' blocks with 'refOptionalfeature'
    2. 'type: refSubclassFeature' references (inlined)
    3. 'type: refClassFeature' references (inlined)
    """
    if not isinstance(entries, list):
        return entries

    result = []
    for entry in entries:
        if not isinstance(entry, dict):
            result.append(entry)
            continue

        e_type = entry.get('type')

        if e_type == 'options':
            resolved_opts = []
            for sub in entry.get('entries', []):
                if isinstance(sub, dict) and sub.get('type') == 'refOptionalfeature':
                    ref_str = sub.get('optionalfeature', '')
                    opt = resolve_ref_optional_feature(ref_str, opt_index)
                    if opt:
                        resolved_opts.append(opt)

            if resolved_opts:
                resolved_opts.sort(key=lambda x: x.get('name', '').lower())
                for opt in resolved_opts:
                    result.append(build_optional_feature_entry(opt))
            else:
                result.append(entry)

        elif e_type in ('refSubclassFeature', 'refClassFeature') and all_features:
            is_subclass_ref = e_type == 'refSubclassFeature'
            ref_str = entry.get('subclassFeature') if is_subclass_ref else entry.get('classFeature', '')

            parts = ref_str.split('|')
            ref_name = parts[0].strip().lower()
            ref_class = parts[1].strip().lower() if len(parts) > 1 else ""

            ref_subclass = ""
            ref_source = ""
            ref_level = parts[5 if is_subclass_ref else 3] if len(parts) > (5 if is_subclass_ref else 3) else ""

            # Robustly parse 5etools pipe syntax
            if is_subclass_ref:
                ref_subclass = parts[3].strip().lower() if len(parts) > 3 else ""
                if len(parts) >= 7 and parts[6].strip():
                    ref_source = parts[6].strip().upper()
                elif len(parts) >= 5 and parts[4].strip():
                    ref_source = parts[4].strip().upper()
            else:
                if len(parts) >= 5 and parts[4].strip():
                    ref_source = parts[4].strip().upper()
                elif len(parts) >= 3 and parts[2].strip():
                    ref_source = parts[2].strip().upper()

            target = None
            for f in all_features:
                if f.get('_data_type') == ('subclassFeature' if is_subclass_ref else 'classFeature'):
                    f_name = str(f.get('name', '')).strip().lower()
                    f_source = str(f.get('source', '')).strip().upper()

                    if f_name == ref_name and (not ref_source or f_source == ref_source):
                        if ref_level and str(f.get("level", "")) != ref_level: continue
                        f_class = str(f.get('className', '')).strip().lower()
                        if ref_class and f_class != ref_class: continue

                        if is_subclass_ref:
                            f_subclass = str(f.get('subclassShortName', '')).strip().lower()
                            if ref_subclass and f_subclass != ref_subclass: continue

                        target = f
                        break

            if target:
                resolved_inner = resolve_feature_entries(target.get('entries', []), opt_index, all_features)
                result.append({
                    "type": "item",
                    "name": target.get('name'),
                    "entries": resolved_inner
                })
            else:
                result.append(entry)

        elif 'entries' in entry:
            new_entry = copy.deepcopy(entry)
            new_entry['entries'] = resolve_feature_entries(entry['entries'], opt_index, all_features)
            result.append(new_entry)

        else:
            result.append(entry)

    return result


# ---------------------------------------------------------------------------
# TABLE BUILDER
# ---------------------------------------------------------------------------

def process_class_tables(item, is_subclass=False):
    """
    Intelligently splits the classTableGroups.
    Columns involving 'spell', 'cantrip', or 'slot' go to the Spellcasting table.
    All other columns (Bardic Die, Sneak Attack, Infusions) merge into the Class Progression.
    """
    tables = []
    name = item.get('name', 'Unknown')

    # 1. Build basic progression features
    features_by_level = {i: [] for i in range(1, 21)}
    feat_key = 'subclassFeatures' if is_subclass else 'classFeatures'
    class_features = item.get(feat_key, [])
    for f in class_features:
        feat_string = f if isinstance(f, str) else f.get('classFeature', '')
        parts = feat_string.split('|')
        level = 0
        if is_subclass and len(parts) >= 6:
            try:
                level = int(parts[5])
            except ValueError:
                pass
        elif not is_subclass and len(parts) >= 4:
            try:
                level = int(parts[3])
            except ValueError:
                pass

        if 1 <= level <= 20:
            features_by_level[level].append(parts[0])

    # 2. Extract columns from table groups
    progression_cols = []
    spell_cols = []
    spell_progression = None
    spell_labels = []

    table_groups = item.get('subclassTableGroups', []) if is_subclass else item.get('classTableGroups', [])

    for group in table_groups:
        if 'rows' in group:
            labels = group.get('colLabels', [])
            for col_idx, label in enumerate(labels):
                col_vals = []
                for row in group['rows']:
                    r = row if isinstance(row, list) else row.get('row', [])
                    if col_idx < len(r):
                        col_vals.append(r[col_idx])
                    else:
                        col_vals.append("-")

                lbl_str = str(label) if not isinstance(label, dict) else str(label.get('name', ''))
                lbl_lower = lbl_str.lower()

                if 'spell' in lbl_lower or 'cantrip' in lbl_lower or 'slot' in lbl_lower:
                    spell_cols.append((label, col_vals))
                else:
                    progression_cols.append((label, col_vals))

        if 'rowsSpellProgression' in group:
            spell_progression = group['rowsSpellProgression']
            spell_labels = group.get('colLabels', [])

    # 3. Build Progression Table
    prog_rows = []
    prog_col_labels = ["Level", "PB", "Features"] + [col[0] for col in progression_cols]

    max_level = 20
    for level in range(1, max_level + 1):
        row = [str(level)]
        row.append(f"+{2 + (level - 1) // 4}")
        feats = ", ".join(features_by_level[level]) if features_by_level.get(level) else "-"
        row.append(feats)
        for col in progression_cols:
            vals = col[1]
            val = vals[level - 1] if level - 1 < len(vals) else "-"
            row.append(val)
        prog_rows.append(row)

    has_any_features = any(features_by_level.values()) or progression_cols
    if has_any_features or not is_subclass:
        tables.append({
            'type': 'table',
            'name': f"{name} Progression",
            'colLabels': prog_col_labels,
            'rows': prog_rows,
            '_force_portrait': True,
            '_unbreakable': True,
            '_standalone': True
        })

    # 4. Build Spell Table
    if spell_progression or spell_cols:
        spell_table_rows = []
        s_labels = ["Level"] + [col[0] for col in spell_cols] + spell_labels

        has_9th_level = any(
            '9th' in str(lbl).lower() or 'level=9' in str(lbl).lower()
            for lbl in s_labels
        )

        s_max_level = max(
            len(spell_progression) if spell_progression else 0,
            len(spell_cols[0][1]) if spell_cols else 0
        )
        if s_max_level == 0:
            s_max_level = 20

        for level in range(1, s_max_level + 1):
            row = [str(level)]
            for col in spell_cols:
                vals = col[1]
                val = vals[level - 1] if level - 1 < len(vals) else "-"
                row.append(val)

            if spell_progression and level - 1 < len(spell_progression):
                row.extend(spell_progression[level - 1])
            elif spell_progression:
                row.extend(["-"] * len(spell_labels))

            spell_table_rows.append(row)

        if has_9th_level and len(spell_table_rows) > 10:
            tables.append({
                'type': 'table',
                'name': f"{name} Spellcasting",
                'colLabels': s_labels,
                'rows': spell_table_rows[:10],
                '_force_portrait': False,
                '_force_landscape': True,
                '_unbreakable': True,
                '_standalone': True
            })
            tables.append({
                'type': 'table',
                'name': f"{name} Spellcasting",
                'colLabels': s_labels,
                'rows': spell_table_rows[10:],
                '_force_portrait': False,
                '_force_landscape': True,
                '_unbreakable': True,
                '_standalone': True
            })
        else:
            tables.append({
                'type': 'table',
                'name': f"{name} Spellcasting",
                'colLabels': s_labels,
                'rows': spell_table_rows,
                '_force_portrait': not has_9th_level,
                '_force_landscape': has_9th_level,
                '_unbreakable': True,
                '_standalone': True
            })

    return tables


# ---------------------------------------------------------------------------
# PROFICIENCY HELPER
# ---------------------------------------------------------------------------

def safe_join_proficiencies(prof_list, item_type=""):
    """Safely unpacks 5eTools proficiency arrays."""
    if not isinstance(prof_list, list):
        return str(prof_list)

    out = []
    for p in prof_list:
        if isinstance(p, str):
            out.append(p[0].upper() + p[1:] if p else "")
        elif isinstance(p, dict):
            if 'choose' in p:
                choose = p['choose']
                count = choose.get('count', 1)
                from_list = choose.get('from', [])
                safe_from = [
                    f if isinstance(f, str) else str(f.get('name', 'options'))
                    for f in from_list
                ]
                out.append(f"Choose {count} from {', '.join(safe_from)}")
            elif 'any' in p:
                count = p['any']
                out.append(f"Choose any {count} {item_type}".strip())
            else:
                out.append("Various Options")
    return ", ".join(out)


# ---------------------------------------------------------------------------
# CLASS ENRICHER
# ---------------------------------------------------------------------------

def enrich_class(item, type_map=None, all_raw=None):
    result = copy.deepcopy(item)
    name = result.get('name', 'Unknown Class')
    entries = []

    opt_index = build_optional_feature_index(all_raw) if all_raw else {}

    ABILITY_MAP = {
        'str': 'Strength', 'dex': 'Dexterity', 'con': 'Constitution',
        'int': 'Intelligence', 'wis': 'Wisdom', 'cha': 'Charisma'
    }

    if 'archetype' not in result:
        result['archetype'] = determine_class_archetypes(item, all_raw)

    pa_list = result.get('primaryAbility', [])
    pa_strs = []

    if pa_list:
        for pa in pa_list:
            if isinstance(pa, dict):
                opts = [ABILITY_MAP.get(k, k.capitalize()) for k, v in pa.items() if v]
                if opts:
                    pa_strs.append(" or ".join(opts))
    else:
        mc_reqs = result.get('multiclassing', {}).get('requirements', {})
        opts = []
        for k, v in mc_reqs.items():
            if k == 'or':
                or_opts = []
                for sub_req in v:
                    or_opts.extend([ABILITY_MAP.get(sk, sk.capitalize()) for sk in sub_req.keys() if sk in ABILITY_MAP])
                if or_opts:
                    opts.append(" or ".join(or_opts))
            elif k in ABILITY_MAP:
                opts.append(ABILITY_MAP[k])
        if opts:
            pa_strs.append(" and ".join(opts))

    if pa_strs:
        entries.append({"type": "item", "name": "Primary Ability", "entry": " and ".join(pa_strs)})

    hd = result.get('hd', {})
    if hd:
        entries.append({"type": "item", "name": "Hit Dice",
                        "entry": f"{hd.get('number', 1)}d{hd.get('faces', 8)} per {name} level"})
        entries.append({"type": "item", "name": "Hit Points at 1st Level",
                        "entry": f"{hd.get('faces', 8)} + your Constitution modifier"})
        entries.append({"type": "item", "name": "Hit Points at Higher Levels",
                        "entry": (f"1d{hd.get('faces', 8)} (or {hd.get('faces', 8) // 2 + 1})"
                                  f" + your Constitution modifier per {name} level after 1st")})

    saves = result.get('proficiency', [])
    if saves:
        save_strs = [ABILITY_MAP.get(s, s.capitalize()) for s in saves]
        entries.append({"type": "item", "name": "Saving Throw Proficiencies", "entry": ", ".join(save_strs)})

    prof = result.get('startingProficiencies', {})
    if prof:
        entries.append({"type": "nested_header", "name": "Proficiencies"})
        if 'armor' in prof:
            entries.append({"type": "item", "name": "Armor",
                            "entry": safe_join_proficiencies(prof['armor'], "armor")})
        if 'weapons' in prof:
            entries.append({"type": "item", "name": "Weapons",
                            "entry": safe_join_proficiencies(prof['weapons'], "weapons")})
        if 'tools' in prof:
            entries.append({"type": "item", "name": "Tools",
                            "entry": safe_join_proficiencies(prof['tools'], "tools")})
        if 'skills' in prof:
            entries.append({"type": "item", "name": "Skills",
                            "entry": safe_join_proficiencies(prof['skills'], "skills")})

    entries.extend(process_class_tables(item, is_subclass=False))

    # 6. Fetch and Append Class Features via direct ordered array mapping
    if all_raw:
        class_name = str(result.get('name', '')).lower().strip()
        class_source = str(result.get('source', '')).upper().strip()

        class_features_refs = result.get('classFeatures', [])

        for ref in class_features_refs:
            ref_str = ref if isinstance(ref, str) else ref.get('classFeature', '')
            if not ref_str: continue

            parts = ref_str.split('|')
            ref_name = parts[0].strip().lower()
            ref_source = ""

            if len(parts) >= 5 and parts[4].strip():
                ref_source = parts[4].strip().upper()
            elif len(parts) >= 3 and parts[2].strip():
                ref_source = parts[2].strip().upper()

            level = 0
            if len(parts) >= 4 and parts[3].isdigit():
                level = int(parts[3])

            target = None
            for f in all_raw:
                if f.get('_data_type') == 'classFeature':
                    f_name = str(f.get('name', '')).strip().lower()
                    f_source = str(f.get('source', '')).strip().upper()

                    if f_name == ref_name and (not ref_source or f_source == ref_source):
                        if level and str(f.get("level", "")) != str(level): continue
                        if str(f.get('className', '')).lower().strip() == class_name and \
                                str(f.get('classSource', '')).upper().strip() == class_source:
                            target = f
                            break

            if target:
                feature_entries = resolve_feature_entries(target.get('entries', []), opt_index, all_raw)
                entries.append({
                    "type": "item",
                    "name": f"{target.get('name')} (Level {level})",
                    "entries": feature_entries
                })

    result['entries'] = entries
    result['meta_left'] = "Class Overview"
    result['_data_type'] = "class"
    return result


# ---------------------------------------------------------------------------
# SUBCLASS ENRICHER
# ---------------------------------------------------------------------------

def enrich_subclass(item, type_map=None, all_raw=None):
    result = copy.deepcopy(item)
    parent_class = result.get('className', 'Unknown Class')
    entries = []

    opt_index = build_optional_feature_index(all_raw) if all_raw else {}

    if 'archetype' not in result:
        result['archetype'] = determine_subclass_archetypes(item, all_raw)

    entries.extend(process_class_tables(item, is_subclass=True))

    # 2. Fetch and Append Subclass Features via direct ordered array mapping
    if all_raw:
        subclass_short_name = str(result.get('shortName', '')).lower().strip()
        class_name = str(result.get('className', '')).lower().strip()

        subclass_features_refs = result.get('subclassFeatures', [])

        for ref in subclass_features_refs:
            ref_str = ref if isinstance(ref, str) else ref.get('subclassFeature', '')
            if not ref_str: continue

            parts = ref_str.split('|')
            ref_name = parts[0].strip().lower()
            ref_source = ""

            if len(parts) >= 7 and parts[6].strip():
                ref_source = parts[6].strip().upper()
            elif len(parts) >= 5 and parts[4].strip():
                ref_source = parts[4].strip().upper()

            level = 0
            if len(parts) >= 6 and parts[5].isdigit():
                level = int(parts[5])

            target = None
            for f in all_raw:
                if f.get('_data_type') == 'subclassFeature':
                    f_name = str(f.get('name', '')).strip().lower()
                    f_source = str(f.get('source', '')).strip().upper()

                    if f_name == ref_name and (not ref_source or f_source == ref_source):
                        if level and str(f.get("level", "")) != str(level): continue
                        if str(f.get('className', '')).lower().strip() == class_name and \
                                str(f.get('subclassShortName', '')).lower().strip() == subclass_short_name:
                            target = f
                            break

            if target:
                f_entries = resolve_feature_entries(target.get('entries', []), opt_index, all_raw)
                entries.append({
                    "type": "item",
                    "name": f"{target.get('name')} (Level {level})",
                    "entries": f_entries
                })

    result['entries'] = entries
    result['meta_left'] = f"{parent_class} Subclass"
    result['_data_type'] = "subclass"
    return result