import os
import sys
import json
import subprocess
import webbrowser
from local_http import LocalRequestHandler
from http.server import SimpleHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON_EXE = sys.executable
ICON_FILE = os.path.join(SCRIPT_DIR, "icons", "favicon.ico")

def create_shortcuts(desktop=False):
    try:
        launch_bat = os.path.join(SCRIPT_DIR, "launch.bat")
        install_bat = os.path.join(SCRIPT_DIR, "install.bat")
        
        # 1. Project Folder Shortcut: Launch TTRPG Generator
        # 2. Project Folder Shortcut: Setup & Repair
        # 3. Desktop Shortcut (Optional): TTRPG Generator
        
        ps_script = f"""
$sh = New-Object -ComObject WScript.Shell;

# Helper to create shortcut
function New-BrandedShortcut {{
    param($Path, $Target, $WorkingDir, $Icon)
    $s = $sh.CreateShortcut($Path)
    $s.TargetPath = $Target
    $s.WorkingDirectory = $WorkingDir
    $s.IconLocation = $Icon
    $s.Save()
}}

# Root Shortcuts
New-BrandedShortcut -Path "{os.path.join(SCRIPT_DIR, 'Launch TTRPG Generator.lnk')}" -Target "{launch_bat}" -WorkingDir "{SCRIPT_DIR}" -Icon "{ICON_FILE}"
New-BrandedShortcut -Path "{os.path.join(SCRIPT_DIR, 'Setup & Repair.lnk')}" -Target "{install_bat}" -WorkingDir "{SCRIPT_DIR}" -Icon "{ICON_FILE}"
"""
        
        if desktop:
            ps_script += f"""
# Desktop Shortcut
$desktopPath = Join-Path ([Environment]::GetFolderPath('Desktop')) 'TTRPG Generator.lnk'
New-BrandedShortcut -Path $desktopPath -Target "{launch_bat}" -WorkingDir "{SCRIPT_DIR}" -Icon "{ICON_FILE}"
"""
            
        subprocess.run(["powershell", "-Command", ps_script], check=True)
        return True, "Shortcuts created successfully."
    except Exception as e:
        return False, f"Failed to create shortcuts: {str(e)}"

def install_dependencies():
    try:
        req_file = os.path.join(SCRIPT_DIR, "requirements.txt")
        if os.path.exists(req_file):
            subprocess.run([PYTHON_EXE, "-s", "-m", "pip", "install", "-r", req_file], check=True)
        renderer_env = os.environ.copy()
        renderer_env.setdefault("PLAYWRIGHT_BROWSERS_PATH", os.path.join(SCRIPT_DIR, "pdf-browser"))
        subprocess.run([PYTHON_EXE, "-m", "playwright", "install", "--no-shell", "chromium"], check=True, env=renderer_env)
        return True, "Dependencies and pinned PDF renderer installed."
    except Exception as e:
        return False, f"Dependency installation failed: {str(e)}"


class InstallerRequestHandler(LocalRequestHandler):
    def do_POST(self):
        if urlparse(self.path).path == '/finish':
            return self.do_GET()
        self.send_error(404)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            from workbench_ui import render_installer
            self.wfile.write(render_installer().encode('utf-8'))
            return
            
        elif parsed.path == '/finish':
            if self.command != 'POST':
                self.send_error(405, 'Use POST for this operation')
                return
            params = parse_qs(parsed.query)
            do_shortcut = params.get('shortcut', ['false'])[0].lower() == 'true'
            
            # Always create folder shortcuts, conditionally create desktop shortcut
            success, message = create_shortcuts(desktop=do_shortcut)
            
            if success:
                # Write a lock file if not present
                with open(os.path.join(SCRIPT_DIR, "install.lock"), "w") as f:
                    f.write("Setup complete")
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"success": True}).encode('utf-8'))
                
                # Small delay to ensure the browser receives the response before we shut down
                import threading
                import time
                def delayed_launch():
                    time.sleep(1)
                    subprocess.Popen(["cmd", "/c", os.path.join(SCRIPT_DIR, "launch.bat")], cwd=SCRIPT_DIR)
                    os._exit(0)
                threading.Thread(target=delayed_launch).start()
            else:
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "message": message}).encode('utf-8'))
            return

        elif parsed.path.startswith('/icons/'):
            return super().do_GET()

        super().do_GET()

def serve_installer(port=8002):
    server_address = ('127.0.0.1', port)
    httpd = HTTPServer(server_address, InstallerRequestHandler)
    url = f'http://localhost:{port}/'
    print(f'Installation complete. Please finish setup at {url}')
    if os.environ.get("TTRPG_NO_BROWSER") != "1":
        webbrowser.open(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.server_close()

if __name__ == '__main__':
    # Run the technical parts first (silent)
    success, message = install_dependencies()
    print(message)
    if not success:
        sys.exit(1)
    if '--headless' in sys.argv:
        with open(os.path.join(SCRIPT_DIR, 'install.lock'), 'w', encoding='utf-8') as lock:
            lock.write('Setup complete')
    else:
        serve_installer()
