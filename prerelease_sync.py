"""Fetch and index prerelease content declared by the installed dataset."""

from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
import urllib.request
import zipfile
from typing import Dict, List, Optional, Tuple

# Dataset category -> top-level JSON keys that mean the file belongs there.
CATEGORY_KEYS = {
    "Classes": ("class", "subclass", "classFeature", "subclassFeature"),
    "Feats": ("feat",),
    "Races": ("race", "subrace"),
    "Spells": ("spell",),
    "Optional Features": ("optionalfeature",),
    "Backgrounds": ("background",),
    "Items": ("item", "baseitem", "magicvariant", "itemGroup"),
    "Bestiary": ("monster",),
    "Deities": ("deity",),
    "Vehicles": ("vehicle", "vehicleUpgrade"),
    "Conditions / Diseases": ("condition", "disease", "status"),
    "Psionics": ("psionic",),
    "Decks": ("deck", "card"),
    "Actions": ("action",),
    "Bastions": ("bastion", "facility"),
    "Languages": ("language", "languageScript"),
}

CATEGORY_SLUGS = {
    "Classes": "classes",
    "Feats": "feats",
    "Races": "races",
    "Spells": "spells",
    "Optional Features": "optionalfeatures",
    "Backgrounds": "backgrounds",
    "Items": "items",
    "Bestiary": "bestiary",
    "Deities": "deities",
    "Vehicles": "vehicles",
    "Conditions / Diseases": "conditions",
    "Psionics": "psionics",
    "Decks": "decks",
    "Actions": "actions",
    "Bastions": "bastions",
    "Languages": "languages",
}

# Official primary paths relative to the dataset root (for combined indexes).
OFFICIAL_PRIMARY = {
    "Classes": "data/class/index.json",
    "Feats": "data/feats.json",
    "Races": "data/races.json",
    "Spells": "data/spells/index.json",
    "Optional Features": "data/optionalfeatures.json",
    "Backgrounds": "data/backgrounds.json",
    "Items": "data/items.json",
    "Bestiary": "data/bestiary/index.json",
    "Deities": "data/deities.json",
    "Vehicles": "data/vehicles.json",
    "Conditions / Diseases": "data/conditionsdiseases.json",
    "Psionics": "data/psionics.json",
    "Decks": "data/decks.json",
    "Actions": "data/actions.json",
    "Bastions": "data/bastions.json",
    "Languages": "data/languages.json",
}

_VECT_RE = re.compile(
    r"""(?:VeCt\.|static\s+)(URL_ROOT_PRERELEASE|URL_PRERELEASE|JSON_PRERELEASE_INDEX)\s*=\s*[`'"]([^`'"]+)[`'"]"""
)

CONTENT_DIR_NAMES = {
    "class", "subclass", "race", "feat", "spell", "collection",
    "optionalfeature", "background", "item", "bestiary", "monster",
    "deity", "vehicle", "psionic", "deck", "action", "bastion",
    "language", "condition", "reward", "object", "trap", "cult",
    "charcreationoption", "recipe",
}


def parse_prerelease_urls(utils_js_path: str) -> Optional[Dict[str, str]]:
    """Return VeCt prerelease URL fields from utils.js, or None if unavailable."""
    if not os.path.isfile(utils_js_path):
        return None
    try:
        with open(utils_js_path, "r", encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return None
    found = dict(_VECT_RE.findall(text))
    root = found.get("URL_ROOT_PRERELEASE")
    if not root:
        return None
    return {
        "URL_ROOT_PRERELEASE": root,
        "URL_PRERELEASE": found.get("URL_PRERELEASE", ""),
        "JSON_PRERELEASE_INDEX": found.get("JSON_PRERELEASE_INDEX", "prerelease/index.json"),
    }


def _zip_url_from_repo(repo_url: str, root_url: str) -> Optional[str]:
    """Derive an archive ZIP URL from the repo / root constants (no hardcoded hosts)."""
    repo_url = (repo_url or "").rstrip("/")
    if not repo_url:
        return None
    branch = "master"
    # URL_ROOT_PRERELEASE often ends with /<branch>/
    m = re.search(r"/([^/]+)/?$", root_url.rstrip("/"))
    if m and m.group(1) not in ("",):
        # root is like https://host/owner/repo/branch/ — take last segment as branch
        parts = root_url.rstrip("/").split("/")
        if len(parts) >= 1:
            branch = parts[-1]
    return f"{repo_url}/archive/refs/heads/{branch}.zip"


def _strip_reprinted_classes(data: dict) -> dict:
    """Drop class/subclass objects superseded via reprintedAs to avoid duplicates."""
    classes = data.get("class")
    if not isinstance(classes, list):
        return data
    dropped_names = {
        c.get("name")
        for c in classes
        if isinstance(c, dict) and c.get("reprintedAs") and c.get("name")
    }
    kept = [c for c in classes if not (isinstance(c, dict) and c.get("reprintedAs"))]
    if not dropped_names and len(kept) == len(classes):
        return data
    out = dict(data)
    out["class"] = kept
    subs = data.get("subclass")
    if dropped_names and isinstance(subs, list):
        out["subclass"] = [
            s for s in subs
            if not (isinstance(s, dict) and s.get("className") in dropped_names)
        ]
    return out


def _file_contributes(data: dict, keys: Tuple[str, ...]) -> bool:
    return any(k in data and isinstance(data[k], list) and data[k] for k in keys)


def _rel_posix(*parts: str) -> str:
    return "/".join(parts)


def _write_json(path: str, obj) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, indent="\t", ensure_ascii=False)
        f.write("\n")


def _clear_managed_content(prerelease_dir: str) -> None:
    """Remove previously synced content dirs and generated indexes; keep index stub."""
    generated = os.path.join(prerelease_dir, "generated")
    if os.path.isdir(generated):
        shutil.rmtree(generated)
    for name in list(os.listdir(prerelease_dir)):
        if name in ("index.json", "generated"):
            continue
        path = os.path.join(prerelease_dir, name)
        if not os.path.isdir(path):
            # Drop leftover top-level json from prior flawed syncs (not the index).
            if name.endswith(".json"):
                os.remove(path)
            continue
        base = name.split(" (")[0]
        if name in CONTENT_DIR_NAMES or base in CONTENT_DIR_NAMES:
            shutil.rmtree(path)


def _copy_content_trees(src_root: str, dest_prerelease: str) -> List[str]:
    """Copy content folders/files from an extracted prerelease repo into prerelease/.

    Returns relative posix paths (from prerelease/) of JSON files copied.
    """
    copied: List[str] = []
    # Archive zip often wraps in repo-name-branch/
    candidates = [src_root]
    entries = [e for e in os.listdir(src_root) if not e.startswith(".")]
    if len(entries) == 1 and os.path.isdir(os.path.join(src_root, entries[0])):
        candidates.insert(0, os.path.join(src_root, entries[0]))

    src = None
    for c in candidates:
        if any(os.path.isdir(os.path.join(c, d)) for d in CONTENT_DIR_NAMES):
            src = c
            break
        if os.path.isdir(os.path.join(c, "class")) or os.path.isdir(os.path.join(c, "collection")):
            src = c
            break
    if src is None:
        src = candidates[0]

    for name in os.listdir(src):
        if name.startswith(".") or name == "index.json":
            continue
        sp = os.path.join(src, name)
        if os.path.isdir(sp):
            if name not in CONTENT_DIR_NAMES and name != "collection":
                continue
            dest = os.path.join(dest_prerelease, name)
            if os.path.exists(dest):
                shutil.rmtree(dest)
            shutil.copytree(sp, dest)
            for root, _dirs, files in os.walk(dest):
                for fn in files:
                    if fn.endswith(".json"):
                        full = os.path.join(root, fn)
                        rel = os.path.relpath(full, dest_prerelease).replace("\\", "/")
                        copied.append(rel)
        # Ignore top-level loose files (package.json, README, etc.).
    return sorted(set(copied))


def _entity_key(dtype: str, item: dict):
    return (
        dtype,
        str(item.get("name", "")).lower(),
        str(item.get("source", "")).lower(),
        str(item.get("shortName", "")).lower(),
        str(item.get("className", "")).lower(),
        str(item.get("classSource", "")).lower(),
    )


def _index_pack_entities(prerelease_dir: str, rel_files: List[str]) -> dict:
    """Index entities across prerelease JSON for local _copy resolution."""
    index = {}
    for rel in rel_files:
        path = os.path.join(prerelease_dir, rel.replace("/", os.sep))
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        for key, val in data.items():
            if key.startswith("_") or not isinstance(val, list):
                continue
            for item in val:
                if isinstance(item, dict) and item.get("name"):
                    index[_entity_key(key, item)] = item
                    # also plain name|source for class-like lookups
                    index[(key, str(item.get("name","")).lower(), str(item.get("source","")).lower())] = item
    return index


def _materialize_copy(item: dict, dtype: str, index: dict) -> dict:
    if not isinstance(item, dict) or "_copy" not in item:
        return item
    copy_meta = item.get("_copy")
    if not isinstance(copy_meta, dict):
        return item
    # Try several key shapes used by class/subclass copies
    candidates = [
        (dtype, str(copy_meta.get("name","")).lower(), str(copy_meta.get("source","")).lower(),
         str(copy_meta.get("shortName","")).lower(), str(copy_meta.get("className","")).lower(),
         str(copy_meta.get("classSource","")).lower()),
        (dtype, str(copy_meta.get("name","")).lower(), str(copy_meta.get("source","")).lower()),
    ]
    base = None
    for key in candidates:
        base = index.get(key)
        if base:
            break
    if not base:
        return item
    merged = dict(base)
    for k, v in item.items():
        if k == "_copy":
            continue
        merged[k] = v
    return merged


def _process_class_files(prerelease_dir: str, rel_files: List[str]) -> None:
    """Inline local _copy refs, then drop reprintedAs-superseded class/subclasses."""
    index = _index_pack_entities(prerelease_dir, rel_files)
    for rel in rel_files:
        if not rel.endswith(".json"):
            continue
        path = os.path.join(prerelease_dir, rel.replace("/", os.sep))
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        changed = False
        for key, val in list(data.items()):
            if key.startswith("_") or not isinstance(val, list):
                continue
            new_list = []
            for item in val:
                if isinstance(item, dict) and "_copy" in item:
                    new_list.append(_materialize_copy(item, key, index))
                    changed = True
                else:
                    new_list.append(item)
            data[key] = new_list
        new_data = _strip_reprinted_classes(data)
        if new_data is not data:
            changed = True
            data = new_data
        if changed:
            _write_json(path, data)



def _entity_dedupe_key(item: dict) -> tuple:
    return (
        str(item.get("name", "")).lower(),
        str(item.get("source", "")).lower(),
        str(item.get("shortName", "")).lower(),
        str(item.get("className", "")).lower(),
        str(item.get("classSource", "")).lower(),
        str(item.get("level", "")),
    )


def _build_indexes(data_root: str, prerelease_dir: str, rel_files: List[str]) -> List[str]:
    """Write per-category playtest JSON (category keys only) plus combined indexes."""
    generated = os.path.join(prerelease_dir, "generated")
    os.makedirs(generated, exist_ok=True)

    # Merge only the arrays that belong to each generator category.
    by_cat: Dict[str, Dict[str, list]] = {
        cat: {key: [] for key in keys} for cat, keys in CATEGORY_KEYS.items()
    }
    seen: Dict[str, Dict[str, set]] = {
        cat: {key: set() for key in keys} for cat, keys in CATEGORY_KEYS.items()
    }

    for rel in rel_files:
        path = os.path.join(prerelease_dir, rel.replace("/", os.sep))
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        for cat, keys in CATEGORY_KEYS.items():
            for key in keys:
                items = data.get(key)
                if not isinstance(items, list):
                    continue
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    dk = _entity_dedupe_key(item)
                    if dk in seen[cat][key]:
                        continue
                    seen[cat][key].add(dk)
                    by_cat[cat][key].append(item)

    populated = []
    for cat, key_lists in by_cat.items():
        payload = {k: v for k, v in key_lists.items() if v}
        if not payload:
            continue
        slug = CATEGORY_SLUGS[cat]
        playtest_name = f"{slug}_playtest.json"
        _write_json(os.path.join(generated, playtest_name), payload)

        official = OFFICIAL_PRIMARY.get(cat)
        combined = {}
        if official:
            combined["_official"] = _rel_posix("..", "..", *official.split("/"))
        combined["_playtest"] = f"./{playtest_name}"
        _write_json(os.path.join(generated, f"{slug}_combined.json"), combined)
        populated.append(cat)
    return populated


def _update_to_import(prerelease_dir: str, rel_files: List[str]) -> None:
    index_path = os.path.join(prerelease_dir, "index.json")
    readme = [
        "NOTE: This feature is designed for use in user-hosted copies of the site.",
        "This file contains as an index for other prerelease files in this directory.",
    ]
    if os.path.isfile(index_path):
        try:
            with open(index_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
            if isinstance(existing, dict) and isinstance(existing.get("readme"), list):
                readme = existing["readme"]
        except (OSError, json.JSONDecodeError):
            pass
    # toImport entries are filenames relative to prerelease/ (as the site expects)
    to_import = sorted(rel_files)
    _write_json(index_path, {"readme": readme, "toImport": to_import})


def _fetch_via_git(repo_url: str, dest_dir: str, git_cmd: str) -> bool:
    try:
        import subprocess
        subprocess.run(
            [git_cmd, "clone", "--depth", "1", repo_url, dest_dir],
            check=True,
            capture_output=True,
        )
        return True
    except Exception as e:
        print(f"Prerelease content: git fetch failed ({e})")
        return False


def _fetch_via_zip(zip_url: str, dest_dir: str) -> bool:
    try:
        os.makedirs(dest_dir, exist_ok=True)
        zip_path = os.path.join(dest_dir, "_archive.zip")
        urllib.request.urlretrieve(zip_url, zip_path)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(dest_dir)
        os.remove(zip_path)
        return True
    except Exception as e:
        print(f"Prerelease content: zip fetch failed ({e})")
        return False


def sync_prerelease_content(data_root: str, git_cmd: Optional[str] = None) -> bool:
    """Download prerelease content into data_root/prerelease using VeCt URLs from utils.js.

    Prefer a shallow git clone of URL_PRERELEASE (same mechanism as the main dataset
    install). Fall back to a branch ZIP derived from that repo URL. Skips quietly
    when utils.js / constants are missing or the network fetch fails.
    """
    utils_path = os.path.join(data_root, "js", "utils.js")
    urls = parse_prerelease_urls(utils_path)
    if not urls:
        print("Prerelease content: skipped (utils.js or URL_ROOT_PRERELEASE not found)")
        return False

    prerelease_dir = os.path.join(data_root, "prerelease")
    os.makedirs(prerelease_dir, exist_ok=True)

    repo_url = urls.get("URL_PRERELEASE") or ""
    root_url = urls["URL_ROOT_PRERELEASE"]
    zip_url = _zip_url_from_repo(repo_url, root_url)

    tmp = tempfile.mkdtemp(prefix="prerelease_sync_")
    try:
        fetched = False
        fetch_src = os.path.join(tmp, "src")
        if git_cmd and repo_url:
            fetched = _fetch_via_git(repo_url, fetch_src, git_cmd)
        if not fetched and zip_url:
            fetch_src = os.path.join(tmp, "zip")
            fetched = _fetch_via_zip(zip_url, fetch_src)
        if not fetched:
            print("Prerelease content: skipped (fetch failed or offline)")
            return False

        _clear_managed_content(prerelease_dir)
        rel_files = _copy_content_trees(fetch_src, prerelease_dir)
        if not rel_files:
            print("Prerelease content: skipped (no content files in fetch)")
            return False

        _process_class_files(prerelease_dir, rel_files)
        rel_files = []
        for root, dirs, files in os.walk(prerelease_dir):
            dirs[:] = [d for d in dirs if d != "generated"]
            for fn in files:
                if not fn.endswith(".json") or fn == "index.json":
                    continue
                full = os.path.join(root, fn)
                rel = os.path.relpath(full, prerelease_dir).replace("\\", "/")
                if rel.startswith("generated/"):
                    continue
                rel_files.append(rel)
        rel_files = sorted(set(rel_files))

        _update_to_import(prerelease_dir, rel_files)
        cats = _build_indexes(data_root, prerelease_dir, rel_files)
        print(f"Prerelease content: synced {len(rel_files)} files for {len(cats)} categories")
        return True
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def playtest_indexes_ready(data_root: str) -> bool:
    gen = os.path.join(data_root, "prerelease", "generated")
    return os.path.isdir(gen) and any(
        fn.endswith("_playtest.json") for fn in os.listdir(gen)
    ) if os.path.isdir(gen) else False
