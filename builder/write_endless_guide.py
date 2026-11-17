"""Generate the player-facing reconstruction budgets from the shipped catalog."""


def write(root,catalog):
    mode=catalog['endless']
    def budget(items):return ', '.join(f'{value:,} {name}' for name,value in items.items())
    lines=['# Reconstruction — experimental Endless mode','',
        'Version '+catalog['version']+' adds Reconstruction as a fourth native Endless mode definition. Choose **Endless → Reconstruction**, then select a map and difficulty. It inherits Endurance maps, weather and native options. Begin a new city: existing saves do not automatically become Reconstruction cities.','',
        '**Beta limitation:** the game loader accepts the new configurations. The mode-selection UI, real deliveries and an in-game save/load cycle have not been verified: computer control was stopped before that check. Offline simulation is not a substitute for that live verification.','',
        'Reconstruction combines permanent megaprojects, recurring relief routes and optional timed contracts. Existing research, recipes, laws and ordinary scenario modes retain their previous definitions. The original three Endless mode records remain byte-identical.','',
        '## Dispatching supplies','',
        'The quest tracker lists an active delivery and its exact budget. Every six game hours the mode checks stockpiles. Once a delivery is affordable, a native dilemma offers **Dispatch supplies** or **Later**. Dispatch rechecks every resource and spends the listed amounts once; Later keeps the supplies and pauses further prompts for twelve hours. An obsolete prompt can always be dismissed.','',
        'Budgets consume existing resources. There is no delivery button on a Factory, no new building footprint and no additional production selector. Reconstructed infrastructure is represented by permanent project rewards, rather than a physical world-map settlement.','',
        '## Twelve permanent megaprojects','',
        'The first project opens after twelve game hours. Projects have no deadline. Each completed project raises Hope greatly, grants its permanent infrastructure benefit, and opens the next project after twelve hours. Workplace bonuses apply equally to human and automaton crews. Storage factors compound.','',
        '| Project | Supply budget | Permanent result |','| --- | --- | --- |']
    for stage in mode['tracks'][0]['stages']:
        lines.append(f"| {stage['title']} | {budget(stage['cost'])} | {stage['description']} |")
    lines+=['','## Three relief routes','',
        'The Foundry route opens two days after founding the city; Gardens after five days; Salvage after eight. Each route has five levels, with budget and cargo multipliers **1×, 3×, 8×, 20× and 50×**. The opening delivery has no deadline. Later deliveries allow eight days.','',
        'Dispatch upgrades a route until level V. Return cargo arrives one day after dispatch, subject to normal storage limits. A new delivery opens seven days after dispatch. At level V deliveries continue indefinitely. A missed deadline raises Discontent slightly and retries the same level after seven days; completed infrastructure is retained.','',
        '| Route | Level I dispatch | Level I return cargo |','| --- | --- | --- |']
    for track in mode['tracks'][1:4]:
        first=track['stages'][0]
        lines.append(f"| {first['title'].split(' - Route')[0]} | {budget(first['cost'])} | {budget(first['cargo'])} |")
    lines+=['','## Optional industrial contracts','',
        'Contracts begin three days after founding the city. Accept an offer to begin its three-day deadline, or pass without penalty. Passing or missing an accepted contract rotates the offer at the same grade; success advances a grade. The next offer arrives seven days later. Missing an accepted deadline raises Discontent slightly.','',
        'Six grades scale these three commission patterns by **1×, 3×, 8×, 20×, 50× and 100×**. Grade VI rotates indefinitely. A successful contract raises Hope greatly and delivers its return cargo after one day. These are stockpile-and-dispatch challenges; they do not track newly produced units separately.','',
        '| Grade I commission | Dispatch | Return cargo |','| --- | --- | --- |']
    for stage in mode['tracks'][4]['stages'][:3]:
        lines.append(f"| {stage['title'].split(' - Grade')[0]} | {budget(stage['cost'])} | {budget(stage['cargo'])} |")
    lines+=['','## Persistence and compatibility','',
        'The mode uses native global city variables, timed effects, custom quests and dilemmas. No executable, DLL, Lua runtime hook, ability component or save-file patch is installed. The new scenario parameter defaults to Disabled; only the Reconstruction mode selects Enabled. Project rewards are scoped to the Reconstruction city.','',
        'Native mechanisms are intended to retain city progress through saves. A real save/load cycle remains unverified in this beta. Do not uninstall the mod and expect a Reconstruction save to retain its custom content. Back up important saves before changing versions.','',
        'All difficulty presets retain the mode flag. Starting resources and research pacing use the existing persistent configuration. The public preset is standard; this owner’s installation retains easiest. New text is provided in English in all thirteen language tables.','',
        '## Validation and authoring tools','',
        'The builder includes bounded binary readers, lossless mode/parameter editors, native scenario writers, an independent decoder and a deterministic scenario audit harness. Native fixtures pin complete choice vectors, conditional-effect boundaries, affordability checks, resource debit fields and quest progress effects. Unsupported layouts fail the build.','',
        '`python builder/validate_endless.py` reads the actual compiled payloads. It checks 121 events, 80 dilemmas and 60 objective definitions (including alternating retry states), all 60 budgets, repeated and stale payment rejection, story-mode isolation, timer-cycle safety, a model checkpoint, a 200-day simulation and 897 text references across thirteen language tables. The model is not the game engine.','',
        '`builder/startup_check.ps1` performs a bounded loader check and captures the log plus JSON diagnostics, including the first serialization errors. It now requires all thirteen relevant configurations to load. Logs, owned source data, backups and saves remain outside Git.','']
    (root/'docs/reconstruction.md').write_text('\n'.join(lines),encoding='utf-8')
