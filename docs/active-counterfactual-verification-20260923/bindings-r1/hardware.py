"""Exact physical-device interlock; records evidence before any model access."""
import os
import socket

EXPECTED_DEVICE = 'NVIDIA RTX 6000 Ada Generation'


def verify_device(torch_api, record):
    observed = {'slurm_job_id': os.environ.get('SLURM_JOB_ID'), 'hostname': socket.gethostname(),
                'expected_device_name': EXPECTED_DEVICE, 'site_partition_label': 'a6000',
                'cuda_available': None, 'visible_device_count': None, 'device_name': None,
                'properties': {}, 'no_model_or_reference_loaded_yet': True}
    try:
        cuda = torch_api.cuda
        observed['cuda_available'] = bool(cuda.is_available())
        observed['visible_device_count'] = int(cuda.device_count())
        if observed['cuda_available'] and observed['visible_device_count']:
            observed['device_name'] = cuda.get_device_name(0)
            props = cuda.get_device_properties(0)
            for key in ('name', 'major', 'minor', 'total_memory', 'multi_processor_count', 'uuid', 'pci_bus_id'):
                if hasattr(props, key):
                    value = getattr(props, key)
                    observed['properties'][key] = value if isinstance(value, (str, int, float, bool)) else str(value)
        observed['query_status'] = 'complete'
    except BaseException as error:
        observed.update(query_status='error', query_error_type=type(error).__name__, query_error=str(error)[:4096], accepted=False)
        record(observed)
        raise
    observed['accepted'] = (observed['cuda_available'] and observed['visible_device_count'] == 1
                            and observed['device_name'] == EXPECTED_DEVICE)
    record(observed)
    if not observed['accepted']:
        raise ValueError('Exact single NVIDIA RTX 6000 Ada Generation required; hardware receipt preserved')
    return observed


def initialize_backend(torch_api, record, auth):
    hardware = verify_device(torch_api, record)
    from bridge import load_backend
    return hardware, load_backend(auth)
