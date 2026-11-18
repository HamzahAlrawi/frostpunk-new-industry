"""Bounded independent decoder for the native subset used by Reconstruction.

The decoder is also the input to the state-machine checks: those checks execute
serialized effects rather than an optimistic second implementation of gameplay.
Unsupported classes, trailing bytes and malformed vectors are hard failures.
"""
from .native_binary import Cursor,SchemaError


def expression(c,compact=False):
    name=c.take(c.u8()).decode() if compact else c.string()
    if name=='ConstantIntegerExpression':return ('constant',c.i32())
    if name=='ConstantFloatExpression':return ('constant',c.f32())
    if name=='FrostpunkVariableValueIntegerExpression':
        if not c.boolean():raise SchemaError('Expected global variable')
        return ('variable',c.string())
    if name=='FrostpunkResourceAmountExpression':return ('resource',c.guid())
    if name=='IntegerComparisonExpression':
        left=expression(c,True);op=c.u32();right=expression(c,True)
        if op not in (0,4):raise SchemaError('Unsupported comparison')
        return ('compare',op,left,right)
    if name=='FloatComparisonExpression':
        left=expression(c,True);op=c.u32();right=expression(c,True)
        if left!=('stress',) or op not in (4,5) or right[0]!='constant' or not 0<=right[1]<=1:
            raise SchemaError('Unsupported Generator stress comparison')
        return ('stress_compare',op,right[1])
    if name=='FrostpunkGeneratorStressExpression':
        return ('stress',)
    if name=='FrostpunkCustomScenarioParameterCheckExpression':
        return ('mode',c.guid(),c.boolean())
    if name=='FrostpunkCurrentScenarioCheckExpression':
        return ('scenario',c.guid(),c.boolean())
    if name=='BooleanOperationExpression':
        if c.u32()!=1:raise SchemaError('Unsupported boolean operation')
        return ('any',expressions(c))
    if name=='CountExpression':
        if not compact or c.take(c.u8())!=b'FrostpunkBuildingsSelector':
            raise SchemaError('Unsupported count selector')
        identity=c.guid()
        if c.take(12)!=b'\1'+bytes(11):raise SchemaError('Unexpected building selector flags')
        return ('building_count',identity)
    if name=='FrostpunkGeneratorIsActiveExpression':return ('generator',c.boolean())
    raise SchemaError('Unsupported expression '+str(name))


def expressions(c):return [expression(c) for _ in range(c.count(32))]


def effects(c):return [effect(c) for _ in range(c.count(256))]


def effect(c):
    name=c.string()
    if name=='FrostpunkSetVariableEffect':
        if not c.boolean():raise SchemaError('Expected global variable')
        return ('set',c.string(),c.u32(),expression(c,True))
    if name=='FrostpunkChangeResourcesEffect':
        return ('resource',c.guid(),expression(c,True),expression(c,True),c.u32())
    if name in ('FrostpunkPredefinedEffect','FrostpunkApplyModifierEffect','FrostpunkRemoveModifierEffect','FrostpunkCreateDilemmaEffect','FrostpunkStartQuestEffect'):
        return ({'FrostpunkPredefinedEffect':'predefined','FrostpunkApplyModifierEffect':'modifier',
                 'FrostpunkRemoveModifierEffect':'remove_modifier','FrostpunkCreateDilemmaEffect':'dilemma','FrostpunkStartQuestEffect':'quest'}[name],c.guid())
    if name=='FrostpunkCreateAgentEffect':
        quantity,appearance,role=c.i32(),c.guid(),c.guid()
        if not 0<quantity<=60 or c.count()!=0:raise SchemaError('Unexpected arrival payload')
        return ('arrival',quantity,appearance,role)
    if name=='FrostpunkModifyWorldMapEffect':
        if c.take(11)!=bytes.fromhex("01ffffffff000000000000"):raise SchemaError('Unexpected world map effect')
        return ('open_map',)
    if name=='FrostpunkSelectEffect':
        selector=c.take(c.u8()).decode()
        if selector=='FrostpunkGeneratorSelector':
            if c.take(7)!=bytes(7):raise SchemaError('Unexpected Generator selector flags')
            operations=effects(c)
            if len(operations)!=1 or operations[0][0]!='vent':
                raise SchemaError('Unexpected selected Generator operation')
            return operations[0]
        if selector=='FrostpunkEntitiesByNameSelector':
            target=('marker',c.string())
        elif selector=='FrostpunkExpeditionSitesSelector':
            target=('site',c.guid())
        else:
            raise SchemaError('Unsupported world map selector '+selector)
        if c.take(7)!=bytes(7):raise SchemaError('Unexpected world map selector flags')
        operations=effects(c)
        if operations!=[('map_reveal',)]:
            raise SchemaError('Unexpected world map selector action')
        return ('map_reveal',target)
    if name=='FrostpunkRevealWorldMapEntityEffect':
        return ('map_reveal',)
    if name=='FrostpunkModifyGeneratorEffect':
        delta=c.f32()
        if not -0.35<=delta<0 or c.u32()!=0:raise SchemaError('Unexpected Generator effect')
        return ('vent',delta)
    if name=='FrostpunkProgressCustomQuestObjectiveEffect':return ('progress',c.guid(),c.string(),c.i32())
    if name=='FrostpunkTimedEffect':
        guid=c.guid();days=c.f32();unit=c.u32();random=c.f32();random_unit=c.u32()
        if unit!=1 or random!=0 or random_unit!=0 or days<=0:raise SchemaError('Unsupported timer')
        return ('timer',guid,days,effects(c))
    if name=='FrostpunkSwitchEffect':
        cases=[]
        for _ in range(c.count(32)):
            if not c.boolean():raise SchemaError('Null switch case')
            label=c.string();conditions=expressions(c);actions=effects(c)
            cases.append((label,conditions,actions))
        return ('switch',cases,('No match',[],[]))
    raise SchemaError('Unsupported effect '+str(name))


def event(c):
    name,guid=c.entry();comments=c.string();enabled=c.boolean();weight=c.f32()
    triggers=[]
    for _ in range(c.count(8)):
        kind=c.string();identity=c.guid()
        if kind=='FrostpunkGameStartedEventTrigger':triggers.append(('start',identity))
        elif kind=='FrostpunkQuestFinishedEventTrigger':triggers.append(('quest',identity,c.guid(),c.u32()))
        elif kind=='FrostpunkExpeditionReturnedEventTrigger':
            if c.take(2)!=b'\0\0':raise SchemaError('Unexpected expedition return flags')
            triggers.append(('scout_return',identity))
        elif kind=='FrostpunkBuildingActivationEventTrigger':
            building=c.guid()
            if c.u32()!=0:raise SchemaError('Unexpected building activation type')
            triggers.append(('construction',identity,building))
        elif kind=='FrostpunkPeriodicEventTrigger':
            period,unit,initial,initial_unit=c.f32(),c.u32(),c.f32(),c.u32()
            if unit!=1 or initial!=0 or initial_unit!=0:raise SchemaError('Unsupported periodic clock')
            triggers.append(('periodic',identity,period))
        else:raise SchemaError('Unsupported trigger '+str(kind))
    return dict(name=name,guid=guid,enabled=enabled,weight=weight,triggers=triggers,
                conditions=expressions(c),effects=effects(c))


CHOICE_METADATA=bytes.fromhex('00000000000000000000000000000000000000000000000000000000000000000100000001000000000000000000000000010000000100000000000000')


def choice(c):
    name,guid=c.entry()
    if c.take(38)!=bytes(38):raise SchemaError('Unexpected choice metadata')
    conditions=expressions(c);actions=effects(c)
    if c.count()!=0:raise SchemaError('Unexpected post-choice effects')
    text=c.string();description=c.string()
    if c.boolean():raise SchemaError('Unexpected choice description option')
    disabled=c.string()
    if c.take(61)!=CHOICE_METADATA:raise SchemaError('Unexpected choice footer')
    return dict(name=name,guid=guid,conditions=conditions,effects=actions,text=text,description=description,disabled=disabled)


def quest(c):
    if not c.boolean():raise SchemaError('Null quest')
    guid=c.guid();name=c.string();length=c.u8();deadline=None
    if length:
        if c.take(length)!=b'FrostpunkFixedDurationTimeout':raise SchemaError('Unknown timeout')
        deadline=c.f32()
        if c.u32()!=1:raise SchemaError('Deadline must use game days')
    if c.boolean() or (c.i32(),c.i32(),c.i32())!=(1,-1,1):raise SchemaError('Unexpected quest type/occurrence limits')
    goals=[]
    for _ in range(c.count(16)):
        kind=c.string();objective=c.guid()
        if c.count()!=0 or c.boolean():raise SchemaError('Unexpected objective conditions')
        text=c.string();description=c.string();metadata=c.take(24)
        goal=dict(guid=objective,text=text,description=description,metadata=metadata.hex())
        if kind=='FrostpunkCustomQuestObjective':
            goal.update(kind='checks',label=c.string(),quantity=c.u32(),bound=c.boolean())
        elif kind=='FrostpunkConstructBuildingOfTypeQuestObjective':
            goal.update(kind='build',target=[c.guid() for _ in range(c.count(112))],quantity=c.u32(),existing=c.boolean())
        elif kind=='FrostpunkActivateBuildingOfTypeQuestObjective':
            goal.update(kind='operate',target=[c.guid() for _ in range(c.count(112))],quantity=c.u32())
            if c.take(3)!=b'\1\1\0':raise SchemaError('Unexpected operating objective flags')
        elif kind=='FrostpunkResearchTechnologyQuestObjective':goal.update(kind='research',target=c.guid(),quantity=1)
        elif kind=='FrostpunkProduceQuestObjective':
            goal.update(kind='produce',quantity=c.u32(),target=[c.guid() for _ in range(c.count(32))])
        elif kind=='FrostpunkEmployAutomatonsQuestObjective':goal.update(kind='automate',quantity=c.f32())
        elif kind=='FrostpunkGatherResourceQuestObjective':
            goal.update(kind='stock',target=c.guid(),quantity=expression(c,True),flags=[c.boolean(),c.boolean()])
        elif kind=='FrostpunkHeatBuildingOfCategoryQuestObjective':
            category,threshold=c.guid(),c.guid()
            amount=expression(c,True)
            if amount[0]!='constant' or c.take(2)!=b'\1\0':raise SchemaError('Unexpected warmth objective')
            goal.update(kind='warm',target=[category,threshold],quantity=amount[1])
        else:raise SchemaError('Unsupported quest objective '+str(kind))
        goals.append(goal)
    if c.take(44)!=bytes(44):raise SchemaError('Unexpected quest callbacks/social problem')
    title=c.string()
    if c.string() is not None or c.string() is not None:raise SchemaError('Unexpected quest descriptions')
    priority=c.f32();hide=c.boolean();color=c.boolean();atlas=c.string();icon=[c.i32() for _ in range(4)];height=c.boolean()
    if hide or not color or height or atlas!='UI\\Tiles\\Icons.dds' or icon!=[4,1,16,16]:raise SchemaError('Unexpected quest view')
    return dict(name=name,guid=guid,deadline=deadline,objectives=goals,objective=goals[0]['guid'],text=goals[0]['text'],description=goals[0]['description'],title=title,metadata=goals[0]['metadata'],priority=priority)
