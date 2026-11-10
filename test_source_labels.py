import json
from pathlib import Path
import tempfile
import unittest

from source_labels import apply_source_labels,load_source_labels


class SourceLabelTest(unittest.TestCase):
    labels={'xua2022clericandrevisedspecies':{'code':'XUA2022ClericAndRevisedSpecies','label':'XUA22CRS','full':'Unearthed Arcana 2022: The Cleric and Revised Species'}}
    def test_source_book_title_takes_precedence_over_embedded_adventure(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'data').mkdir()
            (root/'data/books.json').write_text(json.dumps({'book':[{'source':'MOT','name':'Mythic Odysseys of Theros'}]}),encoding='utf-8')
            (root/'data/adventures.json').write_text(json.dumps({'adventure':[{'source':'MOT','name':'Theros: No Silent Secret'}]}),encoding='utf-8')
            self.assertEqual(load_source_labels(root)['mot']['full'],'Mythic Odysseys of Theros')

    def test_rewrites_only_source_span_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp,'deck.html')
            body='<div class="content-inner"><p>A &amp; B <i>formatted</i>.</p><table><tr><td>1d4 + 2</td></tr></table></div>'
            html='<!DOCTYPE html><html><body><div class="meta"><span>Adventuring Gear</span><span style="font-style: italic;">XUA2022CLERICANDREVISEDSPECIES p.23</span></div>'+body+'<script>if(a < b) run();</script></body></html>'
            path.write_text(html,encoding='utf-8');result=apply_source_labels(path,self.labels)
            updated=path.read_text(encoding='utf-8')
            self.assertEqual(result['changed_labels'],1);self.assertIn('>XUA22CRS p.23</span>',updated)
            self.assertIn('title="Unearthed Arcana 2022: The Cleric and Revised Species [XUA2022ClericAndRevisedSpecies]"',updated)
            self.assertIn(body,updated);self.assertIn('<script>if(a < b) run();</script>',updated)
            apply_source_labels(path,self.labels);self.assertEqual(path.read_text(encoding='utf-8'),updated)

    def test_unknown_sources_remain_verbatim(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp,'deck.html');html='<div class="meta"><span style="font-style: italic;">CUSTOM p.4</span></div>'
            path.write_text(html,encoding='utf-8');apply_source_labels(path,self.labels)
            self.assertEqual(path.read_text(encoding='utf-8'),html)

    def test_metadata_is_escaped(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp,'deck.html');path.write_text('<div class="meta"><span style="font-style: italic;">BAD</span></div>',encoding='utf-8')
            apply_source_labels(path,{'bad':{'code':'BAD','label':'<img src=x onerror=alert(1)>','full':'" onmouseover="alert(1)'}})
            html=path.read_text(encoding='utf-8');self.assertNotIn('<img',html);self.assertIn('&lt;img',html)
            self.assertNotIn('title="" onmouseover=',html)

    def test_reads_provided_abbreviation_and_blocks_index_escape(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);folder=root/'prerelease';folder.mkdir()
            (folder/'index.json').write_text(json.dumps({'toImport':['source.json']}),encoding='utf-8')
            (folder/'source.json').write_text(json.dumps({'_meta':{'sources':[{'json':'XUA2022ClericAndRevisedSpecies','abbreviation':'XUA22CRS','full':'Cleric and Revised Species'}]}}),encoding='utf-8')
            self.assertEqual(load_source_labels(root)['xua2022clericandrevisedspecies']['label'],'XUA22CRS')
            (folder/'index.json').write_text(json.dumps({'toImport':['../outside.json']}),encoding='utf-8')
            with self.assertRaises(ValueError):load_source_labels(root)


if __name__=='__main__':unittest.main()
