# Difficulty and starting supplies

Close Frostpunk before applying changes. Double-click **Edit configuration.cmd**
to open the saved JSON in Notepad, save it, then run **Apply configuration.cmd**.
Apply rebuilds from verified originals and checks all six archives. It does not
stack bonuses on a previous installation.

The saved file is
`%LOCALAPPDATA%\FrostpunkNewIndustry\<game-folder-id>\config.json`.
**Check installation.cmd** prints the exact path and installed preset. Settings
survive updates and uninstall/reinstall. Invalid settings are rejected before
game archives change; status and uninstall work even if the JSON has a typo.

## Presets

A public first installation uses `standard`. These are **additions to the original
starting profile**, before native difficulty adjustments. All 17 native profiles
are covered, including the six story scenarios, Endless variants and auxiliary
profiles. Missing resource entries are added. Scripted rewards are unchanged.

| Preset | Native difficulty effects | Wood | Steel | Coal | Raw food | Rations | Cores |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| easiest | Easy | +200 | +150 | +400 | +150 | +100 | +5 |
| easy | Easy | +150 | +100 | +300 | +100 | +75 | +3 |
| standard | In-game menu | +100 | +75 | +200 | +80 | +50 | +2 |
| hard | Hard | +80 | +50 | +150 | +60 | +30 | +1 |
| extreme | Extreme / native Frostbite | +60 | +40 | +100 | +45 | +20 | +1 |

Every preset supplies more than version 3.10. Bonuses change **new cities**;
they do not add stock to an existing save. Native difficulty adjustments and
resource storage rules still apply, so these are not guaranteed final inventory
totals. Scripted restrictions and weather events remain in force.

Minimal configuration:

```json
{
  "schema_version": 1,
  "preset": "easiest"
}
```

Changing `preset` replaces its defaults. Individual overrides below take
precedence; remove an override to inherit that value from the selected preset.

## Individual settings

| Key | Values | Behavior |
| --- | --- | --- |
| `schema_version` | `1` | Required format version. |
| `preset` | `easiest`, `easy`, `standard`, `hard`, `extreme` | Starting-supply and native difficulty defaults. |
| `native_difficulty` | `menu`, `easy`, `medium`, `hard`, `extreme` | `menu` retains the native table. Other values substitute that native level's effects into all four choices. |
| `difficulty_categories` | Object of category names and difficulty values | Overrides individual categories; `menu` restores that category's original choices. |
| `starting_resources_bonus` | Object of resource names and integer bonuses, 0–50000 | Replaces individual preset bonuses. |
| `workshop_output_multiplier` | Number, 0.25–5; default `1.5625` | Multiplies the native one-to-four-Workshop curve, preserving diminishing returns. |
| `perk_research_duration_multiplier` | Number, 0.1–4; default `0.5` | Multiplies authored durations for mod-added research only. Production recipes and native durations are separate. |

Resource names: `Wood`, `Steel`, `Coal`, `Raw Food`, `Food Rations`, `Steam Cores`.

Difficulty categories, using the game's exact names:

```text
Health                       Nutrition
Economy_Coal                 Economy_Others
Technology                   Economy_Food
Economy_StartingResources     Hope
Weather                      Discontent
Frostland_Resources           Generator
Telegraph Station
```

For easiest settings, weather chosen through the menu, a wood bonus of 250,
and the current research pacing:

```json
{
  "schema_version": 1,
  "preset": "easiest",
  "difficulty_categories": {"Weather": "menu"},
  "starting_resources_bonus": {"Wood": 250},
  "workshop_output_multiplier": 1.5625,
  "perk_research_duration_multiplier": 0.5
}
```

Native difficulty values reuse existing game effects. Category names, level
identifiers and default-selection flags are preserved. The in-game menu labels
stay the same even when a config forces Easy effects for that category. Use
`"native_difficulty": "menu"` to let the menu decide everything. Start a new city
to use a different starting difficulty; this tool does not rewrite saves.

## Command line

From the extracted Windows release folder:

```powershell
.\Frostpunk-New-Industry.exe install --preset easiest --pause
.\Frostpunk-New-Industry.exe config --edit
.\Frostpunk-New-Industry.exe apply --pause
.\Frostpunk-New-Industry.exe apply --preset standard --pause
.\Frostpunk-New-Industry.exe apply --config "D:\Mods\my-settings.json" --pause
```

`--preset` resets individual overrides. `--config` imports a JSON document into
the persistent settings file after successful apply/install. Both accept
`--game "D:\SteamLibrary\steamapps\common\Frostpunk"` for a custom game folder.
An ordinary install reuses saved settings. Updates require uninstalling the
previous version first; the config and original backups remain.
