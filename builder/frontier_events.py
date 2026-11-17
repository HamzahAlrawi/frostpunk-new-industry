"""Mode-specific incidents: response windows, work orders and city trade-offs."""
import re


def option(title,description,bonus=None,cost=None,repair=0,work_days=None,reward='retool',cargo=None,duration=2,morale=0):
    work_days=work_days or (4 if repair==1 else 6)
    if repair:
        description=re.sub(r'within (three|five) days',f'within {work_days} game days',description)
        description=description.replace('Factory -40%','Factory -25%')
    return dict(title=title,description=description,bonus=bonus,cost=cost or {},repair=repair,
                work_days=work_days,reward=reward,cargo=cargo or {},duration=duration,morale=morale)


def incident(campaign,title,days,description,options):
    return dict(campaign=campaign,title=title,response_days=days,description=description,options=options)


def content():
    return [
      incident(1,'A Worksite Accident',1.5,'A structural failure has injured a construction crew. The district needs a response, not another output target.',[
        option('Reassign the medical teams','Two days: healthcare +100%, industry -35%.','quarantine'),
        option('Fund an emergency ward','Spend 400 steel and 200 rations; avoid a production disruption.',cost={'Steel':400,'Food Rations':200},morale=1),
        option('Suspend unsafe work','Two days: all workplace efficiency -35%, cold-related illness -50%.','restcity',morale=1)]),
      incident(1,'The Foundry Needs Retooling',3,'Worn assemblies threaten the production district. Buy time, buy parts, or manufacture a replacement machine.',[
        option('Divert the engineers','Two days: Factory +100%, Workshop -50% efficiency.','engineers'),
        option('Commission a repair automaton','Manufacture one new automaton within three days. Factory -40% until resolved; success grants Factory +75% for two days. The machine remains yours.',repair=1),
        option('Purchase new assemblies','Spend four cores and 600 steel for Factory +75% efficiency for two days.','retool',{'Steam Cores':4,'Steel':600})]),
      incident(1,'The District Petition',4,'The expanding city wants more than factories. Choose which group gets your support.',[
        option('Equip community services','Spend 1,500 wood and 600 steel. Two days: homes/civic services +1 insulation, healthcare +50% efficiency.','community',{'Wood':1500,'Steel':600}),
        option('Hold a civic assembly','Two days: food and healthcare +75% efficiency, industry -25%.','council',morale=1),
        option('Offer trained industrial crews','Two days: industrial/extraction human efficiency +100%, automaton efficiency -25%.','human')]),
      incident(1,'Competing Fuel Bids',2,'Heating crews and the foundry want the same reserve. There is enough capacity for one extraordinary programme.',[
        option('Release the coal reserve','Spend 3,000 coal. Citywide insulation +3 for two days.','burn',{'Coal':3000}),
        option('Seal the work districts','Two days: citywide insulation +2; food and industry efficiency -25%.','seal'),
        option('Issue thermal repair kits','Spend 1,500 wood and 800 steel. Homes, healthcare and civic services gain +3 insulation for two days.','thermal_kits',{'Wood':1500,'Steel':800})]),
      incident(1,'The Survey Column Is Missing',3,'A regional survey has missed its report. Fund a rescue, divert specialists or accept a loss of confidence.',[
        option('Supply a rescue column','Spend 2,500 coal and 1,000 rations. Receive 5,000 wood and 1,500 steel after one day.',cost={'Coal':2500,'Food Rations':1000},cargo={'Wood':5000,'Steel':1500},morale=1),
        option('Divert medical specialists','Two days: industrial efficiency +50%, healthcare efficiency -35%.','survey'),
        option('Abandon the operation','Hope falls moderately. No resources are spent.',morale=-1)]),
      incident(1,'The Charter Congress',5,'The capital must decide what its next period of growth will serve.',[
        option('Put public welfare first','Two days: food/healthcare +75%, industry -25%.','council',morale=1),
        option('Authorise a fabrication drive','Two days: industry +125%, food efficiency -25%.','overclock'),
        option('Distribute winter equipment','Spend 1,500 steel and 1,500 coal. All workplaces +25% efficiency and all insulated buildings +1 insulation for two days.','equipment',{'Steel':1500,'Coal':1500})]),
      incident(2,'A Frozen Heat Main',1.5,'A district heat main is losing pressure. Protect warmth, spend fuel or keep production exposed.',[
        option('Seal the workplaces','Two days: citywide insulation +2, food/industry efficiency -25%.','seal'),
        option('Burn the emergency reserve','Spend 2,000 coal for citywide +3 insulation for two days.','burn',{'Coal':2000}),
        option('Keep production moving','Two days: workplace efficiency +50%, citywide insulation -1.','push')]),
      incident(2,'The Surgery Ward Is Freezing',2,'Medical staff cannot keep every ward productive and warm. Decide which constraint to relieve.',[
        option('Reassign industrial crews','Two days: healthcare +100%, industry -35%.','quarantine'),
        option('Install thermal kits','Spend 1,500 wood and 700 steel. Homes, healthcare and civic services +3 insulation for two days.','thermal_kits',{'Wood':1500,'Steel':700}),
        option('Consolidate patients near the kitchens','Two days: healthcare +2 insulation but -25% efficiency; food workplaces +50% efficiency.','care')]),
      incident(2,'The Coal Convoy Is Overdue',3,'The next fuel shipment will not arrive on schedule. You can buy a replacement, build a repair machine or force local extraction.',[
        option('Trade provisions for fuel','Spend 2,000 rations. Receive 8,000 coal after one day.',cost={'Food Rations':2000},cargo={'Coal':8000}),
        option('Build a repair automaton','Manufacture one new automaton within three days. Factory -40% until resolved; success delivers 10,000 coal and a two-day coal-production boost. The machine remains yours.',repair=1,reward='coalshift',cargo={'Coal':10000}),
        option('Force local extraction','Two days: coal mines/thumpers +75% efficiency, citywide insulation -1.','coalshift')]),
      incident(2,'Frost in the Housing Blocks',4,'Families are crowding into the warmest buildings. Choose a housing, food or civic response.',[
        option('Shelter the housing blocks','Two days: homes +3 insulation, industry -25% efficiency.','housing'),
        option('Expand food and medical relief','Two days: healthcare +100%, food +75%, industry -25%.','relief'),
        option('Issue city repair kits','Spend 2,000 wood, 1,500 steel and 500 rations. Homes, healthcare and civic services +3 insulation for two days.','thermal_kits',{'Wood':2000,'Steel':1500,'Food Rations':500})]),
      incident(2,'An Icebound Workforce',2,'The cold is taking its toll on working crews. Rest, pressure and equipment produce very different cities.',[
        option('Order recovery shifts','Two days: all workplaces -35% efficiency, cold-related illness -50%.','restcity',morale=1),
        option('Demand a production drive','Two days: all workplaces +75% efficiency, cold-related illness +50%.','driven',morale=-1),
        option('Equip protected shifts','Spend three cores and 1,000 steel. Two days: all workplaces +25% efficiency, citywide insulation +1.','equipment',{'Steam Cores':3,'Steel':1000})]),
      incident(2,'The Next Storm Plan',5,'The council has a planning window. A reserve burn, industrial mobilisation and public relief all prepare for different risks.',[
        option('Commit the deep fuel reserve','Spend 12,000 coal for citywide +3 insulation for four days.','burn',{'Coal':12000},duration=4),
        option('Mobilise the industrial district','Three days: industry +125%, food efficiency -25%.','overclock',duration=3),
        option('Mobilise relief services','Three days: healthcare +100%, food +75%, industry -25%.','relief',duration=3,morale=1)]),
      incident(3,'A Servo Cascade',1.5,'Failure in one machine threatens the Factory queue. There are three ways to contain it.',[
        option('Divert engineers to repairs','Two days: Factory +100%, Workshop -50%.','engineers'),
        option('Fit spare assemblies','Spend four cores and 600 steel for Factory +75% for two days.','retool',{'Steam Cores':4,'Steel':600}),
        option('Shut down for maintenance','Two days: Factory efficiency -40%; Discontent falls greatly.','rest',morale=1)]),
      incident(3,'New Clockwork Standards',3,'The network needs a standard machine design. Build a demonstrator, pay for shared training or fall back on human expertise.',[
        option('Commission demonstrator machines','Manufacture two new automatons within three days. Factory -40% until resolved; success grants three days of industrial/extraction automaton +100%, human -35%. Machines remain yours.',repair=2,reward='servo',duration=3),
        option('Pay for shared training','Spend 1,000 steel and 500 coal. Two days: industrial/extraction human and automaton efficiency +50%.','shared',{'Steel':1000,'Coal':500}),
        option('Give human crews the lead','Two days: industrial/extraction human +100%, automaton -25%.','human')]),
      incident(3,'The Engineers Protest',4,'The engineering corps wants a say in the machine economy. Your answer changes who benefits from production.',[
        option('Support the human crews','Two days: industrial/extraction human +100%, automaton -25%; Discontent falls greatly.','human',morale=1),
        option('Put automation first','Two days: industrial/extraction automaton +100%, human -35%; Hope falls moderately.','servo',morale=-1),
        option('Fund joint training','Spend 1,500 steel and 1,000 rations. Two days: industrial/extraction human and automaton +50%.','shared',{'Steel':1500,'Food Rations':1000})]),
      incident(3,'A Steam Core Quality Recall',2,'A batch of assemblies needs replacement. Paying now, manufacturing replacements and restricting output carry different costs.',[
        option('Replace the suspect assemblies','Spend eight cores and 2,000 steel. Factory +75% for four days.','retool',{'Steam Cores':8,'Steel':2000},duration=4),
        option('Manufacture replacement machines','Manufacture two new automatons within three days. Factory -40% until resolved; success grants industry +150% and healthcare +25% for four days. Machines remain yours.',repair=2,reward='masterwork',duration=4),
        option('Restrict the Factory queue','Two days: Factory efficiency -40%.','rest')]),
      incident(3,'The Factory Queue Is Gridlocked',3,'Medical orders, fabrication and maintenance all demand priority. A single queue cannot serve every programme at once.',[
        option('Put medical orders first','Two days: healthcare +100%, industry -35%.','quarantine'),
        option('Prioritise bulk fabrication','Two days: industry +125%, food efficiency -25%.','overclock'),
        option('Cross-train production crews','Spend 2,000 steel and 700 rations. Two days: industrial/extraction human and automaton +50%.','shared',{'Steel':2000,'Food Rations':700})]),
      incident(3,'The Assembly Compact',5,'The commonwealth can attempt a masterwork, distribute equipment or settle on shared standards.',[
        option('Commission a masterwork','Manufacture two new automatons within five days. Factory -40% until resolved; success grants industry +150% and healthcare +25% for four days. Machines remain yours.',repair=2,work_days=8,reward='masterwork',duration=4),
        option('Equip the whole city','Spend eight cores and 3,000 steel. Four days: all workplaces +25% efficiency, citywide insulation +1.','equipment',{'Steam Cores':8,'Steel':3000},duration=4),
        option('Adopt shared standards','Three days: industrial/extraction human and automaton efficiency +50%.','shared',duration=3)])]
