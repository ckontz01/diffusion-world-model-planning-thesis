"""Check Pro-directed documentation arithmetic; no research imports or work."""
import json
from .check import DOC
from wm_diag0_native_v3.common import identity,write_new

def main():
    original=json.loads((DOC/'ARITHMETIC-CHECK-001.json').read_text())
    addendum=DOC/'REVIEW-CLARIFICATIONS-20261016.md';text=addendum.read_text(encoding='utf8')
    batches=64*16;old=batches;new=batches*5;extra=new-old
    assert (batches,new,extra)==(1024,5120,4096)
    assert '4,096' in text and 'UNRESOLVED' in text and 'rtol=2^-6' in text and 'atol=2^-8' in text
    assert 'independent inferential unit remains the parent source/root' in text
    row={'status':'PRO_DIRECTED_DOCUMENTATION_CLARIFICATIONS_CHECKED',
         'original_document':original['document'],'addendum':identity(addendum),'Pro_review':identity(DOC/'PRO-REVIEW-20261016.txt'),
         'prefix_batches':batches,'old_prefix_visual_invocations':old,'proposed_prefix_visual_invocations':new,
         'added_prefix_visual_invocations':extra,'extra_prefix_image_frames':0,
         'full_future_visual_observation_proprio_invocation_counts':'UNRESOLVED; bind actual code and reference suppliers before authorization',
         'future_runtime_sufficiency':'UNTESTED','all_previous_resource_gaps_retained':True,
         'new_research_operations':0,'implementation_authorized':False,'campaign_resumed':False}
    write_new(DOC/'REVIEW-CHECK-001.json',row);print(json.dumps(row,indent=2))

if __name__=='__main__':main()
