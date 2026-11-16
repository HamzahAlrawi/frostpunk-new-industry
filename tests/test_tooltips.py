"""Source coverage and cumulative-tooltip semantics without owned game assets."""
from collections import defaultdict
import json
from pathlib import Path
import unittest

from builder.modifier_conditions import split_technology_condition,with_technology_condition
from builder.research_curation import effect_signature,normalized


ROOT=Path(__file__).resolve().parents[1]


class TooltipTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog=json.loads((ROOT/'mod/catalog.json').read_text())
        cls.tooltips=cls.catalog['modifier_tooltips']

    def test_every_research_and_law_modifier_has_nonempty_source_text(self):
        rows=self.tooltips['records'];by={row['guid']:row for row in rows}
        self.assertEqual(len(rows),len(by))
        for row in rows:
            self.assertTrue(row['title'].strip())
            self.assertTrue(row['description'].strip())
            self.assertTrue(row['source_ids'])
            self.assertTrue(row['name_key'].startswith('Mods/NewIndustry/Modifier/'))
            self.assertTrue(row['description_key'].startswith('Mods/NewIndustry/Modifier/'))
        referenced={law['modifier'] for law in self.catalog['laws']}
        for tech in self.catalog['technologies']:
            referenced.update(tech['global_effects'])
            referenced.update(g for field in ('effects','extra_effects') for _,g in tech[field])
        self.assertLessEqual(referenced,by.keys())

    def test_each_insulation_chain_retains_totals_with_one_active_row(self):
        families=self.tooltips['cumulative_families']
        self.assertEqual(len(families),6)
        for family in families:
            stages=family['stages'];targets={p for stage in stages for info in stage['modifiers'] for p in info['targets']}
            for level in range(len(stages)+1):
                researched={stage['technology'] for stage in stages[:level]}
                before=defaultdict(int);after=defaultdict(int);rows=defaultdict(int)
                for stage in stages[:level]:
                    for info in stage['modifiers']:
                        for target in info['targets']:
                            before[target]+=info['increment']
                            if info['superseded_by'] not in researched:
                                after[target]+=info['total'];rows[target]+=1
                self.assertTrue(all(before[p]==after[p] for p in targets),(family['id'],level))
                self.assertTrue(all(rows[p]<=1 for p in targets),(family['id'],level))
        envelope=next(f for f in families if f['id']=='thermal-envelope')
        self.assertEqual([s['modifiers'][0]['total'] for s in envelope['stages']],[1,2,3,4,5,7])

    def test_predicates_preserve_scalar_views_and_refuse_overwriting_conditions(self):
        original=bytes(238);technology='12'*16
        conditioned=with_technology_condition(original,technology)
        predicate,scalars=split_technology_condition(conditioned)
        self.assertEqual(predicate,dict(technology=technology,inverted=True))
        self.assertEqual(scalars,original)
        self.assertEqual(normalized(conditioned),original)
        with self.assertRaises(AssertionError):with_technology_condition(conditioned,'34'*16)

    def test_effect_fingerprints_distinguish_different_supersession_conditions(self):
        tech=dict(guid='aa'*16,global_effects=[],effects=[('bb'*16,'cc'*16)],extra_effects=[])
        def fingerprint(next_technology):
            records={'cc'*16:('Place',b'NI test',with_technology_condition(bytes(238),next_technology))}
            return effect_signature(tech,records)
        self.assertNotEqual(fingerprint('12'*16),fingerprint('34'*16))


if __name__=='__main__':unittest.main()
