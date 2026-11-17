"""Deterministic audit harness for decoded native events; never a game runtime."""
import copy
import heapq


class World:
    def __init__(self,enabled,events,dilemmas,quests,stock=None):
        self.enabled=enabled;self.events=events;self.dilemmas=dilemmas;self.quests=quests
        self.time=0;self.variables={};self.stock=dict(stock or {});self.queue=[];self.serial=0
        self.open=[];self.active={};self.completed=[];self.modifiers=set();self.predefined=[];self.paid=[]

    def value(self,value):
        kind=value[0]
        if kind=='constant':return value[1]
        if kind=='variable':return self.variables.get(value[1],0)
        if kind=='resource':return self.stock.get(value[1],0)
        if kind=='mode':return (self.enabled==value[1])!=value[2]
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
            elif kind=='progress':
                _,guid,label,quantity=action;assert label=='Dispatch' and quantity==1
                assert guid in self.active,'Completed absent/expired quest'
                self.active.pop(guid);self.completed.append(guid)
            elif kind=='modifier':self.modifiers.add(action[1])
            elif kind=='predefined':self.predefined.append(action[1])
            else:raise AssertionError(action)

    def start(self):
        for event in self.events:
            if event['triggers'][0][0]=='start' and self.all(event['conditions']):self.execute(event['effects'])

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
            if event['triggers'][0][0]=='periodic' and self.all(event['conditions']):self.execute(event['effects'])

    def automate(self):
        for guid in list(self.open):
            if self.click(guid):self.paid.append(guid)

    def run(self,days,automatic=True):
        for _ in range(round(days/0.25)):
            self.step()
            if automatic:self.automate()

    def checkpoint(self):return copy.deepcopy(self)
