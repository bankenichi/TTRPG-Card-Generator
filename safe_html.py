"""Small formatting allowlist for imported prose, never executable markup."""
from html import escape
from html.parser import HTMLParser
import re


class _Prose(HTMLParser):
    tags = {'b', 'strong', 'i', 'em', 'u', 's', 'sub', 'sup', 'br', 'span'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'iframe', 'object'):
            self.hidden += 1
        elif not self.hidden and tag in self.tags:
            safe = []
            for key, value in attrs:
                if key == 'class' and value == 'card-strong':
                    safe.append('class="card-strong"')
                elif key == 'style' and value:
                    styles = []
                    for declaration in value.split(';'):
                        prop, _, val = declaration.partition(':')
                        prop, val = prop.strip().lower(), val.strip()
                        if ((prop == 'color' and re.fullmatch(r'#[0-9a-fA-F]{6}', val))
                            or (prop == 'font-weight' and val in ('bold', 'normal', '900'))
                            or (prop == 'font-size' and val == '1.4em')):
                            styles.append(prop + ':' + val)
                    if styles: safe.append('style="' + ';'.join(styles) + '"')
            self.parts.append('<' + tag + (' ' + ' '.join(safe) if safe else '') + '>')

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'iframe', 'object'):
            self.hidden = max(0, self.hidden - 1)
        elif not self.hidden and tag in self.tags and tag != 'br':
            self.parts.append('</' + tag + '>')

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(escape(data))


def sanitize_prose(value):
    parser = _Prose()
    parser.feed(str(value))
    parser.close()
    return ''.join(parser.parts)
