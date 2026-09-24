"""Reviewed selector, without the preparation-only CPU environment side effect."""
import common
from policy import Selector, Decision
MODE='committed_feedback'
class CommittedFeedbackSelector(Selector):
    MODES=Selector.MODES+(MODE,)
    def select(self,tree,h,ledger,mode=MODE,seed=94021):
        if mode!=MODE: return super().select(tree,h,ledger,mode,seed)
        committed=super().select(tree,h,ledger,'static',seed)
        return Decision(committed.prefix,None,MODE,committed.values,False)
