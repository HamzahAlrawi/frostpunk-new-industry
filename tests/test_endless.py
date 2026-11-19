"""Public, asset-free checks for the shipped Reconstruction progression graph."""
import json
from pathlib import Path
import unittest

from builder.tools.native_binary import Cursor,SchemaError
from builder.tools.scenario_reader import expression,effect


class ReconstructionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mode=json.loads((Path(__file__).resolve().parents[1]/'mod/catalog.json').read_text())['endless']

    def test_five_tracks_and_unique_mode_parameter(self):
        self.assertEqual([t['id'] for t in self.mode['tracks']],['Projects','Foundry','Gardens','Salvage','Contracts'])
        self.assertEqual(len({self.mode[k] for k in ('parameter','enabled','disabled')}),3)
        road=self.mode['story']['winter_road']
        faultline=self.mode['story']['faultline']
        rescue_quests=sum(len(routes) for routes in faultline['rescue_quests'].values())
        self.assertEqual(self.mode['quests'],60+len(self.mode['frontiers']['missions'])+len(self.mode['frontiers']['incidents'])
                         +len(self.mode['frontiers']['work_orders'])+len(self.mode['story']['acts'])
                         +len(self.mode['story']['lifeline']['missions'])+len(road['missions'])
                         +len(road['projects'])+len(road['aftermath'])
                         +len(faultline['missions'])+rescue_quests+len(faultline['opening_quests']))
        self.assertGreater(self.mode['events'],121)

    def test_projects_have_permanent_rewards_and_no_deadlines(self):
        stages=self.mode['tracks'][0]['stages']
        self.assertEqual(len(stages),12)
        self.assertEqual(stages[-1]['next'],99)
        self.assertEqual(len([r for r in self.mode['rewards'] if r['id'].startswith('Reconstruction/')]),11)
        for number,stage in enumerate(stages,1):
            self.assertEqual(stage['state'],number)
            self.assertNotIn('deadline',stage)
            if number<len(stages):self.assertEqual(stage['next'],number+1)
            if number>1:
                previous=stages[number-2]['cost']
                self.assertTrue(all(value>previous.get(name,0) for name,value in stage['cost'].items()))

    def test_relief_routes_repeat_and_survive_failed_deliveries(self):
        for track in self.mode['tracks'][1:4]:
            stages={s['state']:s for s in track['stages']}
            self.assertEqual(len(stages),10)
            for state,stage in stages.items():
                self.assertEqual(stage['cooldown'],7)
                self.assertIn(stage['next'],stages)
                self.assertIn(stage['failure'],stages)
                self.assertEqual(stage['failure']//2,state//2)
                self.assertNotEqual(stage['failure'],state)
                self.assertTrue(stage['cargo'])
                if state//2==1:self.assertIsNone(stage['deadline'])
                else:self.assertEqual(stage['deadline'],8)
            self.assertEqual(stages[10]['next'],11)
            self.assertEqual(stages[11]['next'],10)

    def test_contracts_are_optional_timed_and_continue_at_final_grade(self):
        stages={s['state']:s for s in self.mode['tracks'][4]['stages']}
        self.assertEqual(len(stages),18)
        for state,stage in stages.items():
            self.assertTrue(stage['optional'])
            self.assertEqual(stage['deadline'],3)
            self.assertEqual(stage['failure']//10,state//10)
            self.assertEqual(stage['next']//10,min(state//10+1,6))
            self.assertNotEqual(stage['next'],state)
            self.assertIn(stage['next'],stages)

    def test_no_old_deadline_can_reach_a_new_occurrence(self):
        for track in self.mode['tracks'][1:]:
            by={s['state']:s for s in track['stages']}
            for origin in by.values():
                if not origin.get('deadline'):continue
                frontier=[(origin['state'],0)]
                for _ in range(4):
                    following=[]
                    for state,elapsed in frontier:
                        stage=by[state]
                        for target in {stage['next'],stage['failure']}:
                            total=elapsed+stage['cooldown']
                            if target==origin['state']:self.assertGreater(total,origin['deadline'])
                            else:following.append((target,total))
                    frontier=following

    def test_decoder_rejects_unknown_and_truncated_classes(self):
        for decoder in (expression,effect):
            for raw in (b'\1UnknownClass\0',b'\1IntegerComparisonExpression\0\x19Constant'):
                with self.assertRaises((SchemaError,UnicodeDecodeError)):decoder(Cursor(raw))


if __name__=='__main__':unittest.main()
