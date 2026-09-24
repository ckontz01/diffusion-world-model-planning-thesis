"""Protocol/estimator wiring tests and independent checks of the one saved report."""
import base
import copy, math, subprocess, sys, unittest
import numpy as np
import protocol
from planned_analysis import contrasts, analyze, sensitivity, NAMES

class ProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.e=base.read(base.HERE/'ELIGIBILITY.json'); cls.c=base.read(base.HERE/'PROTOCOL.json'); cls.g=base.read(base.HERE/'GRID.json')
    def test_exact_grid_and_resources(self):
        self.assertTrue(protocol.validate(self.c,self.g,self.e)['valid'])
        self.assertEqual(len(self.g),8197)
    def test_single_baseline_actual_observation(self):
        self.assertEqual(sum(j.get('control')=='early-replan' for j in self.g),512)
        self.assertTrue(all(j['pair'] is None for j in self.g if j.get('control')=='early-replan'))
    def test_only_four_new_fits_no_collection(self):
        fits=[j for j in self.g if j['stage']=='fitting']
        self.assertEqual([(j['seed'],j['updates']) for j in fits],[(94411,192),(94412,192),(94421,192),(94422,192)])
        self.assertFalse(any(j['stage']=='collection' for j in self.g))
    def test_roles_and_canonical_disjointness(self):
        excluded=set(self.e['prior_union'])|set(self.e['rb2'])|set(sum(self.e['acv0'].values(),[]))
        selected=set(self.e['selected_references'])
        self.assertEqual(len(excluded),944); self.assertFalse(selected&excluded)
        self.assertEqual(len(selected),512);self.assertTrue(all(0<=i<1600 for i in selected))
        self.assertEqual(len({r['source_key'] for r in self.e['records'].values()}),512)
    def test_rotation_balanced(self):
        first=[j['control']+str(j['pair']) for j in self.g if j.get('reference')==self.e['selected_references'][0]]
        offsets=[]
        for ref in self.e['selected_references']:
            rows=[j for j in self.g if j.get('reference')==ref]
            offsets.append(first.index(rows[0]['control']+str(rows[0]['pair'])))
        self.assertTrue(all(offsets.count(k)==32 for k in range(16)))
    def test_tampered_grid_rejected(self):
        g=copy.deepcopy(self.g);g[4]['reference']=931
        with self.assertRaises(AssertionError): protocol.validate(self.c,g,self.e)
    def test_execution_always_rejected(self):
        r=subprocess.run([sys.executable,'-B',str(base.HERE/'protocol.py'),'--execute'],capture_output=True,text=True)
        self.assertNotEqual(r.returncode,0);self.assertIn('no research execution',r.stderr)
    def test_binary_shapes_missing_data_rejected(self):
        with self.assertRaises(ValueError): contrasts(np.zeros((1536,5)),np.zeros(512))
        a=np.zeros((512,3,5));a[0,0,0]=np.nan
        with self.assertRaises(ValueError): contrasts(a,np.zeros(512))
    def test_paired_interaction_and_seed_axis(self):
        a=np.zeros((512,3,5),int);a[:,0,3]=1;a[:,1,1]=1
        d=contrasts(a,np.zeros(512))
        np.testing.assert_array_equal(d[0,:,4],[1,-1,0])
        self.assertEqual(d.shape,(512,3,7));self.assertEqual(d[:,:,4].mean(),0)
    def test_early_outcome_used_once_in_source_mean(self):
        a=np.zeros((512,3,5),int);a[:,:,3]=1;a[:,2,3]=0
        d=contrasts(a,np.ones(512));np.testing.assert_allclose(d.mean(axis=1)[:,6],-1/3)
    def test_no_false_precision_identical_seed_copies(self):
        a=np.zeros((512,3,5),int);a[:256,:,3]=1
        r=analyze(a,np.zeros(512)); x=r['contrasts'][NAMES[0]]
        self.assertEqual(r['source_count'],512);self.assertEqual(x['effect'],.5)
        self.assertEqual(x['seed_mean_sample_sd'],0)
        margin=sensitivity()['hoeffding_family7_halfwidth']
        self.assertAlmostEqual(x['simultaneous_hoeffding95'][0],.5-margin)
        self.assertGreater(x['descriptive95'][1]-x['descriptive95'][0],.07)
    def test_family_bounds_and_sensitivity(self):
        s=sensitivity(); self.assertAlmostEqual(s['interaction_halfwidth'],2*s['hoeffding_family7_halfwidth'])
        self.assertAlmostEqual(s['hoeffding_family7_halfwidth'],2*math.sqrt(math.log(280)/1024))
        vals=[r['conservative_difference_scale'] for r in s['normal_80pct_two_sided_bonferroni7']]
        self.assertEqual(vals,sorted(vals));self.assertFalse(s['guaranteed_power'])

class SavedReportChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.r=base.read(base.HERE/'SAVED-DATA-MECHANISM.json')
    def test_all32_unique_actual_sources_and_original_endpoints(self):
        old=base.read(base.PUB/'REPORT.json');r=self.r
        self.assertEqual([x['reference'] for x in r['final_development']],old['source_ids'])
        for row,ys in zip(r['final_development'],old['binary_outcomes_by_source']):
            for a,y in zip(old['controls'],ys):self.assertEqual(row['actual'][a]['native_success'],y)
            self.assertNotIn('committed_feedback',row['actual'])
    def test_twenty_changed_not_twenty_gains(self):
        changed=[x for x in self.r['final_development'] if x['response_changed_suffix']]
        self.assertEqual(len(changed),20)
        self.assertEqual(sum(x['observed_active_minus_no_update'] for x in changed),1)
        self.assertEqual([x['reference'] for x in changed if x['observed_active_minus_no_update']==1],[847])
    def test_all_values_decompose(self):
        for row in self.r['predicted_prefix_decomposition']:
            for p in row['prefixes']:
                self.assertAlmostEqual(p['active_value'],p['terminal_success']+p['committed_active_value']+p['anticipated_feedback_increment'])
                self.assertAlmostEqual(p['anticipated_feedback_increment'],p['same_draw_feedback_increment']+p['quadrature_correction'])
    def test_validation_bank_scores_independently_recomputed(self):
        rows=self.r['validation'];self.assertEqual(len(rows),16)
        for row in rows:
            for p in row['prefixes']:
                if p['terminal']: continue
                y=np.array(p['suffix_outcomes'])
                for label in ('joint_prior','joint_conditional','ordinary_conditional'):
                    q=np.array(p[label]);qc=np.clip(q,1e-12,1-1e-12)
                    self.assertAlmostEqual(float(((q-y)**2).mean()),p['scores'][label]['brier'])
                    self.assertAlmostEqual(float((-y*np.log(qc)-(1-y)*np.log1p(-qc)).mean()),p['scores'][label]['bce'])
    def test_no_fit_or_reference_members_opened(self):
        names=self.r['authentication']['selected_members']
        self.assertFalse(any('collect-fit-' in n or 'reference-' in n or 'fit-dataset' in n for n in names))
        self.assertEqual(self.r['resources']['fits'],0);self.assertEqual(self.r['resources']['physics_steps'],0)
    def test_original_report_unchanged(self):
        self.assertEqual(base.digest((base.PUB/'REPORT.json').read_bytes()),self.r['authentication']['original_report_sha256'])

if __name__=='__main__': unittest.main(verbosity=2)
