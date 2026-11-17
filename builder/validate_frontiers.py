"""Exercise the serialized branching campaigns with explicit simulated player acts."""
from tools.scenario_model import World


P='NI/Frontiers/'


def audit(records,meta,resource_ids):
    events=records['gameevents'];dialogs={r['guid']:r for r in records['dilemmas']};quests={r['guid']:r for r in records['quests']}
    front=meta['frontiers'];stock={guid:1_000_000_000 for guid in resource_ids.values()}
    source={q['guid']:q for q in front['missions']}
    assert len(source)==29 and len(front['campaigns'])==3
    for guid,row in source.items():
        actual=quests[guid]['objectives'];assert len(actual)==len(row['goals'])
        for goal,before in zip(actual,row['goals']):
            assert goal['kind']==before['kind']
            assert abs(goal['quantity']-before.get('quantity',1))<0.000001 if isinstance(goal['quantity'],(int,float)) else True
            if 'target' in before:assert goal['target']==before['target']
    # A full warehouse cannot complete building, research or production goals.
    def create(cid):return World({meta['enabled'],meta['campaign_values'][str(cid)]},events,dialogs,quests,stock)
    idle=create(1);idle.start()
    idle.run(10)
    assert idle.variables[P+'phase']==1 and not idle.completed,'Stockpiles skipped actual city work'
    results=[]
    for campaign in (1,2,3):
      for path in (1,2):
        w=create(campaign);w.start();w.step()
        assert w.variables[P+'campaign']==campaign
        assert front['selector'] not in w.open,'Separate mode opened the collection chooser'
        assert len(w.active)==1 and w.variables[P+'phase']==1,'First objective was delayed'
        while w.variables[P+'phase']<6:
            for guid in list(w.open):
                name=dialogs[guid]['name']
                w.click(guid,path-1 if ' Branch/' in name else 2 if ' Incident/' in name else 0)
            assert w.active,'Chapter stalled without an active objective or doctrine choice'
            for guid in list(w.active):
                for goal in quests[guid]['objectives']:
                    kind=goal['kind'];q=goal['quantity']
                    if kind=='build':w.buildings[goal['target'][0]]=max(w.buildings.get(goal['target'][0],0),q)
                    elif kind=='research':w.researched.add(goal['target'])
                    elif kind=='produce':
                        assert not w.goal_met(guid,goal),'Existing stock counted as new production'
                        w.produced[goal['target'][0]]=w.produced.get(goal['target'][0],0)+q
                    elif kind=='automate':w.automation=min(1,q+0.05)
                    elif kind!='checks':raise AssertionError(kind)
            w.update_quests()
        assert w.variables[P+'path']==path
        for guid in list(w.active):
            for goal in quests[guid]['objectives']:
                if goal['kind']=='automate':w.automation=goal['quantity']+0.05
        # Generator-off and inadequate reserves must pause all operating checks.
        w.generator=False;w.run(1)
        assert w.variables[P+'checks']==0
        w.generator=True;coal=resource_ids['Coal'];w.stock[coal]=0;w.run(1)
        assert w.variables[P+'checks']==0
        w.stock=dict(stock)
        restored=w.checkpoint();restored.start()
        w.run(30,False);restored.run(30,False)
        assert w.__dict__==restored.__dict__,'Model checkpoint replayed setup or changed active objectives'
        assert w.variables[P+'won']==1 and len([q for q in w.completed if q in source])==6
        assert not set(w.active)&source.keys() and w.variables[P+'phase']==99
        assert not any(front['bonuses']['front'+str(i)] in w.modifiers for i in range(1,5)),'A late Whiteout timer reapplied after victory'
        proposal=next(g for g in w.open if ' SecondArc/' in dialogs[g]['name'])
        quiet=w.checkpoint();quiet.click(proposal,2)
        branch=front['campaigns'][campaign-1]['branches'][path-1]
        if branch.get('upkeep'):
            assert not quiet.variables[P+'funded'] and front['bonuses'][branch['bonus']] not in quiet.modifiers
        assert w.click(proposal,0)
        w.execute(dialogs[proposal]['choices'][0]['effects'])
        for phase in (7,8):
            target=next(q for q in source.values() if q['campaign']==campaign and q['phase']==phase)
            assert target['guid'] in w.active
            for goal in target['goals']:
                k=goal['kind'];q=goal.get('quantity',1)
                if k=='build':w.buildings[goal['target'][0]]=q
                elif k=='research':w.researched.add(goal['target'])
                elif k=='produce':w.produced[goal['target'][0]]+=q
                elif k=='automate':w.automation=q+0.05
            w.update_quests()
        target=next(q for q in source.values() if q['campaign']==campaign and q['phase']==9)
        w.variables[P+'active']=0
        w.stock[coal]=0;w.run(1,False)
        assert w.variables[P+'checks']==0
        w.stock=dict(stock);w.run(4,False)
        shifts=next(g['quantity'] for g in target['goals'] if g['kind']=='checks')
        for resource,cost in target['payment'].items():
            assert stock[resource_ids[resource]]-w.stock[resource_ids[resource]]==cost*shifts
        assert w.variables[P+'phase']==100 and front['bonuses'][target['reward']] in w.modifiers
        results.append(dict(campaign=campaign,path=path,completed_chapters=9,won=True))
    # Each funded doctrine pauses on a missing input and recovers only with a buffer.
    maintenance=0
    for story in front['campaigns']:
      for path,branch in enumerate(story['branches'],1):
        if not branch.get('upkeep'):continue
        w=World(meta['enabled'],events,dialogs,quests,stock)
        w.variables.update({P+'version':1,P+'campaign':story['id'],P+'path':path,P+'phase':99,P+'active':1,P+'funded':1})
        bonus=front['bonuses'][branch['bonus']];w.modifiers.add(bonus)
        missing=resource_ids[next(iter(branch['upkeep']))];w.stock[missing]=0
        w.run(branch['period'],False);assert w.variables[P+'funded']==0 and bonus not in w.modifiers
        w.stock=dict(stock);w.step();assert w.variables[P+'funded']==1 and bonus in w.modifiers
        # Spending the last complete payment still buys that interval. Only
        # the following unfunded interval is allowed to suspend the package.
        w=World(meta['enabled'],events,dialogs,quests,stock)
        w.variables.update({P+'version':1,P+'campaign':story['id'],P+'path':path,P+'phase':99,P+'active':1,P+'funded':1})
        w.modifiers.add(bonus)
        for name,cost in branch['upkeep'].items():w.stock[resource_ids[name]]=cost
        w.run(branch['period'],False)
        assert w.variables[P+'funded']==1 and bonus in w.modifiers
        w.run(branch['period'],False)
        assert w.variables[P+'funded']==0 and bonus not in w.modifiers
        maintenance+=1
    from validate_frontier_events import audit as audit_events
    incident_result=audit_events(records,meta,resource_ids)
    assert maintenance==3
    return dict(branch_paths=results,automatic_missions=len(source),maintenance_cases=maintenance,
                stockpiles_cannot_skip_city_work=True,generator_and_reserve_checks=True,**incident_result)
