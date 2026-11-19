# Frostpunk New Industry

A progression overhaul for the original **Frostpunk**, built around renewable Steam Cores, expanded research, alternate station recipes, and new city strategies.

**Current release â€” 3.30.0 beta.** The public installer is tested with Windows Steam Frostpunk 1.6.2. It checks the original archive hashes before making changes.

[Download the Windows installer ZIP](https://github.com/HamzahAlrawi/frostpunk-new-industry/releases/download/v3.30.0/Frostpunk-New-Industry-3.30.0-Windows.zip) Â· [Research catalog](docs/research.md) Â· [Civic laws](docs/laws.md) Â· [Building tooltips](docs/tooltips.md) Â· [New Endless modes](docs/frontiers.md) Â· [Faultline player guide](docs/faultline.md) Â· [Configuration](docs/configuration.md) Â· [Changes in 3.30.0](docs/releases/3.30.0.md) Â· [Report an issue](https://github.com/HamzahAlrawi/frostpunk-new-industry/issues)

## Features

- **Three new Endless modes.** Choose Restoration, Whiteout or Machine Age directly from Endless. Each has six automatic founding chapters, two city doctrines and six recurring incident families. Eighteen incidents provide 54 responses, 36-hour-to-five-day response windows and optional four-to-eight-day manufacturing programmes. [Mode rules, objectives and deadlines](docs/frontiers.md).

- **Renewable Steam Cores.** Find Steam Core Fabrication in the **first column of the added Industry tab, tier II**, then select its recipe at a Factory. Further upgrades culminate in three-core batches. The Arks is explicitly checked.
- **216 active research definitions across supported modes.** Engineering, Industry, City Life, Logistics and Production use fixed themed columns beside the native tabs. 47 smaller upgrades are consolidated into larger ones. Added research has at most one visible parent in its own column; hidden native and cross-tab requirements are removed.
- **Four signable Civic Charters.** Research the City Life civic branch, then sign them in the upper branch of **Adaptation**, or **Administration** in The Last Autumn. Native books, scenario unlocks and Order/Faith laws are preserved. Charters improve Hope/Discontent and provide healthcare, civic heating and illness benefits. [Policies and consolidated upgrades](docs/laws.md).
- **12 research-free laws in four choice trees.** Community Care, Workforce, Winter Preparedness and Public Reserves each start with an immediately available root, followed by two mutually exclusive policies. Choose preventive or critical care, human or mechanical specialisation, district heating or food protection, and storm reserves or industrial capital. These trees share the native Adaptation/Administration book without changing its original branches.
- **Six citywide thermal envelopes.** Three additional stages provide expensive late-game insulation, illness protection and larger heat zones.
- **Readable building modifier sources.** Mod-added modifiers have names and descriptions. Six insulation families use one cumulative heat-tooltip source per building; Thermal Envelope grows from +1 to +7 instead of displaying six separate rows. [Tooltip scope](docs/tooltips.md).
- **Faultline.** Watch the original opening film, guide two advance parties into the Basin, then keep their relief routes open through the last whiteout. Nine acts provide 19 plans, three endings and a city replay. Four original building models serve the campaign. The Valve Works and Relief Dispatch have dedicated work orders. [Player guide](docs/faultline.md).
- **Faster progression.** On Standard, mod-added perks take half their authored research time. Base Workshop output is 56.25% above vanilla, with normal multiple-Workshop scaling. Research before Drawing Boards and additional starting supplies ease the opening.
- **Configurable difficulty.** Five presets change research pacing, production rates, eligible upgrade and law bonuses, native difficulty effects, and starting stockpiles. Edit the persistent JSON, then apply it while the game is closed. [Settings and preset values](docs/configuration.md).
- **Stronger workplaces.** The permanent workplace-efficiency research bonuses grant at least 75% per upgrade where applicable.
- **Alternate production.** Fuelled Stockpots, coal-heated and fermentation Hothouses, retort and rapid-coking kiln batches, baited fishing, dockside ration production, alternate generator-component recipes, and Warehouse salvage.
- **New city strategies.** Safer Radical Treatment, cold protection, wider heat zones, faster construction, linked production-chain improvements, and large storm reserves. Added team-capacity perks have been removed; vanilla team research remains.
- **Better timing.** Opening-game tools arrive earlier and cost less; late research supports sustained production, civic services in storms, and stronger generator stress management. The expanded nine-tab bar uses a narrower layout to keep Production inside the frame.
- **Core-saving construction before Drawing Boards.** Tier 0 packages combine Hothouse, extraction and Infirmary core discounts, or Autumn Reloading Station, fabrication and Infirmary discounts.
- **Specialist city development.** Core-free Infirmaries, limb-sparing Radical Treatment, human and automaton industrial specialisations, compact or large reserve warehouses, and optional overdrive/fuel trade-offs.
- **Core-powered production chains.** Consume renewable cores in Kilns for bulk coal or in Hothouses for burst food production. Alternate fuel, cooking and fishing recipes offer different material and throughput trade-offs. Selectors are checked to stay within four simultaneous options.
- **Reclamation and component reuse.** Make cores in batches of three, reclaim cores into steel, recover wood and steel together at the Army Warehouse, and reuse generator components across The Last Autumn's three fabrication stations. Specialist heating research offers coal-free medical and industrial Heaters, or compact grids that trade heat radius for fuel savings.

Research is included for A New Home, The Arks, The Refugees, The Fall of Winterhome, The Last Autumn, On The Edge, and applicable Endless modes. DLC features require the corresponding DLC. New-game supply bonuses apply when starting a new city.

## Install

1. Save and close Frostpunk.
2. Download the **Windows installer ZIP** from the release page and extract it.
3. Double-click **Install.cmd** and approve the Windows administrator prompt.
4. The installer finds Steam libraries, checks the game build, creates backups, and applies the patches. If discovery fails, paste the game folder shown by Steam's **Manage â†’ Browse local files**.
5. Start Frostpunk normally through Steam. Open a Workshop's technology tree to find the research.

The release ZIP includes a standalone executable. Python is optional when using that download. GitHub's automatically generated **Source code** ZIP requires Python 3.9 or newer to run the installer scripts.

For a custom game folder, run this from the extracted release folder.

```powershell
.\Frostpunk-New-Industry.exe install --game "D:\SteamLibrary\steamapps\common\Frostpunk" --pause
```

The installer requires original supported archives. It refuses incompatible builds and files altered by another archive mod. A Steam file verification restores the stock files when needed. Keep your existing saves backed up when trying a beta overhaul.

## Uninstall or update

Close Frostpunk and double-click **Uninstall.cmd**. It verifies the installed files and restores the original archives. **Check installation.cmd** checks the current state.

Backups and installer logs live under `%LOCALAPPDATA%\FrostpunkNewIndustry\`, in a separate folder for each game installation. The installer changes ten game archive files, including the scene and sequence archive pairs for Faultline. Save files are outside its installation targets.

Uninstall the previous version before installing an update. If an archive operation is interrupted, the next installer run checks its operation journal and recovers the known files.

To change difficulty, double-click **Edit configuration.cmd**, save your JSON,
then close Frostpunk and run **Apply configuration.cmd**. Settings persist across
updates. A public first install uses `standard`; `easiest` selects native Easy
effects and the largest supply bonus. Start a new city for new opening supplies
and difficulty. See [all settings and presets](docs/configuration.md).

## Testing status

- The default copy/insert patches reconstruct the local 3.30.0 build. Configured installs verify the baseline first, then apply the selected difficulty, balance and supply settings.
- Installer tests cover installation, restoration, repeated installation, damaged patches, external modifications, interrupted operations, and rollback after a failed replacement.
- Research tests cover scenario membership, earlier unlocks, unique effect packages, icon/prerequisite-line geometry, and recipe-selector limits. The local binary validator also checks actual serialized recipe prices, outputs, requirements, attachments and effect vectors, and preserves native technology and modifier records.
- Automated tests and owned-data audits cover six Endless paths, 54 incident responses, and all 19 Faultline plans and three endings. The distribution check resolves the four Faultline buildings through the native template catalog on an installed archive copy. See the [release notes](docs/releases/3.30.0.md) for validation and the scenario log checker.

When reporting a problem, include the mod version, scenario, game version, and the installer error or crash description. Installer logs are saved locally in the backup folder's parent directory.

## Build from source

The mod ships as copy/insert instructions. Original game archives, extracted localization files, and game assets are supplied from an owned local installation during the build.

Use Python 3.11 or newer for the builder. From this repository's root, run the following with a stock compatible game folder.

```powershell
python builder/prepare_sources.py --game "C:\Program Files (x86)\Steam\steamapps\common\Frostpunk"
python builder/build_mod.py
python builder/validate_build.py
python builder/validate_configuration.py
python builder/validate_civic.py
python builder/validate_tooltips.py
python builder/validate_endless.py
python builder/package_mod.py --originals "C:\Program Files (x86)\Steam\steamapps\common\Frostpunk"
python builder/write_catalog.py
python -m unittest discover -s tests -v
```

Extracted inputs stay in the ignored `builder/cache/` directory. Intermediate native payloads stay in the ignored `build/` directory. Public patches and the research catalog are written to `mod/`.

For a full archive round-trip test, run `python builder/check_distribution.py --originals "D:\Frostpunk-original-backup" --preset easiest`. It installs into an isolated copy under `build/distribution-qa/`, verifies every configured entry, and restores exact originals. Omit `--preset` to test standard settings. The supplied archive folder is read-only input.

To build the standalone Windows installer, create a virtual environment and install `requirements-build.txt`, then run the following.

```powershell
python -m PyInstaller --onefile --uac-admin --name Frostpunk-New-Industry --add-data "mod;mod" installer.py
```

The executable is written to `dist/`. The GitHub workflow runs installer tests on Windows using synthetic fixtures.

For a bounded local startup check, close Frostpunk and run
`powershell -ExecutionPolicy Bypass -File builder/startup_check.ps1 -Game "D:\SteamLibrary\steamapps\common\Frostpunk"`.
It launches and closes only its own test process, captures a fresh log, requires
the thirteen required game configurations (including Endless modes, events, dilemmas and quests) to finish loading, and rejects serialization
or decompression errors. Logs and a JSON result are written under
`build/startup-check/`. It does not load a save or test campaign balance.

## License and credits

The installer, build tools, and original mod changes are MIT licensed. Frostpunk and its original content belong to 11 bit studios. See [NOTICE.md](NOTICE.md) for tooling credits and third-party license information.
