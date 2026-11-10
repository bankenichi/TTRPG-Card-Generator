"""Validated replacement of dataset trees without discarding a working install."""
import os
import shutil
import tempfile
import zipfile
import json
import stat
from pathlib import Path
from data_paths import _has_5etools_shape, is_within


def validate_dataset(root):
    """Match the loader's JSON requirements before replacing working data."""
    if not _has_5etools_shape(root):
        raise ValueError('Dataset must contain data/class/ and data/spells/')
    data = Path(root) / 'data'
    if not is_within(data, root):
        raise ValueError('Dataset data directory escapes its repository')
    for category in ('class', 'spells'):
        index = data / category / 'index.json'
        if not index.is_file() or not is_within(index, root):
            raise ValueError(f'Dataset is missing a safe data/{category}/index.json')
    for path in data.rglob('*.json'):
        if not is_within(path, root):
            raise ValueError('Dataset JSON link escapes its repository')
        try:
            with path.open(encoding='utf-8') as source:
                json.load(source)
        except (OSError, ValueError) as exc:
            raise ValueError(f'Invalid dataset JSON: {path.relative_to(root)}') from exc


def replace_tree(staged, destination):
    parent = os.path.dirname(os.path.abspath(destination))
    backup = tempfile.mkdtemp(prefix='.backup-', dir=parent)
    previous = os.path.join(backup, 'previous')
    retain_backup = False
    installed = False
    try:
        if os.path.exists(destination):
            os.replace(destination, previous)
        try:
            os.replace(staged, destination)
            installed = True
        except BaseException:
            if os.path.exists(previous):
                try:
                    os.replace(previous, destination)
                except OSError as rollback_error:
                    retain_backup = True
                    raise RuntimeError(f'Replacement failed. Your previous data is preserved at {previous}') from rollback_error
            raise
    finally:
        if not retain_backup and is_within(backup, parent) and os.path.basename(backup).startswith('.backup-'):
            def remove_readonly(function, path, error):
                if not is_within(path, backup):
                    raise error
                os.chmod(path, os.stat(path).st_mode | stat.S_IWUSR)
                function(path)
            try:
                shutil.rmtree(backup, onexc=remove_readonly)
            except OSError:
                if not installed:
                    raise
                print(f'Data installed successfully; old backup cleanup is deferred: {backup}')


def dataset_from_extraction(extracted):
    if _has_5etools_shape(extracted):
        return extracted
    ready = [os.path.join(extracted, name) for name in os.listdir(extracted)
             if _has_5etools_shape(os.path.join(extracted, name))]
    if len(ready) != 1:
        raise ValueError('ZIP must contain data/class/ and data/spells/, optionally inside one repository folder')
    return ready[0]


def safe_extract(archive, destination):
    for entry in archive.infolist():
        path = os.path.join(destination, entry.filename)
        if not is_within(path, destination) or '\\' in entry.filename or ':' in entry.filename:
            raise ValueError('ZIP contains an unsafe path')
        if (entry.external_attr >> 16) & 0o170000 == 0o120000:
            raise ValueError('ZIP symlinks are not supported')
    archive.extractall(destination)
