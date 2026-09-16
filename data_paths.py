"""Locate a 5eTools-shaped data tree under generators/ by structure, not folder name.

A tree is ready when it contains ``data/class`` and ``data/spells`` (the same
signal the launcher has always used). Discovery order:

1. ``generators/data`` if that tree is ready (also the default git/ZIP install target)
2. otherwise the first alphabetically named ready child of ``generators/``
   (``temp_zip`` and hidden names are skipped)

``datasets.json`` keeps canonical paths under ``generators/data/...``. Call
``resolve_dataset_path`` (or ``remap_dataset_catalog``) so those paths land on
whichever ready folder was found — e.g. ``generators/5etools/data/skills.json``.
"""

import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GENERATORS_DIR = os.path.join(SCRIPT_DIR, "generators")
DEFAULT_DATA_DIRNAME = "data"
DEFAULT_DATA_DIR = os.path.join(GENERATORS_DIR, DEFAULT_DATA_DIRNAME)
CANONICAL_DATA_PREFIX = "generators/data"
SKIP_CHILD_NAMES = {"temp_zip"}


def _has_5etools_shape(root):
    """True if *root* contains the 5eTools ``data/class`` and ``data/spells`` dirs."""
    return (
        os.path.isdir(os.path.join(root, "data", "class"))
        and os.path.isdir(os.path.join(root, "data", "spells"))
    )


def discover_data_root(generators_dir=None):
    """Return the preferred ready data root, or None if none is present."""
    generators_dir = generators_dir if generators_dir is not None else GENERATORS_DIR
    default_dir = os.path.join(generators_dir, DEFAULT_DATA_DIRNAME)
    if _has_5etools_shape(default_dir):
        return default_dir
    if not os.path.isdir(generators_dir):
        return None
    for name in sorted(os.listdir(generators_dir), key=str.lower):
        if name in SKIP_CHILD_NAMES or name.startswith("."):
            continue
        path = os.path.join(generators_dir, name)
        if os.path.isdir(path) and _has_5etools_shape(path):
            return path
    return None


def is_data_ready(generators_dir=None):
    return discover_data_root(generators_dir) is not None


def _posix_path(path):
    posix = str(path).replace("\\", "/")
    if posix.startswith("./"):
        posix = posix[2:]
    return posix


def resolve_dataset_path(path, generators_dir=None):
    """Map a canonical ``generators/data/...`` path onto the discovered data root.

    Returns an absolute filesystem path when the canonical prefix matches a
    discovered root; otherwise returns *path* unchanged.
    """
    if not path:
        return path
    root = discover_data_root(generators_dir)
    if not root:
        return path
    posix = _posix_path(path)
    prefix = CANONICAL_DATA_PREFIX
    if posix == prefix or posix.startswith(prefix + "/"):
        remainder = posix[len(prefix):].lstrip("/")
        return os.path.normpath(os.path.join(root, remainder) if remainder else root)
    return path


def to_relative_dataset_path(path, generators_dir=None, script_dir=None):
    """Like ``resolve_dataset_path`` but relative to the repo root when possible."""
    script_dir = script_dir if script_dir is not None else SCRIPT_DIR
    resolved = resolve_dataset_path(path, generators_dir=generators_dir)
    if os.path.isabs(resolved):
        try:
            rel = os.path.relpath(resolved, script_dir)
            return rel.replace("\\", "/")
        except ValueError:
            return resolved
    return str(resolved).replace("\\", "/")


def remap_dataset_catalog(catalog, generators_dir=None, script_dir=None):
    """Rewrite datasets.json ``file`` fields to the discovered data root."""
    for entry in catalog.values():
        if not isinstance(entry, dict) or "file" not in entry:
            continue
        files = entry["file"]
        if isinstance(files, list):
            entry["file"] = [
                to_relative_dataset_path(p, generators_dir=generators_dir, script_dir=script_dir)
                for p in files
            ]
        elif isinstance(files, str):
            entry["file"] = to_relative_dataset_path(
                files, generators_dir=generators_dir, script_dir=script_dir
            )
    return catalog


def translate_served_path(url_path, mapped_fs_path, generators_dir=None):
    """If a canonical ``generators/data`` URL missed on disk, map it to the discovered tree."""
    if os.path.exists(mapped_fs_path):
        return mapped_fs_path
    rel = _posix_path(url_path.split("?", 1)[0]).lstrip("/")
    resolved = resolve_dataset_path(rel, generators_dir=generators_dir)
    if resolved != rel and os.path.exists(resolved):
        return resolved
    return mapped_fs_path
