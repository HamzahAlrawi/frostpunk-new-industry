"""Regression checks for research membership, timing, effects, and line geometry."""
import json
import struct
from pathlib import Path
import unittest

from builder.research_curation import REMOVED_TEAMS, place_scalar_offset
from builder.research_layout import geometry_errors, LANES, _solve


ROOT = Path(__file__).resolve().parents[1]


class ResearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = json.loads((ROOT / 'mod/catalog.json').read_text())
        cls.techs = cls.catalog['technologies']
        cls.by_guid = {t['guid']:t for t in cls.techs}
        cls.by_id = {t['id']:t for t in cls.techs}

    def test_team_perks_retired_and_no_active_dependencies(self):
        self.assertEqual(set(self.catalog['removed_team_perks']), REMOVED_TEAMS)
        retired = {self.by_id[key]['guid'] for key in REMOVED_TEAMS}
        for scenario, ids in self.catalog['scenario_additions'].items():
            self.assertFalse(retired & set(ids), scenario)
            for g in ids:
                self.assertFalse(retired & set(self.by_guid[g]['requires']), self.by_guid[g]['id'])

    def test_unique_effects_within_each_scenario(self):
        for scenario, ids in self.catalog['scenario_additions'].items():
            seen = {}
            for g in ids:
                tech = self.by_guid[g]
                fingerprint = tech['effect_fingerprint']
                self.assertNotIn(fingerprint, seen, (scenario, tech['id'], seen.get(fingerprint)))
                seen[fingerprint] = tech['id']

    def test_layout_spacing_and_all_prerequisite_lines(self):
        for scenario, ids in self.catalog['scenario_additions'].items():
            for name, category in self.catalog['research_tabs']:
                nodes = [self.by_guid[g] for g in ids if self.by_guid[g]['category'] == category]
                self.assertTrue(all(t['column'] in LANES for t in nodes))
                self.assertEqual(geometry_errors(nodes), [], (scenario, name))

    def test_active_mod_requirements_exist_and_are_not_later(self):
        for scenario, ids in self.catalog['scenario_additions'].items():
            members = set(ids)
            for g in ids:
                tech = self.by_guid[g]
                self.assertEqual(len(tech['requires']), len(tech['prerequisite_names']))
                self.assertIn('Requires: ', tech['description'])
                for parent in tech['requires']:
                    if parent in self.by_guid:
                        self.assertIn(parent, members, (scenario, tech['id']))
                        self.assertLessEqual(self.by_guid[parent]['tier'], tech['tier'])

    def test_opening_and_midgame_tools_have_deliberate_timing(self):
        expected = {'StarterTimberTools':0, 'SawmillOutput2':1, 'GatheringLogistics':1,
                    'HuntingSleds':1, 'ScoutBearings':2, 'ScoutOverhaul':3,
                    'ConvoyBearings':2, 'ConvoyRelays':3, 'WardProtocols':3,
                    'GatheringHeat3':2, 'SeedSelection2':3, 'FlightRigs':3,
                    'MiningCoreMounts':0,'AutumnReclaimedReloading':0,'DeepScrapRecovery':1}
        for key, tier in expected.items():
            tech = self.by_id[key]
            self.assertEqual(tech['tier'], tier)
        for key in ('MiningCoreMounts','AutumnReclaimedReloading'):
            self.assertEqual(self.by_id[key]['requires'],[])
            self.assertEqual(self.by_id[key]['cost'],{'Wood':24,'Steel':10})
            self.assertEqual(self.by_id[key]['hours'],2)

    def test_all_non_tier_requirements_are_visible_in_the_same_column(self):
        for mode,ids in self.catalog['scenario_additions'].items():
            for g in ids:
                tech=self.by_guid[g]
                parents=[self.by_guid[p] for p in tech['requires'] if p in self.by_guid]
                self.assertLessEqual(len(parents),1,(mode,tech['id']))
                for parent in parents:
                    self.assertEqual(parent['category'],tech['category'])
                    self.assertEqual(parent['column'],tech['column'])
                    self.assertLess(parent['tier'],tech['tier'])
                self.assertEqual(len(tech['requires'])-len(parents),int(tech['tier']>0))

    def test_six_thermal_envelopes_form_one_unbroken_column(self):
        keys=['CitywideLagging']+['CitywideLagging'+str(n) for n in range(2,7)]
        for tier,key in enumerate(keys):
            tech=self.by_id[key]
            self.assertEqual(tech['tier'],tier)
            if tier:self.assertEqual(tech['visible_parent'],self.by_id[keys[tier-1]]['guid'])
        self.assertGreater(self.by_id[keys[-1]]['cost']['Steam Cores'],0)

    def test_civic_laws_have_shared_research_and_distinct_policies(self):
        self.assertEqual(len(self.catalog['laws']),4)
        for law in self.catalog['laws']:
            self.assertEqual(law['book'],'Civic Charters')
            self.assertEqual(law['cooldown'],18)
            for ids in self.catalog['scenario_additions'].values():self.assertIn(law['research'],ids)
        self.assertEqual(len({law['modifier'] for law in self.catalog['laws']}),4)

    def test_three_core_factory_recipe_uses_a_steam_core_icon(self):
        recipe=next(r for r in self.catalog['recipes'] if r['id']=='MassCoreFabrication')
        self.assertEqual(recipe['icon_atlas'],'UI\\Elements\\Resources_Icos.dds')
        self.assertEqual(recipe['icon'],[1,0])

    def test_layout_checker_rejects_icon_and_line_collisions(self):
        def node(g, column, tier, parents=()):
            return dict(id=g, guid=g, column=column, tier=tier, requires=parents)
        self.assertTrue(geometry_errors([node('a',2,0),node('b',4,0)]))
        self.assertTrue(geometry_errors([node('a',2,0),node('b',8,2,['a']),node('c',5,1)]))
        self.assertTrue(geometry_errors([node('a',2,0),node('b',8,1,['a']),node('c',8,0),node('d',2,1,['c'])]))
        self.assertEqual(geometry_errors([node('a',2,0),node('b',2,1,['a']),node('c',2,2,['b'])]), [])

    def test_place_icon_atlas_shifts_scalars_and_corruption_is_rejected(self):
        base=bytearray(238)
        struct.pack_into('<II',base,76,0,2)
        self.assertEqual(place_scalar_offset(base,96),96)
        atlas=b'\1UI\\Tiles\\Icons.dds\0'
        expanded=base[:32]+atlas+base[33:]
        self.assertEqual(len(expanded),257)
        self.assertEqual(place_scalar_offset(expanded,96),115)
        struct.pack_into('<i',expanded,96,2)
        with self.assertRaises(AssertionError):
            place_scalar_offset(expanded,96)

    def test_dense_intermediate_tier_keeps_a_clear_prerequisite_path(self):
        nodes=[dict(id='parent',guid='p',tier=1,requires=[]),
               dict(id='child',guid='c',tier=3,requires=['p'])]
        nodes += [dict(id='middle'+str(i),guid=str(i),tier=2,requires=[]) for i in range(7)]
        positions=_solve(nodes,{t['guid']:1 for t in nodes})
        self.assertIsNotNone(positions)
        for tech in nodes:tech['column']=positions[tech['guid']]
        self.assertEqual(geometry_errors(nodes),[])


if __name__ == '__main__':
    unittest.main()
