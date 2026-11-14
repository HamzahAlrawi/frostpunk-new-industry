from contextlib import redirect_stdout
import gzip
import hashlib
import io
import json
from pathlib import Path
import shutil
import struct
import tempfile
import unittest
from unittest.mock import patch

from builder.make_delta import make_delta
from installer import ARCHIVES, ENTRY, Installer, exclusive_lock, sha, write_json
from patch_format import apply_patch
from configuration import DEFAULT, DIFFICULTY
from test_configuration import difficulty_fixture


class InstallerTests(unittest.TestCase):
    def setUp(self):
        test_root = Path(__file__).resolve().parents[1] / "build/test-runs"
        test_root.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=test_root)
        self.root = Path(self.temporary.name)
        self.game = self.root / "Steam Library with spaces" / "Frostpunk"
        self.state = self.root / "state"
        self.package = self.root / "package"
        self.game.mkdir(parents=True)
        self.state.mkdir()
        (self.package / "mod/patches").mkdir(parents=True)
        self.manifest = {"version": "3.7.0", "archives": {}}
        for number, base in enumerate(("common", "templates", "localizations")):
            before = (base.encode() + b"\0original fixture ") * 40
            after = before[:31] + b"new research fixture" + before[31:] + b"\0additional fixture"
            stored = gzip.compress(before, mtime=0)[:-8]
            (self.game / (base + ".dat")).write_bytes(stored)
            (self.game / (base + ".idx")).write_bytes(b"\0\2\1" + struct.pack("<Q", 1) + ENTRY.pack(number, len(stored), len(before), 0, 1))
            delta, _ = make_delta(before, after)
            name = base + ".nid"
            (self.package / "mod/patches" / name).write_bytes(delta)
            self.manifest["archives"][base] = {
                "original_files": {extension: sha(self.game / (base + extension)) for extension in (".dat", ".idx")},
                "entries": [{"name": base, "hash": number, "patch": name, "patch_sha256": hashlib.sha256(delta).hexdigest(),
                             "original_sha256": hashlib.sha256(before).hexdigest(), "new_sha256": hashlib.sha256(after).hexdigest(), "size": len(after)}],
            }
        self.installer = Installer(self.game, self.state, self.manifest, self.package)
        self.originals = {name: (self.game / name).read_bytes() for name in ARCHIVES}
        self.running = patch("installer.game_running", return_value=False)
        self.running.start()
        self.output = redirect_stdout(io.StringIO())
        self.output.__enter__()

    def tearDown(self):
        self.output.__exit__(None, None, None)
        self.running.stop()
        self.temporary.cleanup()

    def assert_originals(self):
        self.assertEqual(self.originals, {name: (self.game / name).read_bytes() for name in ARCHIVES})

    def test_install_repeat_uninstall(self):
        self.installer.install()
        receipt = self.installer.installed()
        self.assertEqual(receipt["version"], "3.7.0")
        self.installer.verify(self.game, receipt["files"])
        self.installer.install()
        self.installer.uninstall()
        self.assert_originals()
        self.assertFalse(self.installer.receipt.exists())

    def enable_configuration(self):
        original = difficulty_fixture()
        stored = gzip.compress(original, mtime=0)[:-8]
        (self.game / "common.dat").write_bytes(stored)
        (self.game / "common.idx").write_bytes(b"\0\2\1" + struct.pack("<Q", 1) + ENTRY.pack(0, len(stored), len(original), 0, 1))
        delta, _ = make_delta(original, original)
        (self.package / "mod/patches/common.nid").write_bytes(delta)
        self.manifest["archives"]["common"] = {
            "original_files": {extension: sha(self.game / ("common" + extension)) for extension in (".dat", ".idx")},
            "entries": [{"name": DIFFICULTY, "hash": 0, "patch": "common.nid", "patch_sha256": hashlib.sha256(delta).hexdigest(),
                         "original_sha256": hashlib.sha256(original).hexdigest(), "new_sha256": hashlib.sha256(original).hexdigest(), "size": len(original)}],
        }
        self.manifest["configuration"] = {"schema_version": 1}
        write_json(self.package / "mod/config.json", DEFAULT)
        self.installer = Installer(self.game, self.state, self.manifest, self.package)
        self.originals = {name: (self.game / name).read_bytes() for name in ARCHIVES}

    def test_configuration_applies_and_persists_without_double_patching(self):
        self.enable_configuration()
        self.installer.document = DEFAULT | {"preset": "easiest"}
        self.installer.install()
        easiest = self.installer.installed()
        self.assertEqual(easiest["configuration"]["effective"]["preset"], "easiest")
        self.installer.apply()
        self.assertEqual(self.installer.installed()["files"], easiest["files"])
        self.installer.document = DEFAULT
        self.installer.apply()
        self.assertNotEqual(self.installer.installed()["files"], easiest["files"])
        self.installer.document = DEFAULT | {"preset": "easiest"}
        self.installer.install()  # Same-version install routes changed settings through apply.
        self.assertEqual(self.installer.installed()["files"], easiest["files"])
        self.installer.uninstall()
        self.assert_originals()
        replacement = Installer(self.game, self.state, self.manifest, self.package)
        replacement.install()
        self.assertEqual(replacement.installed()["configuration"]["effective"]["preset"], "easiest")
        replacement.uninstall()

    def test_invalid_configuration_preserves_archives_and_allows_uninstall(self):
        self.enable_configuration()
        self.installer.install()
        files = {name: sha(self.game / name) for name in ARCHIVES}
        self.installer.config_path.write_text('{"preset":"oops"}')
        with self.assertRaises(ValueError):
            self.installer.apply()
        self.assertEqual({name: sha(self.game / name) for name in ARCHIVES}, files)
        self.installer.status()  # Neither status nor restoration requires a valid config.
        self.installer.uninstall()
        self.assert_originals()

    def test_failed_configuration_copy_restores_previous_install(self):
        self.enable_configuration()
        self.installer.install()
        previous = self.installer.installed()
        self.installer.document = DEFAULT | {"preset": "easiest"}
        original_replace = Path.replace

        def fail(path, target):
            if Path(target) == self.game / "common.idx":
                raise OSError("simulated configuration copy failure")
            return original_replace(path, target)

        with patch.object(Path, "replace", fail), self.assertRaises(OSError):
            self.installer.apply()
        self.installer.verify(self.game, previous["files"])
        self.assertEqual(self.installer.installed(), previous)
        self.installer.recover()
        self.assert_originals()

    def test_game_running_prevents_configuration_application(self):
        self.enable_configuration()
        self.installer.install()
        with patch("installer.game_running", return_value=True), self.assertRaises(RuntimeError):
            self.installer.apply()

    def test_completed_configuration_journal_recovers_settings_and_receipt(self):
        self.enable_configuration()
        self.installer.install()
        previous = self.installer.installed()
        self.installer.document = DEFAULT | {"preset": "easiest"}
        configuration = self.installer.configuration()
        staged = self.root / "configured"
        files = self.installer.stage(self.installer.backup, staged, configuration)
        receipt = previous | {"files": files, "configuration": configuration}
        write_json(self.installer.journal, {"action": "install", "before": previous["files"], "target": files, "receipt": receipt})
        for name in ARCHIVES:
            shutil.copyfile(staged / name, self.game / name)
        self.installer.config_path.write_text("interrupted metadata write")
        self.installer.recover()
        self.assertEqual(self.installer.installed(), receipt)
        self.assertEqual(json.loads(self.installer.config_path.read_text()), configuration["document"])
        self.installer.verify(self.game, files)
        self.installer.uninstall()
        self.assert_originals()

    def test_modified_game_is_rejected(self):
        (self.game / "common.dat").write_bytes(b"another mod")
        with self.assertRaises(RuntimeError):
            self.installer.install()
        self.assertEqual((self.game / "common.dat").read_bytes(), b"another mod")

    def test_damaged_patch_preserves_game(self):
        (self.package / "mod/patches/common.nid").write_bytes(b"damaged")
        with self.assertRaises(ValueError):
            self.installer.install()
        self.assert_originals()

    def test_replacement_failure_rolls_back(self):
        original_replace = Path.replace

        def fail_index(path, target):
            if Path(target) == self.game / "common.idx":
                raise OSError("simulated interrupted copy")
            return original_replace(path, target)

        with patch.object(Path, "replace", fail_index), self.assertRaises(OSError):
            self.installer.install()
        self.assert_originals()
        self.installer.recover()
        self.assertFalse(self.installer.journal.exists())

    def test_crash_during_install_recovers_pristine_files(self):
        self.installer.backup.mkdir()
        for name in ARCHIVES:
            shutil.copyfile(self.game / name, self.installer.backup / name)
        staged = self.root / "staged"
        expected = self.installer.stage(self.installer.backup, staged)
        write_json(self.installer.journal, {"action": "install", "before": self.installer.originals, "target": expected})
        shutil.copyfile(staged / "common.dat", self.game / "common.dat")
        self.installer.recover()
        self.assert_originals()

    def test_modified_install_is_not_overwritten_on_uninstall(self):
        self.installer.install()
        (self.game / "templates.idx").write_bytes(b"external change")
        with self.assertRaises(RuntimeError):
            self.installer.uninstall()
        self.assertEqual((self.game / "templates.idx").read_bytes(), b"external change")

    def test_game_running_prevents_install(self):
        with patch("installer.game_running", return_value=True), self.assertRaises(RuntimeError):
            self.installer.install()
        self.assert_originals()

    def test_patch_roundtrip_and_wrong_original(self):
        original = bytes(range(256)) * 200
        revised = original[1300:5000] + b"changed" + original + b"new ending"
        delta, _ = make_delta(original, revised)
        self.assertEqual(apply_patch(original, delta), revised)
        with self.assertRaises(ValueError):
            apply_patch(b"wrong original", delta)

    def test_completed_install_journal_recovers_receipt(self):
        self.installer.backup.mkdir()
        for name in ARCHIVES:
            shutil.copyfile(self.game / name, self.installer.backup / name)
        staged = self.root / "staged"
        expected = self.installer.stage(self.installer.backup, staged)
        receipt = {"game": str(self.game), "version": "3.7.0", "files": expected}
        write_json(self.installer.journal, {"action": "install", "before": self.installer.originals, "target": expected, "receipt": receipt})
        for name in ARCHIVES:
            shutil.copyfile(staged / name, self.game / name)
        self.installer.recover()
        self.assertEqual(self.installer.installed(), receipt)
        self.installer.uninstall()
        self.assert_originals()

    @unittest.skipUnless(__import__("os").name == "nt", "Windows file locking")
    def test_concurrent_installer_is_blocked(self):
        with exclusive_lock(self.state):
            with self.assertRaises(RuntimeError):
                with exclusive_lock(self.state):
                    self.fail("Concurrent lock unexpectedly succeeded")


if __name__ == "__main__":
    unittest.main()
