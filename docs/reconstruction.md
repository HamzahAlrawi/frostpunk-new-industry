# Reconstruction — experimental Endless mode

Version 3.15.0 adds Reconstruction as a fourth native Endless mode definition. Choose **Endless → Reconstruction**, then select a map and difficulty. It inherits Endurance maps, weather and native options. Begin a new city: existing saves do not automatically become Reconstruction cities.

**Beta limitation:** the game loader accepts the new configurations. The mode-selection UI, real deliveries and an in-game save/load cycle have not been verified: computer control was stopped before that check. Offline simulation is not a substitute for that live verification.

Reconstruction combines permanent megaprojects, recurring relief routes and optional timed contracts. Existing research, recipes, laws and ordinary scenario modes retain their previous definitions. The original three Endless mode records remain byte-identical.

## Dispatching supplies

The quest tracker lists an active delivery and its exact budget. Every six game hours the mode checks stockpiles. Once a delivery is affordable, a native dilemma offers **Dispatch supplies** or **Later**. Dispatch rechecks every resource and spends the listed amounts once; Later keeps the supplies and pauses further prompts for twelve hours. An obsolete prompt can always be dismissed.

Budgets consume existing resources. There is no delivery button on a Factory, no new building footprint and no additional production selector. Reconstructed infrastructure is represented by permanent project rewards, rather than a physical world-map settlement.

## Twelve permanent megaprojects

The first project opens after twelve game hours. Projects have no deadline. Each completed project raises Hope greatly, grants its permanent infrastructure benefit, and opens the next project after twelve hours. Workplace bonuses apply equally to human and automaton crews. Storage factors compound.

| Project | Supply budget | Permanent result |
| --- | --- | --- |
| Surveyors Camp | 300 Wood, 150 Steel, 500 Coal, 100 Food Rations | Open a permanent surveying camp. Establish the reconstruction ledger and earn a large Hope increase. |
| Frostland Storehouses | 900 Wood, 600 Steel, 1,500 Coal, 400 Food Rations | Build a regional reserve network. Both Resource Depot sizes gain 100% capacity for every stored resource. |
| Engineers Exchange | 1,800 Wood, 1,400 Steel, 4,000 Coal, 900 Food Rations, 8 Steam Cores | Found a technical exchange. Workshops gain 75% workplace efficiency. |
| Refuge Clinics | 3,500 Wood, 2,500 Steel, 8,000 Coal, 1,800 Food Rations, 20 Steam Cores | Equip the relief clinics. Medical Posts, Infirmaries and Houses of Healing gain 100% workplace efficiency. |
| The Great Foundry | 5,500 Wood, 5,000 Steel, 16,000 Coal, 2,500 Food Rations, 40 Steam Cores | Connect the city to a new foundry complex. Steelworks and Factories gain 75% workplace efficiency. |
| Sheltered Roads | 9,000 Wood, 8,000 Steel, 25,000 Coal, 5,000 Food Rations, 70 Steam Cores | Enclose the reconstruction supply roads. Every building with insulation gains one insulation level. |
| Seed Conservatory | 15,000 Wood, 12,000 Steel, 40,000 Coal, 9,000 Food Rations, 110 Steam Cores | Found a seed reserve. Hothouses, Industrial Hothouses and Cookhouses gain 75% workplace efficiency. |
| Continental Reserve | 22,000 Wood, 18,000 Steel, 65,000 Coal, 14,000 Food Rations, 180 Steam Cores | Open deep supply vaults. Both Resource Depot sizes gain a further 100% capacity. |
| Relay Citadels | 32,000 Wood, 28,000 Steel, 95,000 Coal, 20,000 Food Rations, 280 Steam Cores | Equip permanent relay settlements. Coal mines, sawmills and wall drills gain 75% workplace efficiency. |
| Polar Sanctuary | 45,000 Wood, 42,000 Steel, 140,000 Coal, 30,000 Food Rations, 450 Steam Cores | Complete an inhabited refuge beyond the city. Cold-related illness is reduced by 25%. |
| The Northern Railway | 60,000 Wood, 70,000 Steel, 200,000 Coal, 45,000 Food Rations, 750 Steam Cores | Lay the final railway across the Frostland. All heat zones gain 25% radius. |
| A World Rebuilt | 80,000 Wood, 100,000 Steel, 250,000 Coal, 60,000 Food Rations, 1,200 Steam Cores | Complete the reconstruction programme. All workplaces gain 75% efficiency. Relief routes and contracts continue indefinitely. |

## Three relief routes

The Foundry route opens two days after founding the city; Gardens after five days; Salvage after eight. Each route has five levels, with budget and cargo multipliers **1×, 3×, 8×, 20× and 50×**. The opening delivery has no deadline. Later deliveries allow eight days.

Dispatch upgrades a route until level V. Return cargo arrives one day after dispatch, subject to normal storage limits. A new delivery opens seven days after dispatch. At level V deliveries continue indefinitely. A missed deadline raises Discontent slightly and retries the same level after seven days; completed infrastructure is retained.

| Route | Level I dispatch | Level I return cargo |
| --- | --- | --- |
| Foundry Settlement | 1,600 Coal, 200 Food Rations | 600 Steel |
| Sheltered Gardens | 500 Wood, 800 Coal, 200 Steel | 1,000 Food Rations |
| Salvage Anchorage | 400 Steel, 250 Food Rations | 1,200 Wood, 2 Steam Cores |

## Optional industrial contracts

Contracts begin three days after founding the city. Accept an offer to begin its three-day deadline, or pass without penalty. Passing or missing an accepted contract rotates the offer at the same grade; success advances a grade. The next offer arrives seven days later. Missing an accepted deadline raises Discontent slightly.

Six grades scale these three commission patterns by **1×, 3×, 8×, 20×, 50× and 100×**. Grade VI rotates indefinitely. A successful contract raises Hope greatly and delivers its return cargo after one day. These are stockpile-and-dispatch challenges; they do not track newly produced units separately.

| Grade I commission | Dispatch | Return cargo |
| --- | --- | --- |
| Industrial Reserve | 3,000 Coal, 700 Steel, 2 Steam Cores | 900 Wood, 450 Food Rations |
| Emergency Provisioning | 1,200 Food Rations, 600 Wood, 1,200 Coal | 1,000 Steel, 4 Steam Cores |
| Engineering Expedition | 1,000 Wood, 1,000 Steel, 4 Steam Cores | 6,000 Coal, 600 Food Rations |

## Persistence and compatibility

The mode uses native global city variables, timed effects, custom quests and dilemmas. No executable, DLL, Lua runtime hook, ability component or save-file patch is installed. The new scenario parameter defaults to Disabled; only the Reconstruction mode selects Enabled. Project rewards are scoped to the Reconstruction city.

Native mechanisms are intended to retain city progress through saves. A real save/load cycle remains unverified in this beta. Do not uninstall the mod and expect a Reconstruction save to retain its custom content. Back up important saves before changing versions.

All difficulty presets retain the mode flag. Starting resources and research pacing use the existing persistent configuration. The public preset is standard; this owner’s installation retains easiest. New text is provided in English in all thirteen language tables.

## Validation and authoring tools

The builder includes bounded binary readers, lossless mode/parameter editors, native scenario writers, an independent decoder and a deterministic scenario audit harness. Native fixtures pin complete choice vectors, conditional-effect boundaries, affordability checks, resource debit fields and quest progress effects. Unsupported layouts fail the build.

`python builder/validate_endless.py` reads the actual compiled payloads. It checks 121 events, 80 dilemmas and 60 objective definitions (including alternating retry states), all 60 budgets, repeated and stale payment rejection, story-mode isolation, timer-cycle safety, a model checkpoint, a 200-day simulation and 897 text references across thirteen language tables. The model is not the game engine.

`builder/startup_check.ps1` performs a bounded loader check and captures the log plus JSON diagnostics, including the first serialization errors. It now requires all thirteen relevant configurations to load. Logs, owned source data, backups and saves remain outside Git.
