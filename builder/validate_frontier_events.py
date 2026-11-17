"""Timed decision/work-order expiry, replay safety and mode isolation audit."""
from tools.scenario_model import World

P='NI/Frontiers/'


def audit(records,meta,resource_ids):
    events=records['gameevents'];dialogs={r['guid']:r for r in records['dilemmas']};quests={r['guid']:r for r in records['quests']}
    front=meta['frontiers'];stock={g:1_000_000_000 for g in resource_ids.values()}
    choices=deadlines=repairs=failures=0
    def begin(item):
        cid=item['campaign'];w=World({meta['enabled'],meta['campaign_values'][str(cid)]},events,dialogs,quests,stock)
        w.variables.update({P+'version':1,P+'director_version':2,P+'campaign':cid,P+'phase':99,P+'active':1,P+'alert':0,P+'incident':item['index'],P+'ready':1})
        # Prior manufacturing must never satisfy a newly commissioned repair.
        for work in front['work_orders']:
            for goal in quests[work['guid']]['objectives']:
                for target in goal['target']:w.produced[target]=100
        w.step();assert item['dilemma'] in w.open and item['response_quest'] in w.active
        assert all(dialogs[g]['name'].startswith('NI Frontiers Incident/'+str(cid)+'/') for g in w.open),'Cross-mode incident leaked'
        return w
    for item in front['incidents']:
        assert 1.5<=item['response_days']<=5 and len(item['options'])==3
        assert front['owned_temporary_effects']
        guid=item['dilemma'];row=dialogs[guid]
        assert not item['options'][-1]['cost'] and not item['options'][-1]['repair']
        assert quests[item['response_quest']]['deadline']==item['response_days']
        # Ignore the response; its original deadline resolves it once.
        w=begin(item);w.run(item['response_days']+0.25,False)
        assert w.variables[P+'alert']==0 and w.variables[P+'incident']==(item['index']+1)%6
        assert item['response_quest'] not in w.active
        assert front['bonuses'][item['timeout_bonus']] in w.modifiers
        before=dict(w.stock);w.click(guid,2);assert w.stock==before,'Expired fallback charged or applied a response'
        deadlines+=1
        quiet=begin(item);quiet.variables[P+'active']=0
        quiet.run(item['response_days']+0.25,False)
        assert quiet.variables[P+'alert']==0 and item['response_quest'] not in quiet.active,'Quiet continuation stranded an existing deadline'
        for index,option in enumerate(item['options']):
            w=begin(item);assert w.click(guid,index)
            after=dict(w.stock);w.execute(row['choices'][index]['effects'])
            assert w.stock==after,'Cached decision callback paid twice'
            # Stop new arrivals while retaining already accepted deadlines.
            w.variables[P+'active']=0
            assert item['response_quest'] not in w.active
            if option['repair']:
                work=next(v for v in front['work_orders'] if (v['campaign'],v['incident'],v['choice'])==(item['campaign'],item['index'],index))
                assert work['deadline']*10*0.75*0.75>=front['automaton_hours']*work['quantity']*2,'Repair window lacks a vanilla-production safety margin'
                qid=work['guid'];assert w.variables[P+'alert']==2 and qid in w.active
                goal=quests[qid]['objectives'][0]
                assert not w.goal_met(qid,goal)
                w.variables[P+'active']=0 # Existing orders remain resolvable in quiet continuation.
                w.produced[goal['target'][0]]+=option['repair'];w.update_quests()
                assert w.variables[P+'alert']==0 and qid not in w.active
                assert front['bonuses'][option['reward']] in w.modifiers
                assert front['bonuses']['workprogramme'] not in w.modifiers
                # Success rejects both the old response deadline and work deadline.
                w.run(option['work_days']+item['response_days']+2,False)
                assert not w.active and w.variables[P+'alert']==0
                repairs+=1
                failed=begin(item);failed.click(guid,index);failed.variables[P+'active']=0
                failed.run(option['work_days']+0.25,False)
                assert qid not in failed.active and failed.variables[P+'alert']==0
                assert front['bonuses']['workprogramme'] not in failed.modifiers
                assert front['bonuses'][item['timeout_bonus']] in failed.modifiers
                failures+=1
            else:
                assert w.variables[P+'alert']==0
                transient=set(w.modifiers)
                w.run(max(option['duration'],item['response_days'])+1,False)
                assert not transient&w.modifiers,'A temporary response failed to expire'
            choices+=1
    assert len(front['incidents'])==18 and choices==54 and deadlines==18 and repairs==failures==5
    assert front['incident_cooldown_days']*6>max(w['deadline'] for w in front['work_orders'])
    # Refresh a shared four-day heat package shortly before its old expiry.
    # Neither expiry may remove a newer incarnation of the same modifier.
    long_event=next(i for i in front['incidents'] if i['title']=='The Next Storm Plan')
    short_event=next(i for i in front['incidents'] if i['title']=='A Frozen Heat Main')
    w=begin(long_event);w.click(long_event['dilemma'],0);w.variables[P+'active']=0;w.run(3.5,False)
    w.variables.update({P+'alert':1,P+'incident':short_event['index']})
    w.execute([('quest',short_event['response_quest'])]);w.click(short_event['dilemma'],1)
    w.run(0.75,False);assert front['bonuses']['burn'] in w.modifiers,'Old expiry removed a refreshed heat benefit'
    w.run(1.5,False);assert front['bonuses']['burn'] not in w.modifiers
    return dict(incident_choices=choices,response_expiries=deadlines,work_order_successes=repairs,
                work_order_failures=failures,mode_event_isolation=True,cached_callbacks_safe=True,effect_refresh_safe=True)
