"""Generate the public research reference from the packaged catalog."""
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODES = {'TechHaven':'The Arks','Winterhome':'Winterhome','Default':'A New Home',
         'Default_Endless_Builders':'Endless Builders','Default_Endless':'Endless',
         'Refugees':'The Refugees','Builders':'The Last Autumn','Reconquest':'On The Edge'}


def main():
    catalog=json.loads((ROOT/'mod/catalog.json').read_text())
    membership=catalog['scenario_additions']
    active={g for ids in membership.values() for g in ids}
    lines=['# Research catalog','',
           f"Version {catalog['version']}: {len(active)} active research definitions across the supported modes. Legacy and retired entries are omitted.",'',
           'Tier 0 is available before Drawing Boards. Listed hours include the default 50% reduction to mod-added research durations. Workshop base research output remains 1.5625 times vanilla. Every non-tier research prerequisite is visible in the same column; no added research depends on a hidden native or cross-tab prerequisite.','',
           'Engineering, Industry, City Life, Logistics and Production use fixed themed columns. Steam Core manufacturing is in the FIRST column of the added Industry tab, beginning with Steam Core Fabrication at tier II. The four charter policies occupy the upper branch of Adaptation, or Administration in The Last Autumn. Native books and their scenario unlock rules are preserved.','']
    for title,category in catalog['research_tabs']:
        lines += ['## '+title,'','| Upgrade | Column | Tier | Research cost | Base hours | Effect and prerequisites | Modes |',
                  '| --- | --- | --- | --- | --- | --- | --- |']
        techs=sorted((t for t in catalog['technologies'] if t['guid'] in active and t['category']==category),
                     key=lambda t:(t['column'],t['tier'],t['title']))
        for t in techs:
            cost=', '.join(f'{amount} {resource.lower()}' for resource,amount in t['cost'].items())
            effect=t['description'].replace('\n\n','<br><br>').replace('\n','<br>').replace('|','\\|')
            modes=', '.join(MODES[name] for name,ids in membership.items() if t['guid'] in ids)
            lines.append(f"| {t['title']} | {1+(t['column']-2)//3} | {t['tier']} | {cost} | {t['hours']} | {effect} | {modes} |")
        lines.append('')
    (ROOT/'docs/research.md').write_text('\n'.join(lines).rstrip()+'\n',encoding='utf-8')
    by_id={t['id']:t for t in catalog['technologies']}
    lines=['# Civic Charters','',
           'Research the four linked charter upgrades in City Life. Open Adaptation in the Book of Laws, or Administration in The Last Autumn. The four charters are spaced across the upper branch, above the native laws; zoom or pan upward if needed. Signing uses the normal law system and an 18-hour cooldown. Morale changes happen once when signed; passive benefits remain.','',
           'All four native books, their original order, their scenario unlock conditions and all 112 native laws are unchanged. Order and Faith remain governed by the normal Purpose unlock rules. The old separate Civic Charters book is hidden compatibility data. The original four charter IDs are retained for signed-law progress. Autumn entries prevent re-signing a policy already granted by version 3.12.','',
           'The Last Autumn receives the native Workers Council Motivation benefit in place of each Hope effect. Discontent effects work normally.','',
           '| Law | Research first | When signed and passive benefit |','| --- | --- | --- |']
    for law in (law for law in catalog['laws'] if not law['id'].startswith('Autumn')):
        lines.append(f"| {law['title']} | {law['research_title']} | {law['description']} |")
    lines+=['','## Consolidated research','','Smaller upgrades below are included in the destination upgrade. They no longer occupy separate research slots. Their old definitions and identifiers remain registered for saves.','',
            '| Previous upgrade | Included in |','| --- | --- |']
    for old,new in sorted(catalog['consolidated_technologies'].items()):
        lines.append(f"| {by_id[old]['title']} | {by_id[new]['title']} |")
    (ROOT/'docs/laws.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(f'Wrote {len(active)} research entries.')


if __name__=='__main__':
    main()
