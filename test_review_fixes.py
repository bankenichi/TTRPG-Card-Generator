import copy
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import card_engine as engine
import data_paths
import launcher
from parser_classes import enrich_class
from parser_monsters import enrich_monster
from parser_races import enrich_race
from parser_spells import _spell_pre_filter_hook, enrich_spell
from parser_utils import clean_tags


class ReviewFixesTest(unittest.TestCase):
    def generate(self, data, filters=None):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'fixture.json'
            path.write_text(json.dumps(data), encoding='utf-8')
            output = Path(temp) / 'deck.html'
            result = engine.generate_html({'datasets': [{'file': str(path), 'filters': filters or {}}]}, str(output))
            return result, output.read_text(encoding='utf-8') if output.exists() else ''

    def test_canonical_paths_cannot_escape(self):
        with tempfile.TemporaryDirectory() as temp:
            for sub in ('class', 'spells'):
                Path(temp, 'data', 'data', sub).mkdir(parents=True)
            with self.assertRaises(ValueError):
                data_paths.resolve_dataset_path('generators/data/../../../outside', temp)

    def test_invalid_zip_preserves_installed_data(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp, 'data'); root.mkdir()
            sentinel = root / 'previous'; sentinel.write_text('keep')
            with patch.object(launcher, 'GENERATORS_DIR', temp), patch.object(launcher, 'DATA_DIR', str(root)):
                self.assertFalse(launcher.extract_zip_data(b'invalid')[0])
            self.assertEqual(sentinel.read_text(), 'keep')

    def test_failed_replacement_and_failed_rollback_retain_backup(self):
        from data_install import replace_tree
        with tempfile.TemporaryDirectory() as temp:
            old=Path(temp,'data'); old.mkdir(); (old/'keep').write_text('previous')
            staged=Path(temp,'staged'); staged.mkdir()
            original=os.replace
            calls=[]
            def failing_replace(source,dest):
                calls.append((source,dest))
                if len(calls)>1: raise PermissionError('simulated lock')
                return original(source,dest)
            with patch('data_install.os.replace', side_effect=failing_replace), self.assertRaises(RuntimeError):
                replace_tree(str(staged),str(old))
            backups=list(Path(temp).glob('.backup-*/previous/keep'))
            self.assertEqual(len(backups),1);self.assertEqual(backups[0].read_text(),'previous')

    def test_replacement_cleans_readonly_git_style_files(self):
        from data_install import replace_tree
        import stat
        with tempfile.TemporaryDirectory() as temp:
            old=Path(temp,'data');old.mkdir();locked=old/'object';locked.write_text('old')
            locked.chmod(stat.S_IREAD)
            staged=Path(temp,'staged');staged.mkdir();(staged/'new').write_text('new')
            replace_tree(str(staged),str(old))
            self.assertTrue((old/'new').exists());self.assertFalse(list(Path(temp).glob('.backup-*')))

    def test_zip_accepts_both_root_layouts(self):
        for prefix in ('', 'repo/'):
            with self.subTest(prefix=prefix), tempfile.TemporaryDirectory() as temp:
                stream = io.BytesIO()
                with zipfile.ZipFile(stream, 'w') as archive:
                    for sub in ('class', 'spells'):
                        archive.writestr(prefix + f'data/{sub}/index.json', '{}')
                root = str(Path(temp, 'data'))
                with patch.object(launcher, 'GENERATORS_DIR', temp), patch.object(launcher, 'DATA_DIR', root), patch.object(launcher, 'sync_prerelease_content'), patch.object(launcher, 'get_git_cmd', return_value=None):
                    self.assertTrue(launcher.extract_zip_data(stream.getvalue())[0])
                self.assertTrue(data_paths._has_5etools_shape(root))

    def test_zip_with_corrupt_dataset_json_preserves_previous_install(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp,'data');root.mkdir();(root/'keep').write_text('previous')
            stream=io.BytesIO()
            with zipfile.ZipFile(stream,'w') as archive:
                archive.writestr('data/class/index.json','{}')
                archive.writestr('data/spells/index.json','{}')
                archive.writestr('data/items.json','{broken')
            with patch.object(launcher,'GENERATORS_DIR',temp),patch.object(launcher,'DATA_DIR',str(root)):
                success,message=launcher.extract_zip_data(stream.getvalue())
            self.assertFalse(success);self.assertIn('Invalid dataset JSON',message)
            self.assertEqual((root/'keep').read_text(),'previous')

    def test_prose_sanitizer_strips_scripts_and_event_attributes(self):
        from safe_html import sanitize_prose
        value = sanitize_prose('<script>alert(1)</script><img src=x onerror=alert(2)><i onclick="x()">safe</i>')
        self.assertEqual(value, '<i>safe</i>')

    def test_table_cells_preserve_supported_values_and_formatting(self):
        table = {'type': 'table', 'rows': [[{'type': 'bonus', 'value': 3},
                 {'type': 'dice', 'toRoll': [{'number': 2, 'faces': 6}]},
                 {'type': 'cell', 'roll': {'min': 1, 'max': 4}, 'entry': '{@i Roll again}'}]]}
        html = engine.parse_entry_to_html(table)
        for value in ('+3', '2d6', '1-4 Roll again'):
            self.assertIn(value, html)

    def test_titles_and_metadata_keep_the_original_format(self):
        _, html = self.generate({'skill': [{'name': "Tools & Tinker's Tricks", 'source': 'TST', 'page': 12, 'entries': ['Use a tool.']}]})
        self.assertIn("<span>Tools & Tinker's Tricks</span>", html)
        self.assertIn('TST p.12', html)

    def test_non_item_names_never_condense(self):
        result, html = self.generate({'spell': [{'name': name, 'entries': ['Different rules']} for name in ('Shield', 'Fire Shield')]})
        self.assertEqual(result['item_count'], 2)

        self.assertIn('Fire Shield', html)
        result, _ = self.generate({'monster': [{'name': name, 'entries': []} for name in ('Air Elemental', 'Fire Elemental')]})
        self.assertEqual(result['item_count'], 2)


    def test_item_bonus_variants_keep_distinct_rules_and_rarity(self):
        result, html = self.generate({'item': [
            {'name': 'Weapon +1', 'rarity': 'uncommon', 'entries': ['First only.']},
            {'name': 'Weapon +2', 'rarity': 'rare', 'entries': ['Second only.']}]})
        self.assertEqual(result['item_count'], 2)
        self.assertIn('Second only.', html)

    def test_class_rendering_keeps_existing_badge_formatting(self):
        _, html = self.generate({'class': [{'name': 'Artificer', 'hd': {'faces': 8},
            'rarity_badge': '<b>Test badge</b>'}]})
        self.assertIn('<b>Test badge</b>', html)
        self.assertIn('Artificer', html)

    def test_dataset_zip_cannot_write_outside_tree(self):
        from data_install import safe_extract
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp, 'dataset'); root.mkdir()
            stream = io.BytesIO()
            with zipfile.ZipFile(stream, 'w') as archive:
                archive.writestr('../outside.json', '{"skill":[]}')
            stream.seek(0)
            with zipfile.ZipFile(stream) as archive, self.assertRaises(ValueError):
                safe_extract(archive, root)
            self.assertFalse(Path(temp, 'outside.json').exists())
    def test_feat_category_is_filterable_before_enrichment(self):
        for code, label in [('O', 'Origin Feat'), ('G', 'General Feat'), ('EB', 'Epic Boon'), ('FS', 'Fighting Style')]:
            result, _ = self.generate({'feat': [{'name': 'Feat', 'category': code, 'entries': ['Text']}]}, {'category': [label]})
            self.assertGreater(result['card_count'], 0)

    def test_copy_modifications_change_actions_and_wildcard_text(self):
        from prerelease_sync import _materialize_copy
        base = {'name': 'Base', 'source': 'X', 'action': [{'name': 'Sword', 'entries': ['Base attacks.']}]}
        child = {'name': 'Child', 'source': 'Y', '_copy': {'name': 'Base', 'source': 'X', '_mod': {'action': {'mode': 'replaceArr', 'replace': 'Sword', 'items': {'name': 'Hammer', 'entries': ['Base swings.']}}, '*': {'mode': 'replaceTxt', 'replace': 'Base', 'with': 'Child'}}}}
        result = _materialize_copy(child, 'monster', {('monster', 'base', 'x'): base})
        self.assertEqual(result['action'], [{'name': 'Hammer', 'entries': ['Child swings.']}])
        self.assertEqual(base['action'][0]['name'], 'Sword')

    def test_copy_templates_preserve_explicit_values_and_exclude_lair(self):
        from copy_resolver import materialize
        base = {'_data_type':'monster', 'name':'Base', 'type':'beast', 'legendaryGroup':{'name':'Wrong'}, 'immune':[]}
        child = {'_data_type':'monster', 'name':'Child', 'speed':{'walk':20}, '_copy':{'name':'Base','_templates':[{'name':'Skeleton','source':'X'}]}}
        templates = [{'name':'Skeleton','source':'X','apply':{'_root':{'type':'undead','speed':{'walk':30}},'_mod':{'immune':{'mode':'appendArr','items':'poison'}}}}]
        result = materialize(child, lambda meta,item:base, templates=templates)
        self.assertEqual(result['type'],'undead'); self.assertEqual(result['speed'],{'walk':20})
        self.assertEqual(result['immune'],['poison']); self.assertNotIn('legendaryGroup',result)

    def test_copy_wildcard_modifications_run_after_insertions(self):
        from copy_resolver import apply_mods
        result = apply_mods({'trait':[]}, {'*':{'mode':'replaceTxt','replace':'Base','with':'Child'}, 'trait':{'mode':'appendArr','items':{'name':'Trait','entries':['Base acts.']}}})
        self.assertEqual(result['trait'][0]['entries'],['Child acts.'])

    def test_class_feature_matches_level(self):
        item = {'name': 'Barbarian', 'source': 'X', 'classFeatures': ['Strike|Barbarian|X|13', 'Strike|Barbarian|X|17']}
        features = [{'_data_type': 'classFeature', 'name': 'Strike', 'source': 'X', 'className': 'Barbarian', 'classSource': 'X', 'level': level, 'entries': [text]} for level, text in [(13, 'first'), (17, 'upgrade')]]
        result = enrich_class(item, all_raw=features)
        feature = next(e for e in result['entries'] if e.get('name') == 'Strike (Level 17)')
        self.assertEqual(feature['entries'], ['upgrade'])

    def test_no_invented_lair_cr(self):
        monster = {'name': 'Dragon', 'cr': '21', 'legendaryGroup': {'name': 'Group', 'source': 'X'}}
        group = {'_data_type': 'legendaryGroup', 'name': 'Group', 'source': 'X', 'lairActions': ['Lair text']}
        result = enrich_monster(monster, all_raw=[group])
        challenge = next(e['entry'] for e in result['entries'] if isinstance(e, dict) and e.get('name') == 'Challenge')
        self.assertNotIn('22', challenge)

    def test_legendary_budget_comes_from_data(self):
        result = enrich_monster({'name': 'Dragon', 'legendaryActions': 2, 'legendary': [{'name': 'Move', 'entries': ['Move.']}]})
        text = ' '.join(e for e in result['entries'] if isinstance(e, str))
        self.assertIn('Uses: 2.', text)
        self.assertNotIn('4 in Lair', text)

    def test_spell_footer_preserves_filter_classes(self):
        spell = {'name': 'Arcane Weapon', 'classes': {'fromClassList': [{'name': 'Artificer'}]}}
        _spell_pre_filter_hook(spell, '', [])
        self.assertEqual(enrich_spell(spell)['custom_footer_left'], 'Artificer')

    def test_subrace_inherits_parent_from_loaded_data_without_mutation(self):
        parent = {'_data_type': 'race', 'name': 'Elf', 'source': 'PHB', 'size': ['M'], 'speed': 30, 'entries': ['Inherited trance']}
        child = {'_data_type': 'subrace', 'name': 'Test Mark', 'source': 'UA', 'raceName': 'Elf', 'raceSource': 'PHB', 'entries': ['Subrace ability']}
        original = copy.deepcopy((parent, child))
        result = enrich_race(child, all_raw=[parent, child])
        self.assertEqual(result['name'], 'Elf (Test Mark)')
        self.assertEqual(result['speed'], 30)
        self.assertIn('Inherited trance', result['entries'])
        self.assertIn('Subrace ability', result['entries'])
        self.assertEqual((parent, child), original)

    def test_boolean_speed_is_relative(self):
        result = enrich_race({'speed': {'walk': 30, 'fly': True}})
        speed = next(e['entry'] for e in result['entries'] if e.get('name') == 'Speed')
        self.assertNotIn('True', speed)
        self.assertIn('Walking Speed', speed)

    def test_split_tables_preserve_every_row_in_order(self):
        rows = [[str(i), 'Row ' + str(i) + ' long text ' * 15] for i in range(60)]
        table = {'type':'table','colLabels':['Number','Text'],'rows':rows}
        chunks = engine.split_item_by_lines([table], target_lines=20, absolute_max=24)
        actual = [row for chunk in chunks for entry in chunk if isinstance(entry,dict) and entry.get('type')=='table' for row in entry['rows']]
        self.assertEqual(actual, rows)

    def test_split_paragraphs_keep_all_words_and_atomic_tags(self):
        text = ' '.join(['word'+str(i) for i in range(300)]) + ' {@spell Fireball|PHB} end'
        chunks = engine.split_item_by_lines(['Intro ' * 60, text], target_lines=12, absolute_max=15)
        flattened = ' '.join(entry for chunk in chunks for entry in chunk)
        self.assertEqual(flattened.split(), ('Intro ' * 60 + ' ' + text).split())
        self.assertIn('{@spell Fireball|PHB}', flattened)


if __name__ == '__main__':
    unittest.main()
