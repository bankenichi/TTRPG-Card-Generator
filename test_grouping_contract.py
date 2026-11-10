"""Regression contract for the approved grouping and splitting behavior."""
import ast
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import copy

import card_engine as engine


class GroupingContractTest(unittest.TestCase):
    def generate(self, entries, root='item'):
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp,'fixture.json');output=Path(temp,'cards.html')
            source.write_text(json.dumps(entries if root is None else {root:entries}),encoding='utf-8')
            result=engine.generate_html({'datasets':[{'file':str(source),'filters':{}}]},str(output))
            return result,output.read_text(encoding='utf-8')

    def test_existing_bonus_family_still_combines_rarities_and_prices(self):
        items=[{'name':f'+{bonus} Test Focus','source':'TCE','rarity':rarity,'value':value,
                'entries':[f'Gain a +{bonus} bonus to spell attacks.','Regain one spell slot.']}
               for bonus,rarity,value in [(1,'uncommon',10000),(2,'rare',40000),(3,'very rare',400000)]]
        result,html=self.generate(items)
        self.assertEqual(result['item_count'],1);self.assertEqual(result['card_count'],1)
        self.assertIn('Test Focus, +1, +2, or +3',html)
        self.assertIn('Gain a +1, +2, or +3 bonus',html)

    def test_rarity_price_table_display_does_not_split_existing_family(self):
        items=[{'name':f'+{n} Test Ammunition','entries':[f'Gain a +{n} bonus.','Same rule {@note ({@table Magic Item Values by Rarity|XDMG|'+str(n*100)+' GP})}.']} for n in (1,2,3)]
        result,html=self.generate(items)
        self.assertEqual(result['item_count'],1)
        self.assertIn('Test Ammunition, +1, +2, or +3',html)

    def test_different_rules_are_not_replaced_by_another_bonus_variant(self):
        result,html=self.generate([
            {'name':'Test Blade +1','entries':['Gain a +1 bonus.','May fly.']},
            {'name':'Test Blade +2','entries':['Gain a +2 bonus.','May breathe water.']}])
        self.assertEqual(result['item_count'],2)
        self.assertIn('May fly.',html);self.assertIn('May breathe water.',html)

    def test_actual_currency_costs_in_rules_remain_distinct(self):
        result,html=self.generate([
            {'name':'Test Focus +1','entries':['Gain a +1 bonus. Spend 100 GP to cast a spell.']},
            {'name':'Test Focus +2','entries':['Gain a +2 bonus. Spend 200 GP to cast a spell.']}])
        self.assertEqual(result['item_count'],2)
        self.assertIn('100 GP',html);self.assertIn('200 GP',html)

    def test_currency_costs_in_unrelated_table_links_remain_distinct(self):
        result,html=self.generate([
            {'name':'Test Focus +1','entries':['Gain a +1 bonus.','Spend {@table Casting Costs|TST|100 GP} to cast a spell.']},
            {'name':'Test Focus +2','entries':['Gain a +2 bonus.','Spend {@table Casting Costs|TST|200 GP} to cast a spell.']}])
        self.assertEqual(result['item_count'],2)
        self.assertIn('100 GP',html);self.assertIn('200 GP',html)

    def test_non_item_names_do_not_enter_item_family_grouping(self):
        result,html=self.generate([{'name':name,'entries':['Separate spell rules.']} for name in ('Shield','Fire Shield')],root='spell')
        self.assertEqual(result['item_count'],2);self.assertIn('Fire Shield',html)

    def test_status_names_do_not_enter_item_family_grouping(self):
        result,html=self.generate([{'name':name,'entries':['Separate status rules.']} for name in ('Shield','Fire Shield')],root='status')
        self.assertEqual(result['item_count'],2);self.assertIn('Fire Shield',html)

    def test_non_item_base_cannot_swallow_an_item_element_variant(self):
        result,html=self.generate({'spell':[{'name':'Shield','entries':['Spell rules.']}],
                                   'item':[{'name':'Fire Shield','entries':['Item rules.']}]},root=None)
        self.assertEqual(result['item_count'],2)
        self.assertIn('Spell rules.',html);self.assertIn('Item rules.',html)

    def test_existing_level_family_still_combines(self):
        result,html=self.generate([{'name':f'Test Scroll (Level {n})','entries':['Use the spell.']} for n in (1,2,3)])
        self.assertEqual(result['item_count'],1);self.assertEqual(result['card_count'],1)
        self.assertIn('Level 1',html);self.assertIn('Level 3',html)

    def test_existing_element_family_still_uses_its_base_item(self):
        result,html=self.generate([{'name':name,'entries':[text]} for name,text in [('Test Shield','Base rules.'),('Fire Test Shield','Element rules.')]])
        self.assertEqual(result['item_count'],1);self.assertIn('Base rules.',html)

    def test_enspelled_exception_remains_unchanged(self):
        result,_=self.generate([{'name':f'Enspelled Test Armor +{n}','entries':[f'Spell level {n}.']} for n in (1,2,3)])
        self.assertEqual(result['item_count'],3)

    def test_original_split_function_is_unchanged(self):
        text=Path(engine.__file__).read_text(encoding='utf-8');lines=text.splitlines(keepends=True)
        node=next(n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef) and n.name=='split_item_by_lines')
        source=''.join(lines[node.lineno-1:node.end_lineno])
        self.assertEqual(hashlib.sha256(source.encode()).hexdigest(),'538d505c4ebb6e7d56ac23b10095d4da61a7a28d295c51e0c247a8edeaedbb43')

    def test_engine_is_frozen_with_only_approved_nightingale_exception(self):
        text=Path(engine.__file__).read_text(encoding='utf-8')
        start=text.index('    # Only entities routed to the items parser')
        end=text.index('    seen_titles, final_list = set(), []',start)
        self.assertEqual(hashlib.sha256((text[:start]+text[end:]).encode()).hexdigest(),'d13630ea1f8abc3701fe78bd9ca1c256f1bb44313a137294297d1d23ab602b7b')

    def test_layout_is_frozen_with_only_approved_nightingale_exception(self):
        text=Path(engine.__file__).read_text(encoding='utf-8')
        start=text.index('    final_condensed_items = []\n')
        end=text.index('    html_content = [f',start)
        self.assertEqual(hashlib.sha256(text[start:end].encode()).hexdigest(),'41ce0efea3360a6ecf2fe29834dea3f12e40b6fd0594d5be6c63f47f87145da4')

    def test_nightingale_column_correction_is_limited_to_exact_item_and_source(self):
        name="Queen Ehlissa's Marvelous Nightingale"
        columns=[['First column.'],[{'type':'nested_header','name':'Counterspell'},'Counterspell rule.',
                 {'type':'nested_header','name':'Random Properties'},'Random properties rule.',
                 {'type':'nested_header','name':'Destroying the Nightingale'},'Destroying rule.',
                 {'type':'nested_header','name':'Ensemble Casting'},'Casting rule.']]
        for title,source,corrected in [(name,'AU',True),(name,'TST',False),('Other Nightingale','AU',False)]:
            with self.subTest(title=title,source=source),patch.object(engine,'split_item_by_lines',side_effect=lambda *a,**k:copy.deepcopy(columns)):
                result,html=self.generate([{'name':title,'source':source,'entries':['Seed ' * 200]}])
                self.assertEqual(result['card_count'],1)
                left,right=html.split('<div style="flex: 1; min-width: 0;">')[1:]
                self.assertEqual('Counterspell rule.' in left,corrected)
                self.assertEqual('Counterspell rule.' in right,not corrected)
                self.assertIn('Destroying rule.',right)
                for rule in ('First column.','Counterspell rule.','Random properties rule.','Destroying rule.','Casting rule.'):
                    self.assertEqual(html.count(rule),1)

    def test_original_text_measurement_helper_is_unchanged(self):
        text=Path(engine.__file__).with_name('parser_utils.py').read_text(encoding='utf-8')
        lines=text.splitlines(keepends=True)
        node=next(n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef) and n.name=='clean_tags')
        source=''.join(lines[node.lineno-1:node.end_lineno])
        self.assertEqual(hashlib.sha256(source.encode()).hexdigest(),'3a416ebb3c318c75f2cc256d9e98d137f89e2fd9471239c3400eef3b2abacafe')

    def test_different_attunement_is_not_discarded(self):
        result,html=self.generate([
            {'name':'Test Focus +1','entries':['Gain a +1 bonus.'],'reqAttune':'by a wizard'},
            {'name':'Test Focus +2','entries':['Gain a +2 bonus.'],'reqAttune':'by a cleric'}])
        self.assertEqual(result['item_count'],2)
        self.assertIn('by a wizard',html);self.assertIn('by a cleric',html)


if __name__=='__main__':unittest.main()
