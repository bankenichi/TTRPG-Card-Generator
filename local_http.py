"""Loopback-only HTTP boundary shared by the three local web interfaces."""
import os
from http.server import SimpleHTTPRequestHandler
from urllib.parse import unquote, urlsplit
import re

from data_paths import is_within, translate_served_path

ROOT = os.path.dirname(os.path.abspath(__file__))


class LocalRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('directory', ROOT)
        super().__init__(*args, **kwargs)

    def do_GET(self):
        if urlsplit(self.path).path == '/about':
            from workbench_ui import render_about
            body = render_about().encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()

    def parse_request(self):
        if not super().parse_request():
            return False
        host = urlsplit('//' + self.headers.get('Host', '')).hostname
        origin = self.headers.get('Origin')
        if self.headers.get('Sec-Fetch-Site') == 'cross-site' or host not in ('localhost', '127.0.0.1', '::1') or (
            origin and origin != 'http://' + self.headers.get('Host', '')
        ):
            self.send_error(403, 'Only requests from this local application are allowed')
            return False
        return True

    def end_headers(self):
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Cache-Control', 'no-store')
        filename = os.path.basename(urlsplit(self.path).path)
        if filename.startswith('Custom_Deck_') and filename.endswith('.pdf') and re.fullmatch(r'[A-Za-z0-9_.-]+', filename):
            self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
        super().end_headers()

    def translate_path(self, path):
        decoded = unquote(urlsplit(path).path).replace('\\', '/')
        parts = decoded.strip('/').split('/')
        allowed = (
            parts[0] in ('icons', 'fonts')
            or (parts[0] == 'generators' and decoded.lower().endswith('.json'))
            or (len(parts) == 1 and parts[0].startswith('Custom_Deck_') and parts[0].endswith(('.html', '.pdf')))
        )
        if not allowed or any(p in ('.', '..') or ':' in p or p.startswith('.') for p in parts):
            return os.path.join(self.directory, '.invalid-request')
        result = translate_served_path(decoded, super().translate_path(decoded))
        if not is_within(result, self.directory):
            return os.path.join(self.directory, '.invalid-request')
        return result

    def list_directory(self, path):
        self.send_error(404)
        return None

    def read_json(self, limit=16 * 1024 * 1024):
        import json
        length = int(self.headers.get('Content-Length', '0'))
        if not 0 < length <= limit:
            raise ValueError('Invalid or oversized request')
        return json.loads(self.rfile.read(length))

    def send_json(self, obj, status=200):
        import json
        body = json.dumps(obj).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)
