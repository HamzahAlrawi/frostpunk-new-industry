"""Regression checks for split choice circles and distant law connections."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from builder.law_layout import layout_errors


def branch():
    return [dict(id='root',book_guid='book',position=[-5,-6],default_available=True,branch_root=True,requires_laws=[],excludes_laws=[]),
            dict(id='left',book_guid='book',position=[-5,-10],default_available=True,requires_laws=['root'],excludes_laws=['right']),
            dict(id='right',book_guid='book',position=[-5,-10],default_available=True,requires_laws=['root'],excludes_laws=['left'])]


class LawLayoutTests(unittest.TestCase):
    def test_joined_choice_circle_is_required_and_unrelated_overlap_rejected(self):
        laws=branch()
        self.assertEqual(layout_errors(laws,{}),[])
        separated=deepcopy(laws);separated[2]['position'][0]+=6
        self.assertTrue(any('separated choice halves' in error for error in layout_errors(separated,{})))
        unrelated=dict(id='unrelated',book_guid='book',position=[-5,-10])
        self.assertTrue(any('added law' in error for error in layout_errors(laws+[unrelated],{})))

    def test_distant_nodes_and_connections_are_rejected(self):
        laws=branch()
        for law in laws[1:]:law['position']=[-5,-16]
        errors=layout_errors(laws,{})
        self.assertTrue(any('remote node' in error for error in errors))
        self.assertTrue(any('distant link' in error for error in errors))

    def test_all_published_law_branches_are_compact_in_both_books(self):
        catalog=json.loads((Path(__file__).resolve().parents[1]/'mod/catalog.json').read_text())
        self.assertEqual(layout_errors(catalog['laws'],{}),[])
        for book in ('Adaptation','Administration'):
            laws=[law for law in catalog['laws'] if law['book']==book]
            self.assertEqual(len(laws),16)
            self.assertEqual(len({tuple(law['position']) for law in laws}),12)


if __name__=='__main__':unittest.main()
