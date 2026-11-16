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
           'Engineering, Industry, City Life, Logistics and Production use fixed themed columns. Steam Core manufacturing is in the FIRST column of the added Industry tab, beginning with Steam Core Fabrication at tier II. The four researched charter policies and four research-free law trees are in Adaptation, or Administration in The Last Autumn. Native books and their scenario unlock rules are preserved.','']
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
    lines=['# Civic laws','',
           'Version '+catalog['version']+' adds 12 research-free laws arranged in four choice trees, alongside the four existing researched charters. Open Adaptation in the Book of Laws, or Administration in The Last Autumn. Pan or zoom outward to see the new trees around the native branches. No new book replaces a native category.','',
           'The first law in each new tree is available as soon as the scenario allows law signing, without research or any previous law. It has a 12-hour cooldown. Then choose ONE of its two follow-ups, each with a 24-hour cooldown and no research requirement. Signing one permanently excludes its sibling using the native law exclusion-group system. These choices are independent of Order/Faith and the existing charters. Morale changes happen once when signed; passive benefits remain.','',
           'All four native books, their original order, their scenario unlock conditions and all 112 native laws are unchanged. Order and Faith remain governed by the normal Purpose unlock rules. The old separate Civic Charters book is hidden compatibility data. The original four charter IDs are retained for signed-law progress. Autumn entries prevent re-signing a policy already granted by version 3.12.','',
           'The Last Autumn receives the native Workers Council Motivation benefit in place of each Hope effect. Discontent effects work normally. Its versions use camp accommodation, port and fabrication workplaces where appropriate. Native scenario restrictions, building availability and storm shutdowns still apply.','',
           '## Research-free choice trees','',
           'Four roots plus one chosen follow-up per tree allow eight of the 12 new laws to be signed in one city. There are 16 policy definitions per mode including the four older charters. Each child below requires only its own root, and excludes only the other child in that tree.','']
    defaults=[law for law in catalog['laws'] if law.get('default_available') and not law['id'].startswith('Autumn')]
    autumn={law['id'][6:]:law for law in catalog['laws'] if law['id'].startswith('Autumn')}
    for family in dict.fromkeys(law['family'] for law in defaults):
        tree=[law for law in defaults if law['family']==family]
        root=next(law for law in tree if law['branch_root'])
        children=[law for law in tree if not law['branch_root']]
        lines+=['### '+root['family_title'],'','```mermaid','flowchart TD',
                '    root["'+root['title']+'"] --> a["'+children[0]['title']+'"]',
                '    root --> b["'+children[1]['title']+'"]','```','',
                '| Law | Requirement | When signed and permanent benefit |','| --- | --- | --- |']
        for law in tree:
            gate='None; available from the start' if law['branch_root'] else root['title']+'; choose one follow-up'
            lines.append(f"| {law['title']} | {gate} | {law['description']} |")
        differences=[(law,autumn[law['id']]) for law in tree
                     if law['description']!=autumn[law['id']]['description'] or law['title']!=autumn[law['id']]['title']]
        if differences:
            lines+=['','**The Last Autumn:**','']
            for _,alternate in differences:
                lines.append('- **'+alternate['title']+':** '+alternate['description'])
        lines.append('')
    lines+=['## Existing researched charters','',
           'These four policies retain their research gates and 18-hour cooldowns. Research the linked upgrades in City Life, then sign the policies across the upper charter row of the native law book.','',
           '| Law | Research first | When signed and passive benefit |','| --- | --- | --- |']
    for law in (law for law in catalog['laws'] if not law['id'].startswith('Autumn') and not law.get('default_available')):
        lines.append(f"| {law['title']} | {law['research_title']} | {law['description']} |")
    lines+=['','## Consolidated research','','Smaller upgrades below are included in the destination upgrade. They no longer occupy separate research slots. Their old definitions and identifiers remain registered for saves.','',
            '| Previous upgrade | Included in |','| --- | --- |']
    for old,new in sorted(catalog['consolidated_technologies'].items()):
        lines.append(f"| {by_id[old]['title']} | {by_id[new]['title']} |")
    (ROOT/'docs/laws.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(f'Wrote {len(active)} research entries.')


if __name__=='__main__':
    main()
