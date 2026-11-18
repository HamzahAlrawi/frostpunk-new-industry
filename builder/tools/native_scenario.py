"""Native scenario primitives and templates, derived from owned data at build time.

All untouched bytes stay in the original records. New predicates and effects
use the same schemas as shipped native examples, which are checked below.
"""
import re
from .native_binary import Cursor,Span,SchemaError,u32,i32,f32,string,entry,replace_spans


def typed(name):return string(name)
def compact(name,body=b''):return bytes([len(name)])+name.encode()+body
def integer(value):return compact('ConstantIntegerExpression',i32(value))
def floating(value):return compact('ConstantFloatExpression',f32(value))
def variable(name):return compact('FrostpunkVariableValueIntegerExpression',b'\1'+string(name))
def amount(resource):return compact('FrostpunkResourceAmountExpression',bytes.fromhex(resource))


def compare(left,operator,right):
    return typed('IntegerComparisonExpression')+left+u32(operator)+right


def equals(name,value):return compare(variable(name),0,integer(value))
def affordable(resource,value):return compare(amount(resource),4,integer(value))
def mode_selected(value):return typed('FrostpunkCustomScenarioParameterCheckExpression')+bytes.fromhex(value)+b'\0'


def set_variable(name,value,operation=0):
    return typed('FrostpunkSetVariableEffect')+b'\1'+string(name)+u32(operation)+integer(value)


def change_resource(resource,value):
    return typed('FrostpunkChangeResourcesEffect')+bytes.fromhex(resource)+integer(value)+floating(1)+u32(0)


def predefined(identity):return typed('FrostpunkPredefinedEffect')+bytes.fromhex(identity)
def apply_modifier(identity):return typed('FrostpunkApplyModifierEffect')+bytes.fromhex(identity)
def dilemma(identity):return typed('FrostpunkCreateDilemmaEffect')+bytes.fromhex(identity)
def start_quest(identity):return typed('FrostpunkStartQuestEffect')+bytes.fromhex(identity)
def progress_quest(identity,name,quantity=1):return typed('FrostpunkProgressCustomQuestObjectiveEffect')+bytes.fromhex(identity)+string(name)+i32(quantity)


def delayed(identity,days,effects):
    return typed('FrostpunkTimedEffect')+bytes.fromhex(identity)+f32(days)+u32(1)+f32(0)+u32(0)+u32(len(effects))+b''.join(effects)


def first_match(*cases):
    return typed('FrostpunkSwitchEffect')+u32(len(cases))+b''.join(
        b'\1'+string(label)+u32(len(conditions))+b''.join(conditions)+u32(len(effects))+b''.join(effects)
        for label,conditions,effects in cases)


def guarded(conditions,effects):
    return first_match(('NI guard',conditions,effects))


def event(name,identity,trigger_identity,conditions,effects,period=None):
    if period is None:trigger=typed('FrostpunkGameStartedEventTrigger')+bytes.fromhex(trigger_identity)
    else:trigger=typed('FrostpunkPeriodicEventTrigger')+bytes.fromhex(trigger_identity)+f32(period)+u32(1)+f32(0)+u32(0)
    return (entry(name,identity)+string(None)+b'\1'+f32(1)+u32(1)+trigger
            +u32(len(conditions))+b''.join(conditions)+u32(len(effects))+b''.join(effects))


def append_directory(data,name,next_name,records):
    token=b'\1'+string(name);start=data.index(token);count_at=start+len(token)+16
    count=int.from_bytes(data[count_at:count_at+4],'little')
    end=data.index(b'\1'+string(next_name),count_at)
    if count>3000:raise SchemaError('Unsupported directory count')
    return replace_spans(data,[(Span(count_at,count_at+4),u32(count+len(records))),
                               (Span(end,end),b''.join(records))])


class DilemmaTemplate:
    def __init__(self,data):
        start=data.index(b'\1'+string('IntroEndless'))
        end=data.index(b'\1'+string('IntroEndless_Easy'),start)
        self.source=data[start:end]
        cursor=Cursor(self.source);cursor.entry();self.header_end=cursor.position
        choice=self.source.index(b'\1'+string('And so it begins'))
        self.choices_at=choice-4
        if self.source[self.choices_at:choice]!=u32(1):raise SchemaError('Unsupported intro choices')
        # A complete middle choice pins the neutral metadata/footer independently
        # of any surrounding dilemma's own footer.
        core=data.index(b'\1'+string('SteamCore'));next_choice=data.index(b'\1'+string('OK'),core)
        text=data.index(b'\1@Generated/',core)
        self.choice_footer=data[text:next_choice]
        neutral=re.sub(rb'\x01@Generated/[^\0]+\0',b'\0',self.choice_footer)
        if len(neutral)!=65:raise SchemaError('Unsupported choice footer')
        core_cursor=Cursor(data,core);core_cursor.entry();core_header=core_cursor.position
        condition=affordable('d4d223367a2042b44d465141b7c4472b',1)
        effect_start=data.index(typed('FrostpunkModifyGeneratorEffect'),core)
        core_prefix=bytes(38)+u32(1)+condition+u32(3)
        if data[core_header:effect_start]!=core_prefix or data[text-4:text]!=u32(0):
            raise SchemaError('Native complete choice vectors differ')
        if data[core:next_choice]!=(data[core:core_header]+core_prefix+data[effect_start:text-4]+u32(0)+self.choice_footer):
            raise SchemaError('Native choice round-trip failed')
        intro_text=self.source.index(b'\1@Generated/',choice)
        intro_text_end=self.source.index(0,intro_text+1)+1
        if b'\0'+self.source[intro_text_end:intro_text_end+64]!=neutral:raise SchemaError('Neutral choice layouts differ')
        self.choice_end=intro_text_end+64
        # The intro contains one authored sequence effect, wholly replaced by
        # each generated choice's effects. Its other metadata is preserved.
        if self.source.count(typed('FrostpunkStartSequenceEffect'))!=1:raise SchemaError('Unexpected intro effects')

    def choice(self,name,identity,text,description,conditions,effects,localize,key):
        values={'Text':text,'Description':description,'Disabled text':'This offer is no longer active, or the listed supplies are not in storage.'}
        def label(match):
            field=match.group().decode().rstrip('\0').rsplit('/',1)[-1]
            return localize(key+'/'+field,values[field])
        footer=re.sub(rb'\x01@Generated/[^\0]+\0',label,self.choice_footer)
        return (entry(name,identity)+bytes(38)+u32(len(conditions))+b''.join(conditions)
                +u32(len(effects))+b''.join(effects)+u32(0)+footer)

    def build(self,name,identity,title,description,choices,localize,key,small=True,subtitle='Reconstruction'):
        prefix=bytearray(self.source[self.header_end:self.choices_at])
        if small:prefix[:16]=bytes.fromhex('0ce922d2839700b94741c2c0ba95d45c')
        tail=self.source[self.choice_end:]
        def label(match):
            field=match.group().decode().rstrip('\0').rsplit('/',1)[-1]
            value={'Displayed name':title,'Arc subtitle text':subtitle,'Description':description}[field]
            return localize(key+'/'+field,value)
        tail=re.sub(rb'\x01@Generated/[^\0]+\0',label,tail)
        return entry(name,identity)+prefix+u32(len(choices))+b''.join(choices)+tail


class QuestTemplate:
    def __init__(self,data):
        marker=typed('FrostpunkCustomQuestObjective');obj=data.index(marker)
        # First custom objective is a normal narrative objective with no gates.
        cursor=Cursor(data,obj+len(marker));cursor.guid()
        if cursor.u32()!=0 or cursor.u8()!=0:raise SchemaError('Donor objective has activation gates')
        cursor.string();cursor.string();base_start=cursor.position
        custom=data.index(string('Refugees'),base_start)
        self.objective_metadata=data[base_start:custom]
        if len(self.objective_metadata)!=24:raise SchemaError('Unsupported objective base metadata')
        # This native visible quest has no success/failure effects. Its footer
        # pins all null vectors and UI options; the social-problem link is omitted.
        name=data.index(string('[Reconquest] Hot Springs Plotline'))
        last=data.index(string('ASEnd'),name)+len(string('ASEnd'))+5
        footer=data[last:]
        loc=footer.index(b'\1@Generated/')
        if loc!=44 or footer[:28]!=bytes(28):raise SchemaError('Unsupported neutral quest footer')
        cursor=Cursor(footer,loc);cursor.string()
        if cursor.string() is not None or cursor.string() is not None:raise SchemaError('Non-neutral quest descriptions')
        if cursor.f32()!=-999 or not cursor.boolean() or not cursor.boolean():raise SchemaError('Unsupported quest view fields')
        self.atlas=cursor.string();self.icon=[cursor.i32() for _ in range(4)]
        if not cursor.boolean():raise SchemaError('Unexpected quest footer bytes')
        # The next record starts immediately after this fully parsed footer.
        next_record=Cursor(footer,cursor.position)
        if not next_record.boolean():raise SchemaError('Missing next native quest')
        next_record.guid()
        if not next_record.string():raise SchemaError('Invalid next native quest header')

    def build(self,name,identity,objective_identity,title,budget,localize,key,deadline=None,priority=20):
        timeout=compact('FrostpunkFixedDurationTimeout',f32(deadline)+u32(1)) if deadline is not None else b'\0'
        objective=(typed('FrostpunkCustomQuestObjective')+bytes.fromhex(objective_identity)+u32(0)+b'\0'
                   +localize(key+'/Objective','Dispatch the supplies: '+budget)
                   +localize(key+'/ObjectiveDescription','A delivery offer appears when these supplies are available. You choose whether to dispatch them.')
                   +self.objective_metadata+string('Dispatch')+u32(1)+b'\0')
        footer=(bytes(44)+localize(key+'/Title',title)+string(None)+string(None)+f32(priority)+b'\0\1'
                +string(self.atlas)+b''.join(i32(value) for value in self.icon)+b'\0')
        return b'\1'+bytes.fromhex(identity)+string(name)+timeout+b'\0'+i32(1)+i32(-1)+i32(1)+u32(1)+objective+footer


def validate_native_samples(events,dilemmas,quests,resources):
    sample=event('U: Show SociotechButton','9b74cda12c38899325404efc6bcabef0','beb67d3284ff9ab8cd410ae51fb0837e',[],
                 [typed('FrostpunkAddUnlockEffect')+bytes.fromhex('0175a1b425655ba9834471bc47f0098e')])
    if sample not in events:raise SchemaError('Minimal native event layout differs')
    if affordable(resources['Steam Cores'],1) not in dilemmas:raise SchemaError('Native affordability predicate differs')
    if change_resource(resources['Steam Cores'],-1) not in dilemmas:raise SchemaError('Native payment layout differs')
    if set_variable('HintPossible',42) not in events:raise SchemaError('Native global variable layout differs')
    if progress_quest('9c0badecb6450eb25e40da0c0c0930b1','Wait') not in events:raise SchemaError('Native quest progress layout differs')
    finish=(typed('FrostpunkQuestFinishedEventTrigger')+bytes.fromhex('401a486799d7b68712460cfd5d1ed0f6')
        +bytes.fromhex('76bf929444a495918f4b9d477f9f38da')+u32(0))
    if finish not in events:raise SchemaError('Native successful-quest trigger differs')
    remove=(typed('FrostpunkRemoveModifierEffect')+bytes.fromhex('b0cea22de6636197d34697c845d1d79b')+typed('FrostpunkApplyModifierEffect'))
    if remove not in events:raise SchemaError('Native modifier removal boundary differs')
    if typed('FrostpunkGeneratorIsActiveExpression')+b'\1'+typed('IntegerComparisonExpression') not in events:
        raise SchemaError('Native inverted generator predicate differs')
    # A complete nested native switch ends immediately after its final effect;
    # it has no implicit default-case record. Pin both cases and their boundary.
    probe=(typed('FrostpunkSwitchEffect')+u32(2)+b'\1'+string('kid')+u32(1)
        +typed('FrostpunkAgentLabelCheckExpression')+bytes.fromhex('cd5e9e88d9b04bb90a40f695aa1ffa18')+b'\0'+u32(1)
        +predefined('81caa45e782c2580fd45bb9b52c2936e')
        +b'\1'+string('grown up')+u32(0)+u32(1)+predefined('3c7b6e72022665891648a49a44161f2d')
        +b'\1'+string('No Ceremonial burials'))
    if probe not in events:raise SchemaError('Native complete switch layout differs')
    return DilemmaTemplate(dilemmas),QuestTemplate(quests)
