"""Use native icons for the actual subject instead of a modifier's donor icon."""

RESOURCE_ICONS = {'Steam Cores':(1,0), 'Steel':(0,0), 'Wood':(1,1), 'Coal':(2,1),
                  'Raw Food':(0,2), 'Wooden Materials':(3,1), 'Steam Tools':(3,2), 'Steel Plates':(2,2)}

THEMES = (
    ('Drawing Boards','Generator Efficiency Upgrade II','Steam Hub','Automaton Integration','Heaters','Factory','Gathering Post Insulation'),
    ('Faster Gathering','Sawmill','Steelworks','Coal Thumper','Wall Drill','Charcoal Kiln','Factory'),
    ('Medical Post Upgrade','Hothouse','Hunters\' Gear','Cookhouse Insulation','House','Medical Post Upgrade','Medical Post Upgrade'),
    ('Lighter Scout Sleds','Outpost Depot','Resource Depot Upgrade','Resource Depot Upgrade','Resource Depot Upgrade','Steelworks','Factory'),
    ('Factory','Steelworks','Charcoal Kiln','Hothouse','Cookhouse Insulation','Steelworks','Factory'),
)
AUTUMN_THEMES = (
    ('Drawing Boards','Gathering Post Insulation','Heaters','Safety Improvements','Heaters','Profiles Manufacture','Heaters'),
    ('Faster Gathering','Sawmill','Machine Shop','Charcoal Kiln','Profiles Manufacture','Factory','Factory'),
    ('Medical Post Upgrade','Fishing Harbour','Cookhouse Insulation','Cookhouse Insulation','House','Medical Post Upgrade','Medical Post Upgrade'),
    ('Foragers','Docks','Resource Depot Upgrade','Resource Depot Upgrade','Resource Depot Upgrade','Reloading Station','Factory'),
    ('Profiles Manufacture','Machine Shop','Charcoal Kiln','Foundry','Cookhouse Insulation','Fishing Harbour','Factory'),
)


def curate_icons(specs, native):
    for t in specs:
        if 'route' not in t:continue
        tab, lane = t['route']
        title = (AUTUMN_THEMES if t.get('scenario_scope')=='autumn' else THEMES)[tab][lane]
        # Native scenario variants can use slightly different English titles;
        # all of these donors are in the verified, unchanged native entry table.
        candidates = [r for r in native if r['title'] == title]
        if not candidates:
            candidates = [r for r in native if title.lower() in r['title'].lower()]
        assert candidates, ('Missing semantic icon donor', title)
        donor = candidates[0]
        t['icon_override'] = list(donor['layout'][:2])
        t['icon_source'] = donor['name']
        t['icon_subject'] = title
