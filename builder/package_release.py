"""Create the Windows download from tracked public files and the built executable."""
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile


ROOT = Path(__file__).resolve().parents[1]


def main():
    version = json.loads((ROOT / "mod/manifest.json").read_text())["version"]
    executable = ROOT / "dist/Frostpunk-New-Industry.exe"
    if not executable.is_file():
        raise FileNotFoundError("Build the Windows executable before packaging the release")
    output = ROOT / "dist" / f"Frostpunk-New-Industry-{version}-Windows.zip"
    prefix = f"Frostpunk-New-Industry-{version}/"
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().strip("\0").split("\0")
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in tracked:
            path = ROOT / name
            data = path.read_bytes()
            if path.suffix == ".cmd":
                data = data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
            archive.writestr(prefix + name, data)
        archive.write(executable, prefix + executable.name)
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    (ROOT / "dist/SHA256SUMS.txt").write_text(f"{digest}  {output.name}\n", encoding="utf-8")
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None:
            raise ValueError("Release ZIP failed its integrity check")
    print(f"Built {output.name} ({output.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
