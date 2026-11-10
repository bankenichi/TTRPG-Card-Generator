import copy
import math
from parser_utils import (
    BYPASS_EXCLUDED_SOURCES_DTYPES,
    PRE_FILTER_HOOKS,
    META_ONLY_DTYPES,
    FOOTER_RENDERERS
)

# Register meta types
META_ONLY_DTYPES.update({'legendaryGroup', 'monsterTemplate'})
BYPASS_EXCLUDED_SOURCES_DTYPES.add('monster')

def _parse_cr(cr_val):
    if isinstance(cr_val, dict):
        return cr_val.get('cr', '0')
    return str(cr_val)

def _parse_size(size_list):
    if not size_list: return "M"
    if isinstance(size_list, list):
        return size_list[0]
    return str(size_list)

def _parse_type(type_val):
    if isinstance(type_val, dict):
        return type_val.get('type', 'Unknown')
    return str(type_val)

def pre_filter_monster(norm_item, primary_file, all_raw):
    # CRITICAL: Save backups of the raw dictionaries before we convert them 
    # to strings for the filters. This ensures the card renderer can still 
    # access the tags/subtypes and lair CRs later.
    norm_item['_raw_type'] = copy.deepcopy(norm_item.get('type'))
    norm_item['_raw_cr'] = copy.deepcopy(norm_item.get('cr'))
    
    # Inject filters using the raw types so exact-match filtering doesn't break
    cr = _parse_cr(norm_item.get('cr', '0'))
    sz = _parse_size(norm_item.get('size', ['M']))
    typ = _parse_type(norm_item.get('type', 'Unknown'))
    
    norm_item['cr'] = cr
    norm_item['size'] = sz
    norm_item['type'] = typ

PRE_FILTER_HOOKS['monster'] = pre_filter_monster

def _format_display_type(type_val):
    """Safely extracts subtypes strictly for visual display on the card headers."""
    if isinstance(type_val, dict):
        base_val = type_val.get('type', 'Unknown')
        if isinstance(base_val, dict):
            base_val = base_val.get('type', 'Unknown')
            
        base_type = str(base_val).title()
        tags = type_val.get('tags', [])
        
        if tags:
            parsed_tags = []
            for t in tags:
                if isinstance(t, dict):
                    tag_val = t.get('tag') or t.get('prefix') or ''
                    tag_str = str(tag_val).strip()
                    if tag_str: 
                        parsed_tags.append(tag_str.title())
                else:
                    parsed_tags.append(str(t).title())
            
            if parsed_tags:
                return f"{base_type} ({', '.join(parsed_tags)})"
        return base_type
    return str(type_val).title()

def get_save_mod(item, ability, default_mod):
    """Fetches the explicit save from 5etools, or falls back to the stat modifier."""
    saves = item.get('save', {})
    if ability in saves:
        try:
            return int(str(saves[ability]).replace('+', ''))
        except ValueError:
            pass
    return default_mod

def _build_stats_table(item):
    str_score = item.get('str', 10)
    dex_score = item.get('dex', 10)
    con_score = item.get('con', 10)
    int_score = item.get('int', 10)
    wis_score = item.get('wis', 10)
    cha_score = item.get('cha', 10)
    
    def calc_mod(score):
        try:
            val = int(score)
            mod = (val - 10) // 2
            return mod
        except (ValueError, TypeError):
            return 0

    str_mod = calc_mod(str_score)
    dex_mod = calc_mod(dex_score)
    con_mod = calc_mod(con_score)
    int_mod = calc_mod(int_score)
    wis_mod = calc_mod(wis_score)
    cha_mod = calc_mod(cha_score)

    str_s = get_save_mod(item, 'str', str_mod)
    dex_s = get_save_mod(item, 'dex', dex_mod)
    con_s = get_save_mod(item, 'con', con_mod)
    int_s = get_save_mod(item, 'int', int_mod)
    wis_s = get_save_mod(item, 'wis', wis_mod)
    cha_s = get_save_mod(item, 'cha', cha_mod)

    def f_mod(val):
        return f"+{val}" if val >= 0 else str(val)

    # 3-Column matrix removing borders between internal sections
    return {
        "type": "table",
        "colLabels": ['', '', 'MOD', 'SAVE'],
        "colStyles": [
            'auto-w text-right border-0', 'auto-w text-left border-0', 'auto-w text-center border-0', 'auto-w text-center border-0'
        ],
        "rows": [
            [f"STR", str_score, f_mod(str_mod), f_mod(str_s)],
            [f"DEX", dex_score, f_mod(dex_mod), f_mod(dex_s)],
            [f"CON", con_score, f_mod(con_mod), f_mod(con_s)],
            [f"INT", int_score, f_mod(int_mod), f_mod(int_s)],
            [f"WIS", wis_score, f_mod(wis_mod), f_mod(wis_s)],
            [f"CHA", cha_score, f_mod(cha_mod), f_mod(cha_s)]
        ],
        "_unbreakable": True
    }

def _parse_spellcasting(spellcasting_list):
    """Converts 5etools spellcasting arrays into formatted standard entries."""
    if not spellcasting_list: return []
    
    def _get_spell_str(spell_val):
        if isinstance(spell_val, dict):
            return str(spell_val.get('entry') or spell_val.get('name') or spell_val)
        return str(spell_val)

    entries = []
    for sc in spellcasting_list:
        name = sc.get('name', 'Spellcasting')
        sc_entries = []
        
        if 'headerEntries' in sc:
            sc_entries.extend(sc['headerEntries'])
        
        if 'will' in sc:
            sc_entries.append(f"At will: {', '.join(_get_spell_str(x) for x in sc['will'])}")
        
        if 'daily' in sc:
            for k, v in sc['daily'].items():
                amt = k.replace('e', '')
                suffix = " each" if 'e' in k else ""
                sc_entries.append(f"{amt}/day{suffix}: {', '.join(_get_spell_str(x) for x in v)}")
        
        if 'spells' in sc:
            for lvl, data in sc['spells'].items():
                spell_list = ', '.join(_get_spell_str(x) for x in data.get('spells', []))
                if lvl == '0':
                    sc_entries.append(f"Cantrips (at will): {spell_list}")
                else:
                    slots = data.get('slots', 0)
                    l = int(lvl)
                    ord_s = f"{l}th" if 11 <= (l % 100) <= 13 else f"{l}{['th','st','nd','rd','th'][min(l % 10, 4)]}"
                    slot_str = f"{slots} slot{'s' if slots != 1 else ''}"
                    sc_entries.append(f"{ord_s} level ({slot_str}): {spell_list}")
                    
        if 'footerEntries' in sc:
            sc_entries.extend(sc['footerEntries'])
            
        entries.append({"type": "item", "name": name, "entries": sc_entries})
    return entries

def _format_ac(ac_list):
    if not ac_list: return "10"
    if isinstance(ac_list, list):
        val = ac_list[0]
        if isinstance(val, dict):
            ac = str(val.get('ac', '10'))
            from_str = ", ".join(val.get('from', []))
            cond = val.get('condition', '')
            if from_str and cond: return f"{ac} ({from_str} {cond})"
            elif from_str: return f"{ac} ({from_str})"
            elif cond: return f"{ac} {cond}"
            return ac
        return str(val)
    return str(ac_list)

def _format_hp(hp_val):
    if not hp_val: return "1"
    if isinstance(hp_val, dict):
        avg = hp_val.get('average', '')
        formula = hp_val.get('formula', '')
        if avg and formula: return f"{avg} ({formula})"
        return str(avg or formula or '1')
    return str(hp_val)

def _format_speed(speed_val):
    if not speed_val: return "30 ft."
    if isinstance(speed_val, dict):
        parts = []
        for k, v in speed_val.items():
            if k == 'canHover': continue
            if isinstance(v, bool):
                if v: parts.append(f"{k} equal to walking speed")
                continue
            if k == 'walk': parts.append(f"{v} ft.")
            elif k == 'choose':
                c = v.get('from', [])
                num = v.get('amount', 0)
                note = v.get('note', '')
                parts.append(f"choose {', '.join(c)} {num} ft. {note}".strip())
            else:
                if isinstance(v, dict):
                    num = v.get('number', 0)
                    cond = v.get('condition', '')
                    parts.append(f"{k} {num} ft. {cond}".strip())
                else:
                    parts.append(f"{k} {v} ft.")
        return ", ".join(parts)
    return str(speed_val)

def _format_traits(traits_list):
    if not traits_list: return ""
    parts = []
    for t in traits_list:
        if isinstance(t, str): parts.append(t)
        elif isinstance(t, dict):
            if 'special' in t: parts.append(t['special'])
            elif 'resist' in t: 
                sub = _format_traits(t['resist'])
                note = t.get('note', '')
                parts.append(f"{sub} {note}".strip())
            elif 'immune' in t:
                sub = _format_traits(t['immune'])
                note = t.get('note', '')
                parts.append(f"{sub} {note}".strip())
            elif 'conditionImmune' in t:
                sub = _format_traits(t['conditionImmune'])
                note = t.get('note', '')
                parts.append(f"{sub} {note}".strip())
            elif 'vulnerable' in t:
                sub = _format_traits(t['vulnerable'])
                note = t.get('note', '')
                parts.append(f"{sub} {note}".strip())
            else:
                for k, v in t.items():
                    if isinstance(v, list): parts.append(_format_traits(v))
    return ", ".join(parts)

def _format_skills(skills_dict):
    if not skills_dict: return ""
    parts = [f"{k.title()} {v}" for k, v in skills_dict.items()]
    return ", ".join(parts)

def _format_senses(senses_list, passive):
    parts = []
    if senses_list:
        if isinstance(senses_list, str):
            parts.append(senses_list)
        else:
            for s in senses_list:
                if isinstance(s, str): parts.append(s)
                elif isinstance(s, dict): parts.append(s.get('entry', ''))
    
    parts.append(f"Passive Perception {passive}")
    return ", ".join(parts)

def _format_languages(lang_list):
    if not lang_list: return "\u2014"
    if isinstance(lang_list, str): return lang_list
    parts = []
    for l in lang_list:
        if isinstance(l, str): parts.append(l)
    return ", ".join(parts)

def _title_case_traits(text):
    """Formats lower-case trait lists into proper title case for visual appeal."""
    if not text: return ""
    words = text.split(" ")
    out = []
    for w in words:
        w_lower = w.lower()
        if w_lower in ('and', 'or', 'from', 'by', 'of', 'with', 'the', 'a', 'an', 'in', 'on', 'at', 'to'):
            out.append(w_lower)
        elif w_lower.startswith('ft'):
            out.append(w_lower)
        else:
            if len(w) > 1 and w[0] in ('(', '['):
                out.append(w[0] + w[1].upper() + w[2:])
            else:
                out.append(w[0].upper() + w[1:])
    if out:
        first = out[0]
        if len(first) > 1 and first[0] in ('(', '['):
            out[0] = first[0] + first[1].upper() + first[2:]
        else:
            out[0] = first[0].upper() + first[1:]
    return " ".join(out)

XP_MAP = {"0": 10, "1/8": 25, "1/4": 50, "1/2": 100, "1": 200, "2": 450, "3": 700, "4": 1100, "5": 1800, "6": 2300, "7": 2900, "8": 3900, "9": 5000, "10": 5900, "11": 7200, "12": 8400, "13": 10000, "14": 11500, "15": 13000, "16": 15000, "17": 18000, "18": 20000, "19": 22000, "20": 25000, "21": 33000, "22": 41000, "23": 50000, "24": 62000, "25": 75000, "26": 90000, "27": 105000, "28": 120000, "29": 135000, "30": 155000}

def _calculate_pb(cr_str):
    if cr_str in ("0", "1/8", "1/4", "1/2"):
        return 2
    try:
        cr_val = int(cr_str)
        return max(2, 1 + math.ceil(cr_val / 4))
    except ValueError:
        return 2

def enrich_monster(item, type_map=None, all_raw=None):
    """
    Specific parsing and enrichment for Monsters (Bestiary).
    Converts stat blocks into card-friendly entries.
    """
    # 1. Pre-fetch legendary group to explicitly check for missing lair actions
    lg_data = None
    has_lair_actions = False
    
    if 'legendaryGroup' in item and all_raw:
        lg_ref = item['legendaryGroup']
        lg_name = lg_ref.get('name', '').lower()
        lg_source = lg_ref.get('source', '').lower()
        
        for raw in all_raw:
            if isinstance(raw, dict) and raw.get('_data_type') == 'legendaryGroup':
                if raw.get('name', '').lower() == lg_name and raw.get('source', '').lower() == lg_source:
                    lg_data = raw
                    break
                    
        if lg_data and 'lairActions' in lg_data and lg_data['lairActions']:
            has_lair_actions = True

    # 2. Parse basic CR
    cr_raw = item.get('_raw_cr', item.get('cr', '0'))
    xp_lair = item.get('xpLair')
    
    if isinstance(cr_raw, dict):
        cr_base = str(cr_raw.get('cr', '0'))
        cr_lair = str(cr_raw.get('lair', ''))
        if not xp_lair and 'xpLair' in cr_raw:
            xp_lair = cr_raw.get('xpLair')
    else:
        cr_base = str(cr_raw)
        cr_lair = ""

    # 4. Resolve cross-references for XP/CR values
    if xp_lair and not cr_lair:
        for k, v in XP_MAP.items():
            if str(v) == str(xp_lair):
                cr_lair = k
                break
                
    if cr_lair and not xp_lair:
        xp_lair = XP_MAP.get(str(cr_lair), 0)

    sz = _parse_size(item.get('size', ['M']))
    typ_display = _format_display_type(item.get('_raw_type', item.get('type', 'Unknown')))
    
    alignment_data = item.get('alignment', ['U'])
    align_map = {
        'L': 'Lawful', 'C': 'Chaotic', 'N': 'Neutral', 'G': 'Good', 'E': 'Evil', 'U': 'Unaligned', 'A': 'Any Alignment'
    }
    
    if isinstance(alignment_data, list):
        parsed_aligns = []
        for a in alignment_data:
            if isinstance(a, str):
                parsed_aligns.append(align_map.get(a, a))
            elif isinstance(a, dict):
                val = a.get('alignment', ['U'])
                if isinstance(val, list) and val:
                    parsed_aligns.append(align_map.get(str(val[0]), str(val[0])))
        align_full = " ".join(parsed_aligns) if parsed_aligns else "Unaligned"
    else:
        align_full = align_map.get(str(alignment_data), str(alignment_data))
    
    size_map = {'T': 'Tiny', 'S': 'Small', 'M': 'Medium', 'L': 'Large', 'H': 'Huge', 'G': 'Gargantuan', 'C': 'Colossal'}
    size_full = size_map.get(sz, 'Medium')
    
    item['primary_color'] = "#8B0000"
    item['bg_color'] = "#FFEBEE"
    item['meta_left'] = f"{size_full} {typ_display}, {align_full}"
    item['rarity_badge'] = f"CR {cr_base}"
    
    entries = []
    xp_base = cr_raw.get('xp', XP_MAP.get(str(cr_base), 0)) if isinstance(cr_raw, dict) else XP_MAP.get(str(cr_base), 0)
    pb_val = _calculate_pb(cr_base)

    try:
        dex_score = int(item.get('dex', 10))
    except (TypeError, ValueError):
        dex_score = 10
    dex_mod = (dex_score - 10) // 2

    init_val = dex_mod
    init_dict = item.get('initiative')
    if isinstance(init_dict, dict) and 'proficiency' in init_dict:
        try:
            prof_mult = float(init_dict['proficiency'])
            init_val = dex_mod + int(pb_val * prof_mult)
        except (ValueError, TypeError):
            pass
            
    init_str = f"+{init_val}" if init_val >= 0 else str(init_val)
    
    # 5. Build Final CR String
    if cr_lair and xp_lair:
        cr_formatted = f"{cr_base} or {cr_lair} in lair (XP {xp_base:,}, or {int(xp_lair):,} in lair; PB +{pb_val})"
    else:
        cr_formatted = f"{cr_base} (XP {xp_base:,}; PB +{pb_val})"
    
    # Basic combat stats
    entries.append({"type": "item", "name": "Armor Class", "entry": _format_ac(item.get('ac'))})
    entries.append({"type": "item", "name": "Hit Points", "entry": _format_hp(item.get('hp'))})
    entries.append({"type": "item", "name": "Speed", "entry": _format_speed(item.get('speed'))})
    entries.append({"type": "item", "name": "Initiative", "entry": init_str})
    
    # Ability Scores and Saves Table
    entries.append(_build_stats_table(item))
    
    # Additional Stats
    skills_str = _format_skills(item.get('skill'))
    if skills_str: entries.append({"type": "item", "name": "Skills", "entry": skills_str})
    
    vuln_str = _title_case_traits(_format_traits(item.get('vulnerable')))
    if vuln_str: entries.append({"type": "item", "name": "Damage Vulnerabilities", "entry": vuln_str})
    
    resist_str = _title_case_traits(_format_traits(item.get('resist')))
    if resist_str: entries.append({"type": "item", "name": "Damage Resistances", "entry": resist_str})
    
    immune_str = _title_case_traits(_format_traits(item.get('immune')))
    if immune_str: entries.append({"type": "item", "name": "Damage Immunities", "entry": immune_str})
    
    cond_immune_str = _title_case_traits(_format_traits(item.get('conditionImmune')))
    if cond_immune_str: entries.append({"type": "item", "name": "Condition Immunities", "entry": cond_immune_str})
    
    senses_str = _title_case_traits(_format_senses(item.get('senses'), item.get('passive', 10)))
    if senses_str: entries.append({"type": "item", "name": "Senses", "entry": senses_str})
    
    lang_str = _format_languages(item.get('languages'))
    if lang_str: entries.append({"type": "item", "name": "Languages", "entry": lang_str})
        
    entries.append({"type": "item", "name": "Challenge", "entry": cr_formatted})
    
    # Traits, Actions, Reactions
    if 'trait' in item and item['trait']:
        for act in item['trait']:
            if isinstance(act, dict):
                entries.append({"type": "item", "name": act.get('name', ''), "entries": act.get('entries', [])})
            else:
                entries.append(act)

    sections = [
        ('action', 'Actions'),
        ('bonus', 'Bonus Actions'),
        ('reaction', 'Reactions'),
        ('legendary', 'Legendary Actions'),
        ('mythic', 'Mythic Actions')
    ]
    
    for key, title in sections:
        has_standard_items = bool(item.get(key))
        has_spellcasting = (key == 'action' and 'spellcasting' in item)
        
        if has_standard_items or has_spellcasting:
            if title:
                entries.append({"type": "nested_header", "name": title})
            
            if key == 'legendary':
                if item.get('legendaryHeader'):
                    entries.extend(item['legendaryHeader'])
                else:
                    creature_name = str(item.get('name', 'the creature')).lower()
                    count = item.get('legendaryActions', 3)
                    lair = item.get('legendaryActionsLair')
                    uses = str(count) + (f" ({lair} in Lair)" if lair is not None else "")
                    entries.append(
                        f"Legendary Action Uses: {uses}. Immediately after another creature's turn, "
                        f"the {creature_name} can expend a use to take one of the following actions. "
                        f"The {creature_name} regains all expended uses at the start of each of its turns."
                    )

            if has_standard_items:
                for act in item[key]:
                    if isinstance(act, dict):
                        entries.append({"type": "item", "name": act.get('name', ''), "entries": act.get('entries', [])})
                    else:
                        entries.append(act)
                        
            if has_spellcasting:
                entries.extend(_parse_spellcasting(item['spellcasting']))
                    
    # Insert Lair Actions & Regional Effects if found
    if lg_data:
        if 'lairActions' in lg_data:
            entries.append({"type": "nested_header", "name": "Lair Actions"})
            entries.extend(lg_data['lairActions'])
        if 'regionalEffects' in lg_data:
            entries.append({"type": "nested_header", "name": "Regional Effects"})
            entries.extend(lg_data['regionalEffects'])
                    
    item['entries'] = entries
    return item

def monster_footer(item):
    env = item.get('environment', [])
    treasure = item.get('treasure', [])
    
    env_str = ""
    if env:
        env_str = "Environment: " + ", ".join(env).title()
        
    treasure_str = ""
    if treasure:
        treasure_str = "Treasure: " + ", ".join(treasure).title()
        
    return (env_str, treasure_str)

FOOTER_RENDERERS['monster'] = monster_footer
