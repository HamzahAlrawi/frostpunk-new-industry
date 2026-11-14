"""Settings, native-vector preservation and new-city supply coverage."""
import copy
import struct
import unittest

from configuration import (CATEGORIES, DEFAULT, LEVELS, PRESETS, PROFILE_ANCHOR, RESOURCES,
                           difficulty_categories, difficulty_settings, resolve,
                           starting_profiles, starting_supplies)


def difficulty_fixture():
    chunks = [struct.pack("<I", 13)]
    for number, name in enumerate(CATEGORIES):
        chunks.append(b"\1\1" + name.encode() + b"\0" + bytes([number + 1]) * 16 + struct.pack("<I", 4))
        for level, title in enumerate(LEVELS):
            chunks += [b"\1\1" + title.encode() + b"\0" + bytes([level + 21]) * 16,
                       bytes([int(level == 1)]) + struct.pack("<I", 1) + bytes([level + 41]) * 17]
        chunks.append(b"\1" + name.encode() + b"\0" if number < 12 else b"\0")
    return b"".join(chunks)


class ConfigurationTests(unittest.TestCase):
    def test_defaults_preserve_research_pacing_and_menu(self):
        settings = resolve(DEFAULT)
        self.assertEqual(settings["native_difficulty"], "menu")
        self.assertEqual(settings["workshop_output_multiplier"], 1.5625)
        self.assertEqual(settings["perk_research_duration_multiplier"], 0.5)
        for preset in PRESETS:
            bonuses = resolve(DEFAULT | {"preset": preset})["starting_resources_bonus"]
            for name, before in {"Wood": 40, "Steel": 25, "Coal": 50, "Raw Food": 30}.items():
                self.assertGreater(bonuses[name], before)

    def test_rejects_typoes_and_unsafe_values(self):
        for override in ({"preset": "typo"}, {"schema_version": True}, {"unknown": 1},
                         {"starting_resources_bonus": {"Wood": -1}},
                         {"starting_resources_bonus": {"Wood": True}},
                         {"starting_resources_bonus": {"Wood": 1.5}},
                         {"starting_resources_bonus": {"Wod": 12}},
                         {"difficulty_categories": {"Weather": "typo"}},
                         {"difficulty_categories": {"Whether": "easy"}},
                         {"workshop_output_multiplier": float("nan")},
                         {"perk_research_duration_multiplier": 0}):
            with self.subTest(override=override), self.assertRaises(ValueError):
                resolve(DEFAULT | override)

    def test_resource_and_category_overrides_do_not_mutate_presets(self):
        document = DEFAULT | {"preset": "easiest", "starting_resources_bonus": {"Wood": 123},
                              "difficulty_categories": {"Weather": "menu"}}
        before = copy.deepcopy(document)
        settings = resolve(document)
        self.assertEqual(settings["starting_resources_bonus"]["Wood"], 123)
        self.assertEqual(settings["starting_resources_bonus"]["Steam Cores"], 5)
        self.assertEqual(document, before)
        self.assertEqual(resolve(DEFAULT | {"preset": "easiest"})["starting_resources_bonus"]["Wood"], 200)

    def test_menu_difficulty_is_byte_identical(self):
        original = difficulty_fixture()
        self.assertEqual(difficulty_settings(original, resolve(DEFAULT)), original)

    def test_native_presets_copy_effects_and_preserve_all_headers_and_flags(self):
        original = difficulty_fixture()
        source = difficulty_categories(original)
        for selected, source_index in (("easy", 0), ("medium", 1), ("hard", 2), ("extreme", 3)):
            revised = difficulty_categories(difficulty_settings(original, resolve(DEFAULT | {"native_difficulty": selected})))
            for before, after in zip(source, revised):
                self.assertEqual(before["header"], after["header"])
                self.assertEqual(before["footer"], after["footer"])
                for old, new in zip(before["records"], after["records"]):
                    self.assertEqual(new["header"], old["header"])
                    self.assertEqual(new["body"][:1], old["body"][:1])
                    self.assertEqual(new["body"][1:], before["records"][source_index]["body"][1:])

    def test_category_override_retains_weather_menu_control(self):
        original = difficulty_fixture()
        settings = resolve(DEFAULT | {"preset": "easiest", "difficulty_categories": {"Weather": "menu"}})
        revised = difficulty_categories(difficulty_settings(original, settings))
        source = difficulty_categories(original)
        self.assertEqual(revised[8], source[8])
        self.assertNotEqual(revised[0], source[0])

    def test_all_profiles_receive_missing_resources_without_altering_rewards(self):
        resource_ids = {name: bytes([n + 1]) * 16 for n, name in enumerate(RESOURCES)}
        unknown = b"x" * 16
        rows = []
        for i in range(17):
            header = PROFILE_ANCHOR if i == 0 else b"\1\1Fixture" + str(i).encode() + b"\0" + bytes([i]) * 16
            rows.append(header + struct.pack("<I", 2) + resource_ids["Wood"] + struct.pack("<I", i)
                        + unknown + struct.pack("<I", 70) + b"\1Display\0\0")
        original = b"unrelated prefix" + struct.pack("<I", 17) + b"".join(rows) + b"untouched rewards and scenario data"
        settings = resolve(DEFAULT | {"preset": "easiest"})
        revised = starting_supplies(original, {name: guid.hex() for name, guid in resource_ids.items()},
                                    settings["starting_resources_bonus"])
        before, after = starting_profiles(original), starting_profiles(revised)
        self.assertEqual(len(after), 17)
        self.assertEqual(original[:before[0]["start"]], revised[:after[0]["start"]])
        self.assertEqual(original[before[-1]["end"]:], revised[after[-1]["end"]:])
        for old, new in zip(before, after):
            self.assertEqual(original[old["start"]:old["header_end"]], revised[new["start"]:new["header_end"]])
            self.assertEqual(original[old["vector_end"]:old["end"]], revised[new["vector_end"]:new["end"]])
            items = dict(new["items"])
            self.assertEqual(items[unknown], 70)
            for name, bonus in settings["starting_resources_bonus"].items():
                self.assertEqual(items[resource_ids[name]], dict(old["items"]).get(resource_ids[name], 0) + bonus)


if __name__ == "__main__":
    unittest.main()
