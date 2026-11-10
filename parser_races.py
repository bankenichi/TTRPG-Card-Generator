import copy

def enrich_race(item, type_map=None, all_raw=None):
    """
    Specific parsing and enrichment for Races, Subraces, and Lineages.
    Inherits parent abilities for subraces and formats the title.
    """
    if not isinstance(item, dict): return item

    result = copy.deepcopy(item)

    # Teal/Nature theme for Races
    result['primary_color'] = "#004D40"
    result['bg_color'] = "#E0F2F1"
    result['rarity_badge'] = ""
    
    # Determine Race Type & Handle Subrace Inheritance
    r_type = "Race"
    parent_race = None
    
    if result.get('_data_type') == 'subrace':
        r_type = "Subrace"
        r_name = result.get('raceName')
        r_src = result.get('raceSource')
        
        if r_name and all_raw:
            # Look through the global data to find the parent race
            for raw_item in all_raw:
                if raw_item.get('_data_type') in ('race', 'races') and \
                   str(raw_item.get('name', '')).lower() == str(r_name).lower() and \
                   (not r_src or str(raw_item.get('source', '')).lower() == str(r_src).lower()):
                    parent_race = raw_item
                    break
                    
            if parent_race:
                # 1. Inherit root physical properties if the subrace didn't override them
                for prop in ['size', 'speed', 'darkvision']:
                    if prop not in result and prop in parent_race:
                        result[prop] = copy.deepcopy(parent_race[prop])
                        
                # 2. Prepend parent entries (Flight, Languages, Age, etc.) before subrace entries
                parent_entries = copy.deepcopy(parent_race.get('entries', []))
                if not isinstance(parent_entries, list): parent_entries = [parent_entries]
                
                sub_entries = result.get('entries', [])
                if not isinstance(sub_entries, list): sub_entries = [sub_entries]
                
                result['entries'] = parent_entries + sub_entries
        
        # 3. Update the display name to "Parent (Subrace)"
        if r_name:
            result['name'] = f"{r_name} ({result.get('name', '')})"
            
    elif result.get('lineage'):
        r_type = "Lineage"
        
    result['meta_left'] = r_type
    
    stats = []
    
    # Parse Size safely
    size_val = result.get('size')
    if isinstance(size_val, list):
        size_map = {"T": "Tiny", "S": "Small", "M": "Medium", "L": "Large", "H": "Huge", "G": "Gargantuan"}
        sizes = [size_map.get(s, s) for s in size_val if isinstance(s, str)]
        if sizes:
            stats.append({'type': 'item', 'name': 'Size', 'entry': " or ".join(sizes)})
    elif isinstance(size_val, str):
        size_map = {"T": "Tiny", "S": "Small", "M": "Medium", "L": "Large", "H": "Huge", "G": "Gargantuan"}
        stats.append({'type': 'item', 'name': 'Size', 'entry': size_map.get(size_val, size_val)})
            
    # Parse Speed safely
    sp = result.get('speed')
    if isinstance(sp, int):
        stats.append({'type': 'item', 'name': 'Speed', 'entry': f"{sp} ft."})
    elif isinstance(sp, dict):
        sp_strs = []
        for k, v in sp.items():
            if isinstance(v, bool):
                if v:
                    sp_strs.append(f"{k} equal to walking speed")
            elif isinstance(v, int):
                sp_strs.append(f"{k} {v} ft.")
            elif isinstance(v, dict):
                sp_strs.append(f"{k} {v.get('number', 0)} ft.")
        if sp_strs:
            stats.append({'type': 'item', 'name': 'Speed', 'entry': ", ".join(sp_strs).title()})
                
    # Parse Darkvision
    if result.get('darkvision'):
        stats.append({'type': 'item', 'name': 'Darkvision', 'entry': f"{result['darkvision']} ft."})
        
    if stats:
        entries = result.get('entries', [])
        if not isinstance(entries, list):
            entries = [entries]
        result['entries'] = stats + entries
        
    return result
