from parser_utils import PRE_FILTER_HOOKS


def _category(item, primary_file=None, all_raw=None):
    code = str(item.get('category', ''))
    item['category'] = {'O': 'Origin Feat', 'EB': 'Epic Boon'}.get(
        code, 'Fighting Style' if code.startswith('FS') else 'General Feat')


PRE_FILTER_HOOKS['feat'] = _category
PRE_FILTER_HOOKS['feats'] = _category


def enrich_feat(item, type_map=None):
    """
    Specific parsing and enrichment for Feats.
    """
    if not isinstance(item, dict): return item

    # Determine Feat Category and Theme Colors
    cat = item.get('category', '')
    
    if cat in ('O', 'Origin Feat'):
        meta = "Origin Feat"
        pc = "#2E7D32"  # Forest Green
        bc = "#E8F5E9"
    elif cat in ('EB', 'Epic Boon'):
        meta = "Epic Boon"
        pc = "#6A1B9A"  # Deep Purple
        bc = "#F3E5F5"
    elif str(cat).startswith('FS') or cat == 'Fighting Style':
        meta = "Fighting Style"
        pc = "#C62828"  # Crimson Red
        bc = "#FFEBEE"
    else: 
        meta = "General Feat" # Catches 'G', '', or missing categories from older books
        pc = "#A04000"  # Dark Burnt Amber / Rust (High Contrast)
        bc = "#FFF3E0"
        
    # Apply theme and meta tags
    item['primary_color'] = pc
    item['bg_color'] = bc
    item['rarity_badge'] = ""
    item['meta_left'] = meta
    item['category'] = meta # Overwrites internal category for clean UI filtering
    
    stats = []
    
    # Parse generic prerequisites safely
    if isinstance(item.get('prerequisite'), list):
        prereq_strs = []
        for p in item['prerequisite']:
            if not isinstance(p, dict):
                continue
            
            if p.get('level'): 
                if isinstance(p['level'], int): prereq_strs.append(f"Level {p['level']}")
                elif isinstance(p['level'], dict) and 'level' in p['level']: prereq_strs.append(f"Level {p['level']['level']}")
                else: prereq_strs.append("Level Requirement")
            if p.get('spellcasting') or p.get('spellcasting2020') or p.get('spellcastingFeature'): 
                prereq_strs.append("Spellcasting")
            if p.get('race'): prereq_strs.append("Specific Race")
            if p.get('proficiency'): prereq_strs.append("Specific Proficiency")
            if p.get('ability'): prereq_strs.append("Ability Score Minimum")
            if p.get('feat'): prereq_strs.append("Specific Feat")
            if p.get('background'): prereq_strs.append("Specific Background")
            if p.get('campaign'): prereq_strs.append("Campaign Setting")
            
        if prereq_strs:
            clean_prereqs = list(dict.fromkeys(prereq_strs))
            stats.append({'type': 'item', 'name': 'Prerequisite', 'entry': ", ".join(clean_prereqs)})
            
    if stats:
        entries = item.get('entries', [])
        if not isinstance(entries, list):
            entries = [entries]
        item['entries'] = stats + entries
            
    return item
