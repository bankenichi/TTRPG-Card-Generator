import os
import sys
import json
import webbrowser
from http.server import SimpleHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

# Import the core engine logic
from card_engine import generate_html, generate_backs_html
from data_paths import remap_dataset_catalog, translate_served_path

# ---------------------------------------------------------------------------
# ICON DIRECTORY SCANNER
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CWD = os.getcwd()
possible_dirs = [os.path.join(SCRIPT_DIR, "icons"), os.path.join(CWD, "icons")]
ICON_DIR = next((d for d in possible_dirs if os.path.isdir(d)), possible_dirs[0])

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
def get_datasets_json():
    path = os.path.join(SCRIPT_DIR, "datasets.json")
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            catalog = json.load(f)
        remap_dataset_catalog(catalog)
        return json.dumps(catalog)
    return "{}"

def get_index_html(svg_options_json):
    datasets_json = get_datasets_json()
    html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <link rel="icon" type="image/svg+xml" href="/icons/favicon.svg">
    <title>TTRPG Card Generator Launcher</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 2rem; background: #f4f4f4; color: #111; }
        .panel { max-width: 600px; margin: auto; padding: 1.5rem; background: white; border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,.08); }
        h1 { margin-top: 0; font-size: 1.6rem; }
        
        .dataset-group { margin-bottom: 1rem; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden; background: #fff; }
        .dataset-header { background: #f9f9f9; padding: 10px 15px; display: flex; align-items: center; cursor: pointer; font-weight: bold; }
        .dataset-header input[type="checkbox"] { margin-right: 10px; transform: scale(1.2); }
        .subset-panel { display: none; padding: 10px 15px 15px 35px; border-top: 1px solid #e0e0e0; background: #fff; }
        .subset-category { margin-bottom: 15px; }
        .subset-category strong { display: block; font-size: 0.9em; margin-bottom: 5px; color: #555; }
        
        .filter-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 5px; }
        .filter-grid label { font-size: 0.9em; font-weight: normal; display: flex; align-items: center; cursor: pointer; }
        .filter-grid input { margin-right: 6px; }
        
        /* Options & Uploads */
        .options-panel { padding: 15px; background: #fafafa; }
        .uploads-panel { padding: 15px; border-top: 2px solid #eee; }
        .upload-row { display: flex; gap: 15px; margin-top: 10px; flex-wrap: wrap; }
        .upload-col { flex: 1; min-width: 140px; }
        .upload-col label { display: block; font-weight: bold; margin-bottom: 4px; font-size: 0.95em; }
        .upload-col .help-text { display: block; font-size: 0.75em; color: #777; margin-bottom: 8px; }
        .upload-col input[type="file"], .upload-col select { width: 100%; font-size: 0.85em; padding: 5px; border: 1px solid #ccc; border-radius: 4px; background: #fff; }
        .upload-col input[type="file"] { border-style: dashed; cursor: pointer; background: #fafafa; }
        
        /* Previews */
        .preview-box { width: 100%; aspect-ratio: 2.5 / 3.5; margin-top: 10px; border: 1px solid #ddd; border-radius: 6px; background-color: #f0f0f0; background-repeat: no-repeat; background-position: center; transition: opacity 0.2s; }
        
        /* Button Styles */
        .btn-group { display: flex; gap: 10px; margin-top: 1.5rem; margin-bottom: 1rem; flex-wrap: wrap; }
        .primary-btn { flex: 2; min-width: 150px; padding: 0.9rem 1rem; border: none; border-radius: 8px; font-size: 1.1rem; font-weight: bold; background: #2d7aeb; color: white; cursor: pointer; transition: background 0.2s; }
        .primary-btn:hover { background: #215ec8; }
        .success-btn { flex: 2; min-width: 150px; padding: 0.9rem 1rem; border: none; border-radius: 8px; font-size: 1.1rem; font-weight: bold; background: #2e7d32; color: white; cursor: pointer; transition: background 0.2s; }
        .success-btn:hover { background: #1b5e20; }
        .secondary-btn { flex: 1; min-width: 100px; padding: 0.9rem 1rem; border: none; border-radius: 8px; font-size: 1.1rem; font-weight: bold; background: #e0e0e0; color: #333; cursor: pointer; transition: background 0.2s; }
        .secondary-btn:hover { background: #ccc; }
        .clear-small-btn { padding: 4px 10px; margin-top: 8px; font-size: 0.8em; border: 1px solid #ddd; border-radius: 4px; background: #f9f9f9; color: #555; cursor: pointer; transition: background 0.2s; }
        .clear-small-btn:hover { background: #ececec; }

        .status { padding: 0.75rem 1rem; border-radius: 8px; background: #eef4ff; color: #0b3c79; min-height: 3rem; font-size: 0.95em; }
        a { color: #2d7aeb; font-weight: bold; }
    </style>
</head>
<body>
    <div class="panel">
        <h1>TTRPG Card Generator Controller</h1>
        <p>Select datasets and apply subset filters to generate a custom printable deck.</p>
        
        <div id="datasets-container"></div>
        
        <div class="dataset-group">
            <div class="options-panel">
                <h3 style="margin: 0 0 5px 0;">Visual Options</h3>
                <span style="font-size: 0.85em; color: #666;">Select built-in graphics from your icons folder.</span>
                
                <div class="upload-row">
                    <div class="upload-col">
                        <label>Background</label>
                        <select id="sel-bg"></select>
                        <div class="preview-box" id="prev-bg" style="background-size: cover;"></div>
                    </div>
                    <div class="upload-col">
                        <label>Watermark</label>
                        <select id="sel-wm"></select>
                        <div class="preview-box" id="prev-wm" style="background-size: contain; width: 60%; margin-left: auto; margin-right: auto; border: none; background-color: transparent;"></div>
                    </div>
                    <div class="upload-col">
                        <label>Card Back</label>
                        <select id="sel-cb"></select>
                        <div class="preview-box" id="prev-cb" style="background-size: cover;"></div>
                    </div>
                </div>
            </div>
            
            <div class="uploads-panel">
                <h3 style="margin: 0 0 5px 0;">Custom Overrides</h3>
                <span style="font-size: 0.85em; color: #666;">Upload custom SVGs to manually override the selections above.</span>
                
                <div class="upload-row">
                    <div class="upload-col">
                        <span class="help-text">2.5"x3.5" (750x1050px)</span>
                        <input type="file" id="custom-bg" accept=".svg" />
                    </div>
                    <div class="upload-col">
                        <span class="help-text">120x120px emblem</span>
                        <input type="file" id="custom-wm" accept=".svg" />
                    </div>
                    <div class="upload-col">
                        <span class="help-text">2.5"x3.5" (750x1050px)</span>
                        <input type="file" id="custom-cb" accept=".svg" />
                    </div>
                </div>
            </div>
        </div>
        
        <div class="btn-group">
            <button id="generateBtn" class="primary-btn">Generate Deck</button>
            <button id="generateBacksBtn" class="success-btn">Generate Backs</button>
            <button id="clearAllBtn" class="secondary-btn">Clear All</button>
        </div>
        
        <div id="status" class="status">Ready.</div>
    </div>

    <script>
        const labelMap = {
            "0": "Cantrips", "A": "Abjuration", "C": "Conjuration", "D": "Divination", "E": "Enchantment", 
            "I": "Illusion", "N": "Necromancy", "T": "Transmutation", "V": "Evocation", "str": "Strength", 
            "dex": "Dexterity", "con": "Constitution", "int": "Intelligence", "wis": "Wisdom", "cha": "Charisma",
            "EI": "Eldritch Invocations", "AI": "Artificer Infusions", "AS": "Arcane Shots", "ED": "Elemental Disciplines",
            "FS:F": "Fighting Styles", "RN": "Rune Knight Runes", "PB": "Pact Boons", "MV:B": "Battle Master Maneuvers",
            "MM": "Metamagic", "RP": "Renown Perks", "none": "None / Other", "yes": "Requires Attunement", "no": "No Attunement"
        };

        const DATASETS = __DATASETS_JSON__;

        const container = document.getElementById('datasets-container');

        Object.entries(DATASETS).forEach(([name, data]) => {
            const group = document.createElement('div');
            group.className = 'dataset-group';

            const header = document.createElement('div');
            header.className = 'dataset-header';
            
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.id = `ds-${name}`;
            checkbox.value = name;
            
            const label = document.createElement('label');
            label.htmlFor = `ds-${name}`;
            label.style.display = 'flex';
            label.style.flexDirection = 'column';
            label.style.margin = "0";
            label.style.cursor = "pointer";
            label.style.flexGrow = "1";

            const titleSpan = document.createElement('span');
            titleSpan.innerText = name;
            label.appendChild(titleSpan);

            if (data.subtitle) {
                const subSpan = document.createElement('span');
                subSpan.innerText = data.subtitle;
                subSpan.style.fontSize = "0.75em";
                subSpan.style.color = "#666";
                subSpan.style.fontWeight = "normal";
                subSpan.style.marginTop = "2px";
                label.appendChild(subSpan);
            }

            header.appendChild(checkbox);
            header.appendChild(label);
            group.appendChild(header);

            const subsetPanel = document.createElement('div');
            subsetPanel.className = 'subset-panel';
            subsetPanel.id = `panel-${name}`;

            if (Object.keys(data.filters).length > 0) {
                Object.entries(data.filters).forEach(([filterKey, filterValues]) => {
                    const catDiv = document.createElement('div');
                    catDiv.className = 'subset-category';
                    const filterName = filterKey.charAt(0).toUpperCase() + filterKey.slice(1);
                    catDiv.innerHTML = `<strong>Filter by ${filterName}:</strong>`;
                    
                    const grid = document.createElement('div');
                    grid.className = 'filter-grid';

                    filterValues.forEach(val => {
                        const lbl = document.createElement('label');
                        const chk = document.createElement('input');
                        chk.type = 'checkbox';
                        chk.value = val;
                        chk.dataset.filterKey = filterKey;
                        chk.dataset.datasetName = name;
                        
                        let displayLabel = val.charAt(0).toUpperCase() + val.slice(1);
                        if (filterKey === 'size') {
                            const sizeMap = {"T": "Tiny", "S": "Small", "M": "Medium", "L": "Large", "H": "Huge", "G": "Gargantuan", "C": "Colossal"};
                            displayLabel = sizeMap[val] || displayLabel;
                        } else if (filterKey === 'cr') {
                            displayLabel = val;
                        } else {
                            displayLabel = labelMap[val] || displayLabel;
                        }
                        
                        lbl.appendChild(chk);
                        lbl.appendChild(document.createTextNode(" " + displayLabel));
                        grid.appendChild(lbl);
                    });
                    
                    catDiv.appendChild(grid);
                    const clearBtn = document.createElement('button');
                    clearBtn.className = 'clear-small-btn';
                    clearBtn.type = 'button';
                    clearBtn.textContent = `Clear ${filterName}`;
                    clearBtn.addEventListener('click', () => {
                        grid.querySelectorAll('input[type="checkbox"]').forEach(chk => chk.checked = false);
                    });
                    catDiv.appendChild(clearBtn);

                    subsetPanel.appendChild(catDiv);
                });
            } else {
                subsetPanel.innerHTML = '<span style="color:#888; font-size:0.9em;">No subset filters available for this dataset.</span>';
            }
            
            group.appendChild(subsetPanel);
            container.appendChild(group);

            checkbox.addEventListener('change', (e) => {
                subsetPanel.style.display = e.target.checked ? 'block' : 'none';
            });
        });

        // Setup Visual Options & Previews
        const svgOptions = __SVG_OPTIONS__;
        
        function setupSelect(id, options, defaultVal, previewId) {
            const sel = document.getElementById(id);
            const prev = document.getElementById(previewId);
            
            const autoOpt = document.createElement('option');
            autoOpt.value = 'Default';
            autoOpt.textContent = 'Default';
            sel.appendChild(autoOpt);
            
            options.forEach(opt => {
                const o = document.createElement('option');
                o.value = opt;
                o.textContent = opt;
                if (opt === defaultVal) o.selected = true;
                sel.appendChild(o);
            });
            
            sel.addEventListener('change', () => {
                if (sel.value === 'Default') {
                    prev.style.backgroundImage = `url('/icons/${defaultVal}')`;
                    prev.style.opacity = '0.5';
                } else {
                    prev.style.backgroundImage = `url('/icons/${sel.value}')`;
                    prev.style.opacity = '1';
                }
            });
            
            sel.dispatchEvent(new Event('change'));
        }
        
        setupSelect('sel-bg', svgOptions.backgrounds, 'parchment-background.svg', 'prev-bg');
        setupSelect('sel-wm', svgOptions.watermarks, 'watermark-emblem.svg', 'prev-wm');
        setupSelect('sel-cb', svgOptions.cardBacks, 'card-back.svg', 'prev-cb');

        // Global Clear All Logic
        document.getElementById('clearAllBtn').addEventListener('click', () => {
            document.querySelectorAll('input[type="checkbox"]').forEach(cb => cb.checked = false);
            document.querySelectorAll('input[type="file"]').forEach(file => file.value = "");
            document.querySelectorAll('.subset-panel').forEach(panel => panel.style.display = 'none');
            
            // Reset Dropdowns
            document.getElementById('sel-bg').value = 'parchment-background.svg';
            document.getElementById('sel-wm').value = 'watermark-emblem.svg';
            document.getElementById('sel-cb').value = 'card-back.svg';
            ['sel-bg', 'sel-wm', 'sel-cb'].forEach(id => document.getElementById(id).dispatchEvent(new Event('change')));
            
            document.getElementById('status').textContent = 'All filters and files cleared.';
        });

        // Helper to read uploaded files as base64 Data URLs
        const readFileAsDataURL = (file) => {
            return new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.onload = e => resolve(e.target.result);
                reader.onerror = e => reject(e);
                reader.readAsDataURL(file);
            });
        };

        // Submit Fronts
        const status = document.getElementById('status');
        document.getElementById('generateBtn').addEventListener('click', async () => {
            const payload = { 
                datasets: [], 
                customAssets: {},
                selectedAssets: {
                    background: document.getElementById('sel-bg').value,
                    watermark: document.getElementById('sel-wm').value,
                    cardBack: document.getElementById('sel-cb').value
                }
            };
            
            const bgFile = document.getElementById('custom-bg').files[0];
            const wmFile = document.getElementById('custom-wm').files[0];
            if (bgFile) payload.customAssets.background = await readFileAsDataURL(bgFile);
            if (wmFile) payload.customAssets.watermark = await readFileAsDataURL(wmFile);
            
            document.querySelectorAll('.dataset-header input[type="checkbox"]:checked').forEach(cb => {
                const name = cb.value;
                const file = DATASETS[name].file;
                const filterInputs = document.querySelectorAll(`input[data-dataset-name="${name}"]:checked`);
                
                const filters = {};
                filterInputs.forEach(input => {
                    const key = input.dataset.filterKey;
                    if (!filters[key]) filters[key] = [];
                    filters[key].push(input.value);
                });

                if (DATASETS[name].filters) {
                    for (const key in filters) {
                        if (DATASETS[name].filters[key] && filters[key].length === DATASETS[name].filters[key].length) {
                            delete filters[key];
                        }
                    }
                }

                payload.datasets.push({ name, file, filters });
            });

            if (payload.datasets.length === 0) {
                status.textContent = 'Please select at least one dataset.';
                return;
            }

            status.textContent = 'Generating custom deck...';
            try {
                const response = await fetch('/generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                status.innerHTML = await response.text();
            } catch (error) {
                status.textContent = 'Error: ' + error;
            }
        });

        // Submit Backs
        document.getElementById('generateBacksBtn').addEventListener('click', async () => {
            const payload = { 
                customAssets: {},
                selectedAssets: { cardBack: document.getElementById('sel-cb').value }
            };
            const cbFile = document.getElementById('custom-cb').files[0];
            if (cbFile) payload.customAssets.cardBack = await readFileAsDataURL(cbFile);

            status.textContent = 'Generating 3x3 Card Backs...';
            try {
                const response = await fetch('/generate_backs', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                status.innerHTML = await response.text();
            } catch (error) {
                status.textContent = 'Error: ' + error;
            }
        });
    </script>
</body>
</html>"""
    return html.replace('__SVG_OPTIONS__', svg_options_json)

class GeneratorRequestHandler(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        return translate_served_path(path, super().translate_path(path))

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == '/': 
            svg_options = get_available_svgs()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(get_index_html(svg_options).replace('__DATASETS_JSON__', get_datasets_json()).encode('utf-8'))
            return
            
        # Custom route to serve the SVG previews from the icons folder reliably
        elif parsed.path.startswith('/icons/'):
            filename = os.path.basename(parsed.path)
            filepath = os.path.join(ICON_DIR, filename)
            if os.path.exists(filepath):
                self.send_response(200)
                self.send_header('Content-Type', 'image/svg+xml')
                self.end_headers()
                with open(filepath, 'rb') as f:
                    self.wfile.write(f.read())
                return
            else:
                self.send_response(404)
                self.end_headers()
                return
                
        super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        
        # Route for normal card fronts
        if parsed.path == '/generate':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                payload = json.loads(post_data.decode('utf-8'))
                output_filename = "Custom_Deck_Cards.html"
                
                result = generate_html(payload, output_html_path=output_filename)
                
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                
                if result and isinstance(result, dict) and result.get("card_count", 0) > 0: 
                    cc = result["card_count"]
                    ic = result["item_count"]
                    tc = result["type_counts"]
                    
                    sorted_tc = sorted(tc.items(), key=lambda item: item[1], reverse=True)
                    badges = "".join([f'<span style="display: inline-block; background: #d0def4; color: #0b3c79; padding: 3px 8px; border-radius: 12px; font-size: 0.8em; margin: 0 4px 4px 0;"><strong>{k}:</strong> {v}</span>' for k, v in sorted_tc])
                    
                    html_resp = f'''
                    <div style="margin-bottom: 10px;">
                        <span style="font-size: 1.1em; color: #111;">Success! Generated a deck of <strong>{cc}</strong> cards from <strong>{ic}</strong> unique items.</span>
                    </div>
                    <div style="margin-bottom: 15px;">
                        {badges}
                    </div>
                    <p><a href="/{output_filename}" target="_blank" style="text-decoration: none; font-weight: bold; background: #2d7aeb; color: #fff; padding: 8px 16px; border-radius: 6px;">Open Custom Deck</a></p>
                    '''
                    self.wfile.write(html_resp.encode('utf-8'))
                else: 
                    self.wfile.write(b'<p style="color: #d32f2f;">No cards matched your filter criteria.</p>')
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f'Server Error: {str(e)}'.encode('utf-8'))
            return
            
        # Route for card backs
        if parsed.path == '/generate_backs':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                payload = json.loads(post_data.decode('utf-8'))
                output_filename = "Custom_Deck_Backs.html"
                
                generate_backs_html(payload, output_html_path=output_filename)
                
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                
                html_resp = f'''
                <div style="margin-bottom: 10px;">
                    <span style="font-size: 1.1em; color: #111;">Success! Generated a printable page of Card Backs.</span>
                </div>
                <p><a href="/{output_filename}" target="_blank" style="text-decoration: none; font-weight: bold; background: #2e7d32; color: #fff; padding: 8px 16px; border-radius: 6px;">Open Card Backs</a></p>
                '''
                self.wfile.write(html_resp.encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f'Server Error: {str(e)}'.encode('utf-8'))
            return

def serve_gui(port=8000):
    server_address = ('', port)
    httpd = HTTPServer(server_address, GeneratorRequestHandler)
    url = f'http://localhost:{port}/'
    print(f'Serving card generator UI at {url}')
    webbrowser.open(url)
    try: 
        httpd.serve_forever()
    except KeyboardInterrupt: 
        print('\nServer stopped.')
        httpd.server_close()

if __name__ == '__main__':
    serve_gui()