"""Synthetic tests: never connect to a cluster or load project data."""
import csv
import importlib.util
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from e18_expanded_capacity_audit import identifiers, read_tsv, read_h5_ids, ledger, id_digest

class Tests(unittest.TestCase):
    def test_unknown_identifier_rejected_without_value(self):
        with self.assertRaisesRegex(ValueError,'values withheld'):
            identifiers([99],{1,2})
    def test_padding_and_duplicates(self):
        self.assertEqual(identifiers([1,1,2,-1],{1,2}),{1,2})
    def test_other_negative_rejected(self):
        with self.assertRaises(ValueError): identifiers([-2],{1,2})
    def test_digest_order_independent(self):
        self.assertEqual(id_digest({1,2}),id_digest({2,1}))
    def test_ledger_deduplicates_overlaps(self):
        d=ledger({'P3':{1,2,3,4}}, {'a':{1,2},'b':{2,3}},['a','b'])
        self.assertEqual([r['newly_excluded'] for r in d['P3']['steps']],[2,1])
        self.assertEqual(d['P3']['remaining_count'],1)
    def test_ledger_no_input_mutation(self):
        parts={'P3':{1,2}};ledger(parts,{'a':{1}},['a'])
        self.assertEqual(parts,{'P3':{1,2}})
    def test_tsv_success_column_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'table.tsv';p.write_text('episode_id\tsuccess\n1\tSECRET\n')
            with self.assertRaisesRegex(ValueError,'schema'):read_tsv(p,{1})
    def test_tsv_identifiers_only(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'membership.tsv';p.write_text('episode_id\tepisode_length\n1\t180\n2\t200\n')
            ids,meta=read_tsv(p,{1,2});self.assertEqual(ids,{1,2})
            self.assertNotIn('ids',meta)
    def test_h5_source_and_target_union_without_cost_read(self):
        touched=[]
        class DS:
            dtype=SimpleNamespace(kind='i')
            def __init__(self,name,values): self.name=name;self.values=values
            def __getitem__(self,index): touched.append(self.name);return self.values
        class F(dict):
            def __enter__(self):return self
            def __exit__(self,*args):pass
        f=F(source_episode_id=DS('source',[1,2]),target_episode_id=DS('target',[2,3]),costs=DS('costs',[888]))
        hp=SimpleNamespace(File=lambda *args:F(f),Dataset=DS)
        np=SimpleNamespace(unique=lambda v:SimpleNamespace(tolist=lambda:sorted(set(v))))
        with patch.dict(sys.modules,{'h5py':hp,'numpy':np}):
            union,old,meta=read_h5_ids(Path('synthetic.h5'),{1,2,3})
        self.assertEqual(union,{1,2,3});self.assertEqual(old,{1,2})
        self.assertEqual(touched,['source','target'])
        self.assertEqual(meta['target_or_other_ids_not_in_old_projection'],1)
        self.assertFalse(meta['whole_hdf5_hashed'])

if __name__=='__main__':unittest.main()
