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
        self.assertEqual(len(keys),22)
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
                    'Industrial Hothouse':1,'Fishing Harbour':1,'Army Warehouse':3}
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


if __name__=='__main__':
    unittest.main()
