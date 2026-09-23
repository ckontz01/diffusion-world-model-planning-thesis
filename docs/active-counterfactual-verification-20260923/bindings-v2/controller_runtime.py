"""Authenticate existing host controller binaries; no dependency installation."""
import common as c
import sys


def verify():
    pins=c.read(c.ROOT/'CONTROLLER-RUNTIME.json')
    c.require(list(sys.version_info[:3])==pins['python_version'],'Controller Python version')
    for name,h in pins['files'].items():c.require(c.sha(name)==h,'Controller binary identity: '+name)
    c.require('numpy' not in sys.modules and 'torch' not in sys.modules,'Controller must remain stdlib-only')
    return pins
