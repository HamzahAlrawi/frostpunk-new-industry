"""Check a Frostpunk console log for Switchback Basin map and prefab loading."""
import argparse
import re
from pathlib import Path
from time import monotonic, sleep

from faultline_buildings import DEFINITIONS
from winter_road_maps import CITY, WORLD


DEFAULT_LOG = Path(r"C:\Program Files (x86)\Steam\steamapps\common\Frostpunk\ConsoleOutput.html")
SUCCESS = "resource loaded successfully ("
LOADING = "loading template resource: "
ERRORS = ("class factory cannot create", "serializationflag_versiontolerant", "inflate() failed",
          "missing building template for", "unable to find building template for entry")
PREFABS = {"templates/" + spec["path"].removesuffix(".binarytemplate") for spec in DEFINITIONS.values()}


def inspect(log):
    city_loaded = world_loaded = False
    found = set()
    loading = error = None
    for number, line in enumerate(log, 1):
        line = line.lower()
        if f"[{CITY.lower()}] scene loading time:" in line:
            city_loaded = True
            world_loaded = False
        if f"[{WORLD.lower()}] scene loading time:" in line:
            world_loaded = True
        if LOADING in line:
            loading = re.sub(r"<[^>]*>", "", line.split(LOADING, 1)[1]).strip()
        if SUCCESS in line:
            path = line.split(SUCCESS, 1)[1].split(")", 1)[0]
            if path in PREFABS:
                found.add(path)
        if failure := next((message for message in ERRORS if message in line), None):
            error = f"line {number}: {failure}"
            break
    checks = [(city_loaded, "Switchback Basin city load"), (world_loaded, "Switchback Frostland load"),
              (found == PREFABS, f"Faultline building loads ({len(found)}/{len(PREFABS)})")]
    for passed, label in checks:
        print(f"{'PASS' if passed else 'MISSING'}  {label}")
    if error:
        print(error)
        if loading:
            print(f"Last requested template: {loading}")
    return all(passed for passed, _ in checks) and error is None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path, nargs="?", default=DEFAULT_LOG)
    parser.add_argument("--wait", type=int, default=0, metavar="SECONDS",
                        help="wait for an active game to release its console log")
    args = parser.parse_args()
    expires = monotonic() + max(0, args.wait)
    while True:
        try:
            with args.log.open(encoding="utf-8", errors="replace") as log:
                return 0 if inspect(log) else 1
        except PermissionError:
            if monotonic() >= expires:
                parser.exit(2, "The console is locked by Frostpunk. Check the log after the game closes.\n")
            sleep(1)
        except OSError as error:
            parser.exit(2, f"Cannot read console log: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
