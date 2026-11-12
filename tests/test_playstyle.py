"""Cross-feature checks for the new city strategies and production selectors."""
import itertools
import json
from pathlib import Path
import unittest


ROOT=Path(__file__).resolve().parents[1]


class PlaystyleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog=json.loads((ROOT/'mod/catalog.json').read_text())
        cls.techs={t['id']:t for t in cls.catalog['technologies']}
        cls.by_guid={t['guid']:t for t in cls.techs.values()}
        cls.recipes={r['id']:r for r in cls.catalog['recipes']}

    def ancestors(self,g):
        result=set()
        def visit(x):
            if x in result:return
            result.add(x)
            for p in self.by_guid.get(x,{}).get('requires',[]):visit(p)
        visit(g)
        return result

    def test_new_research_is_limited_to_appropriate_modes(self):
        keys=self.catalog['playstyle_research']
        self.assertEqual(sum(self.techs[key]['added_in']=='3.9.0' for key in keys),22)
        self.assertEqual(sum(self.techs[key]['added_in']=='3.10.0' for key in keys),25)
        for key in keys:
            t=self.techs[key]
            actual={mode for mode,ids in self.catalog['scenario_additions'].items() if t['guid'] in ids}
            self.assertEqual(actual,set(t['scenarios']),key)
        self.assertEqual(self.techs['BuilderAssemblyPlatforms']['scenarios'],['Default_Endless_Builders'])
        edge=set(self.catalog['scenario_additions']['Reconquest'])
        for key in ('BoilerBufferDrums','ArtificialSpring','AutonomousMaintenance','BuilderAssemblyPlatforms'):
            self.assertNotIn(self.techs[key]['guid'],edge)
        for key in ('SlowSimmeredBroth','LimbSparingSurgery','FieldInfirmaries','CondensateHeaters','WinterArtisanGuilds','CoreChargedRetorts'):
            self.assertIn(self.techs[key]['guid'],edge)

    def test_production_selectors_never_exceed_four_options(self):
        # Native maxima include law-dependent cooking choices and mutually
        # exclusive native extraction upgrades. Metadata is also checked against
        # emitted requirement bytes by the independent owned-build validator.
        native_max={'Factory':2,'Cookhouse':2,'Charcoal Kiln':1,'Hothouse':1,
                    'Industrial Hothouse':1,'Fishing Harbour':1,'Army Warehouse':3,
                    'Profiles Manufacture':1,'Machine Shop':1,'Foundry':1}
        for mode,ids in self.catalog['scenario_additions'].items():
            for building,base in native_max.items():
                recipes=[r for r in self.recipes.values() if r['building']==building and r['unlock'] in ids]
                for path in {p for r in recipes for p in r['targets']}:
                    station=[r for r in recipes if path in r['targets']]
                    relevant={r['unlock'] for r in station}
                    for bits in itertools.product((False,True),repeat=len(relevant)):
                        learned={g for g,value in zip(sorted(relevant),bits) if value}
                        if any(not (self.ancestors(g)&relevant)<=learned for g in learned):continue
                        visible=[r for r in station if r['unlock'] in learned and not set(r.get('excludes',[]))&learned]
                        self.assertLessEqual(base+len(visible),4,(mode,path,[r['id'] for r in visible]))

    def test_broth_conserves_food_but_costs_fuel_and_throughput(self):
        broth=self.recipes['SlowSimmeredBroth'];stock=self.recipes['FuelledStockpots']
        self.assertGreater(broth['amount']/broth['inputs']['Raw Food'],stock['amount']/stock['inputs']['Raw Food'])
        self.assertGreater(broth['inputs']['Coal']/broth['amount'],stock['inputs']['Coal']/stock['amount'])
        self.assertLess(broth['amount']/broth['hours'],stock['amount']/stock['hours'])

    def test_retort_replacement_preserves_a_real_production_choice(self):
        for prefix in ('','Autumn'):
            retort=self.recipes[prefix+'RetortCharcoal'];closed=self.recipes[prefix+'ClosedCycleRetorts']
            rapid=self.recipes[prefix+'RapidCoking']
            self.assertIn(closed['unlock'],retort['excludes'])
            net=closed['amount']-closed['inputs']['Coal']
            self.assertGreater(net/closed['inputs']['Wood'],retort['amount']/retort['inputs']['Wood'])
            self.assertLess(net/closed['hours'],rapid['amount']/rapid['hours'])

    def test_core_conversion_recipes_require_renewable_core_research(self):
        for key in ('CoreChargedRetorts','ArtificialSpring','IndustrialArtificialSpring'):
            recipe=self.recipes[key]
            self.assertEqual(recipe['inputs']['Steam Cores'],1)
            self.assertIn(self.techs['Cores3']['guid'],self.ancestors(recipe['unlock']))
        self.assertEqual(self.recipes['CoreChargedRetorts']['building'],'Charcoal Kiln')
        self.assertNotEqual(self.recipes['ArtificialSpring']['building'],'Factory')

    def test_all_added_research_is_half_duration_with_higher_workshop_output(self):
        self.assertEqual(self.catalog['perk_research_duration_multiplier'],0.5)
        self.assertEqual(self.catalog['base_research_multiplier']/1.25,1.25)
        for tech in self.techs.values():
            self.assertEqual(tech['hours'],tech['unscaled_hours']*0.5,tech['id'])
            self.assertGreater(tech['hours'],0)

    def test_new_recipe_upgrades_replace_predecessors(self):
        for previous,next_key in [('Cores3','MassCoreFabrication'),('DeepScrapRecovery','ClosedLoopMetallurgy'),
                                  ('FuelledStockpots','PressureKitchens'),('WarehouseSalvage','EdgeRecoveryLots'),
                                  ('CoalHeatedSeedbeds','TimberSubstrateBeds'),('IndustrialCoalSeedbeds','TimberSubstrateBeds'),
                                  ('BaitedNets','AutumnColdCurrentLures'),('AdvancedBaitedNets','AutumnColdCurrentLures')]:
            self.assertIn(self.techs[next_key]['guid'],self.recipes[previous]['excludes'])
        mixed=self.recipes['EdgeRecoveryLots']
        self.assertEqual(mixed['inputs']['Steam Cores'],1)
        self.assertEqual(mixed['byproducts'],{'Wood':40})
        self.assertEqual(mixed['amount'],100)

    def test_autumn_component_reuse_links_existing_stations(self):
        profiles=self.recipes['AutumnReusableFormwork']
        composites=self.recipes['AutumnRefractoryCasting']
        exchangers=self.recipes['AutumnCompositeDies']
        self.assertIn(exchangers['output'],profiles['inputs'])
        self.assertIn(profiles['output'],composites['inputs'])
        self.assertIn(composites['output'],exchangers['inputs'])
        self.assertEqual({r['building'] for r in (profiles,composites,exchangers)},
                         {'Profiles Manufacture','Machine Shop','Foundry'})


if __name__=='__main__':
    unittest.main()
