import os
import json
import copy
from html import escape
from parser_utils import PRE_FILTER_HOOKS

SCHOOL_MAP = {
    'A': 'Abjuration',
    'C': 'Conjuration',
    'D': 'Divination',
    'E': 'Enchantment',
    'I': 'Illusion',
    'N': 'Necromancy',
    'T': 'Transmutation',
    'V': 'Evocation'
}

# Thematic color mapping for magic schools (Primary Hex, Background Hex)
SCHOOL_COLORS = {
    'A': ("#0D47A1", "#E3F2FD"), # Blue
    'C': ("#E65100", "#FFF3E0"), # Orange
    'D': ("#455A64", "#ECEFF1"), # Silver/Grey
    'E': ("#C2185B", "#FCE4EC"), # Pink/Magenta
    'I': ("#4A148C", "#F3E5F5"), # Purple
    'N': ("#000000", "#F5F5F5"), # Black
    'T': ("#1B5E20", "#F1F8E9"), # Green
    'V': ("#B71C1C", "#FFEBEE")  # Red
}

# Local cache so we only load sources.json once per directory
_sources_cache = {}

def get_spell_classes(spell_name, origin_file):
    if not origin_file:
        return {}
        
    if origin_file not in _sources_cache:
        dir_name = os.path.dirname(os.path.abspath(origin_file))
        sources_path = os.path.join(dir_name, 'sources.json')
        class_map = {}
        
        if os.path.exists(sources_path):
            try:
                with open(sources_path, 'r', encoding='utf-8') as f:
                    raw = json.load(f)
                for src_key, spells_dict in raw.items():
                    if isinstance(spells_dict, dict):
                        for s_name, s_data in spells_dict.items():
                            k = s_name.lower().strip()
                            if k not in class_map: 
                                class_map[k] = {}
                            if 'class' in s_data: 
                                class_map[k]['class'] = s_data['class']
                            if 'classVariant' in s_data: 
                                class_map[k]['classVariant'] = s_data['classVariant']
            except Exception:
                pass
                
        _sources_cache[origin_file] = class_map
        
    return _sources_cache[origin_file].get(spell_name.lower().strip(), {})


# ---------------------------------------------------------------------------
# PRE-FILTER HOOK
# Aggregates class lists from the item itself and from the supplemental
# sources.json so that 'classes' is available as a filter field before
# enrichment runs.
# ---------------------------------------------------------------------------
def _spell_pre_filter_hook(norm_item: dict, primary_file: str, all_raw: list) -> None:
    classes = []

    # Classes embedded directly in the item
    if 'class' in norm_item and isinstance(norm_item['class'], list):
        classes.extend([c.get('name') for c in norm_item['class'] if c.get('name')])
    if 'classVariant' in norm_item and isinstance(norm_item['classVariant'], list):
        classes.extend([c.get('name') for c in norm_item['classVariant'] if c.get('name')])
    if 'classes' in norm_item and isinstance(norm_item['classes'], dict):
        from_cl = norm_item['classes'].get('fromClassList', [])
        classes.extend([c.get('name') for c in from_cl if c.get('name')])

    # Supplemental sources.json
    extra = get_spell_classes(norm_item.get('name', ''), primary_file)
    if 'class' in extra:
        classes.extend([c.get('name') for c in extra['class'] if c.get('name')])
    if 'classVariant' in extra:
        classes.extend([c.get('name') for c in extra['classVariant'] if c.get('name')])

    norm_item['classes'] = list(dict.fromkeys(c for c in classes if c))

for _dt in ('spell', 'spells'):
    PRE_FILTER_HOOKS[_dt] = _spell_pre_filter_hook


# ---------------------------------------------------------------------------
# ENRICHMENT
# ---------------------------------------------------------------------------
def enrich_spell(item, type_map=None):
    stats = []
    
    school_code = str(item.get('school', 'V')).upper()
    school_name = SCHOOL_MAP.get(school_code, 'Unknown School')
    pc, bc = SCHOOL_COLORS.get(school_code, ("#000000", "#F5F5F5"))

    # Apply colors
    item['primary_color'] = pc
    item['bg_color'] = bc

    # Upper right badge: Spell Level number only
    level = item.get('level', 0)
    item['rarity_badge'] = f'<span style="color: {pc}; font-weight: 900;">{escape(str(level))}</span>'

    # Header Subtitle: School ONLY
    item['meta_left'] = school_name

    # Footer Processing: Classes on the left, Ritual on the right
    is_ritual = item.get('meta', {}).get('ritual', False)
    item['custom_footer_right'] = "Ritual" if is_ritual else ""
    
    classes = []
    # 1. Base item classes
    if isinstance(item.get('classes'), list):
        classes.extend(c for c in item['classes'] if isinstance(c, str))
    if 'class' in item and isinstance(item['class'], list):
        classes.extend([c.get('name') for c in item['class'] if c.get('name')])
    if 'classVariant' in item and isinstance(item['classVariant'], list):
        classes.extend([c.get('name') for c in item['classVariant'] if c.get('name')])
    if 'classes' in item and isinstance(item['classes'], dict):
        from_cl = item['classes'].get('fromClassList', [])
        classes.extend([c.get('name') for c in from_cl if c.get('name')])
        
    # 2. Supplemental sources.json classes
    extra = get_spell_classes(item.get('name', ''), item.get('_origin_file', ''))
    if 'class' in extra:
        classes.extend([c.get('name') for c in extra['class'] if c.get('name')])
    if 'classVariant' in extra:
        classes.extend([c.get('name') for c in extra['classVariant'] if c.get('name')])
        
    # Deduplicate while preserving order
    seen = set()
    unique_classes = []
    for c in classes:
        if c not in seen:
            seen.add(c)
            unique_classes.append(c)
            
    item['custom_footer_left'] = ", ".join(unique_classes)

    # --- 1. Casting Time ---
    time_list = item.get('time', [])
    if time_list:
        t = time_list[0]
        t_str = f"{t.get('number', '')} {t.get('unit', '')}".strip()
        if t.get('condition'):
            t_str += f" ({t.get('condition')})"
        stats.append({'type': 'item', 'name': 'Casting Time', 'entry': t_str})

    # --- 2. Range ---
    range_dict = item.get('range', {})
    r_type = range_dict.get('type')
    r_dist = range_dict.get('distance', {})
    d_type = r_dist.get('type')
    d_amount = r_dist.get('amount')
    
    range_val = ""
    if d_type == 'self':
        range_val = "Self"
        if r_type and r_type not in ('point', 'self'):
            range_val += f" ({d_amount}-foot {r_type})" if d_amount else f" ({r_type})"
    elif d_type == 'touch':
        range_val = "Touch"
    elif d_type == 'feet':
        range_val = f"{d_amount} feet"
        if r_type and r_type != 'point':
             range_val += f" ({r_type})"
    elif d_type == 'miles':
        range_val = f"{d_amount} mile{'s' if d_amount and d_amount > 1 else ''}"
    elif d_type == 'sight':
        range_val = "Sight"
    elif d_type == 'unlimited':
        range_val = "Unlimited"
    else:
        if d_amount and d_type:
            range_val = f"{d_amount} {d_type}"
        elif d_type:
            range_val = str(d_type).title()
            
    if range_val:
        stats.append({'type': 'item', 'name': 'Range', 'entry': range_val})

    # --- 3. Components ---
    comp_list = []
    c = item.get('components', {})
    if c.get('v'): comp_list.append('V')
    if c.get('s'): comp_list.append('S')
    if 'm' in c:
        m = c['m']
        if isinstance(m, str):
            comp_list.append(f"M ({m})")
        elif isinstance(m, dict):
            text = m.get('text', '')
            if text:
                comp_list.append(f"M ({text})")
            else:
                comp_list.append("M")
    comp_str = ", ".join(comp_list)
    if comp_str:
        stats.append({'type': 'item', 'name': 'Components', 'entry': comp_str})

    # --- 4. Duration ---
    dur_list = item.get('duration', [])
    if dur_list:
        d = dur_list[0]
        d_type = d.get('type')
        dur_str = ""
        if d_type == 'instant':
            dur_str = "Instantaneous"
        elif d_type == 'permanent':
            dur_str = "Until dispelled"
            if d.get('ends'):
                dur_str += f" or triggered" if 'trigger' in d['ends'] else ""
        elif d_type == 'timed':
            d_amt = d.get('duration', {}).get('amount', '')
            d_unit = d.get('duration', {}).get('type', '')
            dur_str = f"{d_amt} {d_unit}{'s' if isinstance(d_amt, int) and d_amt > 1 else ''}"
        else:
            dur_str = "Special"
            
        if d.get('concentration'):
            dur_str = f"Concentration, up to {dur_str}"
            
        if dur_str:
            stats.append({'type': 'item', 'name': 'Duration', 'entry': dur_str})

    # --- 5. Entries & Higher Level Parsing ---
    final_entries = stats
    if item.get('entries'):
        final_entries.extend(copy.deepcopy(item['entries']))
        
    if item.get('entriesHigherLevel'):
        final_entries.extend(copy.deepcopy(item['entriesHigherLevel']))
        
    item['entries'] = final_entries
    return item
