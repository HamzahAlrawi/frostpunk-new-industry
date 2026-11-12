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
           'Tier 0 is available before Drawing Boards. Listed hours are base research hours; city research modifiers and Workshop scaling still apply. Prerequisites in another tab remain mandatory and are listed by name in the tooltip.','',
           'Research is arranged in Engineering, Industry, City Life, and Logistics alongside the native tabs. A 1920-pixel-wide or larger display is recommended for the expanded tab bar.','']
    for title,category in catalog['research_tabs']:
        lines += ['## '+title,'','| Upgrade | Tier | Research cost | Base hours | Effect and prerequisites | Modes |',
                  '| --- | --- | --- | --- | --- | --- |']
        techs=sorted((t for t in catalog['technologies'] if t['guid'] in active and t['category']==category),
                     key=lambda t:(t['tier'],t['title']))
        for t in techs:
            cost=', '.join(f'{amount} {resource.lower()}' for resource,amount in t['cost'].items())
            effect=t['description'].replace('\n\n','<br><br>').replace('\n','<br>').replace('|','\\|')
            modes=', '.join(MODES[name] for name,ids in membership.items() if t['guid'] in ids)
            lines.append(f"| {t['title']} | {t['tier']} | {cost} | {t['hours']} | {effect} | {modes} |")
        lines.append('')
    (ROOT/'docs/research.md').write_text('\n'.join(lines).rstrip()+'\n',encoding='utf-8')
    print(f'Wrote {len(active)} research entries.')


if __name__=='__main__':
    main()
