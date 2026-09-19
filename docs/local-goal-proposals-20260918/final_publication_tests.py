"""Consistency checks of the completed publication, not scientific gates."""
import json
import math
import unittest
from pathlib import Path

DOC=Path(__file__).resolve().parent


class Publication(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.a=json.loads((DOC/'FINAL-AGGREGATE-PROJECTION.json').read_text())
        cls.account=json.loads((DOC/'FINAL-ACCOUNTING.json').read_text())
        cls.auth=json.loads((DOC/'FINAL-AUTHENTICATION.json').read_text())

    def test_full_population_and_weighting(self):
        a=self.a;rows=a['rows'];refs={r['reference'] for r in rows}
        self.assertEqual(len(rows),384);self.assertEqual(len(refs),32)
        self.assertEqual({(r['reference'],r['family'],r['horizon'],r['seed']) for r in rows},
            {(r,f,h,s) for r in refs for f in ['gmm','diffusion'] for h in [75,150] for s in [8301,8302,8303]})
        self.assertEqual({r['reference'] for r in a['source_effects']},refs)
        for e in a['source_effects']:
            for family in ['gmm','diffusion']:
                rr=[r for r in rows if r['reference']==e['reference'] and r['family']==family]
                self.assertAlmostEqual(e[family],sum(r['success'] for r in rr)/6)
            self.assertAlmostEqual(e['diffusion_minus_gmm'],e['diffusion']-e['gmm'])
        self.assertAlmostEqual(a['primary'],sum(e['diffusion_minus_gmm'] for e in a['source_effects'])/32)
        self.assertEqual(sum(a['paired_outcome_counts'].values()),192)

    def test_strata_and_published_counts(self):
        for cell in self.a['strata']:
            rr=[r for r in self.a['rows'] if all(r[k]==cell[k] for k in ['family','horizon','seed'])]
            self.assertEqual(len(rr),32);self.assertAlmostEqual(cell['success'],sum(r['success'] for r in rr)/32)
        for family,summary in self.a['supporting']['by_family'].items():
            rows=[r for r in self.a['rows'] if r['family']==family]
            self.assertEqual(summary['successes'],sum(r['success'] for r in rows))
            self.assertEqual(summary['physical_actions'],sum(r['steps'] for r in rows))
            self.assertTrue(all(r['failure'] is None for r in rows))
            self.assertTrue(all(r['steps']==2*r['horizon'] for r in rows if not r['success']))

    def test_resource_reconciliation(self):
        a=self.account;groups=a['groups']
        self.assertEqual(sum(v['workers'] for v in groups.values()),204)
        self.assertEqual(sum(v['allocation_seconds'] for k,v in groups.items() if k!='analysis')+a['failure_gpu_allocation_seconds'],a['gpu_allocation_seconds'])
        self.assertEqual(groups['analysis']['allocation_seconds'],a['cpu_allocation_wall_seconds'])
        self.assertEqual(a['attempts'],a['successful_coordinates']+3)
        self.assertEqual(sum(f['updates'] for f in self.a['fits']),72000)
        self.assertEqual(sum(f['row_presentations'] for f in self.a['fits']),9216000)
        self.assertEqual(self.auth['optimizer_updates_policy_recovery'],0)

    def test_backup_and_original_aggregate_binding(self):
        request=json.loads((DOC/'FINAL-BACKUP-REQUEST.json').read_text())
        verified=json.loads((DOC/'FINAL-BACKUP-VERIFIED.json').read_text())
        for k in ['sha256','bytes','files']:self.assertEqual(request[k],verified[k])
        original=self.a['original_aggregate']
        self.assertEqual({k:original[k] for k in ['sha256','bytes']},request['members'][original['archive_member']])
        self.assertEqual(len(request['members']),1733)
        for prefix in ['failed-run','prior-run','validation-run','run','failed-source','prior-source','validation-source','source',
                       'failed-control','prior-control','validation-control','new-control']:
            self.assertTrue(any(k.startswith(prefix+'/') for k in request['members']))


if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Publication))
    if not result.wasSuccessful():raise SystemExit(1)
    with (DOC/'FINAL-PUBLICATION-TESTS.json').open('x',encoding='utf8',newline='\n') as f:
        json.dump(dict(tests=result.testsRun,failures=0,errors=0,scientific_gates_added=0,
            model_or_simulator_calls=0,new_allocation_count=0,scope='Completed publication consistency only'),f,indent=2);f.write('\n')
