"""Deterministic audit harness for decoded native events; never a game runtime."""
import copy
import heapq


class World:
    def __init__(self,enabled,events,dilemmas,quests,stock=None,scenario=None):
        self.enabled=enabled;self.events=events;self.dilemmas=dilemmas;self.quests=quests
        self.selected=set(enabled) if isinstance(enabled,(list,tuple,set)) else {enabled}
        self.time=0;self.variables={};self.stock=dict(stock or {});self.queue=[];self.serial=0
        self.open=[];self.active={};self.completed=[];self.modifiers=set();self.predefined=[];self.paid=[]
        self.buildings={};self.researched=set();self.produced={};self.production_start={};self.progress={}
        self.automation=0;self.generator=True;self.scenario=scenario
        self.arrivals={};self.operating={};self.warm_homes=0;self.world_map=False

    def value(self,value):
        kind=value[0]
        if kind=='constant':return value[1]
        if kind=='variable':return self.variables.get(value[1],0)
        if kind=='resource':return self.stock.get(value[1],0)
        if kind=='mode':return (value[1] in self.selected)!=value[2]
        if kind=='scenario':return (value[1]==self.scenario)!=value[2]
        if kind=='generator':return self.generator!=value[1]
        if kind=='compare':
            left,right=self.value(value[2]),self.value(value[3])
            return left==right if value[1]==0 else left>=right
        raise AssertionError(value)

    def all(self,conditions):return all(self.value(c) for c in conditions)

    def execute(self,actions):
        for action in actions:
            kind=action[0]
            if kind=='set':
                _,name,op,value=action;value=self.value(value)
                if op==0:self.variables[name]=value
                elif op==1:self.variables[name]=self.variables.get(name,0)+value
                else:raise AssertionError(action)
            elif kind=='resource':
                _,guid,quantity,multiplier,origin=action
                assert origin==0 and self.value(multiplier)==1
                self.stock[guid]=self.stock.get(guid,0)+self.value(quantity)
                assert self.stock[guid]>=0,'Payment overdrawn'
            elif kind=='timer':
                self.serial+=1;heapq.heappush(self.queue,(self.time+action[2],self.serial,action[3]))
            elif kind=='switch':
                selected=next((case for case in action[1] if self.all(case[1])),action[2])
                if self.all(selected[1]):self.execute(selected[2])
            elif kind=='dilemma':
                assert action[1] in self.dilemmas;self.open.append(action[1])
            elif kind=='quest':
                guid=action[1];assert guid in self.quests and guid not in self.active,'Duplicate active quest'
                deadline=self.quests[guid]['deadline'];self.active[guid]=None if deadline is None else self.time+deadline
                self.production_start[guid]=dict(self.produced);self.progress[guid]={}
            elif kind=='progress':
                _,guid,label,quantity=action
                assert guid in self.active,'Completed absent/expired quest'
                self.progress.setdefault(guid,{})[label]=self.progress.get(guid,{}).get(label,0)+quantity
                self.update_quests()
            elif kind=='modifier':self.modifiers.add(action[1])
            elif kind=='arrival':
                key=action[2:]
                self.arrivals[key]=self.arrivals.get(key,0)+action[1]
            elif kind=='open_map':self.world_map=True
            elif kind=='remove_modifier':self.modifiers.discard(action[1])
            elif kind=='predefined':self.predefined.append(action[1])
            else:raise AssertionError(action)

    def start(self):
        for event in self.events:
            if event['triggers'][0][0]=='start' and self.all(event['conditions']):self.execute(event['effects'])

    def return_scouts(self):
        for event in self.events:
            if event['triggers'][0][0]=='scout_return' and self.all(event['conditions']):self.execute(event['effects'])

    def activate_building(self,building):
        for event in self.events:
            kind,_,*target=event['triggers'][0]
            if kind=='construction' and target==[building] and self.all(event['conditions']):
                self.execute(event['effects'])

    def goal_met(self,guid,goal):
        kind=goal['kind'];quantity=goal['quantity']
        if kind=='checks':return self.progress.get(guid,{}).get(goal['label'],0)>=quantity
        if kind=='build':return sum(self.buildings.get(g,0) for g in goal['target'])>=quantity
        if kind=='operate':return sum(self.operating.get(g,0) for g in goal['target'])>=quantity
        if kind=='warm':return self.warm_homes>=quantity
        if kind=='research':return goal['target'] in self.researched
        if kind=='produce':return sum(self.produced.get(g,0)-self.production_start[guid].get(g,0) for g in goal['target'])>=quantity
        if kind=='automate':return self.automation>quantity
        if kind=='stock':return self.stock.get(goal['target'],0)>=self.value(quantity)
        raise AssertionError(goal)

    def update_quests(self):
        for guid in list(self.active):
            if not all(self.goal_met(guid,goal) for goal in self.quests[guid]['objectives']):continue
            self.active.pop(guid);self.completed.append(guid)
            for event in self.events:
                trigger=event['triggers'][0]
                if trigger[0]=='quest' and trigger[2:]==(''+guid,0) and self.all(event['conditions']):self.execute(event['effects'])

    def click(self,guid,index=0):
        choice=self.dilemmas[guid]['choices'][index]
        if not self.all(choice['conditions']):return False
        self.execute(choice['effects'])
        if guid in self.open:self.open.remove(guid)
        return True

    def step(self,days=0.25):
        target=self.time+days
        while self.queue and self.queue[0][0]<=target:
            self.time,_,actions=heapq.heappop(self.queue);self.execute(actions)
        self.time=target
        for guid,deadline in list(self.active.items()):
            if deadline is not None and deadline<=self.time:self.active.pop(guid)
        for event in self.events:
            trigger=event['triggers'][0]
            if trigger[0]=='periodic' and abs(self.time/trigger[2]-round(self.time/trigger[2]))<0.0001 and self.all(event['conditions']):self.execute(event['effects'])
        self.update_quests()

    def automate(self):
        for guid in list(self.open):
            if self.click(guid):self.paid.append(guid)

    def run(self,days,automatic=True):
        for _ in range(round(days/0.25)):
            self.step()
            if automatic:self.automate()

    def checkpoint(self):return copy.deepcopy(self)
