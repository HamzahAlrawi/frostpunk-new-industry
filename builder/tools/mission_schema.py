"""Native automatic mission objectives and successful-quest event triggers."""
from .native_binary import Cursor,SchemaError,string,u32,i32,f32,entry
from .native_scenario import typed,integer,compact


KINDS={'build':'ConstructBuildingOfType','research':'ResearchTechnology',
       'produce':'Produce','automate':'EmployAutomatons','stock':'GatherResource','checks':'Custom',
       'operate':'ActivateBuildingOfType'}


def completed_event(name,identity,trigger_id,quest,conditions,effects):
    return (entry(name,identity)+b'\0\1'+f32(1)+u32(1)
        +typed('FrostpunkQuestFinishedEventTrigger')+bytes.fromhex(trigger_id)+bytes.fromhex(quest)+u32(0)
        +u32(len(conditions))+b''.join(conditions)+u32(len(effects))+b''.join(effects))


class MissionWriter:
    def __init__(self,data,quest_template):
        self.template=quest_template
        # Check complete class-specific fields against native adjacent-object
        # boundaries, rather than accepting an isolated prefix as a fixture.
        for kind,expected in (
            ('build',u32(1)+bytes.fromhex('ef89bf3e0a1a40bfa149355bdc4e83b5')+u32(1)+b'\1'),
            ('produce',u32(1)+u32(3)+bytes.fromhex('cc33ac0c093846b56040ff68fee8e948061c4e12f375c4a75b42f32d97bc2d1eb21a11b15c4a53803b418396e9e7b82c')),
            ('automate',f32(0.5)),
            ('stock',bytes.fromhex('0bcf0b94b94337859c44bcdf67f9bee1')+integer(200)+b'\1\1')):
            marker=typed('Frostpunk'+KINDS[kind]+'QuestObjective');at=data.index(marker)
            c=Cursor(data,at+len(marker));c.guid()
            if c.count()!=0 or c.boolean():raise SchemaError('Non-neutral objective donor')
            c.string();c.string()
            if c.take(24)!=self.template.objective_metadata:raise SchemaError('Objective metadata differs')
            if c.take(len(expected))!=expected or data[c.position]!=0 and data[c.position]!=1:raise SchemaError('Objective layout differs: '+kind)
        marker=typed('FrostpunkResearchTechnologyQuestObjective')
        at=data.index(marker,50000);c=Cursor(data,at+len(marker));c.guid();c.count();c.boolean();c.string();c.string();c.take(24);c.guid()
        if data[c.position:c.position+len(marker)]!=marker:raise SchemaError('Research objective boundary differs')
        native_boundary=(u32(1)+bytes.fromhex('99c50bbc0ec952ace541f69166fab316')+u32(1)+b'\1\1\0'
            +typed('FrostpunkRescueSurvivorsQuestObjective')+bytes.fromhex('da8485fad05f07b31444575bf9f7ae52'))
        if native_boundary not in data:raise SchemaError('Native activation objective boundary differs')

    def objective(self,goal,identity,localize,key):
        kind=goal['kind'];target=goal.get('target');quantity=goal.get('quantity',1)
        body=(typed('Frostpunk'+KINDS[kind]+'QuestObjective')+bytes.fromhex(identity)+u32(0)+b'\0'
            +localize(key+'/Text',goal['text'])+localize(key+'/Description',goal.get('description',goal['text']))
            +self.template.objective_metadata)
        if kind=='build':body+=u32(len(target))+b''.join(bytes.fromhex(v) for v in target)+u32(quantity)+b'\1'
        elif kind=='operate':body+=u32(len(target))+b''.join(bytes.fromhex(v) for v in target)+u32(quantity)+b'\1\1\0'
        elif kind=='research':body+=bytes.fromhex(target)
        elif kind=='produce':body+=u32(quantity)+u32(len(target))+b''.join(bytes.fromhex(v) for v in target)
        elif kind=='automate':body+=f32(quantity)
        elif kind=='stock':body+=bytes.fromhex(target)+integer(quantity)+b'\1\1'
        elif kind=='checks':body+=string(goal.get('label','Stability'))+u32(quantity)+b'\0'
        else:raise SchemaError('Unsupported objective '+kind)
        return body

    def build(self,name,identity,title,goals,guid,localize,key,deadline=None):
        objects=[self.objective(goal,guid(key+'/'+str(i)),localize,key+'/'+str(i)) for i,goal in enumerate(goals)]
        qt=self.template
        footer=(bytes(44)+localize(key+'/Title',title)+b'\0\0'+f32(30)+b'\0\1'
            +string(qt.atlas)+b''.join(i32(v) for v in qt.icon)+b'\0')
        timeout=compact('FrostpunkFixedDurationTimeout',f32(deadline)+u32(1)) if deadline else b'\0'
        return b'\1'+bytes.fromhex(identity)+string(name)+timeout+b'\0'+i32(1)+i32(-1)+i32(1)+u32(len(objects))+b''.join(objects)+footer
