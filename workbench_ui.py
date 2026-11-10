"""Controller-only presentation. No generated-card styles or rendering logic."""
import json
from pathlib import Path

UI_DIR = Path(__file__).resolve().parent / 'ui'


def _read(name):
    return (UI_DIR / name).read_text(encoding='utf-8')


def _json(value):
    return json.dumps(value, ensure_ascii=False).replace('<', '\\u003c').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')


def _render(template, config, script):
    return (_read(template).replace('__SHELL_CSS__', _read('shell.css'))
            .replace('__BOOTSTRAP__', _json(config)).replace('__SCRIPT__', _read(script)))


def render_workbench(datasets_json, svg_options_json, platform='desktop', pdf_export_enabled=True):
    config = {'datasets': json.loads(datasets_json), 'assets': json.loads(svg_options_json),
              'platform': platform, 'pdfExport': pdf_export_enabled}
    return (_render('workbench.html.template', config, 'workbench.js')
            .replace('__WORKBENCH_CSS__', _read('workbench.css')))


def render_setup(ready, platform='desktop', in_generator=False):
    return _render('setup.html.template', {'ready': ready, 'platform': platform, 'inGenerator': in_generator}, 'setup.js')


def render_installer():
    return _render('installer.html.template', {}, 'installer.js')


def render_about():
    return _read('about.html.template').replace('__SHELL_CSS__', _read('shell.css'))


def render_privacy():
    return _read('privacy.html.template').replace('__SHELL_CSS__', _read('shell.css'))


def render_viewer(manifest):
    return (_render('viewer.html.template', manifest, 'viewer.js')
            .replace('__VIEWER_CSS__', _read('viewer.css')))
