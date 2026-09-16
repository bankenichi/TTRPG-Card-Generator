import os
import sys
import json
import subprocess
import zipfile
import shutil
import webbrowser
import io
from http.server import SimpleHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

from data_paths import (
    GENERATORS_DIR,
    DEFAULT_DATA_DIR as DATA_DIR,
    is_data_ready,
    translate_served_path,
)

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

def setup_from_git(repo_url):
    git_cmd = get_git_cmd()
    if not git_cmd:
        return False, "Git not found. Please install Git or use a ZIP file."
    
    if os.path.exists(DATA_DIR):
        shutil.rmtree(DATA_DIR)
    
    try:
        subprocess.run([git_cmd, "clone", repo_url, DATA_DIR], check=True)
        return True, "Successfully cloned repository."
    except Exception as e:
        return False, f"Git clone failed: {str(e)}"

def extract_zip_data(zip_bytes):
    if os.path.exists(DATA_DIR):
        shutil.rmtree(DATA_DIR)
    os.makedirs(DATA_DIR, exist_ok=True)
    
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as zip_ref:
            members = zip_ref.namelist()
            if not members:
                return False, "ZIP file is empty."

            # Heuristic: if all files are inside a single folder, extract that folder's contents
            first_part = members[0].split('/')[0]
            if all(m.startswith(first_part + '/') for m in members if '/' in m):
                temp_extract = os.path.join(GENERATORS_DIR, "temp_zip")
                if os.path.exists(temp_extract): shutil.rmtree(temp_extract)
                zip_ref.extractall(temp_extract)
                src_path = os.path.join(temp_extract, first_part)
                for item in os.listdir(src_path):
                    shutil.move(os.path.join(src_path, item), DATA_DIR)
                shutil.rmtree(temp_extract)
            else:
                zip_ref.extractall(DATA_DIR)
            
        return True, "Successfully extracted ZIP."
    except Exception as e:
        return False, f"ZIP extraction failed: {str(e)}"

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>TTRPG Card Generator - Setup</title>
    <link rel="icon" type="image/svg+xml" href="/icons/favicon.svg">
    <style>
        body { font-family: Arial, sans-serif; margin: 2rem; background: #f4f4f4; color: #111; }
        .panel { max-width: 600px; margin: auto; padding: 2rem; background: white; border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,.1); }
        h1 { margin-top: 0; color: #2d7aeb; }
        .form-group { margin-bottom: 1.5rem; }
        label { display: block; font-weight: bold; margin-bottom: 0.5rem; }
        input[type="text"], input[type="file"] { width: 100%; padding: 0.75rem; border: 1px solid #ccc; border-radius: 6px; box-sizing: border-box; }
        .btn { display: inline-block; padding: 0.75rem 1.5rem; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; text-decoration: none; transition: background 0.2s; }
        .btn-primary { background: #2d7aeb; color: white; }
        .btn-primary:hover { background: #215ec8; }
        .status { margin-top: 1rem; padding: 1rem; border-radius: 6px; display: none; }
        .status-success { background: #e8f5e9; color: #2e7d32; display: block; }
        .status-error { background: #ffebee; color: #c62828; display: block; }
        .help-text { font-size: 0.85em; color: #666; margin-top: 0.25rem; }
    </style>
</head>
<body>
    <div class="panel">
        <h1>Welcome to TTRPG Card Generator</h1>
        <div id="welcome-message" style="display: __WELCOME_DISPLAY__;">
            <p>It looks like you haven't set up your data source yet. This tool requires a compatible dataset (containing a <code>data/</code> folder with <code>class/</code>, <code>spells/</code>, etc.).</p>
        </div>
        
        <div id="setup-form" style="display: __SETUP_DISPLAY__;">
            <div class="form-group">
                <label>Option 1: Clone from Git Repository</label>
                <input type="text" id="repo-url" placeholder="https://github.com/example/my-ttrpg-data.git">
                <p class="help-text">Enter the URL of a compatible data repository.</p>
                <button class="btn btn-primary" onclick="setupGit()">Clone Repository</button>
            </div>
            
            <hr>
            
            <div class="form-group">
                <label>Option 2: Upload Data ZIP</label>
                <input type="file" id="zip-file" accept=".zip">
                <p class="help-text">Select a ZIP file containing the compatible data structure.</p>
                <button class="btn btn-primary" onclick="setupZip()">Upload and Extract</button>
            </div>
        </div>

        <div id="status" class="status"></div>
        
        <div id="launch-panel" style="display: __LAUNCH_DISPLAY__; margin-top: 2rem; border-top: 2px solid #eee; padding-top: 1rem;">
            <p style="color: #2e7d32; font-weight: bold;">Data is ready!</p>
            <button class="btn btn-primary" onclick="launchGenerator()">Launch Card Generator</button>
            <button class="btn" style="background: #eee;" onclick="toggleSetup()">Manage Data Source</button>
        </div>
    </div>

    <script>
        function setStatus(msg, isError) {
            const s = document.getElementById('status');
            s.textContent = msg;
            s.className = 'status ' + (isError ? 'status-error' : 'status-success');
        }

        async function setupGit() {
            const url = document.getElementById('repo-url').value;
            if (!url) return alert('Please enter a URL');
            setStatus('Cloning repository... this may take a minute.', false);
            const resp = await fetch('/setup?type=git&url=' + encodeURIComponent(url));
            const data = await resp.json();
            if (data.success) {
                location.reload();
            } else {
                setStatus(data.message, true);
            }
        }

        async function setupZip() {
            const fileInput = document.getElementById('zip-file');
            if (fileInput.files.length === 0) return alert('Please select a ZIP file');
            
            setStatus('Uploading and extracting ZIP...', false);
            const formData = new FormData();
            formData.append('zip', fileInput.files[0]);

            try {
                const resp = await fetch('/setup-zip', {
                    method: 'POST',
                    body: formData
                });
                const data = await resp.json();
                if (data.success) {
                    location.reload();
                } else {
                    setStatus(data.message, true);
                }
            } catch (e) {
                setStatus('Upload failed: ' + e, true);
            }
        }

        async function launchGenerator() {
            setStatus('Launching generator... closing this tab.', false);
            fetch('/launch').then(() => {
                window.close();
                setTimeout(() => {
                    document.body.innerHTML = '<div class="panel"><h1>Launched</h1><p>The generator is running in a new window. You can close this tab.</p></div>';
                }, 500);
            });
        }

        function toggleSetup() {
            const f = document.getElementById('setup-form');
            const w = document.getElementById('welcome-message');
            const isHidden = f.style.display === 'none';
            f.style.display = isHidden ? 'block' : 'none';
            if (w) w.style.display = isHidden ? 'block' : 'none';
        }
    </script>
</body>
</html>"""

class LauncherRequestHandler(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        return translate_served_path(path, super().translate_path(path))

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == '/':
            ready = is_data_ready()
            html = HTML_TEMPLATE.replace('__LAUNCH_DISPLAY__', 'block' if ready else 'none')
            html = html.replace('__WELCOME_DISPLAY__', 'none' if ready else 'block')
            html = html.replace('__SETUP_DISPLAY__', 'none' if ready else 'block')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(html.encode('utf-8'))
            return
        
        elif parsed.path == '/setup':
            params = parse_qs(parsed.query)
            stype = params.get('type', [''])[0]
            success, message = False, ""
            
            if stype == 'git':
                url = params.get('url', [''])[0]
                success, message = setup_from_git(url)
                
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"success": success, "message": message}).encode('utf-8'))
            return

        elif parsed.path == '/launch':
            if is_data_ready():
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"Launching...")
                
                # Small delay to ensure the browser receives the response before we shut down
                import threading
                import time
                def delayed_launch():
                    time.sleep(1)
                    subprocess.Popen([sys.executable, "card_controller.py"])
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
        if self.path == '/setup-zip':
            content_length = int(self.headers['Content-Length'])
            boundary = self.headers['Content-Type'].split("=")[1].encode()
            
            # Very simple multipart parser for this specific use case
            body = self.rfile.read(content_length)
            parts = body.split(b'--' + boundary)
            zip_bytes = b""
            for part in parts:
                if b'name="zip"' in part:
                    # Find the start of the file content after the headers
                    header_end = part.find(b'\\r\\n\\r\\n') + 4
                    if header_end < 4: # Handle both CRLF and LF
                        header_end = part.find(b'\\n\\n') + 2
                    
                    zip_bytes = part[header_end:].rstrip(b'\\r\\n').rstrip(b'\\n').rstrip(b'--')
                    break
            
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
    server_address = ('', port)
    httpd = HTTPServer(server_address, LauncherRequestHandler)
    url = f'http://localhost:{port}/'
    print(f'Starting Setup Launcher at {url}')
    webbrowser.open(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.server_close()

if __name__ == '__main__':
    serve_launcher()
