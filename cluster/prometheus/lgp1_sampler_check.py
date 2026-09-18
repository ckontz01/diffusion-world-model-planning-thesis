"""Artificial strict-determinism check inside the authorized GPU allocation."""
import torch
from local_goal_models import sample,categorical_cdf

def check(device='cpu'):
    assert torch.are_deterministic_algorithms_enabled()
    class Fixed:
        family='gmm'
        def __call__(self,*args):
            logits=torch.tensor([[0.,-1.,2.,-3.,.25,1.,-2.,.5]],device=device)
            means=torch.arange(8,device=device,dtype=torch.float32)[None,:,None,None].expand(1,8,3,10)
            return logits,means,torch.zeros_like(means)
    inputs=(torch.zeros((1,3,192),device=device),)
    model=Fixed();seed=314159
    a=sample(model,inputs,300,torch.Generator(device=device).manual_seed(seed))
    b=sample(model,inputs,300,torch.Generator(device=device).manual_seed(seed))
    torch.testing.assert_close(a,b,rtol=0,atol=0)
    rng=torch.Generator(device=device).manual_seed(seed)
    logits,means,ls=model()
    u=torch.rand((1,300),device=device,generator=rng)
    expected_cdf=logits.softmax(-1).cpu().cumsum(-1).to(device);expected_cdf[:,-1]=1
    torch.testing.assert_close(categorical_cdf(logits),expected_cdf,rtol=0,atol=0)
    modes=(u[:,:,None]>expected_cdf[:,None]).sum(-1)
    expected=means[torch.arange(1,device=device)[:,None],modes]+torch.randn((1,300,3,10),device=device,generator=rng)
    torch.testing.assert_close(a,expected,rtol=0,atol=0)
    assert torch.are_deterministic_algorithms_enabled()
    return dict(passed=True,device=str(device),strict_determinism=True,repeat_bit_identical=True,
                declared_cdf_and_rng_exact=True,research_model_calls=0,synthetic_candidates=300)
