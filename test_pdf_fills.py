from pathlib import Path
import tempfile
import unittest

from pypdf import PdfReader,PdfWriter
from pypdf.generic import DictionaryObject,FloatObject,IndirectObject,NameObject

from pdf_fills import normalize_raw,coalesce_native_fills


PREFIX=b'.5451 0 0 rg\n/G1 gs\n'
FILLS=b'19 96 35 11 re\nf\n54 96 30 11 re\nf\n84 96 37 11 re\nf\n121 96 37 11 re\nf\n'
STATES={'/G1':DictionaryObject({NameObject('/ca'):FloatObject('.1'),NameObject('/BM'):NameObject('/Normal')})}


class PdfFillTest(unittest.TestCase):
    def test_native_rgb_stroke_and_fill_on_one_line(self):
        raw=b'.5451 0 0 RG '+PREFIX+FILLS
        result,count=normalize_raw(raw,STATES)
        self.assertEqual((result,count),(b'.5451 0 0 RG '+PREFIX+b'19 96 139 11 re\nf\n',3))

    def test_adjacent_cells_preserve_other_native_bytes_exactly(self):
        before=b'q\n.153717726 1 2 3 4 5 c\nn\n'
        after=b'0.333333333 1 2 3 4 5 cm\nBT\n<000100020003> Tj\nET\nQ\n'
        raw=before+PREFIX+FILLS+after
        result,count=normalize_raw(raw,STATES)
        self.assertEqual(count,3)
        self.assertEqual(result,before+PREFIX+b'19 96 139 11 re\nf\n'+after)
        self.assertEqual(normalize_raw(result,STATES),(result,0))

    def test_raw_decimal_adjacency_has_no_float_rounding_tolerance(self):
        raw=PREFIX+b'0 0 1.00000000000000000001 2 re\nf\n1.00000000000000000002 0 1 2 re\nf\n'
        self.assertEqual(normalize_raw(raw,STATES),(raw,0))
        exact=PREFIX+b'0 0 1.00000000000000000001 2 re\nf\n1.00000000000000000001 0 1 2 re\nf\n'
        self.assertEqual(normalize_raw(exact,STATES),(PREFIX+b'0 0 2.00000000000000000001 2 re\nf\n',1))

    def test_gaps_overlap_different_rows_and_degenerate_dimensions_unchanged(self):
        for second in (b'2 0 1 2',b'.5 0 1 2',b'1 1 1 2',b'1 0 1 3',b'1 0 0 2',b'1 0 -1 2'):
            with self.subTest(second=second):
                raw=PREFIX+b'0 0 1 2 re\nf\n'+second+b' re\nf\n'
                self.assertEqual(normalize_raw(raw,STATES),(raw,0))

    def test_no_join_across_text_graphics_state_or_clipping_operations(self):
        for intervening in (b'BT\n(x) Tj\nET\n',b'0 0 0 rg\n',b'q\n',b'0 0 10 10 re\nW\nn\n'):
            with self.subTest(intervening=intervening):
                raw=PREFIX+b'0 0 1 2 re\nf\n'+intervening+b'1 0 1 2 re\nf\n'
                self.assertEqual(normalize_raw(raw,STATES),(raw,0))

    def test_open_paths_comments_and_unreviewed_states_are_not_rewritten(self):
        for raw,states in [(b'0 0 m\n'+PREFIX+FILLS,STATES),
                           (PREFIX+FILLS.replace(b're\nf',b're\n% comment\nf'),STATES),
                           (PREFIX+FILLS,{}),
                           (PREFIX+FILLS,{'/G1':DictionaryObject({NameObject('/ca'):FloatObject('1'),NameObject('/BM'):NameObject('/Normal')})}),
                           (PREFIX+FILLS,{'/G1':DictionaryObject({**STATES['/G1'],NameObject('/SMask'):NameObject('/None')})})]:
            with self.subTest(raw=raw,states=states):self.assertEqual(normalize_raw(raw,states),(raw,0))

    def test_source_text_that_looks_like_fill_commands_is_preserved(self):
        raw=b'BT\n(Example\n'+PREFIX+FILLS+b') Tj\nET\n'
        self.assertEqual(normalize_raw(raw,STATES),(raw,0))
        with self.assertRaisesRegex(ValueError,'changed other drawing commands'):
            normalize_raw(raw+PREFIX+FILLS,STATES)

    def test_inline_image_false_match_cannot_change_image_bytes(self):
        data=b'x\n'+PREFIX+FILLS
        raw=b'BI\n/W '+str(len(data)).encode()+b' /H 1 /CS /G /BPC 8\nID '+data+b'\nEI\n'+PREFIX+FILLS
        with self.assertRaisesRegex(ValueError,'changed other drawing commands'):
            normalize_raw(raw,STATES)

    def test_normalized_content_is_a_valid_compressed_indirect_stream(self):
        from pypdf.generic import DecodedStreamObject
        writer=PdfWriter();page=writer.add_blank_page(width=612,height=792)
        page[NameObject('/Resources')]=DictionaryObject({NameObject('/ExtGState'):DictionaryObject({NameObject('/G1'):STATES['/G1']})})
        stream=DecodedStreamObject();stream.set_data(PREFIX+FILLS)
        page[NameObject('/Contents')]=writer._add_object(stream)
        self.assertEqual(coalesce_native_fills(page,writer),3)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'fills.pdf';writer.write(path)
            reader=PdfReader(path,strict=True);contents=reader.pages[0]['/Contents']
            self.assertIsInstance(reader.pages[0].raw_get('/Contents'),IndirectObject)
            self.assertEqual(contents['/Filter'],'/FlateDecode')
            self.assertEqual(contents.get_data(),PREFIX+b'19 96 139 11 re\nf\n')
            self.assertEqual([op for _,op in reader.pages[0].get_contents().operations],[b'rg',b'gs',b're',b'f'])


if __name__=='__main__':unittest.main()
