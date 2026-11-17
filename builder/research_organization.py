"""Explicit columns, visible prerequisites and consolidation of small research."""
from collections import defaultdict


# One entry is one screen slot: canonical-id followed by effects consolidated
# into that upgrade. Recipe-unlock definitions are never consolidated away.
COLD = [
 [
  ['WorkshopSpeed1+WorkshopHeat','WorkshopSpeed2','WorkshopSpeed3','WorkshopBench','WorkshopSteam','WinterArtisanGuilds'],
  ['StarterGeneratorGrates+BoilerBufferDrums','GeneratorDraught','MasteryOverdriveValves','MasteryOverdriveRecovery','GeneratorReheat+RecuperatingAccumulators','GeneratorSeal+GovernorSafeties'],
  ['StarterHubValves|EdgeBrazierGrates','MasteryHubDraught|EdgeBrazierRadius','HubPipeLagging','SteamTrunklines|EdgeBrazierNetworks','HubReturnLines|EdgeCompactHeatingGrid','CompactHeatingGrid'],
  ['MasteryAutomatonCalibration','AutomatonSawmillServos+AutomatonSteelworksServos+AutomatonWallDrillServos','ClockworkSynchronisers','MasteryMedicalAutomata','AutonomousMaintenance',''],
  ['ServiceLiners','WorksiteWarmBreaks+StormDutyClothing','CondensateHeaters','ProtectedHealthcareHeaters','IndustrialHeatRecovery','CivicLagging'],
  ['MiningCoreMounts+HothouseCoreMounts+FieldInfirmaries','ToolLibraries','MineLifts','IndustrialStorm','MasteryWorksNetwork','MasteryFactoryLines'],
  ['CitywideLagging','CitywideLagging2','CitywideLagging3','CitywideLagging4','CitywideLagging5','CitywideLagging6'],
 ],
 [
  ['','','Cores1','Cores2','Cores3','MassCoreFabrication'],
  ['StarterTimberTools+SawmillWindwalls+SawmillSurvey+MasteryTimberSurvey+EdgeSawmillCalibration+EdgeTimberMaps','SawmillOutput2','','','',''],
  ['StarterSteelTooling','SteelworksRolling+SteelworksRefractoryLining','MasterySteelFeeders','SteelworksShiftTeams','SteelworksContinuousCasting+IndustrialHeat+SteelOutput',''],
  ['ThumperScreens','CoalHandlingShelters','SteamThumperFeed','CoalCircuit','ThumperWinterization','ThumperOutput2'],
  ['','MineAirlocks','DrillGearboxes','CoalMineHeat+DrillHeat+EdgeCoalCrews','DrillOutput','CoalMineOutput3'],
  ['MasteryKilnRotas+EdgeKilnCrews','KilnHeat','MasteryFuelDistrict','','',''],
  ['StarterGatheringTeams+GatheringWorkwear','GatheringLogistics+GatheringSort+GatheringReach','GatheringHeat3','','',''],
 ],
 [
  ['FieldDressings+StarterWardStoves','MasteryClinicRotas+ConservativeSurgery+EdgeClinicRotas','MedicalEfficiency2+LimbSparingSurgery','WardProtocols+InfirmaryRounds+MasteryClinicSteam+InfirmaryRecoveryWards','MedicalHeat3','MedicalHeat4'],
  ['CropRotation','MasteryIrrigation','MasteryProvisionLines','SeedSelection2','HothouseHeat3','HothouseHeat4'],
  ['StarterHuntingKits+HuntersFieldKits+HuntingTrails','HuntingSleds','HangarCargoSlings','FlightRigs','',''],
  ['MasteryPrepBenches+EdgeMealPrep','CookhouseSteamShell','','','CookhouseHeat2',''],
  ['TentWindbreaks','BunkhouseDraughtLocks','CareHouseLiners','HouseVestibules','HouseInsulatedFloors',''],
  ['PreventiveMedicine','','','','',''],
  ['CivicReassurance','CivicGrievances','CivicRecovery','CivicMutualAid','',''],
 ],
 [
  ['EarlyScoutSleds','','ScoutBearings','ScoutOverhaul','EndlessRelayWorkshops',''],
  ['','OutpostDispatch','ConvoyBearings','ConvoyRelays','',''],
  ['DepotShelving+MasteryCargoRacks','StackedDepots','ModularWarehouses','DistributedCaches','','ReclamationStockyards'],
  ['EdgeDepotFuel','CoalStorageCompactors','','CoalReserveBins','DeepCoalBins',''],
  ['EmergencyFoodBins+EdgeRationReserve','FoodReserveBins','','','ProvisionCells','PolarProvisionVaults'],
  ['','SteelworksIngotRacks','','','',''],
  ['','RedeploymentKits','BuilderAssemblyPlatforms','','',''],
 ],
 [
  ['EdgeWarehouseSorting','EdgeWarehouseBaffles','EdgeWarehouseWinches','','',''],
  ['ScrapRecovery','DeepScrapRecovery','','','ClosedLoopMetallurgy',''],
  ['','RetortCharcoal','RapidCoking','ClosedCycleRetorts','','CoreChargedRetorts'],
  ['','CoalHeatedSeedbeds','FermentationBeds','','TimberSubstrateBeds','ArtificialSpring'],
  ['SlowSimmeredBroth','FuelledStockpots','','','PressureKitchens',''],
  ['EdgeWarehouseSalvage','','','','EdgeRecoveryLots',''],
  ['','','','','',''],
 ],
]
AUTUMN = [
 [
  ['AutumnWorkshopSpeed1+AutumnWorkshopSeals','AutumnWorkshopSpeed2','AutumnWorkshopSpeed3',''],
  ['AutumnShelterLiners+AutumnServiceLiners','AutumnWindproofWorksites','AutumnWinterLining','AutumnCompactHeat'],
  ['AutumnFuelWorkwear','','AutumnCondensateHeaters','AutumnSteamTrunklines'],
  ['AutumnStarterSafety+AutumnProfileGuardrails','AutumnMachineGuards','AutumnFabricationSafety','AutumnSafetyInfirmary'],
  ['','AutumnStormDutyClothing','','AutumnHealthcareHeaters'],
  ['AutumnReclaimedReloading+AutumnCoreFreeFabrication+AutumnFieldInfirmaries','AutumnAssemblyPlatforms','AutumnArtisanGuilds',''],
  ['','','','AutumnIndustrialHeaters'],
 ],
 [
  ['AutumnStarterGathering+AutumnGatheringRotas','AutumnGatheringReach','',''],
  ['AutumnStarterTimber+AutumnLogRacks+AutumnTimberMaps','','',''],
  ['AutumnFabricationShifts','AutumnExchangerTemplates','AutumnExchangerRigs','AutumnCompositeJigs'],
  ['','','AutumnKilnShifts',''],
  ['AutumnProfileJigs','','',''], [], [],
 ],
 [
  ['AutumnFieldDressings+AutumnPreventiveMedicine','AutumnMedicalRotas+AutumnConservativeSurgery','AutumnEmergencyWards+AutumnLimbSparingSurgery','AutumnRapidRounds'],
  ['AutumnStarterFishing','AutumnSeasonalFishing+AutumnNetCrews','AutumnColdwaterNets','AutumnFarWaterTrawlers'],
  ['AutumnKitchenRotas','AutumnFoodLineInsulation','',''], [], [], [], [],
 ],
 [
  ['AutumnForagerSleds','AutumnRelayMarkers','AutumnForagerMealRoutes',''],
  ['AutumnDockSignals','AutumnPortClearing','AutumnDockRosters','AutumnPortConsolidation'],
  ['AutumnDepotPallets','AutumnPortWarehouses','AutumnDistributedCaches','AutumnBulkStockyards'],
  ['','AutumnCoalCompactors','',''],
  ['','AutumnCampReserves','AutumnProvisionLockers',''],
  ['AutumnHeavyCargo','AutumnReloadingGantries','AutumnCraneBrakes','AutumnCraneRigging'],
  ['','AutumnRedeploymentKits','',''],
 ],
 [
  ['AutumnSteamCuredProfiles','','AutumnReusableFormwork',''],
  ['','AutumnFuelTemperedExchangers','','AutumnCompositeDies'],
  ['','AutumnRetortCharcoal','AutumnRapidCoking','AutumnClosedCycleRetorts'],
  ['','','AutumnCharcoalAlloy','AutumnRefractoryCasting'],
  ['AutumnSlowSimmeredBroth','','AutumnPressureKitchens',''],
  ['','AutumnBaitedNets','AutumnColdCurrentLures','AutumnDocksideSmokehouses'], [],
 ],
]


COMBINED_DESCRIPTIONS = {
    'WorkshopSpeed1': 'Workshops gain 35% workplace efficiency for both work roles and +1 insulation.',
    'AutumnWorkshopSpeed1': 'Workshops gain 35% workplace efficiency for both work roles and +1 insulation.',
    'StarterGeneratorGrates': 'The Generator burns 12% less coal and overdrive stress builds 10% more slowly.',
    'GeneratorReheat': 'The Generator burns 12% less coal and recovers from overdrive stress 25% faster.',
    'GeneratorSeal': 'The Generator burns 10% less coal. Overdrive stress builds 15% more slowly and recovers 10% faster.',
    'StarterGatheringTeams': 'Gathering Posts collect resources 45% faster and gain +1 insulation.',
    'GatheringLogistics': 'Gathering Posts collect resources 30% faster and gain 35% collection radius.',
    'MedicalEfficiency2': 'Medical Posts gain 50% healing efficiency for both work roles. Radical Treatment no longer causes amputations at Medical Posts.',
    'WardProtocols': 'Infirmaries gain 55% healing efficiency and +2 insulation. Medical Posts gain +1 insulation. Houses of Healing gain 75% healing efficiency.',
    'SteelworksContinuousCasting': 'All Steelworks grades produce 65% more steel and gain +3 insulation. Both Resource Depot sizes gain 50% steel capacity.',
}


def organize(specs, membership, native, guid):
    by_id = {t['id']: t for t in specs}
    by_guid = {t['guid']: t for t in specs}
    active = set().union(*(set(ids) for ids in membership.values()))
    consolidated = {}
    positions = {}
    for plan in (COLD, AUTUMN):
        for tab, branches in enumerate(plan):
            for lane, branch in enumerate(branches):
                for tier, alternatives in enumerate(branch):
                    for group in filter(None, alternatives.split('|')):
                        keys = group.split('+');target = by_id[keys[0]]
                        assert target['guid'] in active, ('Inactive organization target', target['id'])
                        assert target['guid'] not in positions, ('Repeated research slot', target['id'])
                        positions[target['guid']] = (tab, lane, tier)
                        sources = [by_id[k] for k in keys[1:]]
                        for source in sources:
                            for field in ('global_effects','effects','extra_effects'):
                                target[field] += [value for value in source[field] if value not in target[field]]
                            consolidated[source['id']] = target['id']
                            for mode, ids in membership.items():
                                if source['guid'] in ids:
                                    if target['guid'] not in ids:ids.append(target['guid'])
                                    ids.remove(source['guid'])
                        if sources:
                            descriptions = [t['description'].split('\n\nRequires:')[0] for t in [target] + sources]
                            target['description'] = COMBINED_DESCRIPTIONS.get(target['id'], '\n\n'.join(dict.fromkeys(descriptions)))
                            target['consolidated_upgrades'] = keys[1:]
                        target['pre_organization_tier'] = target['tier']
                        target['tier'] = tier
    active = set().union(*(set(ids) for ids in membership.values()))
    assert active == positions.keys(), ('Unassigned active research', [by_guid[g]['id'] for g in active - positions.keys()])
    core = by_id['MiningCoreMounts']
    core.update(title='Core-Saving Construction Standards', cost={'Wood':24,'Steel':10}, hours=4,
                description='Hothouses, Coal Mines, Wall Drills and Infirmaries cost one fewer Steam Core to construct across their supported grades. This removes the core requirement of basic core-powered buildings; advanced grades can still require cores. Wood and steel construction costs are unchanged.')
    by_id['AutumnReclaimedReloading'].update(title='Core-Saving Port Construction', cost={'Wood':24,'Steel':10}, hours=4,
                description='Reloading Stations, Machine Shops, Foundries and Infirmaries cost one fewer Steam Core to construct across their supported grades. Wood and steel costs are unchanged.')
    by_id['AutomatonSawmillServos']['title'] = 'Industrial Automaton Actuators'
    # Every non-tier requirement must be an actual visible line in the same lane.
    scopes = {g:{mode for mode, ids in membership.items() if g in ids} for g in active}
    tier_ids = {int(t['name'][0:2]): t['guid'] for t in native if 'TierUnlock' in t['name']}
    assert set(tier_ids) == {1,2,3,4,5}
    for tech in specs:
        if tech['guid'] not in active:
            tech['requires'] = [tier_ids[tech['tier']]] if tech['tier'] else []
    branches = defaultdict(list)
    for g, (tab, lane, tier) in positions.items():branches[tab,lane].append(g)
    for branch in branches.values():
        for child in sorted(branch, key=lambda g:positions[g][2]):
            tab, lane, tier = positions[child]
            candidates = [g for g in branch if positions[g][2] < tier and scopes[g] >= scopes[child]]
            candidates.sort(key=lambda g:positions[g][2], reverse=True)
            parent = next((g for g in candidates if not any(
                positions[g][2] < positions[h][2] < tier and scopes[h] & scopes[child] for h in branch)), None)
            tech = by_guid[child]
            tech['requires'] = ([tier_ids[tier]] if tier else []) + ([parent] if parent else [])
            tech['route'] = [tab, lane]
            tech['visible_parent'] = parent
    for mode, ids in membership.items():
        membership[mode] = sorted(ids, key=lambda g:(by_guid[g]['tier'], positions[g][0], positions[g][1], g))
    return consolidated
