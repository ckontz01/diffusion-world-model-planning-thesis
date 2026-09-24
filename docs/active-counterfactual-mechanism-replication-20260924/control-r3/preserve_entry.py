"""Preserve all original and R1 roots after combined independent acceptance."""
import r1 as r
import argparse
import preserve_r1 as p

def main():
    ap=argparse.ArgumentParser();ap.add_argument('operation',choices=['archive','backup']);ap.add_argument('--approval',required=True);ap.add_argument('--request');a=ap.parse_args();ctx=r.Context(a.approval)
    if a.operation=='archive':
        accepted=r.read(ctx.control/'FINAL-ACCEPTANCE.json')
        r.require(accepted['attempts']==8199 and accepted['recovery_approval']==ctx.approval_sha and accepted['recovery_manifest']==ctx.binding['manifest'],'R3 final acceptance required')
        print(p.archive(ctx.auth,ctx.control,ctx.control/'FINAL-ACCEPTANCE.json'))
    else:
        # Native Windows does not have cluster paths: Context is intended for host archive.
        raise RuntimeError('Use transport.py backup for native Windows exact-request verification')

if __name__=='__main__':main()
