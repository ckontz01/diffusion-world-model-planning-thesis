"""Validate remote program syntax before passing existing authenticated SSH route."""
import ast
from wm_diag0_preflight_v1.transport import ssh as existing_ssh

def ssh(code,payload=None,timeout=90):
    ast.parse(code,filename='remote-control',feature_version=(3,6))
    return existing_ssh(code,payload=payload,timeout=timeout)
