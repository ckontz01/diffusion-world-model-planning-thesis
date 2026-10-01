"""Additional parent identity manifests and initializer dependencies, no outcomes."""
import json
from dtv_success_cost import metadata as m

def main():
    m.REMOTE = m.REMOTE.replace("paths=[]", """paths=[]
paths += list((R/'data/stablewm/derived/candidate-pools/pusht-v1').glob('*/manifest.json'))
for study in ('gdp-cem-e14','gdp-cem-e16','gdp-cem-e18'):
 paths += list((R/'experiments'/study).glob('*/p2-manifests/**/queries.tsv'))
paths += [R/('envs/hi-lewm-artifact-py311-cu121-swm006/lib/python3.11/site-packages/stable_worldmodel/'+n) for n in ('envs/dmcontrol/dmcontrol.py','envs/dmcontrol/custom_tasks/reacher.py')]
""").replace("paths += list((R/'manifests/partitions'/ (task+'-v1')).glob('*.tsv'))", "pass").replace("paths += list((R/'manifests/partitions'/ (task+'-v1')).glob('*summary.json'))", "pass").replace("paths += list((R/'manifests'/study/task).rglob('*.tsv'))", "pass").replace("if study=='acid-alternative-v1':paths += list((R/'manifests'/study/task).glob('summary.json'))", "pass")
    # Reuse the transport but save an exclusive second receipt, retaining first.
    m.DOC=m.DOC/'additional';m.main()
if __name__=='__main__':main()
