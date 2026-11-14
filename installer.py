"""Install New Industry using verified originals and persistent archive backups."""
import argparse
from contextlib import contextmanager
import gzip
import hashlib
import json
import logging
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib

from patch_format import apply_patch
from configuration import DEFAULT, PRESETS, configure_entry, fingerprint, resolve


ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
ENTRY = struct.Struct("<IQQQB")
ARCHIVES = ("common.dat", "common.idx", "templates.dat", "templates.idx", "localizations.dat", "localizations.idx")


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def game_running():
    if os.name != "nt":
        return False
    result = subprocess.run(["tasklist", "/FI", "IMAGENAME eq Frostpunk.exe", "/FO", "CSV", "/NH"],
                            capture_output=True, text=True, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
    return '"frostpunk.exe"' in result.stdout.lower()


def write_json(path, value):
    pending = path.with_suffix(".pending")
    pending.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    pending.replace(path)


def find_game():
    candidates = []
    if os.name == "nt":
        import winreg
        for hive, key, value in (
            (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", "SteamPath"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath"),
        ):
            try:
                with winreg.OpenKey(hive, key) as handle:
                    steam = Path(winreg.QueryValueEx(handle, value)[0])
                candidates.append(steam / "steamapps/common/Frostpunk")
                libraries = steam / "steamapps/libraryfolders.vdf"
                if libraries.exists():
                    import re
                    for location in re.findall(r'"path"\s+"([^"]+)"', libraries.read_text(encoding="utf-8")):
                        candidates.append(Path(location.replace("\\\\", "\\")) / "steamapps/common/Frostpunk")
            except OSError:
                continue
    candidates.append(Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Steam/steamapps/common/Frostpunk")
    for candidate in candidates:
        if (candidate / "Frostpunk.exe").is_file():
            return candidate.resolve()
    location = input("Paste the Frostpunk game folder shown by Steam > Manage > Browse local files: ").strip().strip('"')
    return Path(location).expanduser().resolve()


@contextmanager
def exclusive_lock(folder):
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / "installer.lock").open("a+b") as stream:
        stream.write(b"0")
        stream.flush()
        stream.seek(0)
        if os.name == "nt":
            import msvcrt
            try:
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as error:
                raise RuntimeError("Another New Industry installer is running") from error
        try:
            yield
        finally:
            if os.name == "nt":
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)


class Installer:
    def __init__(self, game, state, manifest, package=ROOT, document=None):
        self.game = Path(game).resolve()
        self.state = Path(state).resolve()
        self.manifest = manifest
        self.package = Path(package)
        self.backup = self.state / "backup"
        self.receipt = self.state / "installed.json"
        self.journal = self.state / "operation.json"
        self.config_path = self.state / "config.json"
        self.document = document
        self.originals = {base + extension: digest for base, archive in manifest["archives"].items()
                          for extension, digest in archive["original_files"].items()}
        if set(self.originals) != set(ARCHIVES):
            raise ValueError("Manifest must describe exactly the six Frostpunk archives")

    def verify(self, folder, expected):
        for name, digest in expected.items():
            if Path(name).name != name or name not in ARCHIVES:
                raise ValueError("Invalid archive name")
            if sha(Path(folder) / name) != digest:
                raise RuntimeError(f"{name} does not match the expected build. Use an unmodified supported Steam installation.")

    def installed(self):
        return json.loads(self.receipt.read_text(encoding="utf-8")) if self.receipt.exists() else None

    def configuration(self):
        if "configuration" not in self.manifest:
            return None
        path = self.config_path if self.config_path.exists() else self.package / "mod/config.json"
        document = self.document if self.document is not None else json.loads(path.read_text(encoding="utf-8-sig"))
        settings = resolve(document)
        return {"document": document, "effective": settings, "sha256": fingerprint(settings)}

    def stage(self, source, destination, configuration=None):
        configuration = self.configuration() if configuration is None else configuration
        if configuration:
            logging.info("Staging preset %s configuration %s", configuration["effective"]["preset"], configuration["sha256"])
        self.verify(source, self.originals)
        destination = Path(destination)
        destination.mkdir(parents=True, exist_ok=True)
        for base, archive in self.manifest["archives"].items():
            index = bytearray((Path(source) / (base + ".idx")).read_bytes())
            count, = struct.unpack_from("<Q", index, 3)
            if index[:3] != b"\0\2\1" or len(index) != 11 + count * ENTRY.size:
                raise ValueError(f"Invalid {base} archive index")
            positions = {ENTRY.unpack_from(index, position)[0]: position for position in range(11, len(index), ENTRY.size)}
            shutil.copyfile(Path(source) / (base + ".dat"), destination / (base + ".dat"))
            with (Path(source) / (base + ".dat")).open("rb") as reader, (destination / (base + ".dat")).open("ab") as writer:
                for patch in archive["entries"]:
                    position = positions[patch["hash"]]
                    identifier, stored, size, offset, packed = ENTRY.unpack_from(index, position)
                    reader.seek(offset)
                    original = reader.read(stored)
                    if packed and original.startswith(b"\x1f\x8b"):
                        original = zlib.decompressobj(31).decompress(original)
                    if len(original) != size or hashlib.sha256(original).hexdigest() != patch["original_sha256"]:
                        raise ValueError(f"Original entry failed verification: {patch['name']}")
                    payload = self.package / "mod/patches" / patch["patch"]
                    if payload.parent.resolve() != (self.package / "mod/patches").resolve():
                        raise ValueError("Invalid patch path")
                    if sha(payload) != patch["patch_sha256"]:
                        raise ValueError(f"Patch is damaged: {patch['name']}")
                    revised = apply_patch(original, payload.read_bytes())
                    if len(revised) != patch["size"] or hashlib.sha256(revised).hexdigest() != patch["new_sha256"]:
                        raise ValueError(f"Reconstructed entry failed verification: {patch['name']}")
                    if configuration:
                        revised = configure_entry(patch["name"], original, revised, self.manifest["configuration"],
                                                  configuration["effective"])
                    logging.info("Staged %s bytes=%s sha256=%s", patch["name"], len(revised), hashlib.sha256(revised).hexdigest())
                    compressed = gzip.compress(revised, compresslevel=9, mtime=0)[:-8]
                    ENTRY.pack_into(index, position, identifier, len(compressed), len(revised), writer.tell(), 1)
                    writer.write(compressed)
            (destination / (base + ".idx")).write_bytes(index)
        return {name: sha(destination / name) for name in ARCHIVES}

    def replace(self, source, expected, rollback):
        if game_running():
            raise RuntimeError("Close Frostpunk before changing its archives")
        changed = []
        pending = []
        try:
            for name in ARCHIVES:
                temporary = self.game / (name + ".new-industry-pending")
                pending.append(temporary)
                shutil.copyfile(Path(source) / name, temporary)
                if sha(temporary) != expected[name]:
                    raise ValueError(f"Copy verification failed: {name}")
                temporary.replace(self.game / name)
                changed.append(name)
            self.verify(self.game, expected)
        except BaseException:
            for name in changed:
                shutil.copyfile(Path(rollback) / name, self.game / name)
            raise
        finally:
            for path in pending:
                path.unlink(missing_ok=True)

    def recover(self):
        if not self.journal.exists():
            return
        if game_running():
            raise RuntimeError("Close Frostpunk to finish the interrupted installation")
        plan = json.loads(self.journal.read_text(encoding="utf-8"))
        current = {name: sha(self.game / name) for name in ARCHIVES}
        for name, digest in current.items():
            if digest not in (plan["before"][name], plan["target"][name]):
                raise RuntimeError(f"{name} changed outside the interrupted installer. Restore using Steam's file verification.")
        if current == plan["target"] and plan["action"] == "install":
            if "configuration" in plan["receipt"]:
                write_json(self.config_path, plan["receipt"]["configuration"]["document"])
            write_json(self.receipt, plan["receipt"])
        else:
            self.verify(self.backup, self.originals)
            with tempfile.TemporaryDirectory(prefix="recovery-", dir=self.state) as temporary:
                for name in ARCHIVES:
                    shutil.copyfile(self.game / name, Path(temporary) / name)
                self.replace(self.backup, self.originals, temporary)
            self.receipt.unlink(missing_ok=True)
        self.journal.unlink()
        print("Recovered the interrupted archive operation.")

    def install(self):
        if game_running():
            raise RuntimeError("Save your game and close Frostpunk before installing")
        configuration = self.configuration()  # Validate before backup, staging, or archive writes.
        receipt = self.installed()
        if receipt:
            self.verify(self.game, receipt["files"])
            if receipt["version"] == self.manifest["version"]:
                if receipt.get("configuration", {}).get("sha256") == (configuration or {}).get("sha256"):
                    if configuration:
                        write_json(self.config_path, configuration["document"])
                    print("This version and configuration are already installed and verified.")
                    return
                return self.apply()
            raise RuntimeError("Uninstall the previous New Industry version before installing this update")
        self.verify(self.game, self.originals)
        self.backup.mkdir(parents=True, exist_ok=True)
        for name, digest in self.originals.items():
            saved = self.backup / name
            if not saved.exists():
                shutil.copyfile(self.game / name, saved)
            if sha(saved) != digest:
                raise ValueError(f"Original backup failed verification: {name}")
        with tempfile.TemporaryDirectory(prefix="staging-", dir=self.state) as temporary:
            print("Building and verifying the modded archives...")
            expected = self.stage(self.backup, temporary, configuration)
            receipt = {"game": str(self.game), "version": self.manifest["version"], "files": expected}
            if configuration:
                receipt["configuration"] = configuration
            write_json(self.journal, {"action": "install", "before": self.originals, "target": expected, "receipt": receipt})
            self.replace(temporary, expected, self.backup)
            try:
                if configuration:
                    write_json(self.config_path, configuration["document"])
                write_json(self.receipt, receipt)
            except BaseException:
                self.replace(self.backup, self.originals, temporary)
                raise
            self.journal.unlink()
        print(f"Installed New Industry {self.manifest['version']}. Start Frostpunk normally through Steam.")
        print(f"Original archive backups: {self.backup}")
        self.print_configuration(receipt)

    def apply(self):
        if game_running():
            raise RuntimeError("Save your game and close Frostpunk before applying configuration")
        configuration = self.configuration()
        receipt = self.installed()
        if not receipt or receipt["version"] != self.manifest["version"]:
            raise RuntimeError("Install this release before applying its configuration")
        if configuration is None:
            raise RuntimeError("This release has no configurable settings")
        self.verify(self.game, receipt["files"])
        self.verify(self.backup, self.originals)
        with tempfile.TemporaryDirectory(prefix="configure-", dir=self.state) as temporary:
            folder = Path(temporary)
            staged, rollback = folder / "staged", folder / "rollback"
            expected = self.stage(self.backup, staged, configuration)
            rollback.mkdir()
            for name in ARCHIVES:
                shutil.copyfile(self.game / name, rollback / name)
            updated = {"game": str(self.game), "version": self.manifest["version"],
                       "files": expected, "configuration": configuration}
            write_json(self.journal, {"action": "install", "before": receipt["files"],
                                      "target": expected, "receipt": updated})
            self.replace(staged, expected, rollback)
            try:
                write_json(self.config_path, configuration["document"])
                write_json(self.receipt, updated)
            except BaseException:
                self.replace(rollback, receipt["files"], staged)
                raise
            self.journal.unlink()
        print("Applied and verified the configuration. Start Frostpunk normally through Steam.")
        self.print_configuration(updated)

    def print_configuration(self, receipt):
        if "configuration" in receipt:
            settings = receipt["configuration"]["effective"]
            print(f"Installed preset: {settings['preset']}; native difficulty: {settings['native_difficulty']}")
            print(f"Configuration: {self.config_path}")

    def config(self, edit=False):
        if not self.config_path.exists() or self.document is not None:
            configuration = self.configuration()
            if configuration is None:
                raise RuntimeError("This release has no configurable settings")
            write_json(self.config_path, configuration["document"])
        print(f"Edit {self.config_path}, then close Frostpunk and run Apply configuration.cmd.")
        if edit:
            if os.name != "nt":
                raise RuntimeError("Automatic configuration editing requires Windows; edit the printed path instead")
            subprocess.Popen(["notepad.exe", str(self.config_path)])

    def uninstall(self):
        if game_running():
            raise RuntimeError("Save your game and close Frostpunk before uninstalling")
        receipt = self.installed()
        if receipt is None:
            self.verify(self.game, self.originals)
            print("Original Frostpunk archives are already installed.")
            return
        self.verify(self.game, receipt["files"])
        self.verify(self.backup, self.originals)
        with tempfile.TemporaryDirectory(prefix="rollback-", dir=self.state) as temporary:
            for name in ARCHIVES:
                shutil.copyfile(self.game / name, Path(temporary) / name)
            write_json(self.journal, {"action": "uninstall", "before": receipt["files"], "target": self.originals})
            self.replace(self.backup, self.originals, temporary)
            try:
                self.receipt.unlink()
            except BaseException:
                self.replace(temporary, receipt["files"], self.backup)
                raise
            self.journal.unlink()
        print("Restored and verified all six original Frostpunk archives.")

    def status(self):
        receipt = self.installed()
        self.verify(self.game, receipt["files"] if receipt else self.originals)
        print(f"New Industry {receipt['version']} is installed and verified." if receipt else "Original Frostpunk archives are installed and verified.")
        if receipt:
            self.print_configuration(receipt)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", nargs="?", default="install", choices=("install", "uninstall", "status", "apply", "config"))
    parser.add_argument("--game", type=Path, help="Frostpunk folder, if Steam discovery does not find it")
    parser.add_argument("--pause", action="store_true", help="Keep the console open after completion")
    parser.add_argument("--config", type=Path, help="Import a JSON configuration and retain it for later updates")
    parser.add_argument("--preset", choices=tuple(PRESETS), help="Select a preset, resetting individual overrides")
    parser.add_argument("--edit", action="store_true", help="Open the saved configuration in Notepad (config action)")
    args = parser.parse_args()
    if args.config and args.preset:
        parser.error("Choose --config or --preset")
    if (args.config or args.preset) and args.action not in ("install", "apply", "config"):
        parser.error("Configuration options require install, apply, or config")
    if args.edit and args.action != "config":
        parser.error("--edit requires the config action")
    result = 0
    try:
        game = args.game.expanduser().resolve() if args.game else find_game()
        identity = hashlib.sha256(os.path.normcase(str(game)).encode()).hexdigest()[:16]
        state = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / ".local/share"))) / "FrostpunkNewIndustry" / identity
        with exclusive_lock(state):
            logging.basicConfig(filename=state / "installer.log", level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
            manifest = json.loads((ROOT / "mod/manifest.json").read_text(encoding="utf-8"))
            print(f"Frostpunk New Industry {manifest['version']}\nGame folder: {game}")
            logging.info("%s %s %s", args.action, manifest["version"], game)
            document = (json.loads(args.config.read_text(encoding="utf-8-sig")) if args.config else
                        DEFAULT | {"preset": args.preset} if args.preset else None)
            installer = Installer(game, state, manifest, document=document)
            installer.recover()
            if args.action == "config":
                installer.config(edit=args.edit)
            else:
                getattr(installer, args.action)()
            logging.info("Completed %s", args.action)
    except Exception as error:
        logging.exception("Installer failed")
        print(f"ERROR: {error}", file=sys.stderr)
        result = 1
    if args.pause or (getattr(sys, "frozen", False) and len(sys.argv) == 1):
        input("Press Enter to close...")
    return result


if __name__ == "__main__":
    raise SystemExit(main())
