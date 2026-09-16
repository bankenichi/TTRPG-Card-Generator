"""Smoke tests for 5eTools data-root discovery and dataset path resolution."""

import json
import os
import tempfile
import unittest

import data_paths
from data_paths import (
    remap_dataset_catalog,
    resolve_dataset_path,
    to_relative_dataset_path,
    translate_served_path,
)


def _ready_tree(root):
    os.makedirs(os.path.join(root, "data", "class"), exist_ok=True)
    os.makedirs(os.path.join(root, "data", "spells"), exist_ok=True)


class DataPathsTest(unittest.TestCase):
    def test_prefers_generators_data_when_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            _ready_tree(os.path.join(tmp, "data"))
            _ready_tree(os.path.join(tmp, "5etools"))
            self.assertEqual(
                data_paths.discover_data_root(tmp),
                os.path.join(tmp, "data"),
            )

    def test_discovers_5etools_child_when_data_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            _ready_tree(os.path.join(tmp, "5etools"))
            os.makedirs(os.path.join(tmp, "aaa_incomplete", "data"), exist_ok=True)
            self.assertEqual(
                data_paths.discover_data_root(tmp),
                os.path.join(tmp, "5etools"),
            )
            self.assertTrue(data_paths.is_data_ready(tmp))

    def test_incomplete_default_data_does_not_win(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "data", "data"), exist_ok=True)
            _ready_tree(os.path.join(tmp, "5etools"))
            self.assertEqual(
                data_paths.discover_data_root(tmp),
                os.path.join(tmp, "5etools"),
            )

    def test_first_alphabetical_ready_child(self):
        with tempfile.TemporaryDirectory() as tmp:
            _ready_tree(os.path.join(tmp, "zeta"))
            _ready_tree(os.path.join(tmp, "5etools"))
            self.assertEqual(
                data_paths.discover_data_root(tmp),
                os.path.join(tmp, "5etools"),
            )

    def test_skips_temp_zip_and_hidden(self):
        with tempfile.TemporaryDirectory() as tmp:
            _ready_tree(os.path.join(tmp, "temp_zip"))
            _ready_tree(os.path.join(tmp, ".hidden"))
            self.assertIsNone(data_paths.discover_data_root(tmp))

    def test_skills_path_resolves_under_5etools(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree = os.path.join(tmp, "5etools")
            _ready_tree(tree)
            skills = os.path.join(tree, "data", "skills.json")
            with open(skills, "w", encoding="utf-8") as f:
                json.dump({"skill": [{"name": "Athletics"}]}, f)

            resolved = resolve_dataset_path(
                "generators/data/data/skills.json", generators_dir=tmp
            )
            self.assertEqual(os.path.normpath(resolved), os.path.normpath(skills))
            self.assertTrue(os.path.exists(resolved))

            rel = to_relative_dataset_path(
                "generators/data/data/skills.json",
                generators_dir=tmp,
                script_dir=tmp,
            )
            self.assertEqual(rel.replace("\\", "/"), "5etools/data/skills.json")

    def test_remap_catalog_and_http_translate(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree = os.path.join(tmp, "5etools")
            _ready_tree(tree)
            skills = os.path.join(tree, "data", "skills.json")
            with open(skills, "w", encoding="utf-8") as f:
                f.write("{}")

            catalog = {
                "Skills": {"file": "generators/data/data/skills.json", "filters": {}},
                "Spells": {"file": ["generators/data/data/spells/index.json"], "filters": {}},
            }
            remap_dataset_catalog(catalog, generators_dir=tmp, script_dir=tmp)
            self.assertEqual(catalog["Skills"]["file"], "5etools/data/skills.json")
            self.assertEqual(catalog["Spells"]["file"], ["5etools/data/spells/index.json"])

            missing = os.path.join(tmp, "generators", "data", "data", "skills.json")
            mapped = translate_served_path(
                "/generators/data/data/skills.json",
                missing,
                generators_dir=tmp,
            )
            self.assertEqual(os.path.normpath(mapped), os.path.normpath(skills))

    def test_engine_loads_skills_from_5etools_tree(self):
        from card_engine import get_dataset_items

        with tempfile.TemporaryDirectory() as tmp:
            tree = os.path.join(tmp, "5etools")
            _ready_tree(tree)
            skills = os.path.join(tree, "data", "skills.json")
            with open(skills, "w", encoding="utf-8") as f:
                json.dump({"skill": [{"name": "Athletics", "ability": "str"}]}, f)

            original = data_paths.GENERATORS_DIR
            data_paths.GENERATORS_DIR = tmp
            try:
                items = get_dataset_items("generators/data/data/skills.json")
                self.assertEqual(len(items), 1)
                self.assertEqual(items[0]["name"], "Athletics")
                self.assertEqual(items[0]["_data_type"], "skill")
            finally:
                data_paths.GENERATORS_DIR = original


if __name__ == "__main__":
    unittest.main()
