"""Apply 5etools copy modifications to data, shared by loading and prerelease sync."""
import copy
import math
import re
import ast
import operator

ENTRY_PROPS = ('entries', 'action', 'bonus', 'reaction', 'trait', 'legendary', 'mythic',
               'variant', 'spellcasting', 'actionHeader', 'legendaryHeader', 'mythicHeader')
PRESERVE_BASE = set('page otherSources referenceSources srd srd52 basicRules basicRules2024 reprintedAs hasFluff hasFluffImages hasToken tokenCredit tokenCustom foundryTokenScale altArt _versions'.split())
PRESERVE_MONSTER = set('legendaryGroup environment soundClip altArt variant dragonCastingColor familiar'.split())
SKILL_ABILITIES = dict(zip(
    ('athletics', 'acrobatics', 'sleight of hand', 'stealth', 'arcana', 'history',
     'investigation', 'nature', 'religion', 'animal handling', 'insight', 'medicine',
     'perception', 'survival', 'deception', 'intimidation', 'performance', 'persuasion'),
    ('str', 'dex', 'dex', 'dex', 'int', 'int', 'int', 'int', 'int', 'wis', 'wis',
     'wis', 'wis', 'wis', 'cha', 'cha', 'cha', 'cha')))


def as_list(value):
    return value if isinstance(value, list) else [value]


def _walk(value, fn):
    if isinstance(value, str):
        return fn(value)
    if isinstance(value, list):
        return [_walk(v, fn) for v in value]
    if isinstance(value, dict):
        return {k: _walk(v, fn) for k, v in value.items()}
    return value


def _pb(target):
    cr = target.get('cr', '0')
    if isinstance(cr, dict): cr = cr.get('cr', '0')
    return max(2, 1 + math.ceil(float(cr) / 4)) if '/' not in str(cr) else 2


def _math(expression):
    operations = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
                  ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv}
    def visit(node):
        if isinstance(node, ast.Constant) and type(node.value) in (int, float): return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in operations:
            return operations[type(node.op)](visit(node.left), visit(node.right))
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
            return (-1 if isinstance(node.op, ast.USub) else 1) * visit(node.operand)
        raise ValueError('Unsupported copy arithmetic expression')
    if len(expression) > 200: raise ValueError('Copy arithmetic expression is too long')
    return visit(ast.parse(expression, mode='eval').body)


def resolve_variables(value, target):
    def replace(match):
        mode, _, detail = match[1].partition('__')
        name = str(target.get('shortName') or target.get('name', 'creature'))
        if mode == 'name': return str(target.get('name', 'creature'))
        if mode in ('short_name', 'title_short_name'):
            name = name if target.get('isNamedCreature') else 'the ' + name.lower()
            return name[0].upper() + name[1:] if mode == 'title_short_name' else name
        ability = (int(target.get(detail, 10))-10)//2
        if mode in ('dc', 'spell_dc'): return str(8 + ability + _pb(target))
        if mode == 'to_hit': return f'{ability + _pb(target):+d}'
        if mode == 'damage_mod': return f' + {ability}' if ability > 0 else f' - {-ability}' if ability < 0 else ''
        size = target.get('size', ['M'])
        size = size[0] if isinstance(size, list) else size
        mult = {'L':2, 'H':3, 'G':4}.get(size, 1)
        if mode == 'size_mult': return str(math.floor(mult * _math(detail)) if detail else mult)
        if mode == 'damage_avg':
            expression = re.sub(r'\b(str|dex|con|int|wis|cha)\b', lambda m: str((int(target.get(m[0],10))-10)//2), detail)
            return str(math.floor(_math(expression.replace('size_mult', str(mult)))))
        return match[0]
    return _walk(value, lambda text: re.sub(r'<\$(.*?)\$>', replace, text))


def _spell_mod(target, mod):
    traits = target.get('spellcasting', [])
    trait = next((s for s in traits if not mod.get('name') or s.get('name') == mod['name']), None)
    if trait is None:
        raise ValueError('Copy spell modification has no matching spellcasting trait')
    mode = mod['mode']
    for key, data in mod.items():
        if key in ('mode', 'name'):
            continue
        if key == 'spells':
            for level, value in data.items():
                slot = trait.setdefault('spells', {}).setdefault(level, {})
                if mode == 'addSpells':
                    slot.setdefault('spells', []).extend(value.get('spells', []))
                    slot.update({k: v for k, v in value.items() if k != 'spells'})
                else:
                    _change_spell_list(slot.setdefault('spells', []), value, mode)
        elif isinstance(data, dict):
            for frequency, value in data.items():
                _change_spell_list(trait.setdefault(key, {}).setdefault(frequency, []), value, mode)
        elif isinstance(data, list):
            _change_spell_list(trait.setdefault(key, []), data, mode)


def _change_spell_list(spells, values, mode):
    if mode == 'addSpells':
        spells.extend(copy.deepcopy(values))
    elif mode == 'removeSpells':
        spells[:] = [s for s in spells if s not in values]
    else:
        for replacement in as_list(values):
            old = replacement['replace']
            if old not in spells:
                raise ValueError(f'Copy could not find spell {old}')
            i = spells.index(old)
            spells[i:i+1] = as_list(replacement['with'])


def apply_mods(target, mods):
    for prop, modifications in sorted(mods.items(), key=lambda item: (2 if item[0] == '*' else 1 if item[0] == '_' else 0, item[0])):
        for mod in as_list(modifications):
            if prop == '_':
                if mod['mode'] in ('addSpells', 'replaceSpells', 'removeSpells'):
                    _spell_mod(target, mod)
                    continue
                if mod['mode'] == 'addSkills':
                    cr = target.get('cr', '0')
                    if isinstance(cr, dict): cr = cr.get('cr', '0')
                    pb = max(2, 1 + math.ceil(float(cr) / 4)) if '/' not in str(cr) else 2
                    for skill, multiplier in mod['skills'].items():
                        ability = SKILL_ABILITIES[skill]
                        value = multiplier * pb + (target.get(ability, 10) - 10) // 2
                        skills = target.setdefault('skill', {})
                        skills[skill] = f'{max(value, int(skills.get(skill, value))):+d}'
                    continue
                if mod['mode'] == 'addSenses':
                    senses = target.setdefault('senses', [])
                    for sense in as_list(mod['senses']):
                        found = next((i for i,s in enumerate(senses) if re.search(re.escape(sense['type']) + r' (\d+)', s, re.I)), None)
                        if found is None: senses.append(f"{sense['type']} {sense['range']} ft.")
                        elif int(re.search(r'\d+', senses[found])[0]) < sense['range']:
                            senses[found] = f"{sense['type']} {sense['range']} ft."
                    continue
                if mod['mode'] == 'maxSize':
                    sizes = 'TSMLHGC'; maximum = sizes.index(mod['max'])
                    target['size'] = [s for s in target.get('size', ['M']) if sizes.index(s) <= maximum] or [mod['max']]
                    continue
                if mod['mode'] == 'scalarMultXp':
                    from parser_monsters import XP_MAP
                    cr = target.get('cr', '0')
                    if not isinstance(cr, dict): cr = {'cr': cr}
                    xp = cr.get('xp', XP_MAP.get(str(cr['cr']), 0)) * mod['scalar']
                    cr['xp'] = math.floor(xp) if mod.get('floor') else xp
                    target['cr'] = cr
                    continue
                if mod['mode'] == 'setProp':
                    _apply_prop(target, '', mod)
                    continue
                raise ValueError(f"Unsupported copy modification: {mod['mode']}")
            props = [p for p in ENTRY_PROPS if p in target] if prop == '*' else [prop]
            for field in props:
                _apply_prop(target, field, mod)
    return target


def _apply_prop(target, prop, mod):
    path = prop.split('.') if prop else []
    if isinstance(mod, dict) and mod.get('mode') == 'setProp':
        path += str(mod.get('prop', '')).split('.') if mod.get('prop') else []
    if not path:
        raise ValueError('Copy modification requires a property')
    parent = target
    for part in path[:-1]:
        parent = parent.setdefault(part, {})
    key = path[-1]
    if mod == 'remove':
        parent.pop(key, None)
        return
    mode = mod.get('mode')
    if mode in ('scalarAddProp', 'scalarMultProp'):
        value = parent.get(key)
        if not isinstance(value, dict): return
        for field in list(value) if mod['prop'] == '*' else [mod['prop']]:
            original = value[field]
            result = float(original) + mod['scalar'] if mode == 'scalarAddProp' else float(original) * mod['scalar']
            if mod.get('floor'): result = math.floor(result)
            if float(result).is_integer(): result = int(result)
            value[field] = f'{result:+}' if isinstance(original, str) else result
        return
    if mode == 'prefixSuffixStringProp':
        fields = [key] + (mod['prop'].split('.') if mod.get('prop') else [])
        value = parent
        for field in fields[:-1]: value = value.get(field, {})
        if isinstance(value.get(fields[-1]), str): value[fields[-1]] = mod.get('prefix','') + value[fields[-1]] + mod.get('suffix','')
        return
    if mode in ('scalarAddHit', 'scalarAddDc'):
        tag = 'hit' if mode == 'scalarAddHit' else 'dc'
        parent[key] = _walk(parent.get(key, []), lambda text: re.sub(r'\{@' + tag + r' ([+-]?\d+)\}', lambda m: '{@' + tag + ' ' + str(int(m[1]) + mod['scalar']) + '}', text))
        return
    if mode == 'setProp':
        parent[key] = copy.deepcopy(mod.get('value'))
        return
    if mode == 'replaceTxt':
        if key not in parent: return
        pattern = re.compile(mod['replace'], re.I if 'i' in mod.get('flags', '') else 0)
        replacement = re.sub(r'\$(\d+)', r'\\g<\1>', mod.get('with', ''))
        def replace(text):
            if mod.get('tagInsensitive'):
                return pattern.sub(replacement, text)
            return ''.join(p if p.startswith('{@') else pattern.sub(replacement, p)
                           for p in re.split(r'(\{@[^}]*\})', text))
        fields = mod.get('props', [None, 'entries', 'headerEntries', 'footerEntries'])
        value = parent[key]
        if not isinstance(value, list): value = [value]
        for i, entry in enumerate(value):
            if isinstance(entry, str) and None in fields:
                value[i] = replace(entry)
            elif isinstance(entry, dict):
                for field in fields:
                    if field is not None and field in entry:
                        entry[field] = _walk(entry[field], replace)
        parent[key] = value
        return
    current = parent.setdefault(key, [])
    if not isinstance(current, list):
        raise ValueError(f'Copy modification {mode} requires an array: {prop}')
    items = copy.deepcopy(as_list(mod.get('items', [])))
    if mode == 'appendArr': current.extend(items)
    elif mode == 'prependArr': current[:0] = items
    elif mode == 'appendIfNotExistsArr': current.extend(i for i in items if i not in current)
    elif mode == 'insertArr':
        index = mod['index']
        if index == -1: index = len(current)
        current[index:index] = items
    elif mode in ('replaceArr', 'replaceOrAppendArr'):
        selector = mod.get('replace')
        index = selector.get('index') if isinstance(selector, dict) else None
        if index is None:
            pattern = re.compile(selector['regex'], re.I if 'i' in selector.get('flags', '') else 0) if isinstance(selector, dict) and 'regex' in selector else None
            index = next((i for i, value in enumerate(current)
                          if (bool(pattern.search(str(value.get('name', '') if isinstance(value, dict) else value))) if pattern
                              else (value.get('name') if isinstance(value, dict) else value) == selector)), None)
        if index is not None and 0 <= index < len(current): current[index:index+1] = items
        elif mode == 'replaceOrAppendArr': current.extend(items)
        else: raise ValueError(f'Copy could not find {selector!r} in {prop}')
    elif mode == 'removeArr':
        names = as_list(mod.get('names', []))
        current[:] = [i for i in current if (i.get('name') if isinstance(i, dict) else i) not in names and i not in items]
    else:
        raise ValueError(f'Unsupported copy modification: {mode}')


def materialize(item, lookup, depth=0, seen=None, templates=None):
    meta = item.get('_copy')
    if not isinstance(meta, dict): return copy.deepcopy(item)
    seen = set() if seen is None else seen
    if id(item) in seen or depth > 20:
        raise ValueError(f"Circular copy reference: {item.get('name')}")
    base = lookup(meta, item)
    if base is None: return copy.deepcopy(item)
    merged = materialize(base, lookup, depth + 1, seen | {id(item)}, templates)
    merged.pop('_copy', None)
    excluded = PRESERVE_BASE | (PRESERVE_MONSTER if item.get('_data_type') == 'monster' else set())
    preserve = meta.get('_preserve', {})
    for field in excluded:
        if field not in item and not (preserve.get('*') or preserve.get(field)):
            merged.pop(field, None)
    for key, value in item.items():
        if key == '_copy': continue
        if value is None: merged.pop(key, None)
        else: merged[key] = copy.deepcopy(value)
    mods = copy.deepcopy(meta.get('_mod', {}))
    for reference in meta.get('_templates', []):
        template = next((t for t in templates or [] if t.get('name','').lower() == reference.get('name','').lower() and t.get('source','').lower() == reference.get('source','').lower()), None)
        if template is None: raise ValueError(f'Missing copy template: {reference}')
        applied = template.get('apply', {})
        for key, value in applied.get('_root', {}).items():
            if key not in item: merged[key] = copy.deepcopy(value)
        for key, value in applied.get('_mod', {}).items():
            mods[key] = as_list(mods.get(key, [])) + copy.deepcopy(as_list(value))
    return apply_mods(merged, resolve_variables(mods, merged))
