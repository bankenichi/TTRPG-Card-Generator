import json
import os
import re
import base64
import copy
import math

# Import our separated Domain Parsers
from parser_bastions import enrich_bastion
from parser_actions import enrich_action
from parser_items import enrich_item_data
from parser_conditions import enrich_condition
from parser_decks import enrich_deck
from parser_deities import enrich_deity
from parser_psionics import enrich_psionic
from parser_vehicles import enrich_vehicle
from parser_feats import enrich_feat
from parser_races import enrich_race
from parser_spells import enrich_spell
from parser_classes import enrich_class, enrich_subclass
from parser_optionalfeatures import enrich_optional_feature
from parser_skills import enrich_skill
from parser_backgrounds import enrich_background
from parser_monsters import enrich_monster
from sources import get_source_priority
from icons import (
    resolve_card_icon_name, 
    resolve_watermark_name, 
    resolve_background_name, 
    resolve_card_back_name, 
    resolve_divider_name
)
from parser_languages import enrich_language
from parser_utils import (
    clean_tags,
    tokenize_text,
    SOURCE_PRIORITY_OVERRIDES,
    PRE_FILTER_HOOKS,
    NORMALIZE_TYPE_HOOKS,
    FOOTER_RENDERERS,
)
from data_paths import resolve_dataset_path

# ---------------------------------------------------------------------------
# ASSET LOADERS
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CWD = os.getcwd()
possible_dirs = [os.path.join(SCRIPT_DIR, "icons"), os.path.join(CWD, "icons")]
ICON_DIR = next((d for d in possible_dirs if os.path.isdir(d)), possible_dirs[0])

_svg_data_uri_cache = {}

def load_svg_as_data_uri(filename, force_stretch=False):
    cache_key = (filename, force_stretch)
    if cache_key in _svg_data_uri_cache:
        return _svg_data_uri_cache[cache_key]
    filepath = os.path.join(ICON_DIR, filename)
    if not os.path.exists(filepath): 
        _svg_data_uri_cache[cache_key] = ""
        return ""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            svg_str = f.read()
            if force_stretch and 'preserveAspectRatio' not in svg_str:
                svg_str = re.sub(r'<svg ', '<svg preserveAspectRatio="none" ', svg_str, count=1)
            encoded = base64.b64encode(svg_str.encode("utf-8")).decode("utf-8")
            result = f"data:image/svg+xml;base64,{encoded}"
            _svg_data_uri_cache[cache_key] = result
            return result
    except Exception:
        _svg_data_uri_cache[cache_key] = ""
        return ""

def get_dataset_items(filename):
    filename = resolve_dataset_path(filename)
    if not os.path.exists(filename): return []
    with open(filename, 'r', encoding='utf-8') as f:
        raw = json.load(f)
        
    items = []
    
    if isinstance(raw, dict) and all(isinstance(v, str) and str(v).endswith('.json') for v in raw.values()):
        base_dir = os.path.dirname(filename)
        for relative_path in raw.values():
            items.extend(get_dataset_items(os.path.join(base_dir, relative_path)))
        return items

    if isinstance(raw, dict):
        valid_root_keys = [
            'item', 'items', 'itemGroup', 'magicvariant', 'baseitem', 'itemType', 'itemProperty', 'itemTypeAdditionalEntries', 'itemEntry',
            'action', 'actions', 'spell', 'spells', 'bastion', 'bastions', 'facility',
            'condition', 'conditions', 'disease', 'diseases', 'status', 'vehicle', 'vehicles', 'vehicleUpgrade',
            'deity', 'deities', 'language', 'languages', 'psionic', 'psionics',
            'maneuver', 'maneuvers', 'metamagic', 'deck', 'decks', 'card', 'cards', 'feat', 'race', 'subrace',
            'class', 'subclass', 'classFeature', 'subclassFeature', 'skill', 'skills',
            'optionalfeature', 'optionalfeatures', 'background', 'backgrounds',
            'monster', 'legendaryGroup', 'monsterTemplate'
        ]
        matched = False
        for key in valid_root_keys:
            if key in raw and isinstance(raw[key], list):
                for it in raw[key]:
                    if isinstance(it, dict): it['_data_type'] = key
                items.extend(raw[key])
                matched = True
        
        if not matched:
            items.append(raw)
    elif isinstance(raw, list):
        items.extend(raw)
    return items

def resolve_copy(item, raw_dict, depth=0):
    if depth > 5 or not isinstance(item, dict) or '_copy' not in item:
        return item
    
    copy_meta = item['_copy']
    if not isinstance(copy_meta, dict):
        cname = str(copy_meta).lower().strip()
        csource = ""
        cabbr = ""
    else:
        cname = copy_meta.get('name', '').lower().strip()
        csource = copy_meta.get('source', '').lower().strip()
        cabbr = copy_meta.get('abbreviation', '').upper().strip()
    
    target = None
    if cname:
        target = raw_dict.get((cname, csource)) or raw_dict.get(cname)
    if not target and cabbr:
        for v in raw_dict.values():
            if not isinstance(v, dict): continue
            if v.get('abbreviation', '').upper().strip() == cabbr and (not csource or v.get('source', '').lower().strip() == csource):
                target = v
                break
    
    if not target:
        return item
        
    resolved_target = copy.deepcopy(resolve_copy(target, raw_dict, depth + 1))
    
    _mod = copy_meta.get('_mod', {}) if isinstance(copy_meta, dict) else {}
    if 'entries' in _mod and 'entries' in resolved_target:
        mod_entries = _mod['entries']
        if isinstance(mod_entries, dict):
            if mod_entries.get('mode') == 'appendArr':
                items_to_append = mod_entries.get('items', [])
                if not isinstance(items_to_append, list):
                    items_to_append = [items_to_append]
                resolved_target['entries'].extend(items_to_append)
            elif mod_entries.get('mode') == 'replaceArr':
                replace_target = mod_entries.get('replace')
                idx = None
                
                if isinstance(replace_target, dict):
                    idx = replace_target.get('index')
                elif isinstance(replace_target, str):
                    for i, e in enumerate(resolved_target['entries']):
                        if isinstance(e, dict) and e.get('name') == replace_target:
                            idx = i
                            break
                        elif isinstance(e, str) and e == replace_target:
                            idx = i
                            break
                            
                items_to_replace = mod_entries.get('items', [])
                if not isinstance(items_to_replace, list):
                    items_to_replace = [items_to_replace]
                    
                if isinstance(idx, int) and 0 <= idx < len(resolved_target['entries']):
                    resolved_target['entries'] = resolved_target['entries'][:idx] + items_to_replace + resolved_target['entries'][idx+1:]
                    
    for k, v in item.items():
        if k != '_copy':
            resolved_target[k] = copy.deepcopy(v)
            
    return resolved_target

def extract_entries(item, raw_dict, depth=0, item_entry_dict=None):
    if depth > 5: return [] 
    entries = item.get('entries') or item.get('text') or item.get('desc') or item.get('description')
    additional = item.get('additionalEntries')
    
    if not entries:
        entries = []
        if not entries and 'inherits' in item and isinstance(item['inherits'], dict):
            inh = item['inherits']
            if 'entries' in inh:
                raw_entries_str = json.dumps(inh['entries'])
                for k, v in list(inh.items()) + list(item.items()):
                    if isinstance(v, (str, int)):
                        raw_entries_str = raw_entries_str.replace(f"{{={k}}}", str(v))
                entries = json.loads(raw_entries_str)
            else:
                iname = inh.get('name', '').lower().strip()
                iabbr = inh.get('abbreviation', '').upper().strip()
                isource = inh.get('source', '').lower().strip()
                target = None
                if iname:
                    target = raw_dict.get((iname, isource)) or raw_dict.get(iname)
                if not target and iabbr:
                    for v in raw_dict.values():
                        if not isinstance(v, dict): continue
                        if v.get('abbreviation', '').upper().strip() == iabbr and (not isource or v.get('source', '').lower().strip() == isource):
                            target = v
                            break
                if target:
                    entries = copy.deepcopy(extract_entries(target, raw_dict, depth + 1, item_entry_dict))
                    
    if isinstance(entries, str): entries = [entries]
    elif isinstance(entries, dict): entries = [entries]
    elif not entries: entries = []
    else: entries = list(entries)
    
    if item_entry_dict:
        resolved = []
        for e in entries:
            if isinstance(e, str) and '#itemEntry' in e:
                template_entries = resolve_item_entry_str(e, item_entry_dict, item)
                if template_entries:
                    resolved.extend(template_entries if isinstance(template_entries, list) else [template_entries])
            else:
                resolved.append(e)
        entries = resolved
    
    if additional:
        if isinstance(additional, list): entries.extend(additional)
        else: entries.append(additional)
        
    return entries

def get_inherited_val(item, key, default=None):
    if key in item:
        return item[key]
    if 'inherits' in item and isinstance(item['inherits'], dict):
        return item['inherits'].get(key, default)
    return default

def _normalize_type(item):
    dtype = item.get('_data_type', '')
    hook = NORMALIZE_TYPE_HOOKS.get(dtype)
    if hook:
        return hook(item)
    return item.get('type', '')

def normalize_item(item, raw_dict, item_entry_dict=None):
    if not isinstance(item, dict): return None
    entries = extract_entries(item, raw_dict, item_entry_dict=item_entry_dict)
    
    src = get_inherited_val(item, 'source', '')
    page = get_inherited_val(item, 'page', '')
    name = item.get('name') or item.get('title') or item.get('id') or 'UNKNOWN'
    name = name.replace('(*)', '').replace('( *)', '').strip()
    rarity = str(get_inherited_val(item, 'rarity', ''))
    
    value = get_inherited_val(item, 'value')
    if value is None:
        value = get_inherited_val(item, 'cost')
        
    result = copy.deepcopy(item)
    result.update({
        'name': name,
        'source': str(src).upper().strip(),
        'page': page,
        'category': item.get('category') or item.get('type') or item.get('group') or item.get('facilityType') or '',
        'vehicleType': item.get('vehicleType', ''),
        'type': _normalize_type(item),
        'rarity': rarity.strip(),
        'value': value,
        '_data_type': item.get('_data_type', ''),
        'entries': entries
    })
    return result

# ---------------------------------------------------------------------------
# CONDENSER ENGINE UTILS
# ---------------------------------------------------------------------------

from parser_items import (
    extract_bonus_name,
    extract_variant_name,
    replace_bonus_text,
    entry_is_placeholder,
    resolve_item_entry_str,
)

def route_and_enrich(item, base_data_list, type_map, prop_map, raw_dict, all_raw):
    dtype = item.get('_data_type', '')
    if dtype in ('facility', 'bastion', 'bastions'): return enrich_bastion(item, type_map)
    elif dtype in ('action', 'actions'): return enrich_action(item, type_map)
    elif dtype in ('condition', 'conditions', 'disease', 'diseases', 'status'): return enrich_condition(item, type_map)
    elif dtype in ('deck', 'decks', 'card', 'cards'): return enrich_deck(item, type_map)
    elif dtype in ('deity', 'deities'): return enrich_deity(item, type_map)
    elif dtype in ('psionic', 'psionics'): return enrich_psionic(item, type_map)
    elif dtype in ('vehicle', 'vehicles', 'vehicleUpgrade'): return enrich_vehicle(item, type_map)
    elif dtype in ('feat', 'feats'): return enrich_feat(item, type_map)
    elif dtype in ('race', 'races', 'subrace', 'subraces'): return enrich_race(item, type_map, all_raw)
    elif dtype in ('spell', 'spells'): return enrich_spell(item, type_map)
    elif dtype == 'class': return enrich_class(item, type_map, all_raw)
    elif dtype == 'subclass': return enrich_subclass(item, type_map, all_raw)
    elif dtype in ('skill', 'skills'): return enrich_skill(item, type_map)
    elif dtype in ('optionalfeature', 'optionalfeatures'): return enrich_optional_feature(item, type_map)
    elif dtype in ('language', 'languages'): return enrich_language(item, type_map)
    elif dtype in ('background', 'backgrounds'): return enrich_background(item, type_map)
    elif dtype == 'monster': return enrich_monster(item, type_map, all_raw)
    else: return enrich_item_data(item, base_data_list, type_map, prop_map, raw_dict)

# ---------------------------------------------------------------------------
# CELL UNPACKER & SPATIAL CALCULATORS
# ---------------------------------------------------------------------------
def get_cell_text(cell):
    if isinstance(cell, list):
        return " ".join(get_cell_text(c) for c in cell)
        
    if isinstance(cell, dict):
        if cell.get('type') == 'cell':
            parts = []
            if 'roll' in cell:
                roll = cell['roll']
                if isinstance(roll, dict):
                    pad = roll.get('pad', False)
                    if 'min' in roll and 'max' in roll: parts.append(f"{roll['min']:02d}-{roll['max']:02d}" if pad else f"{roll['min']}-{roll['max']}")
                    elif 'exact' in roll: parts.append(f"{roll['exact']:02d}" if pad else f"{roll['exact']}")
            if 'entry' in cell: parts.append(clean_tags(str(cell['entry'])))
            return " ".join(p for p in parts if p).strip()
            
        if cell.get('type') == 'dice':
            rolls = cell.get('toRoll', [])
            if rolls:
                r = rolls[0]
                return f"{r.get('number', 1)}d{r.get('faces', 6)}"
        if cell.get('type') == 'bonus':
            return f"+{cell.get('value', 0)}"
        if 'roll' in cell and isinstance(cell['roll'], dict):
            r = cell['roll']
            if 'exact' in r: return str(r['exact'])
            if 'min' in r and 'max' in r: return f"{r['min']}-{r['max']}"
        if 'entry' in cell: 
            return clean_tags(str(cell['entry']))

    return clean_tags(str(cell))

def flatten_entries(entries, list_depth=0):
    flat = []
    if isinstance(entries, list):
        for e in entries: flat.extend(flatten_entries(e, list_depth))
    elif isinstance(entries, dict):
        if entries.get('type') == 'list' and 'items' in entries:
            if entries.get('name'): flat.append({'type': 'nested_header', 'name': entries['name']})
            for it in entries['items']:
                if isinstance(it, str): flat.append({'type': 'bulleted_string', 'entry': it, 'depth': list_depth})
                elif isinstance(it, dict):
                    if it.get('type') == 'item':
                        if it.get('name'): flat.append({'type': 'bulleted_header', 'name': it.get('name'), 'depth': list_depth})
                        if 'entry' in it: flat.extend(flatten_entries([it['entry']], list_depth + 1))
                        if 'entries' in it: flat.extend(flatten_entries(it['entries'], list_depth + 1))
                    else:
                        flat.extend(flatten_entries([it], list_depth + 1))
                else: flat.append({'type': 'bulleted_string', 'entry': str(it), 'depth': list_depth})
        elif 'entries' in entries and isinstance(entries['entries'], list):
            if 'name' in entries: flat.append({'type': 'nested_header', 'name': entries['name']})
            flat.extend(flatten_entries(entries['entries'], list_depth))
        else:
            flat.append(entries)
    else:
        if list_depth > 0: flat.append({'type': 'indented_string', 'entry': str(entries), 'depth': list_depth})
        else: flat.append(entries)
    return flat

def estimate_row_lines(row, col_widths, total_chars_per_line):
    cells = row if isinstance(row, list) else row.get('row', []) if isinstance(row, dict) else [row]
    if not cells: return 1
    
    max_lines = 1
    for i, cell in enumerate(cells):
        text_len = len(get_cell_text(cell))
        width = col_widths[i] if i < len(col_widths) else (total_chars_per_line / len(cells))
        lines = math.ceil(text_len / max(width, 1))
        max_lines = max(max_lines, lines)
        
    return max_lines

def get_table_col_widths(table_dict, total_chars_per_line):
    rows = table_dict.get('rows', [])
    labels = table_dict.get('colLabels', [])
    
    if not rows and not labels:
        return []
        
    cols_count = max(len(labels), max((len(r if isinstance(r, list) else r.get('row', []) if isinstance(r, dict) else [r])) for r in rows) if rows else 0)
    if cols_count == 0: return []

    col_max_lengths = [0] * cols_count
    
    for i, label in enumerate(labels):
        if i < cols_count: col_max_lengths[i] = max(col_max_lengths[i], len(get_cell_text(label)))
        
    for row in rows:
        cells = row if isinstance(row, list) else row.get('row', []) if isinstance(row, dict) else [row]
        for i, cell in enumerate(cells):
            if i < cols_count: col_max_lengths[i] = max(col_max_lengths[i], len(get_cell_text(cell)))

    total_len = sum(col_max_lengths)
    if total_len == 0:
        return [total_chars_per_line / cols_count] * cols_count
        
    return [max((l / total_len) * total_chars_per_line, 10) for l in col_max_lengths]


def estimate_lines(e, chars_per_line):
    if isinstance(e, str): return len(clean_tags(e)) // chars_per_line + 1
    if isinstance(e, dict):
        t = e.get('type')
        if t == 'table': 
            col_widths = get_table_col_widths(e, chars_per_line)
            return sum(estimate_row_lines(r, col_widths, chars_per_line) for r in e.get('rows', [])) + 3
        if t in ('bulleted_string', 'indented_string'): return len(clean_tags(e.get('entry', ''))) // max((chars_per_line - 5), 10) + 1
        if t in ('bulleted_header', 'nested_header'): return 1
        if t == 'list': return sum((len(get_cell_text(i)) // max((chars_per_line - 5), 10) + 1) for i in e.get('items', [])) + 1
        if 'entries' in e: return sum(estimate_lines(sub, chars_per_line) for sub in e['entries']) + 1
    return 1

def split_item_by_lines(flat_entries, target_lines=38, absolute_max=46, chars_per_line=45):
    chunks, current_chunk, current_lines = [], [], 0
    queue = list(enumerate(flat_entries))
    
    while queue:
        e_idx, e = queue.pop(0)
        e_lines = estimate_lines(e, chars_per_line)
        
        remaining_lines = sum(estimate_lines(x[1], chars_per_line) for x in queue) + e_lines
        
        if remaining_lines <= 12 and (current_lines + remaining_lines) <= absolute_max:
            current_chunk.append(e)
            current_lines += e_lines
            continue
            
        if isinstance(e, dict) and e.get('type') == 'table':
            unbreakable = e.get('_unbreakable', False)

            if current_chunk and isinstance(current_chunk[-1], dict) and current_chunk[-1].get('type') == 'table':
                chunks.append(current_chunk)
                current_chunk = []
                current_lines = 0

            rows = e.get('rows', [])
            table_has_tags = '{@' in str(rows)
            col_widths = get_table_col_widths(e, chars_per_line)
            
            if (len(rows) <= 5 and not table_has_tags) or unbreakable:
                if current_lines + e_lines > target_lines and current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = []
                    current_lines = 0
                current_chunk.append(e)
                current_lines += e_lines
            else:
                current_table_rows, local_lines = [], 3
                row_limit = 14 if current_lines >= 6 else 16
                
                for r_idx, row in enumerate(rows):
                    r_lines = estimate_row_lines(row, col_widths, chars_per_line)
                    remaining_rows = len(rows) - 1 - r_idx
                    
                    hit_hard_limit = (len(current_table_rows) >= row_limit)
                    hit_line_limit = (current_lines + local_lines + r_lines > target_lines)
                    
                    if hit_hard_limit or hit_line_limit:
                        if not hit_hard_limit and remaining_rows <= 2 and (current_lines + local_lines + r_lines + remaining_rows * 1.5) <= absolute_max:
                            current_table_rows.append(row)
                            local_lines += r_lines
                        else:
                            orphan_rows = [row]
                            orphan_lines = r_lines
                            
                            if remaining_rows == 0 and len(current_table_rows) > 1:
                                stolen_row = current_table_rows.pop()
                                orphan_rows.insert(0, stolen_row)
                                orphan_lines += estimate_row_lines(stolen_row, col_widths, chars_per_line)
                                
                            if current_table_rows:
                                tp = copy.deepcopy(e)
                                tp['rows'] = current_table_rows
                                current_chunk.append(tp)
                            
                            if current_chunk:
                                chunks.append(current_chunk)
                                current_chunk = []
                                current_lines = 0
                                
                            current_table_rows = orphan_rows
                            local_lines = 3 + orphan_lines
                            row_limit = 16 
                    else:
                        current_table_rows.append(row)
                        local_lines += r_lines
                        
                if current_table_rows:
                    tp = copy.deepcopy(e)
                    tp['rows'] = current_table_rows
                    current_chunk.append(tp)
                    current_lines += local_lines
                    
                    if local_lines > 14:
                        chunks.append(current_chunk)
                        current_chunk = []
                        current_lines = 0
            continue
            
        else:
            is_header = isinstance(e, dict) and e.get('type') in ('nested_header', 'bulleted_header')
            force_split = False
            if is_header and queue:
                next_lines = estimate_lines(queue[0][1], chars_per_line)
                if current_lines > (target_lines * 0.75) and (current_lines + e_lines + next_lines > target_lines): 
                    force_split = True
                    
            last_h = len(current_chunk) > 0 and isinstance(current_chunk[-1], dict) and current_chunk[-1].get('type') in ('nested_header', 'bulleted_header')
            
            exceeds_target = (current_lines + e_lines > target_lines)
            exceeds_abs = (current_lines + e_lines > absolute_max)
            
            if ((exceeds_target and current_lines >= (target_lines * 0.6)) or exceeds_abs or force_split) and current_chunk and not last_h:
                space_left = target_lines - current_lines
                
                if isinstance(e, str) and space_left >= 3 and e_lines > space_left:
                    tokens = tokenize_text(e)
                    split_idx = int(len(tokens) * (space_left / e_lines))
                    if 0 < split_idx < len(tokens):
                        part1 = " ".join(tokens[:split_idx])
                        part2 = " ".join(tokens[split_idx:])
                        current_chunk.append(part1)
                        chunks.append(current_chunk)
                        current_chunk = []
                        current_lines = 0
                        queue.insert(0, (e_idx, part2))
                        continue
                        
                elif isinstance(e, dict) and e.get('type') in ('bulleted_string', 'indented_string') and space_left >= 3 and e_lines > space_left:
                    text = e.get('entry', '')
                    tokens = tokenize_text(text)
                    split_idx = int(len(tokens) * (space_left / e_lines))
                    if 0 < split_idx < len(tokens):
                        part1_text = " ".join(tokens[:split_idx])
                        part2_text = " ".join(tokens[split_idx:])
                        part1 = copy.deepcopy(e)
                        part1['entry'] = part1_text
                        part2 = copy.deepcopy(e)
                        part2['type'] = 'indented_string' 
                        part2['entry'] = part2_text
                        current_chunk.append(part1)
                        chunks.append(current_chunk)
                        current_chunk = []
                        current_lines = 0
                        queue.insert(0, (e_idx, part2))
                        continue
                
                chunks.append(current_chunk)
                current_chunk = []
                current_lines = 0
                current_chunk.append(e); current_lines += e_lines
            else:
                current_chunk.append(e); current_lines += e_lines
                
    if current_chunk: chunks.append(current_chunk)
    if not chunks: chunks.append([])
    return chunks

def get_table_metrics(flat_entries):
    max_cols, max_chars, max_cell, has_table = 0, 0, 0, False
    for entry in flat_entries:
        if isinstance(entry, dict) and entry.get('type') == 'table':
            has_table = True
            labels = entry.get('colLabels', [])
            cols = len(labels)
            t_chars = sum(len(clean_tags(str(l))) for l in labels)
            for row in entry.get('rows', []):
                rc = row if isinstance(row, list) else row.get('row', []) if isinstance(row, dict) else [row]
                cols = max(cols, len(rc))
                for cell in rc:
                    c_str = get_cell_text(cell)
                    max_cell = max(max_cell, len(c_str))
                    t_chars += len(c_str)
            max_cols, max_chars = max(max_cols, cols), max(max_chars, t_chars)
    return max_cols, max_chars, max_cell, has_table

def parse_entry_to_html(entry):
    html = ""
    if isinstance(entry, str): 
        cleaned = clean_tags(entry)
        if cleaned: html += f'<p>{cleaned}</p>'
    elif isinstance(entry, dict):
        if entry.get('type') == 'nested_header':
            html += f'<div class="card-nested"><strong class="card-strong">{clean_tags(entry.get("name", ""))}:</strong></div>'
        elif entry.get('type') == 'bulleted_string':
            depth = entry.get('depth', 0)
            margin = depth * 1.2
            html += f'<div style="margin: 0 0 0.4em {margin}em; display: flex;"><span style="margin-right: 0.4em;">•</span><div>{clean_tags(entry.get("entry", ""))}</div></div>'
        elif entry.get('type') == 'bulleted_header':
            depth = entry.get('depth', 0)
            margin = depth * 1.2
            name_raw = clean_tags(entry.get("name", "")).strip()
            while name_raw.endswith(':'): name_raw = name_raw[:-1].strip()
            html += f'<div style="margin: 0.4em 0 0.2em {margin}em; display: flex;"><span style="margin-right: 0.4em;">•</span><div><strong class="card-strong">{name_raw}:</strong></div></div>'
        elif entry.get('type') == 'indented_string':
            depth = entry.get('depth', 0)
            margin = 0.8 + (depth * 1.2)
            html += f'<div style="margin: 0 0 0.4em {margin}em;">{clean_tags(entry.get("entry", ""))}</div>'
        elif entry.get('type') == 'item':
            name_raw = clean_tags(entry.get('name', '')).strip()
            while name_raw.endswith(':'): name_raw = name_raw[:-1].strip()
            name_str = f'<strong class="card-strong">{name_raw}:</strong> ' if name_raw else ''
            e_html = ""
            if 'entry' in entry: e_html = clean_tags(entry['entry']) if isinstance(entry['entry'], str) else parse_entry_to_html(entry['entry'])
            elif 'entries' in entry:
                for e in entry['entries']: e_html += parse_entry_to_html(e) if isinstance(e, dict) else f'<span>{clean_tags(e)} </span>'
            if name_str or e_html: html += f'<p>{name_str}{e_html}</p>'
        elif entry.get('type') == 'table':
            name_raw = clean_tags(entry.get('name', '')).strip()
            if name_raw:
                html += f'<div class="card-nested" style="margin-top: 6px;"><strong class="card-strong">{name_raw}</strong></div>'
            html += '<div class="card-table-block"><table class="card-table">'
            cols = entry.get('colLabels', [])
            col_styles = entry.get('colStyles', [])
            if cols:
                th_html = ""
                for i, c in enumerate(cols):
                    style_class = f' class="{col_styles[i]}"' if i < len(col_styles) and col_styles[i] else ''
                    nowrap = ' style="white-space:nowrap"' if len(clean_tags(str(c))) < 10 else ''
                    th_html += f'<th{style_class}{nowrap}>{clean_tags(str(c))}</th>'
                html += f"<thead><tr>{th_html}</tr></thead>"
            html += "<tbody>"
            for row in entry.get('rows', []):
                html += "<tr>"
                rc = row if isinstance(row, list) else row.get('row', []) if isinstance(row, dict) else [row]
                for i, cell in enumerate(rc):
                    style_class = f' class="{col_styles[i]}"' if i < len(col_styles) and col_styles[i] else ''
                    cell_text = get_cell_text(cell)
                    nowrap = ' style="white-space:nowrap"' if len(cell_text) < 10 else ''
                    html += f'<td{style_class}{nowrap}>{cell_text}</td>'
                html += "</tr>"
            html += "</tbody></table></div>"
        elif entry.get('type') == 'list':
            html += '<ul class="card-list">'
            for it in entry.get('items', []):
                if isinstance(it, str): html += f'<li>{clean_tags(it)}</li>'
                else: html += f'<li>{parse_entry_to_html(it)}</li>'
            html += '</ul>'
        elif 'entries' in entry:
            name = clean_tags(entry.get('name', '')).upper()
            if name: html += f'<div class="card-nested"><strong class="card-strong">{name}:</strong> '
            for e in entry['entries']: html += parse_entry_to_html(e) if isinstance(e, dict) else f'<span>{clean_tags(e)} </span>'
            if name: html += '</div>'
    elif isinstance(entry, list):
        for e in entry: html += parse_entry_to_html(e)
    return html

def generate_html(payload, output_html_path=None):
    if output_html_path is None:
        output_html_path = "Custom_Deck_Cards.html"

    custom_assets = payload.get('customAssets', {})
    selected_assets = payload.get('selectedAssets', {})
    
    items = []
    base_data_list = []
    raw_dict = {}
    type_map = {}
    prop_map = {}
    item_entry_dict = {}
    all_raw_global = []

    datasets_req = payload.get('datasets', [])
    if not datasets_req: return {"card_count": 0}

    for ds_info in datasets_req:
        dataset_files = ds_info['file'] if isinstance(ds_info['file'], list) else [ds_info['file']]
        dataset_files = [resolve_dataset_path(f) for f in dataset_files]
        primary_file = dataset_files[0]
        filters = ds_info.get('filters', {})

        raw_items = []
        for dataset_filename in dataset_files:
            raw_items.extend(get_dataset_items(dataset_filename))

        base_file = os.path.join(os.path.dirname(os.path.abspath(primary_file)), 'items-base.json')
        base_items = get_dataset_items(base_file) if os.path.exists(base_file) else []
        base_data_list.extend(base_items)

        magic_file = os.path.join(os.path.dirname(os.path.abspath(primary_file)), 'magicvariants.json')
        magic_items = get_dataset_items(magic_file) if os.path.exists(magic_file) else []

        all_raw = raw_items + base_items + magic_items
        all_raw_global.extend(all_raw)

        supplemental_data = {}
        for raw in all_raw:
            if isinstance(raw, dict) and not raw.get('_data_type'):
                for src_key, items_dict in raw.items():
                    if isinstance(items_dict, dict):
                        for item_name, item_props in items_dict.items():
                            if isinstance(item_props, dict):
                                i_key = item_name.lower().strip()
                                if i_key not in supplemental_data:
                                    supplemental_data[i_key] = {}
                                for k, v in item_props.items():
                                    if isinstance(v, list):
                                        supplemental_data[i_key].setdefault(k, []).extend(v)
                                    else:
                                        supplemental_data[i_key][k] = v

        for base in base_items:
            if not isinstance(base, dict): continue
            if base.get('_data_type') == 'itemType':
                abbr = base.get('abbreviation', '').split('|')[0].strip().upper()
                name = base.get('name', '').strip()
                if abbr and name: type_map[abbr] = name
            elif base.get('_data_type') == 'itemProperty':
                abbr = base.get('abbreviation', '').split('|')[0].strip().upper()
                name = base.get('name', '').strip()
                if not name and base.get('entries') and isinstance(base['entries'], list) and len(base['entries']) > 0:
                    first_entry = base['entries'][0]
                    if isinstance(first_entry, dict) and first_entry.get('name'):
                        name = first_entry.get('name')
                if abbr and name: prop_map[abbr] = name

        for base in base_items:
            if not isinstance(base, dict): continue
            if base.get('_data_type') == 'itemEntry' and 'entriesTemplate' in base:
                n = base.get('name', '').lower().strip()
                s = str(base.get('source', '')).lower().strip()
                if n:
                    item_entry_dict[(n, s)] = base
                    item_entry_dict[n] = base

        for item in all_raw:
            if not isinstance(item, dict): continue
            if 'name' in item:
                n, s = item['name'].lower().strip(), str(item.get('source', '')).lower().strip()
                raw_dict[(n, s)] = item; raw_dict[n] = item

        is_items_dataset = 'items' in os.path.basename(primary_file).lower()
        primary_raw_items = get_dataset_items(primary_file)
        items_to_process = all_raw if is_items_dataset else primary_raw_items

        from parser_utils import META_ONLY_DTYPES
        meta_types = META_ONLY_DTYPES

        ds_best = {}  
        for item in items_to_process:
            if not isinstance(item, dict): continue
            if item.get('_data_type') in meta_types: continue

            resolved_item = resolve_copy(item, raw_dict)
            norm_item = normalize_item(resolved_item, raw_dict, item_entry_dict)
            if not norm_item: continue

            src = norm_item['source']
            name_key = norm_item.get('name', '').lower().strip()
            dtype = norm_item.get('_data_type', '')
            current_priority = get_source_priority(src)

            priority_hook = SOURCE_PRIORITY_OVERRIDES.get(dtype)
            if priority_hook:
                override = priority_hook(src)
                if override is not None:
                    current_priority = override

            pre_filter_hook = PRE_FILTER_HOOKS.get(dtype)
            if pre_filter_hook:
                pre_filter_hook(norm_item, primary_file, all_raw)

            if name_key not in ds_best or current_priority < ds_best[name_key][0]:
                ds_best[name_key] = (current_priority, norm_item)

        for name_key, (_, norm_item) in ds_best.items():
            passed_filters = True
            for f_key, f_allowed_values in filters.items():
                if not f_allowed_values: continue

                if f_key == 'level':
                    item_val = norm_item.get(f_key)
                    if str(item_val) not in map(str, f_allowed_values): passed_filters = False

                elif f_key == 'rarity':
                    item_val = str(norm_item.get('rarity', '')).lower().strip()
                    _known_rarities = {'common', 'uncommon', 'rare', 'very rare', 'legendary', 'artifact'}
                    if item_val not in _known_rarities:
                        item_val = 'none'
                    if item_val not in [v.lower() for v in f_allowed_values]: passed_filters = False

                elif f_key == 'attunement':
                    req = norm_item.get('reqAttune')
                    if req is None and isinstance(norm_item.get('inherits'), dict):
                        req = norm_item['inherits'].get('reqAttune')
                    attune_val = 'yes' if req else 'no'
                    if attune_val not in [v.lower() for v in f_allowed_values]: passed_filters = False

                elif f_key == 'name':
                    name_candidates = norm_item.get('filter_class_name') or [norm_item.get('name', '')]
                    allowed_upper = [str(v).upper() for v in f_allowed_values]
                    if not any(str(n).upper() in allowed_upper for n in name_candidates):
                        passed_filters = False

                else:
                    item_val = norm_item.get(f_key)
                    if isinstance(item_val, list):
                        if not any(str(v).upper() in [str(av).upper() for av in f_allowed_values] for v in item_val):
                            passed_filters = False
                    else:
                        if str(item_val).upper() not in [str(v).upper() for v in f_allowed_values]: passed_filters = False

            if not passed_filters: continue
            norm_item['_origin_file'] = primary_file
            items.append(norm_item)

    if not items: return {"card_count": 0}

    unique_items = {}
    for item in items:
        if not isinstance(item, dict): continue
        name_key = item.get('name', '').lower().strip()
        source = item.get('source', '')
        origin_file = item.get('_origin_file', '')
        dedup_key = f"{origin_file}_{name_key}"
        
        current_priority = get_source_priority(source)
        if dedup_key not in unique_items or current_priority < get_source_priority(unique_items[dedup_key].get('source', '')):
            enriched = route_and_enrich(item, base_data_list, type_map, prop_map, raw_dict, all_raw_global)
            if isinstance(enriched, dict) and '_origin_file' not in enriched:
                enriched['_origin_file'] = origin_file
            unique_items[dedup_key] = enriched
    
    grouped_items = {}
    for item in unique_items.values():
        base_name, variant_key, variant_type = extract_variant_name(item.get('name', 'Unknown'))
        base_key = base_name.lower().strip()
        origin_file = item.get('_origin_file', '')
        group_key = f"{origin_file}_{base_key}"
        
        if group_key not in grouped_items: grouped_items[group_key] = {'variants': {}, 'base': None, 'variant_type': None}
        if variant_type:
            grouped_items[group_key]['variants'][variant_key] = item
            if grouped_items[group_key]['variant_type'] is None: grouped_items[group_key]['variant_type'] = variant_type
        else: grouped_items[group_key]['base'] = item
        
    condensed_items = []
    for group in grouped_items.values():
        base_item, variants, v_type = group['base'], group['variants'], group['variant_type']
        base_has_text = False
        if base_item:
            b_flat = flatten_entries(base_item.get('entries', []))
            b_txt = re.sub(r'<[^>]+>', '', "".join(parse_entry_to_html(e) for e in b_flat)).strip()
            if b_txt or any(isinstance(x, dict) and x.get('type') == 'table' for x in b_flat):
                base_has_text = True
                
        if base_has_text and not entry_is_placeholder(base_item.get('entries', [])):
            condensed_items.append(base_item)
            
        if variants:
            b_keys = sorted(list(variants.keys()))
            if v_type == 'bonus' and len(b_keys) > 1:
                b_str = f"{b_keys[0]} or {b_keys[-1]}" if len(b_keys) == 2 else ", ".join(b_keys[:-1]) + f", or {b_keys[-1]}"
                ni = copy.deepcopy(variants[b_keys[0]])
                ni['name'] = f"{extract_bonus_name(ni['name'])[0]}, {b_str}"
                ni['entries'] = replace_bonus_text(ni['entries'], b_keys[0], b_str)
                condensed_items.append(ni)
            elif v_type == 'level' and len(b_keys) > 1:
                b_str = f"{b_keys[0]} \u2013 {b_keys[-1]}" if len(b_keys) > 2 else f"{b_keys[0]} or {b_keys[-1]}"
                ni = copy.deepcopy(variants[b_keys[0]])
                ni['name'] = f"{extract_bonus_name(ni['name'])[0]} ({b_str})"
                condensed_items.append(ni)
            elif v_type == 'element':
                if base_has_text and not entry_is_placeholder(base_item.get('entries', [])):
                    pass 
                else:
                    b_str = ", ".join(b_keys[:-1]) + f", or {b_keys[-1]}" if len(b_keys) > 2 else f"{b_keys[0]} or {b_keys[-1]}"
                    ni = copy.deepcopy(variants[b_keys[0]])
                    ni['name'] = f"{extract_variant_name(ni['name'])[0]} ({b_str.title()})"
                    condensed_items.append(ni)
            else: condensed_items.extend(variants.values())
    
    seen_titles, final_list = set(), []
    for item in condensed_items:
        tk = str(item.get('name', '')).strip().lower()
        origin_file = item.get('_origin_file', '')
        unique_tk = f"{origin_file}_{tk}"
        
        de = item.get('entries', [])
        flat_de = flatten_entries(de)
        rendered_dummy = "".join(parse_entry_to_html(entry) for entry in flat_de)
        txt_dummy = re.sub(r'<[^>]+>', '', rendered_dummy).strip()
        has_table = any(isinstance(x, dict) and x.get('type') == 'table' for x in flat_de)
        
        if not txt_dummy and not has_table:
            continue
            
        if unique_tk and unique_tk not in seen_titles and not entry_is_placeholder(item.get('entries', [])):
            seen_titles.add(unique_tk)
            final_list.append(item)
            
    condensed_items = final_list

    expanded_items = []
    for item in condensed_items:
        de = item.get('entries', [])
        current_entries = []
        for e in de:
            if isinstance(e, dict) and e.get('_standalone'):
                if current_entries:
                    it = copy.deepcopy(item)
                    it['entries'] = current_entries
                    expanded_items.append(it)
                    current_entries = []
                
                it_table = copy.deepcopy(item)
                it_table['entries'] = [e]
                if e.get('_standalone_name'):
                    it_table['name'] = e['_standalone_name']
                expanded_items.append(it_table)
            else:
                current_entries.append(e)
        if current_entries:
            it = copy.deepcopy(item)
            it['entries'] = current_entries
            expanded_items.append(it)

    condensed_items = expanded_items

    unique_item_count = len(condensed_items)
    type_counts = {}
    for item in condensed_items:
        t = item.get('meta_left', '').strip()
        if not t:
            t = str(item.get('_data_type', 'Unknown')).capitalize()
        type_counts[t] = type_counts.get(t, 0) + 1

    final_condensed_items = []
    for item in condensed_items:
        de = item.get('entries', [])
        flat_de = flatten_entries(de)
        
        rendered_dummy = "".join(parse_entry_to_html(entry) for entry in flat_de)
        txt_dummy = re.sub(r'<[^>]+>', '', rendered_dummy)
        
        max_cols, max_chars, max_cell, has_table = get_table_metrics(flat_de)
        
        is_stat_table = has_table and max_cols == 6 and max_chars < 150
        is_wide_table = has_table and not is_stat_table and (max_cols >= 4 or (max_cols == 3 and max_cell > 60))
        has_multiple_tables = sum(1 for x in flat_de if isinstance(x, dict) and x.get('type') == 'table') > 1
        
        force_portrait = any(isinstance(x, dict) and x.get('_force_portrait') for x in flat_de)
        force_landscape = any(isinstance(x, dict) and x.get('_force_landscape') for x in flat_de)
        
        chars_per_line = 85 if (is_wide_table or force_landscape) and not force_portrait else 45
        tl = sum(estimate_lines(x, chars_per_line) for x in flat_de)
        
        if force_landscape:
            base_target = 32
            base_max = 40
            layout_type = 'landscape'
            chunks_per_card = 1
            chars_per_line = 85
        elif force_portrait:
            base_target = 48
            base_max = 58
            layout_type = 'portrait'
            chunks_per_card = 1
            chars_per_line = 45
        elif is_wide_table:
            base_target = 32
            base_max = 40
            layout_type = 'landscape'
            chunks_per_card = 1
            chars_per_line = 85
        elif tl > 35 or has_multiple_tables or len(txt_dummy) > 750 or is_stat_table:
            base_target = 30
            base_max = 40
            layout_type = 'landscape_two_col'
            chunks_per_card = 2
            chars_per_line = 45
            tl = sum(estimate_lines(x, chars_per_line) for x in flat_de) 
        else:
            base_target = 48
            base_max = 58
            layout_type = 'portrait'
            chunks_per_card = 1
            chars_per_line = 45
            
        if layout_type == 'landscape' and item.get('_data_type') == 'monster':
            base_target = 30
            base_max = 40
            layout_type = 'landscape_two_col'
            chunks_per_card = 2
            chars_per_line = 45
            tl = sum(estimate_lines(x, chars_per_line) for x in flat_de)
            
        if item.get('custom_footer_left') or item.get('custom_footer_right'):
            base_target -= 3
            base_max -= 3
            
        if layout_type == 'landscape_two_col':
            if tl > base_target * 2:
                nc = int(tl / base_target) + 1
                target_lines = (tl / nc) + 2
                abs_max = base_max
            else:
                target_lines = max((tl / 2) + 2, 10)
                abs_max = target_lines + 4
            chunks = split_item_by_lines(flat_de, target_lines=target_lines, absolute_max=abs_max, chars_per_line=chars_per_line)
        else:
            if tl > base_target:
                nc = int(tl / base_target) + 1
                target_lines = (tl / nc) + 2
            else:
                target_lines = base_target
            chunks = split_item_by_lines(flat_de, target_lines=target_lines, absolute_max=base_max, chars_per_line=chars_per_line)
            
        card_contents = []
        if chunks_per_card == 2:
            for i in range(0, len(chunks), 2):
                card_contents.append(chunks[i:i+2])
        else:
            for chunk in chunks:
                card_contents.append([chunk])
                
        for idx, content in enumerate(card_contents):
            ic = copy.deepcopy(item)
            if len(card_contents) > 1:
                ic['name'] = f"{item.get('name', 'UNKNOWN')} {idx + 1}/{len(card_contents)}"
            
            ic['cols'] = content
            ic['layout'] = 'landscape' if layout_type == 'landscape_two_col' else layout_type
            ic['is_two_col_layout'] = (layout_type == 'landscape_two_col')
            final_condensed_items.append(ic)
            
    condensed_items = final_condensed_items

    html_content = [f"""
    <!DOCTYPE html>
    <html lang="en">
    <head><meta charset="UTF-8"><title>Custom TTRPG Deck</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Open+Sans:ital,wght@0,400;0,700;1,400&display=swap');
            * {{ box-sizing: border-box; }}
            body {{ font-family: 'Open Sans', sans-serif; background-color: #2b2b2b; margin: 0; padding: 20px; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
            @media print {{ body {{ background-color: white; padding: 0; }} @page {{ size: letter; margin: 0; }} }}
            .page {{ width: 8.5in; height: 11in; display: grid; grid-template-columns: repeat(3, 2.5in); grid-template-rows: repeat(3, 3.5in); margin: 0 auto; padding: 0.25in 0.5in; page-break-after: always; background-color: white; }}
            .card-slot {{ width: 2.5in; height: 3.5in; display: flex; align-items: center; justify-content: center; position: relative; }}
            .card {{ position: relative; border-style: solid; border-width: 3px; border-radius: 8px; overflow: hidden; display: flex; flex-direction: column; flex-shrink: 0; border-color: var(--primary); background-color: var(--bg); }}
            .card::before {{ content: ""; position: absolute; top: 0; left: 0; right: 0; bottom: 0; background-image: var(--bg-uri); background-size: 100% 100%; background-repeat: no-repeat; background-position: center; z-index: 0; }}
            .card::after {{ content: ""; position: absolute; top: 50%; left: 50%; width: 75%; height: 75%; transform: translate(-50%, -50%); background-color: var(--primary); mask-image: var(--watermark-uri); -webkit-mask-image: var(--watermark-uri); mask-size: contain; -webkit-mask-size: contain; mask-repeat: no-repeat; -webkit-mask-repeat: no-repeat; mask-position: center; -webkit-mask-position: center; z-index: 0; opacity: 0.25; pointer-events: none; }}
            .portrait {{ width: 2.5in; height: 3.5in; padding: 16px; display: flex; flex-direction: column; }}
            .landscape {{ width: 3.5in; height: 2.5in; transform: rotate(-90deg); padding: 6px 16px; display: flex; flex-direction: column; }}
            .header, .header-divider, .content-wrapper {{ position: relative; z-index: 1; width: 100%; }}
            .header {{ display: flex; align-items: center; gap: 12px; margin-bottom: 2px; padding: 0; }}
            .content-wrapper {{ flex-grow: 1; overflow: hidden; display: flex; flex-direction: column; padding: 0; min-height: 0; }}
            .icon {{ width: 34px; height: 34px; flex-shrink: 0; background-color: var(--primary); mask-image: var(--icon-uri); -webkit-mask-image: var(--icon-uri); mask-size: contain; -webkit-mask-size: contain; mask-repeat: no-repeat; -webkit-mask-repeat: no-repeat; mask-position: center; -webkit-mask-position: center; }}
            .title-box {{ flex-grow: 1; min-width: 0; display: flex; flex-direction: column; }}
            .title {{ font-size: 12px; font-weight: bold; text-transform: uppercase; margin: 0; line-height: 1.1; color: var(--primary); word-wrap: break-word; }}
            .meta {{ display: flex; justify-content: space-between; font-size: 8px; font-weight: bold; margin-top: 4px; color: var(--primary); }}
            .content-inner {{ width: 100%; min-width: 0; height: max-content; overflow-wrap: anywhere; word-wrap: break-word; padding-bottom: 2px; }}
            .content-inner p {{ margin: 0 0 0.4em 0; color: #111111; break-inside: auto; overflow-wrap: anywhere; }}
            .card-list {{ margin: 0 0 0.4em 0; padding-left: 1.2em; color: #111111; }}
            .card-nested {{ margin: 0 0 0.4em 0; color: #111111; }}
            .card-strong {{ color: var(--primary); }}
            
            .card-table-block {{ display: block; width: 100%; max-width: 100%; break-inside: auto; }}
            .card-table {{ border-color: var(--primary); color: #111111; width: 100%; table-layout: auto; border-collapse: collapse; margin-bottom: 0.4em; }}
            .card-table th, .card-table td {{ border-color: var(--primary); border: 1px solid; padding: 2px 4px; text-align: left; font-size: 0.9em !important; min-width: 0; max-width: 100%; word-wrap: break-word; white-space: normal; vertical-align: top; }}
            .card-table th {{ color: var(--primary); background-color: rgba(0,0,0,0.05); }}
            .card-table tr {{ break-inside: avoid; page-break-inside: avoid; }}
            .card-table tbody tr:nth-child(even) {{ background-color: color-mix(in srgb, var(--primary) 10%, transparent); }}
            
            .auto-w {{ width: 1%; white-space: nowrap !important; }}
            .text-center {{ text-align: center !important; }}
            .text-right {{ text-align: right !important; }}
            .text-left {{ text-align: left !important; }}
            .border-0 {{ border: none !important; }}
            .col-2 {{ width: 16.666% !important; }}
            
            .header-divider {{ display: block; width: min(2in, 100%); max-width: 2in !important; height: 10px !important; flex-shrink: 0; margin: 6px auto; background-color: var(--primary); mask-image: var(--divider-uri); -webkit-mask-image: var(--divider-uri); mask-size: 100% 100%; -webkit-mask-size: 100% 100%; mask-repeat: no-repeat; -webkit-mask-repeat: no-repeat; mask-position: center; -webkit-mask-position: center; }}
            .card-footer {{ display: flex; flex-direction: column; margin-top: auto; padding-top: 6px; color: var(--primary); font-size: 8px; font-weight: bold; z-index: 1; border-top: 1px solid transparent; }}
        </style>
    </head><body>"""]

    CARDS_PER_PAGE = 9
    for i in range(0, len(condensed_items), CARDS_PER_PAGE):
        chunk = condensed_items[i:i + CARDS_PER_PAGE]
        html_content.append('<div class="page">')
        for item in chunk:
            oc = item.get('layout', 'portrait')
            cols = item.get('cols', [item.get('entries', [])])
            
            if len(cols) == 2:
                rendered_1 = "".join(parse_entry_to_html(entry) for entry in cols[0])
                rendered_2 = "".join(parse_entry_to_html(entry) for entry in cols[1])
                
                content_html = f'''
                <div class="content-inner" style="display: flex; gap: 20px; width: 100%;">
                    <div style="flex: 1; min-width: 0;">{rendered_1}</div>
                    <div style="flex: 1; min-width: 0;">{rendered_2}</div>
                </div>
                '''
            else:
                rendered = "".join(parse_entry_to_html(entry) for entry in cols[0])
                extra_style = "column-count: 2; column-gap: 20px;" if item.get('is_two_col_layout') else ""
                content_html = f'<div class="content-inner" style="{extra_style}">{rendered}</div>'
                
            meta_left = item.get('meta_left', '')
            rarity_badge = item.get('rarity_badge', '')
            pc = item.get('primary_color', '#1B5E20')
            bc = item.get('bg_color', '#F1F8E9')

            page_str = f"p.{item.get('page', '')}" if item.get('page') else ""
            src_str = f"{item.get('source', 'UNK')} {page_str}".strip()

            _dtype = item.get('_data_type', '')
            _footer_renderer = FOOTER_RENDERERS.get(_dtype) or FOOTER_RENDERERS.get('_items')
            cost_str, weight_str = ('', '')
            if _footer_renderer:
                cost_str, weight_str = _footer_renderer(item)

            custom_footer_left = clean_tags(item.get('custom_footer_left', ''))
            custom_footer_right = clean_tags(item.get('custom_footer_right', ''))
            
            footer_html = ""
            if custom_footer_left or custom_footer_right:
                footer_html += f'<div style="display: flex; justify-content: space-between; width: 100%; margin-bottom: 2px;"><span>{custom_footer_left}</span><span>{custom_footer_right}</span></div>'
            if cost_str or weight_str:
                footer_html += f'<div style="display: flex; justify-content: space-between; width: 100%;"><span>{cost_str}</span><span>{weight_str}</span></div>'
            
            icon_name = resolve_card_icon_name(item, item.get('_origin_file', 'items.json'))
            iur = load_svg_as_data_uri(f"{icon_name}.svg")
            if not iur: iur = ""
                
            div_name = resolve_divider_name(item, item.get('_origin_file', 'items.json'))
            div_uri = load_svg_as_data_uri(f"{div_name}.svg")
            if not div_uri: div_uri = ""
                
            # Override watermark (Priority: 1. Uploaded, 2. Selected from UI Dropdown, 3. Dynamic Icons.py)
            wur = custom_assets.get('watermark')
            if not wur:
                sel_wm = selected_assets.get('watermark')
                if sel_wm and sel_wm != 'Default':
                    wur = load_svg_as_data_uri(sel_wm)
                    
                if not wur:
                    watermark_name = resolve_watermark_name(item, item.get('_origin_file', 'items.json'))
                    wur = load_svg_as_data_uri(f"{watermark_name}.svg")
                    if not wur: wur = ""
                
            # Override background (Priority: 1. Uploaded, 2. Selected from UI Dropdown, 3. Dynamic Icons.py)
            bg_uri = custom_assets.get('background')
            if bg_uri and bg_uri.startswith('data:image/svg+xml;base64,'):
                try:
                    b64_data = bg_uri.split(',', 1)[1]
                    svg_str = base64.b64decode(b64_data).decode('utf-8')
                    if 'preserveAspectRatio' not in svg_str:
                        svg_str = re.sub(r'<svg ', '<svg preserveAspectRatio="none" ', svg_str, count=1)
                        encoded = base64.b64encode(svg_str.encode("utf-8")).decode("utf-8")
                        bg_uri = f"data:image/svg+xml;base64,{encoded}"
                except Exception:
                    pass

            if not bg_uri:
                sel_bg = selected_assets.get('background')
                if sel_bg and sel_bg != 'Default':
                    bg_uri = load_svg_as_data_uri(sel_bg, force_stretch=True)
                    
                if not bg_uri:
                    bg_name = resolve_background_name(item, item.get('_origin_file', 'items.json'))
                    bg_uri = load_svg_as_data_uri(f"{bg_name}.svg", force_stretch=True)
                    if not bg_uri: bg_uri = ""
            
            html_content.append(f"""
            <div class="card-slot">
                <div class="card {oc}" style="--primary: {pc}; --bg: {bc}; --icon-uri: url('{iur}'); --watermark-uri: url('{wur}'); --bg-uri: url('{bg_uri}'); --divider-uri: url('{div_uri}');">
                    <div class="header">
                        <div class="icon"></div>
                        <div class="title-box">
                            <h1 class="title" style="display: flex; justify-content: space-between; width: 100%;">
                                <span>{item.get('name', 'UNKNOWN')}</span>
                                <span style="flex-shrink: 0; margin-left: 8px;">{rarity_badge}</span>
                            </h1>
                            <div class="meta"><span>{meta_left}</span><span style="font-style: italic;">{src_str}</span></div>
                        </div>
                    </div>
                    <div class="header-divider"></div>
                    <div class="content-wrapper">
                        {content_html}
                    </div>
                    <div class="card-footer">
                        {footer_html}
                    </div>
                </div>
            </div>""")
        html_content.append('</div>')

    html_content.append("""
        <script>
            window.onload = function() {
                const VALID_SIZES = [11.5, 11.25, 11.0, 10.75, 10.5, 10.25, 10.0, 9.75, 9.5, 9.25, 9.0, 8.75, 8.5, 8.25, 8.0, 7.75, 7.5, 7.25, 7.0, 6.75, 6.5, 6.25, 6.0, 5.75, 5.5, 5.25, 5.0, 4.75, 4.5];
                const MIN_SIZE = VALID_SIZES[VALID_SIZES.length - 1]; 
                document.querySelectorAll('.card').forEach(card => {
                    const wrapper = card.querySelector('.content-wrapper'), inner = card.querySelector('.content-inner'), header = card.querySelector('.header'), divider = card.querySelector('.header-divider'), title = card.querySelector('.title'), meta = card.querySelector('.meta'), icon = card.querySelector('.icon'), footer = card.querySelector('.card-footer');
                    if (!wrapper || !inner) return;
                    const isLandscape = card.classList.contains('landscape');
                    const isOverflowing = () => {
                        if (isLandscape) { card.style.setProperty('transform', 'none', 'important'); void card.offsetHeight; }
                        let overflows = inner.scrollHeight > wrapper.clientHeight || inner.scrollWidth > wrapper.clientWidth;
                        if (!overflows) {
                            const wRect = wrapper.getBoundingClientRect(), tables = inner.querySelectorAll('.card-table-block');
                            for (let i = 0; i < tables.length; i++) {
                                const tRect = tables[i].getBoundingClientRect();
                                if (tRect.bottom > wRect.bottom + 1.5 || tables[i].scrollWidth > tables[i].clientWidth + 1.5) { overflows = true; break; }
                            }
                        }
                        if (isLandscape) { card.style.removeProperty('transform'); void card.offsetHeight; }
                        return overflows;
                    };
                    const applySize = (size) => {
                        const ratio = (size - MIN_SIZE) / (11.5 - MIN_SIZE);
                        inner.style.setProperty('font-size', size + 'px', 'important');
                        inner.style.setProperty('line-height', (1.1 + ratio * 0.25).toFixed(2), 'important');
                        if (footer) { footer.style.setProperty('font-size', Math.max(size * 0.70, 6) + 'px', 'important'); }
                        if (title) { title.style.setProperty('font-size', Math.max(size * 1.04, 7) + 'px', 'important'); title.style.setProperty('line-height', (0.95 + ratio * 0.15).toFixed(2), 'important'); }
                        if (meta) { meta.style.setProperty('font-size', Math.max(size * 0.70, 6) + 'px', 'important'); meta.style.setProperty('margin-top', (ratio * 4).toFixed(1) + 'px', 'important'); }
                        if (icon) { icon.style.setProperty('width', Math.max(size * 2.9, 12) + 'px', 'important'); icon.style.setProperty('height', Math.max(size * 2.9, 12) + 'px', 'important'); }
                        if (header) { header.style.setProperty('gap', Math.max(size * 1.0, 2) + 'px', 'important'); header.style.setProperty('margin-bottom', (ratio * 2).toFixed(1) + 'px', 'important'); }
                        if (divider) { divider.style.setProperty('height', (3 + ratio * 7).toFixed(1) + 'px', 'important'); divider.style.setProperty('margin', (0.5 + ratio * 5.5).toFixed(1) + 'px auto', 'important'); }
                    };
                    for (let i = 0; i < VALID_SIZES.length; i++) { applySize(VALID_SIZES[i]); if (!isOverflowing()) break; }
                });
            };
        </script></body></html>""")
    
    with open(output_html_path, 'w', encoding='utf-8') as f: f.write("\n".join(html_content))
    
    return {
        "card_count": len(condensed_items),
        "item_count": unique_item_count,
        "type_counts": type_counts
    }

def generate_backs_html(payload, output_html_path="Custom_Deck_Backs.html"):
    custom_assets = payload.get('customAssets', {})
    selected_assets = payload.get('selectedAssets', {})
    
    # Priority 1: Custom Override Upload
    cb_uri = custom_assets.get('cardBack')
    if cb_uri and cb_uri.startswith('data:image/svg+xml;base64,'):
        try:
            b64_data = cb_uri.split(',', 1)[1]
            svg_str = base64.b64decode(b64_data).decode('utf-8')
            if 'preserveAspectRatio' not in svg_str:
                svg_str = re.sub(r'<svg ', '<svg preserveAspectRatio="none" ', svg_str, count=1)
                encoded = base64.b64encode(svg_str.encode("utf-8")).decode("utf-8")
                cb_uri = f"data:image/svg+xml;base64,{encoded}"
        except Exception:
            pass
            
    # Priority 2 & 3: Dropdown Option -> Dynamic fallback
    if not cb_uri:
        sel_cb = selected_assets.get('cardBack')
        if sel_cb and sel_cb != 'Default':
            cb_uri = load_svg_as_data_uri(sel_cb, force_stretch=True)
            
        if not cb_uri:
            cb_name = resolve_card_back_name(payload)
            cb_uri = load_svg_as_data_uri(f"{cb_name}.svg", force_stretch=True)
            if not cb_uri: cb_uri = ""
        
    html_content = [f"""
    <!DOCTYPE html>
    <html lang="en">
    <head><meta charset="UTF-8"><title>Custom TTRPG Deck Backs</title>
        <style>
            * {{ box-sizing: border-box; }}
            body {{ background-color: #2b2b2b; margin: 0; padding: 20px; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
            @media print {{ body {{ background-color: white; padding: 0; }} @page {{ size: letter; margin: 0; }} }}
            .page {{ width: 8.5in; height: 11in; display: grid; grid-template-columns: repeat(3, 2.5in); grid-template-rows: repeat(3, 3.5in); margin: 0 auto; padding: 0.25in 0.5in; background-color: white; page-break-after: always; }}
            .card-slot {{ width: 2.5in; height: 3.5in; display: flex; align-items: center; justify-content: center; }}
            .card-back {{ width: 100%; height: 100%; background-image: url('{cb_uri}'); background-size: 100% 100%; background-repeat: no-repeat; background-position: center; border-radius: 8px; overflow: hidden; }}
        </style>
    </head>
    <body>
        <div class="page">
    """]
    
    for _ in range(9):
        html_content.append(f"""
            <div class="card-slot">
                <div class="card-back"></div>
            </div>
        """)
        
    html_content.append("</div></body></html>")
    
    with open(output_html_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(html_content))
        
    return True