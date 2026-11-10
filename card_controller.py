import os
import sys
import json
import webbrowser
from html import escape
from http.server import SimpleHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from local_http import LocalRequestHandler
from deck_output import write_batches
from pdf_export import start_export, export_status

# Import the core engine logic
from card_engine import generate_html, generate_backs_html
from data_paths import (
    remap_dataset_catalog,
    translate_served_path,
    resolve_dataset_path,
    discover_data_root,
)
from prerelease_sync import playtest_indexes_ready

# ---------------------------------------------------------------------------
# ICON DIRECTORY SCANNER
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CWD = os.getcwd()
possible_dirs = [os.path.join(SCRIPT_DIR, "icons"), os.path.join(CWD, "icons")]
ICON_DIR = next((d for d in possible_dirs if os.path.isdir(d)), possible_dirs[0])


def _extract_deck_body_pages(html_text):
    """Return the .page blocks between <body> and the fit-to-card <script>."""
    import re
    m = re.search(r"<body>(.*?)<script>", html_text, re.DOTALL | re.IGNORECASE)
    return (m.group(1).strip() if m else "")


def _merge_deck_html(partial_paths, output_html_path):
    """Concatenate printable .page blocks from separately generated decks."""
    if not partial_paths:
        with open(output_html_path, "w", encoding="utf-8") as f:
            f.write("<!DOCTYPE html><html><body></body></html>")
        return

    with open(partial_paths[0], encoding="utf-8") as f:
        first = f.read()

    head_end = first.lower().find("<body>")
    if head_end < 0:
        raise RuntimeError("Deck HTML missing <body>")
    head = first[: head_end + len("<body>")]

    script_start = first.lower().find("<script>")
    if script_start < 0:
        raise RuntimeError("Deck HTML missing <script>")
    tail = first[script_start:]

    body_parts = []
    styles = set()
    import re
    for p in partial_paths:
        with open(p, encoding="utf-8") as f:
            html = f.read()
        styles.update(re.findall(r"\.asset-[a-f0-9]+\{[^}]*\}", html))
        chunk = _extract_deck_body_pages(html)
        if chunk:
            body_parts.append(chunk)

    with open(output_html_path, "w", encoding="utf-8") as f:
        extra_css = "\n".join(sorted(styles))
        f.write(head.replace("</head>", "<style>" + extra_css + "</style></head>"))
        f.write("\n")
        f.write("\n".join(body_parts))
        f.write("\n")
        f.write(tail)


def generate_html_isolated(payload, output_html_path=None):
    """Like generate_html, but each datasets[] entry runs in its own pass.

    Each pass loads its required official lookup dependencies independently.
    Keep emitted card selection separate so combined selections preserve both
    source versions without changing their inherited rules.
    """
    import tempfile

    if output_html_path is None:
        output_html_path = "Custom_Deck_Cards.html"

    datasets_req = payload.get("datasets", []) or []
    if len(datasets_req) <= 1:
        result = generate_html(payload, output_html_path=output_html_path)
        if result.get('card_count', 0):
            from source_labels import apply_source_labels
            apply_source_labels(output_html_path)
        return result

    partials = []
    mergeable = []
    total_cards = 0
    total_items = 0
    type_counts = {}
    try:
        for i, ds in enumerate(datasets_req):
            fd, tmp_path = tempfile.mkstemp(prefix=f"deck_part_{i}_", suffix=".html", dir=SCRIPT_DIR)
            os.close(fd)
            partials.append(tmp_path)
            part_payload = {
                "datasets": [ds],
                "customAssets": payload.get("customAssets", {}),
                "selectedAssets": payload.get("selectedAssets", {}),
            }
            result = generate_html(part_payload, output_html_path=tmp_path) or {}
            cc = int(result.get("card_count", 0) or 0)
            total_cards += cc
            total_items += int(result.get("item_count", 0) or 0)
            for k, v in (result.get("type_counts") or {}).items():
                type_counts[k] = type_counts.get(k, 0) + int(v)
            # generate_html may return early without writing a full deck
            if cc > 0 and os.path.getsize(tmp_path) > 0:
                # Style block is large; scan the file for <body> rather than a tiny prefix.
                with open(tmp_path, encoding="utf-8") as _hf:
                    _html = _hf.read()
                if "<body>" in _html.lower():
                    mergeable.append(tmp_path)

        if total_cards <= 0 or not mergeable:
            with open(output_html_path, "w", encoding="utf-8") as f:
                f.write("<!DOCTYPE html><html><body><p>No cards.</p></body></html>")
            return {"card_count": 0, "item_count": 0, "type_counts": {}}

        _merge_deck_html(mergeable, output_html_path)
        from source_labels import apply_source_labels
        apply_source_labels(output_html_path)
        return {
            "card_count": total_cards,
            "item_count": total_items,
            "type_counts": type_counts,
        }
    finally:
        for p in partials:
            try:
                os.remove(p)
            except OSError:
                pass


def get_available_svgs():
    bg_files, wm_files, cb_files = [], [], []
    if os.path.isdir(ICON_DIR):
        for f in os.listdir(ICON_DIR):
            if f.endswith('.svg'):
                fl = f.lower()
                # Tightened to parchment-background to avoid grabbing backgrounds.svg
                if 'parchment-background' in fl: bg_files.append(f)
                if 'watermark' in fl: wm_files.append(f)
                if 'card-back' in fl or 'cardback' in fl: cb_files.append(f)
                
    # Sort alphabetically first
    bg_files = sorted(list(set(bg_files)))
    wm_files = sorted(list(set(wm_files)))
    cb_files = sorted(list(set(cb_files)))

    # Force the core defaults to the top of the list
    if 'parchment-background.svg' in bg_files:
        bg_files.remove('parchment-background.svg')
    bg_files.insert(0, 'parchment-background.svg')

    if 'watermark-emblem.svg' in wm_files:
        wm_files.remove('watermark-emblem.svg')
    wm_files.insert(0, 'watermark-emblem.svg')

    if 'card-back.svg' in cb_files:
        cb_files.remove('card-back.svg')
    cb_files.insert(0, 'card-back.svg')

    return json.dumps({
        "backgrounds": bg_files,
        "watermarks": wm_files,
        "cardBacks": cb_files
    })

# ---------------------------------------------------------------------------
# CONTROLLER UI & SERVER
# ---------------------------------------------------------------------------
def _paths_exist(files):
    if not files:
        return False
    seq = files if isinstance(files, list) else [files]
    return any(os.path.exists(resolve_dataset_path(p)) for p in seq)


def get_datasets_json():
    path = os.path.join(SCRIPT_DIR, "datasets.json")
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            catalog = json.load(f)
        remap_dataset_catalog(catalog)
        root = discover_data_root()
        ready = bool(root and playtest_indexes_ready(root))
        for entry in catalog.values():
            if not isinstance(entry, dict):
                continue
            if not ready or not _paths_exist(entry.get("playtestFile")):
                entry.pop("playtestFile", None)
                entry.pop("combinedFile", None)
                if isinstance(entry.get("filters"), dict):
                    entry["filters"].pop("playtest", None)
        return json.dumps(catalog)
    return "{}"

def get_index_html(svg_options_json):
    from workbench_ui import render_workbench
    return render_workbench(get_datasets_json(), svg_options_json)


def validate_payload(payload):
    if not isinstance(payload, dict):
        raise ValueError('Expected a deck request')
    allowed = set()
    for dataset in json.loads(get_datasets_json()).values():
        for key in ('file', 'playtestFile', 'combinedFile'):
            value = dataset.get(key, [])
            allowed.update(os.path.normcase(os.path.abspath(resolve_dataset_path(f)))
                           for f in (value if isinstance(value, list) else [value]))
    for dataset in payload.get('datasets', []):
        files = dataset.get('file', [])
        for filename in (files if isinstance(files, list) else [files]):
            if os.path.normcase(os.path.abspath(resolve_dataset_path(filename))) not in allowed:
                raise ValueError('Select a dataset provided by this application')
    return payload


class GeneratorRequestHandler(LocalRequestHandler):
    def translate_path(self, path):
        return translate_served_path(path, super().translate_path(path))

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == '/export-status':
            try:
                self.send_json(export_status(parse_qs(parsed.query).get('id', [''])[0]))
            except (ValueError, OSError) as exc:
                self.send_json({'error': str(exc)}, 400)
            return
        if parsed.path == '/data-setup':
            from workbench_ui import render_setup
            from data_paths import is_data_ready
            body = render_setup(is_data_ready(), in_generator=True).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed.path == '/':
            svg_options = get_available_svgs()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(get_index_html(svg_options).encode('utf-8'))
            return
            
        super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        
        if parsed.path == '/export-pdf':
            try:
                payload = self.read_json()
                self.send_json({'id': start_export(payload.get('kind', 'Cards'))}, 202)
            except (ValueError, OSError) as exc:
                self.send_json({'error': str(exc)}, 400)
            return

        if parsed.path in ('/setup', '/setup-zip'):
            from launcher import LauncherRequestHandler
            if parsed.path == '/setup':
                return LauncherRequestHandler.do_GET(self)
            return LauncherRequestHandler.do_POST(self)

        # Route for normal card fronts
        if parsed.path == '/generate':
            try:
                payload = validate_payload(self.read_json())
                output_filename = "Custom_Deck_Cards.html"
                
                result = generate_html_isolated(payload, output_html_path=os.path.join(SCRIPT_DIR, output_filename))
                manifest = write_batches(os.path.join(SCRIPT_DIR, output_filename)) if result.get("card_count", 0) else None
                
                if 'application/json' in self.headers.get('Accept', ''):
                    self.send_json({**result, 'sheet_count': manifest['sheet_count'] if manifest else 0,
                                    'preview': '/' + output_filename, 'kind': 'Cards'})
                    return
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                
                if result and isinstance(result, dict) and result.get("card_count", 0) > 0: 
                    cc = result["card_count"]
                    ic = result["item_count"]
                    tc = result["type_counts"]
                    
                    sorted_tc = sorted(tc.items(), key=lambda item: item[1], reverse=True)
                    badges = "".join([f'<span style="display: inline-block; background: #d0def4; color: #0b3c79; padding: 3px 8px; border-radius: 12px; font-size: 0.8em; margin: 0 4px 4px 0;"><strong>{escape(str(k))}:</strong> {v}</span>' for k, v in sorted_tc])
                    
                    html_resp = f'''
                    <div style="margin-bottom: 10px;">
                        <span style="font-size: 1.1em; color: #111;">Success! Generated a deck of <strong>{cc}</strong> cards from <strong>{ic}</strong> unique items.</span>
                    </div>
                    <div style="margin-bottom: 15px;">
                        {badges}
                        <p>{manifest['sheet_count']} sheets in one continuous preview.</p>
                    </div>
                    <p><a href="/{output_filename}" target="_blank" style="text-decoration: none; font-weight: bold; background: #2d7aeb; color: #fff; padding: 8px 16px; border-radius: 6px;">Open Custom Deck</a> <button onclick="exportPdf('Cards')">Export PDF</button></p>
                    '''
                    self.wfile.write(html_resp.encode('utf-8'))
                else: 
                    self.wfile.write(b'<p style="color: #d32f2f;">No cards matched your filter criteria.</p>')
            except Exception as e:
                if 'application/json' in self.headers.get('Accept', ''):
                    self.send_json({'error': str(e)}, 400 if isinstance(e, ValueError) else 500)
                    return
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f'Server Error: {__import__("html").escape(str(e))}'.encode('utf-8'))
            return
            
        # Route for card backs
        if parsed.path == '/generate_backs':
            try:
                payload = validate_payload(self.read_json())
                output_filename = "Custom_Deck_Backs.html"
                
                generate_backs_html(payload, output_html_path=os.path.join(SCRIPT_DIR, output_filename))
                manifest = write_batches(os.path.join(SCRIPT_DIR, output_filename))
                if 'application/json' in self.headers.get('Accept', ''):
                    self.send_json({'card_count': 9, 'item_count': 9, 'type_counts': {},
                                    'sheet_count': manifest['sheet_count'], 'preview': '/' + output_filename, 'kind': 'Backs'})
                    return
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                
                html_resp = f'''
                <div style="margin-bottom: 10px;">
                    <span style="font-size: 1.1em; color: #111;">Success! Generated a printable page of Card Backs.</span>
                </div>
                <p><a href="/{output_filename}" target="_blank" style="text-decoration: none; font-weight: bold; background: #2e7d32; color: #fff; padding: 8px 16px; border-radius: 6px;">Open Card Backs</a> <button onclick="exportPdf('Backs')">Export PDF</button></p>
                '''
                self.wfile.write(html_resp.encode('utf-8'))
            except Exception as e:
                if 'application/json' in self.headers.get('Accept', ''):
                    self.send_json({'error': str(e)}, 400 if isinstance(e, ValueError) else 500)
                    return
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f'Server Error: {__import__("html").escape(str(e))}'.encode('utf-8'))
            return

def serve_gui(port=8000):
    server_address = ('127.0.0.1', port)
    httpd = HTTPServer(server_address, GeneratorRequestHandler)
    url = f'http://localhost:{port}/'
    print(f'Serving card generator UI at {url}')
    if os.environ.get("TTRPG_NO_BROWSER") != "1":
        webbrowser.open(url)
    try: 
        httpd.serve_forever()
    except KeyboardInterrupt: 
        print('\nServer stopped.')
        httpd.server_close()

if __name__ == '__main__':
    serve_gui()
