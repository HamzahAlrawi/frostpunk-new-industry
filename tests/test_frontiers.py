"""Asset-free campaign reachability and UI-fit regression checks."""
import json
from pathlib import Path
import unittest

from builder.tools.native_binary import Cursor
from builder.tools.scenario_reader import expression
from builder.tools.scenario_model import World


class FrontierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.meta=json.loads((Path(__file__).resolve().parents[1]/'mod/catalog.json').read_text())['endless']
        cls.front=cls.meta['frontiers']

    def test_all_six_branches_have_complete_nine_chapter_arcs(self):
        self.assertEqual([s['id'] for s in self.front['campaigns']],[1,2,3])
        self.assertEqual(len(self.front['missions']),29)
        for story in self.front['campaigns']:
            self.assertEqual(len(story['branches']),2)
            for path in (1,2):
                chosen=[m for m in self.front['missions'] if m['campaign']==story['id'] and m['path'] in (None,path)]
                self.assertEqual([m['phase'] for m in chosen],list(range(1,10)))

    def test_objectives_require_actual_city_development(self):
        kinds={g['kind'] for m in self.front['missions'] for g in m['goals']}
        self.assertEqual(kinds,{'build','research','produce','automate','checks'})
        for mission in self.front['missions']:
            self.assertTrue(mission['goals'])
            for goal in mission['goals']:
                self.assertTrue(goal['text'])
                if goal['kind']=='produce':
                    self.assertEqual(len(goal['target']),6)
                    self.assertGreaterEqual(goal['quantity'],2)
                if goal['kind']=='checks':self.assertGreaterEqual(goal['quantity'],8)

    def test_doctrines_and_incidents_have_distinct_effect_packages(self):
        branches=[b for s in self.front['campaigns'] for b in s['branches']]
        self.assertEqual(len({b['bonus'] for b in branches}),6)
        self.assertEqual(sum('upkeep' in b for b in branches),3)
        self.assertEqual(len(self.front['incidents']),18)
        self.assertEqual(len({i['title'] for i in self.front['incidents']}),18)
        for cid in (1,2,3):self.assertEqual(sum(i['campaign']==cid for i in self.front['incidents']),6)

    def test_all_mode_cards_and_research_tabs_fit_their_frames(self):
        ui=self.meta['ui']
        self.assertEqual(ui['mode_columns'],6)
        self.assertEqual(ui['research_tabs'],9)
        self.assertEqual((ui['native_orientation'],ui['native_alignment']),(1,3))
        self.assertLessEqual(6*ui['mode_width']+5*ui['mode_gap'],1163.95)
        self.assertLessEqual(ui['ornament_extent'],1163.95)
        self.assertLessEqual(178+9*ui['tab_width'],1200)

    def test_generator_predicate_respects_native_inversion(self):
        world=World(None,[],{},{});prefix=b'\1FrostpunkGeneratorIsActiveExpression\0'
        positive=expression(Cursor(prefix+b'\0'));negative=expression(Cursor(prefix+b'\1'))
        self.assertTrue(world.value(positive));self.assertFalse(world.value(negative))
        world.generator=False
        self.assertFalse(world.value(positive));self.assertTrue(world.value(negative))

    def test_response_and_repair_deadlines_are_bounded_and_explained(self):
        for incident in self.front['incidents']:
            self.assertGreaterEqual(incident['response_days'],1.5)
            self.assertLessEqual(incident['response_days'],5)
            self.assertEqual(len(incident['options']),3)
            self.assertFalse(incident['options'][-1]['cost'])
            self.assertFalse(incident['options'][-1]['repair'])
        for work in self.front['work_orders']:
            self.assertGreaterEqual(work['deadline'],4)
            self.assertLessEqual(work['deadline'],8)
            self.assertGreaterEqual(work['deadline']*10*0.75*0.75,self.front['automaton_hours']*work['quantity']*2)

    def test_three_separate_mode_definitions_use_unique_campaign_values(self):
        modes=self.meta['modes']
        self.assertEqual([m['title'] for m in modes],['Restoration','Whiteout','Machine Age'])
        self.assertEqual(len({m['value'] for m in modes}),3)
        self.assertTrue(all(len(m['title'])<=12 and len(m['subtitle'])<=8 for m in modes))


if __name__=='__main__':unittest.main()
