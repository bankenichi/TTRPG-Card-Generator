"""Lossless PDF composition for native WebView captures, without reflowing text.

PNG backgrounds are reused; opaque pixel differences and their binary masks
retain the original rendered card pixels. The desktop vector exporter is separate.
"""
import hashlib
from pathlib import Path
import struct
import zlib

from pypdf import PdfWriter
from pypdf.generic import (ArrayObject, BooleanObject, DecodedStreamObject,
                          DictionaryObject, EncodedStreamObject, NameObject, NumberObject)


def _png(path):
    source = Path(path).read_bytes()
    if not source.startswith(b'\x89PNG\r\n\x1a\n'):
        raise ValueError('Captured artwork is not PNG')
    cursor = 8
    dimensions = None
    compressed = []
    while cursor < len(source):
        length = struct.unpack('>I', source[cursor:cursor+4])[0]
        kind = source[cursor+4:cursor+8]
        value = source[cursor+8:cursor+8+length]
        cursor += length + 12
        if kind == b'IHDR':
            width,height,bits,color,compression,filtering,interlaced = struct.unpack('>IIBBBBB',value)
            if (bits,color,compression,filtering,interlaced) != (8,2,0,0,0):
                raise ValueError('Captured RGB PNG has unsupported encoding')
            dimensions = width,height
        elif kind == b'IDAT': compressed.append(value)
        elif kind == b'IEND': break
    if not dimensions or not compressed:
        raise ValueError('Captured PNG is incomplete')
    return dimensions,b''.join(compressed),hashlib.sha256(source).hexdigest()


def _safe(directory,name):
    if not isinstance(name,str) or Path(name).name != name or '/' in name or '\\' in name:
        raise ValueError('Invalid capture filename')
    return Path(directory,name)


class RenderedPdfWriter:
    def __init__(self):
        self.writer = PdfWriter()
        self.writer.pdf_header = b'%PDF-1.4'
        self.images = {}
        self.masks = {}
        self.solids = {}
        self.cards = 0

    def _mask(self,path,width,height):
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest(),width,height
        if digest not in self.masks:
            stream = EncodedStreamObject()
            stream._data = data
            stream.update({NameObject('/Type'):NameObject('/XObject'),NameObject('/Subtype'):NameObject('/Image'),
                           NameObject('/Width'):NumberObject(width),NameObject('/Height'):NumberObject(height),
                           NameObject('/ColorSpace'):NameObject('/DeviceGray'),NameObject('/BitsPerComponent'):NumberObject(8),
                           NameObject('/Filter'):NameObject('/FlateDecode'),NameObject('/Interpolate'):BooleanObject(False),
                           NameObject('/DecodeParms'):DictionaryObject({NameObject('/Predictor'):NumberObject(15),
                               NameObject('/Columns'):NumberObject(width),NameObject('/Colors'):NumberObject(1),
                               NameObject('/BitsPerComponent'):NumberObject(8)})})
            self.masks[digest] = self.writer._add_object(stream)
        return self.masks[digest]

    def _image(self,path,mask=None):
        (width,height),data,digest = _png(path)
        mask_ref = self._mask(mask,width,height) if mask else None
        identity = digest,mask_ref.idnum if mask_ref else None
        if identity not in self.images:
            stream = EncodedStreamObject()
            stream._data = data
            stream.update({NameObject('/Type'):NameObject('/XObject'),NameObject('/Subtype'):NameObject('/Image'),
                           NameObject('/Width'):NumberObject(width),NameObject('/Height'):NumberObject(height),
                           NameObject('/ColorSpace'):NameObject('/DeviceRGB'),NameObject('/BitsPerComponent'):NumberObject(8),
                           NameObject('/Filter'):NameObject('/FlateDecode'),NameObject('/Interpolate'):BooleanObject(False),
                           NameObject('/DecodeParms'):DictionaryObject({NameObject('/Predictor'):NumberObject(15),
                               NameObject('/Columns'):NumberObject(width),NameObject('/Colors'):NumberObject(3),
                               NameObject('/BitsPerComponent'):NumberObject(8)})})
            if mask_ref: stream[NameObject('/SMask')] = mask_ref
            self.images[identity] = self.writer._add_object(stream)
        return self.images[identity],width,height

    def _solid(self,color,width,height,mask):
        mask_ref=self._mask(mask,width,height)
        identity=color,width,height,mask_ref.idnum
        if identity not in self.solids:
            rgb=bytes((color>>shift)&255 for shift in (16,8,0))
            stream=EncodedStreamObject()
            stream._data=zlib.compress(rgb*(width*height))
            stream.update({NameObject('/Type'):NameObject('/XObject'),NameObject('/Subtype'):NameObject('/Image'),
                           NameObject('/Width'):NumberObject(width),NameObject('/Height'):NumberObject(height),
                           NameObject('/ColorSpace'):NameObject('/DeviceRGB'),NameObject('/BitsPerComponent'):NumberObject(8),
                           NameObject('/Filter'):NameObject('/FlateDecode'),NameObject('/Interpolate'):BooleanObject(False),
                           NameObject('/SMask'):mask_ref})
            self.solids[identity]=self.writer._add_object(stream)
        return self.solids[identity],width,height

    def append(self,directory,record):
        ratio = float(record['ratio'])
        paper = record['page']
        if not 0 < ratio < 10 or abs(paper['width']-816)>.01 or abs(paper['height']-1056)>.01:
            raise ValueError('The rendered sheet dimensions changed')
        page = self.writer.add_blank_page(612,792)
        resources = DictionaryObject()
        commands = ['1 1 1 rg 0 0 612 792 re f']
        for index,card in enumerate(record['cards']):
            layers = [(card['background'],'Normal')]
            for color in card.get('colors',[]): layers.append((color,'Normal'))
            for mode in ('multiply','screen'):
                if card.get(mode): layers.append((card[mode],mode.title()))
            for layer,(name,mode) in enumerate(layers):
                if isinstance(name,dict):
                    image,width,height=self._solid(name['color'],card['pixelWidth'],card['pixelHeight'],_safe(directory,name['alpha']))
                else: image,width,height = self._image(_safe(directory,name))
                if (width,height) != (card['pixelWidth'],card['pixelHeight']):
                    raise ValueError('A captured card bitmap changed dimensions')
                x = (card['left']/ratio-paper['x'])*.75
                y = 792-(card['top']/ratio-paper['y']+height/ratio)*.75
                w,h = width/ratio*.75,height/ratio*.75
                key = f'/Card{index}_{layer}'
                resources[NameObject(key)] = image
                commands.append(f'q /{mode} gs {w:.9f} 0 0 {h:.9f} {x:.9f} {y:.9f} cm {key} Do Q')
        modes = DictionaryObject({NameObject('/'+mode):DictionaryObject({NameObject('/Type'):NameObject('/ExtGState'),
                                     NameObject('/BM'):NameObject('/'+mode)}) for mode in ('Normal','Multiply','Screen')})
        page[NameObject('/Resources')] = DictionaryObject({NameObject('/XObject'):resources,NameObject('/ExtGState'):modes})
        page[NameObject('/Group')] = DictionaryObject({NameObject('/S'):NameObject('/Transparency'),
                                                       NameObject('/CS'):NameObject('/DeviceRGB')})
        contents = DecodedStreamObject()
        contents.set_data(('\n'.join(commands)+'\n').encode('ascii'))
        page[NameObject('/Contents')] = self.writer._add_object(contents)
        self.cards += len(record['cards'])

    def write(self,path):
        if not self.writer.pages: raise ValueError('There are no captured sheets')
        self.writer.add_metadata({'/Creator':'TTRPG Card Generator','/Subject':'Original rendered card pixels; lossless PNG layers'})
        self.writer.write(path)
        return {'sheets':len(self.writer.pages),'cards':self.cards,'bytes':Path(path).stat().st_size,
                'format':'lossless-rendered-cards','searchable_text':False}

    def close(self):
        self.writer.close()
