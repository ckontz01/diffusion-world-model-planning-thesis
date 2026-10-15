import ast,unittest
from .submit import program

class Repair(unittest.TestCase):
    def test_only_configured_GPU_QOS_and_new_journals(self):
        p=program('a'*64,{'source_commit':'b'*40})
        ast.parse(p,feature_version=(3,6))
        self.assertIn("--qos=normal-a6000",p);self.assertNotIn('--account=',p)
        self.assertIn('SBATCH-R1-',p);self.assertIn('SUBMIT-R1-STARTED',p)
        self.assertNotIn("write('SUBMISSION-ERROR.json'",p)
        self.assertIn('known_job_ids',p)

if __name__=='__main__':unittest.main()
