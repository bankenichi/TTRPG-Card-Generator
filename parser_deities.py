import copy
import json
from parser_utils import (
    BYPASS_EXCLUDED_SOURCES_DTYPES,
    PRE_FILTER_HOOKS,
)
from data_paths import resolve_dataset_path

PANTHEON_COLORS = {
    "Faerûnian": ("#5D4037", "#FFF8E1"),
    "Elven":     ("#053508", "#E8F5E9"),
    "Exandria":  ("#BD2BB5", "#EDE7F6"),
    "Greyhawk":  ("#E65100", "#FFF3E0"),
    "Dragonlance":("#B71C1C", "#FFEBEE"),
    "Eberron":   ("#006064", "#E0F7FA"),
    "Dwarven":   ("#001EFE", "#EFEBE9"),
    "Theros":    ("#01579B", "#E1F5FE"),
    "Gnome":     ("#827717", "#F1F8E9"),
    "Halfling":  ("#427900", "#FFEBEE"),
    "Drow":      ("#5100CA", "#EDE7F6"),
    "Orc":       ("#030303", "#CFD8DC"),
    "Yuan-Ti":   ("#004D40", "#E8F5E9"),
    "Duergar":   ("#740034", "#FAFAFA"),
    "Unknown":   ("#455A64", "#ECEFF1"),
}

# 1. Keys to NEVER render as basic stat lines at the top of the card
NORMALIZED_EXCLUSIONS = {
    'name', 'source', 'page', 'pantheon', 'entries', 'symbolimg',
    'primarycolor', 'bgcolor', 'iconname', 'metaleft', 'srd',
    'basicrules', 'additionalsources', 'customextensionof',
    'reprintalias', 'piety', 'type', 'vehicletype', 'rarity',
    'category', 'datatype', 'originfile'
}

# 2. Normalized display map
DISPLAY_NAME_MAP = {
    'altnames': 'Alternate Names'
}

# 3. Pantheons to prioritize in the tier system
FAERUN_PANTHEONS = {
    'Faerûnian', 'Forgotten Realms', 'Drow', 'Elven', 
    'Dwarven', 'Orc', 'Halfling', 'Gnomish'
}

# Keys that should be chopped at the comma to prevent duplicates like "Deceit, spiders"
COMMA_SPLIT_KEYS = {
    'domains', 'province', 'altnames', 'worshipers', 'title', 'symbol', 'alignment'
}

def get_priority(source, pantheon):
    """Calculates the ranking score for incoming data to determine merge order."""
    if source == "XPHB": return 4
    if pantheon in FAERUN_PANTHEONS: return 3
    if source == "PHB": return 1
    return 2

def to_list(val, key):
    """Ensures a value is a list. Splits strings by comma for specific fields to allow deduplication."""
    normalized_key = str(key).lower().replace('_', '').replace(' ', '')
    result = []
    
    if isinstance(val, list):
        for item in val:
            if isinstance(item, str) and normalized_key in COMMA_SPLIT_KEYS:
                result.extend([i.strip() for i in item.split(',') if i.strip()])
            else:
                result.append(copy.deepcopy(item))
    elif isinstance(val, str):
        if normalized_key in COMMA_SPLIT_KEYS:
            result.extend([i.strip() for i in val.split(',') if i.strip()])
        else:
            result.append(val.strip())
    else:
        result.append(copy.deepcopy(val))
        
    return result

def merge_lists(dominant_list, secondary_list):
    """Merges secondary into dominant, keeping dominant's order and items. Removes dupes case-insensitively."""
    result = copy.deepcopy(dominant_list)
    # Track lowercased string representations to catch duplicates like "Spiders" and "spiders"
    seen = {str(x).lower() for x in result}
    
    for item in secondary_list:
        if str(item).lower() not in seen:
            result.append(copy.deepcopy(item))
            seen.add(str(item).lower())
    return result

# 4. Dynamically cache and merge everything into arrays using the Tiered Priority
MASTER_STATS = {}
try:
    with open(resolve_dataset_path('generators/data/data/deities.json'), 'r', encoding='utf-8') as f:
        _data = json.load(f)
        for _deity in _data.get('deity', []):
            _name = _deity.get('name')
            if not _name:
                continue
            
            if _name not in MASTER_STATS:
                MASTER_STATS[_name] = {}
                
            _source = str(_deity.get('source', '')).strip()
            _pantheon = str(_deity.get('pantheon', 'Unknown Pantheon')).strip()
            _priority = get_priority(_source, _pantheon)
            
            # Track the highest priority pantheon name
            if '_best_pantheon' not in MASTER_STATS[_name]:
                MASTER_STATS[_name]['_best_pantheon'] = _pantheon
                MASTER_STATS[_name]['_pan_priority'] = _priority
            elif _priority > MASTER_STATS[_name]['_pan_priority']:
                MASTER_STATS[_name]['_best_pantheon'] = _pantheon
                MASTER_STATS[_name]['_pan_priority'] = _priority
            
            for _key, _val in _deity.items():
                if not _val or str(_key).startswith('_'):
                    continue
                
                # Do not cache purely administrative/routing keys
                _norm = str(_key).lower().replace('_', '').replace(' ', '')
                if _norm in {'name', 'source', 'page', 'pantheon', 'srd', 'basicrules', 'additionalsources', 'customextensionof', 'reprintalias', 'piety'}:
                    continue
                    
                new_items = to_list(_val, _key)
                
                if _key not in MASTER_STATS[_name]:
                    MASTER_STATS[_name][_key] = {'val': new_items, 'priority': _priority}
                else:
                    curr = MASTER_STATS[_name][_key]
                    
                    if _priority > curr['priority']:
                        # New data is higher priority; it becomes the base, old data appends to it
                        curr['val'] = merge_lists(new_items, curr['val'])
                        curr['priority'] = _priority
                    else:
                        # Old data remains higher/equal priority; new data appends to it
                        curr['val'] = merge_lists(curr['val'], new_items)
                                
except FileNotFoundError:
    pass


# ---------------------------------------------------------------------------
# BYPASS EXCLUDED SOURCES
# Deities should always pass through the global source exclusion filter.
# ---------------------------------------------------------------------------
BYPASS_EXCLUDED_SOURCES_DTYPES.update({'deity', 'deities'})


# ---------------------------------------------------------------------------
# PRE-FILTER HOOK
# Injects the cross-source best pantheon into the normalized item so that
# pantheon-based filters see a consistent value before enrichment runs.
# ---------------------------------------------------------------------------
def _deity_pre_filter_hook(norm_item: dict, primary_file: str, all_raw: list) -> None:
    d_name = norm_item.get('name')
    if d_name and d_name in MASTER_STATS:
        norm_item['pantheon'] = MASTER_STATS[d_name].get('_best_pantheon', norm_item.get('pantheon', 'Unknown Pantheon'))
    elif 'pantheon' not in norm_item:
        norm_item['pantheon'] = 'Unknown Pantheon'

for _dt in ('deity', 'deities'):
    PRE_FILTER_HOOKS[_dt] = _deity_pre_filter_hook


# ---------------------------------------------------------------------------
# ENRICHMENT
# ---------------------------------------------------------------------------
def enrich_deity(item, type_map=None):
    # 5. Overwrite the item with the fully merged, deduplicated "Super-Cache"
    name = item.get('name')
    if name and name in MASTER_STATS:
        item['pantheon'] = MASTER_STATS[name].get('_best_pantheon', item.get('pantheon', 'Unknown Pantheon'))
        
        for key, cache_obj in MASTER_STATS[name].items():
            if str(key).startswith('_'):
                continue
            item[key] = copy.deepcopy(cache_obj['val'])

    stats = []
        
    pantheon_key = str(item.get('pantheon', 'Unknown Pantheon')).title()
    
    # Resolve Item Colors & Badges
    pc, bc = PANTHEON_COLORS.get(pantheon_key, ("#455A64", "#ECEFF1"))
    item['primary_color'] = pc
    item['bg_color'] = bc
    item['meta_left'] = f"{pantheon_key}"

    # 6. Dynamically build stats from whatever keys remain
    for key, val in item.items():
        if str(key).startswith('_'):
            continue
            
        normalized_key = str(key).lower().replace('_', '').replace(' ', '')
        if normalized_key in NORMALIZED_EXCLUSIONS:
            continue

        # Format display name
        display_name = DISPLAY_NAME_MAP.get(normalized_key, str(key).replace('_', ' ').title().strip())

        # Format the value
        if isinstance(val, list):
            if all(isinstance(i, str) for i in val):
                delimiter = "/" if normalized_key == "alignment" else ", "
                val_str = delimiter.join(val)
            else:
                continue
        elif isinstance(val, str):
            val_str = val
        else:
            continue

        stats.append({'type': 'item', 'name': display_name, 'entry': val_str})

    # 7. Safely attach the built stats to the top of the rich entries array
    if stats:
        if 'entries' not in item or not item['entries']:
            item['entries'] = stats
        else:
            if isinstance(item['entries'], list):
                item['entries'] = stats + item['entries']
            else:
                item['entries'] = stats + [item['entries']]
            
    return item