# Frostpunk New Industry

A progression overhaul for the original **Frostpunk**, built around renewable Steam Cores, expanded research, alternate station recipes, and new city strategies.

**Current release — 3.10.0 beta.** The public installer is tested with Windows Steam Frostpunk 1.6.2. It checks the original archive hashes before making changes.

[Download the Windows installer ZIP](https://github.com/HamzahAlrawi/frostpunk-new-industry/releases/download/v3.10.0/Frostpunk-New-Industry-3.10.0-Windows.zip) · [Research catalog](docs/research.md) · [Changes in 3.10](docs/releases/3.10.0.md) · [Report an issue](https://github.com/HamzahAlrawi/frostpunk-new-industry/issues)

## Features

- **Renewable Steam Cores.** Research Factory fabrication and its improved production recipes.
- **256 active research definitions across supported modes.** Engineering, Industry, City Life, and Logistics join the native tabs. Scenario research lists select the upgrades that fit each mode. Added research is checked for duplicate effect packages, icon collisions, and crossing or obstructed prerequisite lines.
- **Faster progression.** All mod-added perks have half their authored base research duration. Workshop base research output is 25% higher than version 3.9, or 56.25% above vanilla, with normal multiple-Workshop scaling. Research before Drawing Boards and additional starting supplies ease the opening.
- **Stronger workplaces.** The permanent workplace-efficiency research bonuses grant at least 75% per upgrade where applicable.
- **Alternate production.** Fuelled Stockpots, coal-heated and fermentation Hothouses, retort and rapid-coking kiln batches, baited fishing, dockside ration production, alternate generator-component recipes, and Warehouse salvage.
- **New city strategies.** Safer Radical Treatment, cold protection, wider heat zones, faster construction, linked production-chain improvements, and large storm reserves. Added team-capacity perks have been removed; vanilla team research remains.
- **Better timing.** Opening-game tools arrive earlier and cost less; late research supports sustained production, civic services in storms, and stronger generator stress management. A 1920-pixel-wide or larger display is recommended for the expanded tab bar.
- **Core-saving building research.** Modular Hothouses, extraction machinery, and the restored Last Autumn Reloading Station discount.
- **Specialist city development.** Core-free Infirmaries, limb-sparing Radical Treatment, human and automaton industrial specialisations, compact or large reserve warehouses, and optional overdrive/fuel trade-offs.
- **Core-powered production chains.** Consume renewable cores in Kilns for bulk coal or in Hothouses for burst food production. Alternate fuel, cooking and fishing recipes offer different material and throughput trade-offs. Selectors are checked to stay within four simultaneous options.
- **Reclamation and component reuse.** Make cores in batches of three, reclaim cores into steel, recover wood and steel together at the Army Warehouse, and reuse generator components across The Last Autumn's three fabrication stations. Specialist heating research offers coal-free medical and industrial Heaters, or compact grids that trade heat radius for fuel savings.

Research is included for A New Home, The Arks, The Refugees, The Fall of Winterhome, The Last Autumn, On The Edge, and applicable Endless modes. DLC features require the corresponding DLC. New-game supply bonuses apply when starting a new city.

## Install

1. Save and close Frostpunk.
2. Download the **Windows installer ZIP** from the release page and extract it.
3. Double-click **Install.cmd** and approve the Windows administrator prompt.
4. The installer finds Steam libraries, checks the game build, creates backups, and applies the patches. If discovery fails, paste the game folder shown by Steam's **Manage → Browse local files**.
5. Start Frostpunk normally through Steam. Open a Workshop's technology tree to find the research.

The release ZIP includes a standalone executable. Python is optional when using that download. GitHub's automatically generated **Source code** ZIP requires Python 3.9 or newer to run the installer scripts.

For a custom game folder, run this from the extracted release folder.

```powershell
.\Frostpunk-New-Industry.exe install --game "D:\SteamLibrary\steamapps\common\Frostpunk" --pause
```

The installer requires original supported archives. It refuses incompatible builds and files altered by another archive mod. A Steam file verification restores the stock files when needed. Keep your existing saves backed up when trying a beta overhaul.

## Uninstall or update

Close Frostpunk and double-click **Uninstall.cmd**. It verifies the installed files and restores the original archives. **Check installation.cmd** checks the current state.

Backups and installer logs live under `%LOCALAPPDATA%\FrostpunkNewIndustry\`, in a separate folder for each game installation. The installer changes six game archive files. Save files are outside its installation targets.

Uninstall the previous version before installing an update. If an archive operation is interrupted, the next installer run checks its operation journal and recovers the known files.

## Testing status

- The copy/insert patches reconstruct the same entries as the local 3.10.0 build.
- Installer tests cover installation, restoration, repeated installation, damaged patches, external modifications, interrupted operations, and rollback after a failed replacement.
- Research tests cover scenario membership, earlier unlocks, unique effect packages, icon/prerequisite-line geometry, and recipe-selector limits. The local binary validator also checks actual serialized recipe prices, outputs, requirements, attachments and effect vectors, and preserves native technology and modifier records.
- The mod's configuration and startup checks passed. Earlier builds completed full campaigns. The newest gameplay effects still need broader campaign testing, so this release is marked **beta**.

When reporting a problem, include the mod version, scenario, game version, and the installer error or crash description. Installer logs are saved locally in the backup folder's parent directory.

## Build from source

The mod ships as copy/insert instructions. Original game archives, extracted localization files, and game assets are supplied from an owned local installation during the build.

Use Python 3.11 or newer for the builder. From this repository's root, run the following with a stock compatible game folder.

```powershell
python builder/prepare_sources.py --game "C:\Program Files (x86)\Steam\steamapps\common\Frostpunk"
python builder/build_mod.py
python builder/validate_build.py
python builder/package_mod.py --originals "C:\Program Files (x86)\Steam\steamapps\common\Frostpunk"
python builder/write_catalog.py
python -m unittest discover -s tests -v
```

Extracted inputs stay in the ignored `builder/cache/` directory. Intermediate native payloads stay in the ignored `build/` directory. Public patches and the research catalog are written to `mod/`.

For a full archive round-trip test, run `python builder/check_distribution.py --originals "D:\Frostpunk-original-backup"`. It installs into an isolated copy under `build/distribution-qa/`, verifies every patched entry, and restores the exact originals. The supplied archive folder is read-only input.

To build the standalone Windows installer, create a virtual environment and install `requirements-build.txt`, then run the following.

```powershell
python -m PyInstaller --onefile --uac-admin --name Frostpunk-New-Industry --add-data "mod;mod" installer.py
```

The executable is written to `dist/`. The GitHub workflow runs installer tests on Windows using synthetic fixtures.

For a bounded local startup check, close Frostpunk and run
`powershell -ExecutionPolicy Bypass -File builder/startup_check.ps1 -Game "D:\SteamLibrary\steamapps\common\Frostpunk"`.
It launches and closes only its own test process, captures a fresh log, requires
the six main game configurations to finish loading, and rejects serialization
or decompression errors. Logs and a JSON result are written under
`build/startup-check/`. It does not load a save or test campaign balance.

## License and credits

The installer, build tools, and original mod changes are MIT licensed. Frostpunk and its original content belong to 11 bit studios. See [NOTICE.md](NOTICE.md) for tooling credits and third-party license information.
