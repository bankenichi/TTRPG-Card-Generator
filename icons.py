# icons.py
import os

# Centralized mapping of _data_type or meta_left labels to SVG filenames
ICON_MAP = {
    # Data Types & Core Categories
    "action": "action-triangle-glyph",
    "actions": "action-triangle-glyph",
    "background": "backgrounds",
    "backgrounds": "backgrounds",
    "bastion": "bastions",
    "bastions": "bastions",
    "facility": "bastions",
    "bestiary": "bestiary",
    "monster": "bestiary",
    "monsters": "bestiary",
    "class": "classes",
    "classes": "classes",
    "condition": "conditions-diseases",
    "conditions": "conditions-diseases",
    "disease": "conditions-diseases",
    "diseases": "conditions-diseases",
    "status": "conditions-diseases",
    "deck": "decks",
    "decks": "decks",
    "card": "decks",
    "cards": "decks",
    "deity": "deities",
    "deities": "deities",
    "feat": "feats",
    "feats": "feats",
    "item": "items",
    "items": "items",
    "language": "languages",
    "languages": "languages",
    "psionic": "psionics",
    "psionics": "psionics",
    "race": "races",
    "races": "races",
    "subrace": "races",
    "subraces": "races",
    "lineage": "races",
    "spell": "spells",
    "spells": "spells",
    "vehicle": "vehicles",
    "vehicles": "vehicles",
    "vehicleupgrade": "vehicle-upgrades",
    "vehicle upgrade": "vehicle-upgrades",
    "vehicle upgrades": "vehicle-upgrades",
    "supernatural gift": "supernatural-gifts",
    "supernatural gifts": "supernatural-gifts",
    "skill": "skills",
    "skills": "skills",
    
    # Meta Labels (Optional Features & Specifics)
    "optional feature": "optionalfeatures",
    "optional features": "optionalfeatures",
    "optionalfeature": "optionalfeatures",
    "optionalfeatures": "optionalfeatures",
    "maneuver": "maneuvers",
    "metamagic": "metamagic",
    "eldritch invocation": "eldritch-invocation",
    "arcane shot": "arcane-shot",
    "renown perk": "renown-perk",
    "elemental discipline": "elemental-discipline",
    "rune": "rune-knight-rune",
    "artificer infusion": "items",
    "fighting style": "action-triangle-glyph",
    "pact boon": "eldritch-invocation",
    
    # Specific Classes
    "artificer": "artificer",
    "barbarian": "barbarian",
    "bard": "bard",
    "cleric": "cleric",
    "druid": "druid",
    "fighter": "fighter",
    "monk": "monk",
    "paladin": "paladin",
    "ranger": "ranger",
    "rogue": "rogue",
    "sorcerer": "sorcerer",
    "warlock": "warlock",
    "wizard": "wizard",
    "psion": "psion",
    "mystic": "mystic",
    "sidekick": "sidekick"
}

CORE_CLASSES = [
    "artificer", "barbarian", "bard", "cleric", "druid", 
    "fighter", "monk", "paladin", "ranger", "rogue", 
    "sorcerer", "warlock", "wizard", "psion", "mystic", "sidekick"
]

def resolve_card_icon_name(item, dataset_filename):
    """
    Determines the correct SVG icon name to use based on the item's data type, 
    meta label, or origin file.
    """
    meta = str(item.get('meta_left', '')).lower().strip()
    dtype = str(item.get('_data_type', '')).lower().strip()
    name = str(item.get('name', '')).lower().strip()
    cat_value = str(item.get('category') or item.get('type') or '').lower().strip()

    # 1. SMART CLASS INTERCEPTOR
    if dtype in ('class', 'classes', 'subclass', 'subclasses'):
        parent_class = str(item.get('className', '')).lower().strip()
        for c in CORE_CLASSES:
            if c in name or c in meta or c in parent_class:
                return ICON_MAP.get(c, 'classes')
        return ICON_MAP.get('classes', 'classes')

    # 2. Check Meta Label
    if meta in ICON_MAP:
        return ICON_MAP[meta]

    # 3. Check specific type/category fields
    if cat_value in ICON_MAP:
        return ICON_MAP[cat_value]
        
    if '|' in cat_value:
        cat_value_simple = cat_value.split('|')[0]
        if cat_value_simple in ICON_MAP:
            return ICON_MAP[cat_value_simple]
            
    # 4. Check strict _data_type
    if dtype in ICON_MAP:
        return ICON_MAP[dtype]
            
    # 5. Check origin dataset filename
    dataset_key = os.path.basename(dataset_filename).lower()
    if 'items' in dataset_key:
        return 'items'
        
    # Universal Fallback
    return 'action-triangle-glyph'

def resolve_watermark_name(item, dataset_filename):
    return 'watermark-emblem'

def resolve_background_name(item, dataset_filename):
    return 'parchment-background'

def resolve_card_back_name(payload=None):
    return 'card-back'

def resolve_divider_name(item, dataset_filename):
    return 'ornamental-divider'
