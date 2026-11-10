import os
import sys
import json
import subprocess
import zipfile
import shutil
import webbrowser
import io
import tempfile
from email.parser import BytesParser
from email.policy import default
from data_install import replace_tree, dataset_from_extraction, safe_extract, validate_dataset
from data_paths import _has_5etools_shape
from local_http import LocalRequestHandler
from http.server import SimpleHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

from data_paths import (
    GENERATORS_DIR,
    DEFAULT_DATA_DIR as DATA_DIR,
    is_data_ready,
    translate_served_path,
)
from prerelease_sync import sync_prerelease_content
from verified_srd import install_bundled_srd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GIT_EXE = os.path.join(SCRIPT_DIR, "git-portable", "bin", "git.exe")

def get_git_cmd():
    # Try system git first
    try:
        subprocess.run(["git", "--version"], capture_output=True, check=True)
        return "git"
    except:
        if os.path.exists(GIT_EXE):
            return GIT_EXE
    return None


def _is_srd_source(root):
    try:
        with open(os.path.join(root, 'manifest.json'), encoding='utf-8') as source:
            manifest = json.load(source)
        return isinstance(manifest, dict) and manifest.get('source_id') == 'SRD521' and manifest.get('srd') == '5.2.1'
    except (OSError, ValueError):
        return False

def setup_from_git(repo_url):
    git_cmd = get_git_cmd()
    if not git_cmd:
        return False, "Git not found. Please install Git or use a ZIP file."
    if not repo_url or repo_url.startswith('-'):
        return False, "Please provide a repository URL or local repository path."
    try:
        os.makedirs(GENERATORS_DIR, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.install-', dir=GENERATORS_DIR) as temp:
            staged = os.path.join(temp, 'repository')
            subprocess.run([git_cmd, "clone", "--no-hardlinks", "--", repo_url, staged], check=True)
            validate_dataset(staged)
            if not _is_srd_source(staged):
                sync_prerelease_content(staged, git_cmd=git_cmd)
            replace_tree(staged, DATA_DIR)
        return True, "Successfully cloned repository."
    except Exception as e:
        return False, f"Git clone failed: {e}"


def extract_zip_data(zip_bytes):
    try:
        os.makedirs(GENERATORS_DIR, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.install-', dir=GENERATORS_DIR) as temp:
            extracted = os.path.join(temp, 'extracted')
            with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as archive:
                safe_extract(archive, extracted)
            staged = dataset_from_extraction(extracted)
            validate_dataset(staged)
            if not _is_srd_source(staged):
                sync_prerelease_content(staged, git_cmd=get_git_cmd())
            replace_tree(staged, DATA_DIR)
        return True, "Successfully extracted ZIP."
    except Exception as e:
        return False, f"ZIP extraction failed: {e}"


class LauncherRequestHandler(LocalRequestHandler):
    def translate_path(self, path):
        return translate_served_path(path, super().translate_path(path))

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == '/':
            from workbench_ui import render_setup
            html = render_setup(is_data_ready())
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(html.encode('utf-8'))
            return
        
        elif parsed.path == '/setup':
            if self.command != 'POST':
                self.send_error(405, 'Use POST for this operation')
                return
            params = parse_qs(parsed.query)
            stype = params.get('type', [''])[0]
            success, message = False, ""
            
            if stype == 'git':
                url = params.get('url', [''])[0]
                success, message = setup_from_git(url)
            elif stype == 'srd':
                try:
                    install_bundled_srd(DATA_DIR)
                    success, message = True, 'SRD 5.2.1 is ready.'
                except Exception as exc:
                    success, message = False, f'SRD setup failed: {exc}'
                
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"success": success, "message": message}).encode('utf-8'))
            return

        elif parsed.path == '/launch':
            if self.command != 'POST':
                self.send_error(405, 'Use POST for this operation')
                return
            if is_data_ready():
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"Launching...")
                
                # Small delay to ensure the browser receives the response before we shut down
                import threading
                import time
                def delayed_launch():
                    time.sleep(1)
                    subprocess.Popen([sys.executable, os.path.join(SCRIPT_DIR, "card_controller.py")], cwd=SCRIPT_DIR)
                    os._exit(0)
                threading.Thread(target=delayed_launch).start()
                return
            else:
                self.send_response(403)
                self.end_headers()
                self.wfile.write(b"Data not ready.")
                return

        super().do_GET()

    def do_POST(self):
        if urlparse(self.path).path in ('/setup', '/launch'):
            return self.do_GET()
        if self.path == '/setup-zip':
            try:
                content_length = int(self.headers.get('Content-Length', '0'))
                if not 0 < content_length <= 1024 * 1024 * 1024:
                    raise ValueError('ZIP upload must be between 1 byte and 1 GB')
                content_type = self.headers.get('Content-Type', '')
                body = self.rfile.read(content_length)
                message = BytesParser(policy=default).parsebytes(
                    ('Content-Type: ' + content_type + '\r\nMIME-Version: 1.0\r\n\r\n').encode() + body
                )
                zip_bytes = next((part.get_payload(decode=True) for part in message.iter_parts()
                                  if part.get_param('name', header='content-disposition') == 'zip'), b'')
            except (ValueError, StopIteration) as exc:
                self.send_json({'success': False, 'message': str(exc)}, 400)
                return

            if zip_bytes:
                success, message = extract_zip_data(zip_bytes)
            else:
                success, message = False, "No ZIP data found in upload."

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"success": success, "message": message}).encode('utf-8'))
            return

def serve_launcher(port=8001):
    server_address = ('127.0.0.1', port)
    httpd = HTTPServer(server_address, LauncherRequestHandler)
    url = f'http://localhost:{port}/'
    print(f'Starting Setup Launcher at {url}')
    if os.environ.get("TTRPG_NO_BROWSER") != "1":
        webbrowser.open(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.server_close()

if __name__ == '__main__':
    serve_launcher()
