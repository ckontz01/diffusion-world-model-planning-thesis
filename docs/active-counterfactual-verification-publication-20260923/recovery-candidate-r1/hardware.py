"""Candidate corrected device gate: partition label is not the hardware name.

No execution authority or allocation is provided here. This exact class is
documented by existing repository hardware specifications for gpu09/a6000.
"""
EXPECTED_DEVICE='NVIDIA RTX 6000 Ada Generation'

def verify_device(torch_api,record):
    cuda=torch_api.cuda
    available=bool(cuda.is_available())
    count=int(cuda.device_count()) if available else 0
    observed={'cuda_available':available,'visible_device_count':count,
              'device_name':cuda.get_device_name(0) if count else None,
              'expected_device_name':EXPECTED_DEVICE,
              'site_partition_label':'a6000','no_model_or_reference_loaded_yet':True}
    record(observed)  # preserve the actual identity even when the guard fails
    if not available or count!=1 or observed['device_name']!=EXPECTED_DEVICE:
        raise ValueError('Exact allocated GPU identity failed: '+repr(observed))
    return observed
