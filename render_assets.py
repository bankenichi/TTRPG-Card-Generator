"""Self-contained font/asset CSS keeps previews offline and avoids repeated SVGs."""
import base64
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def font_css():
    faces = json.loads((ROOT / 'fonts' / 'manifest.json').read_text(encoding='utf-8'))
    return '\n'.join(
        "@font-face{font-family:'Open Sans';font-style:%s;font-weight:%s;src:url(data:font/ttf;base64,%s) format('truetype');font-display:block;}"
        % (face['style'], face['weight'], base64.b64encode((ROOT / 'fonts' / face['file']).read_bytes()).decode('ascii'))
        for face in faces)


def asset_class(definitions, property_name, uri):
    identity = property_name + '\0' + uri
    name = 'asset-' + hashlib.sha256(identity.encode()).hexdigest()[:20]
    definitions[name] = f".{name}{{--{property_name}:url('{uri}');}}"
    return name


def validate_custom_assets(assets):
    for key, uri in assets.items():
        if not isinstance(uri, str) or not uri.startswith('data:image/svg+xml;base64,'):
            raise ValueError(f'Custom {key} must be a base64 SVG image')
        if len(uri) > 8 * 1024 * 1024:
            raise ValueError('Custom SVG exceeds 6 MB')
        base64.b64decode(uri.split(',', 1)[1], validate=True)
