"""Fail-fast EGL routing guard. Imports only; no probe context or extra episode."""
import importlib
import os
from pathlib import Path
from dtv_success_cost.common import load,sha,write
from dtv_success_cost_r2.common import RECOVERY
VENDOR=RECOVERY/'dtv_success_cost_r2/nvidia-egl.json'
ENV=dict(MUJOCO_GL='egl',PYOPENGL_PLATFORM='egl',SDL_VIDEODRIVER='dummy',MPLBACKEND='Agg')
def validate_environment(environ=None):
    env=os.environ if environ is None else environ
    if any(env.get(k)!=v for k,v in ENV.items()) or env.get('__EGL_VENDOR_LIBRARY_FILENAMES')!=str(VENDOR):
        raise RuntimeError('headless EGL launch contract missing/changed; never fall back to GLFW')
    if load(VENDOR)!=dict(file_format_version='1.0.0',ICD=dict(library_path='libEGL_nvidia.so.0')):
        raise RuntimeError('NVIDIA EGL driver routing changed')
    return {k:env[k] for k in list(ENV)+['__EGL_VENDOR_LIBRARY_FILENAMES']}
def validate_backend(output,importer=importlib.import_module):
    env=validate_environment()
    # Do not instantiate a context here: the included real episode performs its
    # own original native render. No warm-up, physics probe or extra CUDA work.
    mujoco=importer('mujoco');dm=importer('dm_control._render');platform=importer('OpenGL.platform')
    modules=dict(mujoco_context=mujoco.GLContext.__module__,dm_renderer=dm.Renderer.__module__,pyopengl_platform=type(platform.PLATFORM).__module__)
    if not modules['mujoco_context'].endswith('.egl') or dm.BACKEND!='egl' or not modules['dm_renderer'].endswith('.egl_renderer') or not modules['pyopengl_platform'].endswith('.egl'):
        raise RuntimeError('runtime selected a non-EGL renderer; stop before evaluation access')
    value=dict(environment=env,modules=modules,vendor_sha256=sha(VENDOR),extra_contexts=0,extra_episodes=0,physics_probe=False)
    write(Path(output)/'RENDER-BACKEND.json',value);return value
def verify_evidence(directory):
    value=load(Path(directory)/'RENDER-BACKEND.json')
    if value.get('environment')!=dict(ENV,__EGL_VENDOR_LIBRARY_FILENAMES=str(VENDOR)) or value.get('vendor_sha256')!=sha(VENDOR) or value.get('extra_contexts')!=0 or value.get('extra_episodes')!=0 or value.get('physics_probe') is not False:
        raise RuntimeError('headless render evidence changed')
    modules=value['modules']
    if not modules['mujoco_context'].endswith('.egl') or not modules['dm_renderer'].endswith('.egl_renderer') or not modules['pyopengl_platform'].endswith('.egl'):raise RuntimeError('EGL backend proof changed')
    return value

