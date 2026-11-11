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
