"""Generate player rules and incident deadlines from the shipped mode data."""


def write(root,catalog):
    mode=catalog['endless'];front=mode['frontiers']
    lines=['# Restoration, Whiteout and Machine Age','',
        'Choose **Endless → Restoration**, **Endless → Whiteout** or **Endless → Machine Age**, then select a map and difficulty. These are three separate mode entries beside Endurance, The Builders and Serenity. There is no campaign chooser inside a new city. The modes use native Endless maps and Endurance weather.','',
        '**Experimental beta:** the final mode data and UI geometry pass offline validation. The final installed build also passes native loader startup. Six-card rendering, live missions and events, and real save/load remain unverified.','',
        '## Founding chapters and continuing play','',
        'Each mode has six founding chapters. Construct districts, research the named technologies, manufacture new automatons, assign machines to workplaces and maintain operating reserves. Chapters complete automatically; there is no mandatory dispatch button. Existing stockpiles do not substitute for new automaton production.','',
        'After chapter two, choose one of two city doctrines. Three doctrines charge automatic upkeep. Missing an input pauses the whole bonus; holding two payments of every input resumes it. A last complete payment buys its interval before a following unfunded interval suspends the package.','',
        'Final operating checks occur every six game hours while the Generator is on and the listed reserves remain in storage. Checks pause when a condition fails. They retain supplies, while normal consumption and doctrine upkeep continue.','',
        'The mode continues after its founding chapters. Incidents and upkeep stay active by default. The completion event also offers quiet continuation: no new incidents or doctrine bills, while existing response/repair deadlines still apply.','']
    for story in front['campaigns']:
        title=next(m['title'] for m in mode['modes'] if m['value']==mode['campaign_values'][str(story['id'])])
        lines+=['## '+title,'',story['description'],'',
                '| Doctrine | Effects and upkeep |','| --- | --- |']
        for branch in story['branches']:lines.append(f"| {branch['title']} | {branch['description']} |")
        lines+=['','| Chapter | Path | Automatically tracked objectives |','| --- | --- | --- |']
        for mission in (m for m in front['missions'] if m['campaign']==story['id']):
            path=story['branches'][mission['path']-1]['title'] if mission['path'] else 'Both'
            goals='<br>'.join(g['text']+(' — '+g['description'] if g['kind']=='checks' else '') for g in mission['goals'])
            lines.append(f"| {mission['phase']}. {mission['title']} | {path} | {goals} |")
        lines+=['','### Incidents and deadlines','',
            'The response countdown appears in the quest tracker. Ignoring it raises Discontent moderately and imposes a two-day disruption: recovery shifts in Restoration, heat restrictions in Whiteout, or a Factory shutdown in Machine Age. Repair programmes have a separate countdown beginning when accepted.','',
            '| Incident | Response window | Responses and consequences |','| --- | --- | --- |']
        for event in (e for e in front['incidents'] if e['campaign']==story['id']):
            days=event['response_days'];window=f'{days*24:g} hours' if days<2 else f'{days:g} days'
            responses='<br>'.join('**'+o['title']+':** '+o['description'] for o in event['options'])
            lines.append(f"| {event['title']} | {window} | {responses} |")
        lines.append('')
    lines+=['## Timing and safety rules','',
        'Each mode has six recurring incident families and eighteen responses. The first incident can arrive soon after chapter three; later incidents become eligible two days after resolving the previous one. Unanswered incidents and accepted repair programmes block further incidents, keeping the city from receiving several competing deadlines at once.','',
        'Response windows range from 36 game hours to five days. Factory repair programmes allow four days for one new automaton, six days for two, and eight days for the masterwork. The native base automaton cycle is four working hours; validation checks a safety margin even with the programme and human-doctrine efficiency penalties. Machines built for a programme remain yours.','',
        'A repair programme temporarily reduces Factory efficiency by 25%. Success removes that reduction and grants the stated reward. Failure removes the programme reduction, raises Discontent and applies the mode’s two-day disruption. Cargo arrives one day after resolution.','',
        'Every incident has a free final alternative. It also dismisses an expired prompt without changing the city. Choice effects recheck state and affordability internally, protecting against cached or repeated clicks. A refreshed temporary effect supersedes its previous expiry, so an old timer cannot remove the current benefit.','',
        '## The Whiteout front','',
        'Four fronts arrive 2, 5, 9 and 13 days after the city begins. Citywide insulation declines to -1, -2, -3 and -4. Each front replaces its predecessor, leaving one current source tooltip. Final operating checks wait for the fourth front. Completing the founding chapters clears the front; Whiteout’s own incidents continue.','',
        '## Compatibility and layout','',
        'Start a new city to use a separate mode. Existing version 3.15 supply-dispatch cities retain their projects, deliveries and earned rewards; they receive an update notice. [Legacy reference](reconstruction.md).','',
        'Native story scenarios, laws, research, recipes and original Endless mode records retain their gameplay definitions. The menu now supplies six explicit slots, compact descriptions and normal text proportions. Original orientation/alignment enums are preserved. All nine research tabs, including Production, use a narrower bar layout. Live rendering remains unverified.','',
        'The persistent difficulty config is retained. Public first installs use standard; the owner’s installation retains easiest. New content and compact menu summaries are supplied in English in all thirteen language tables.','',
        '## Validation','',
        f"The owned-data audit decodes {mode['events']} added events, {mode['dilemmas']} dilemmas and {mode['quests']} quests, including legacy content. It checks all six founding paths, twenty automatic chapter definitions, 54 incident responses, 18 ignored-response expiries, five repair successes and failures, all three funded doctrines, cached callbacks, late timers, mode isolation and research availability.",'',
        '66 public tests pass. Existing research, law, tooltip, all-five-preset and archive checks pass. Geometry bounds include card ornaments and preserve native layout enum values. The final installed build loaded thirteen required configurations and the edited Endless menu template without serialization errors. Startup did not open a save or start a city.','']
    (root/'docs/frontiers.md').write_text('\n'.join(lines),encoding='utf-8')
    (root/'docs/reconstruction.md').write_text('# Legacy Reconstruction cities\n\n'
        'The version 3.15 supply-dispatch mode is retained for existing cities. New cities use the separate '
        '[Restoration, Whiteout and Machine Age modes](frontiers.md).\n\n'
        'The [version 3.15 guide](https://github.com/HamzahAlrawi/frostpunk-new-industry/blob/v3.15.0/docs/reconstruction.md) records the unchanged legacy project budgets and route rules.\n',encoding='utf-8')
