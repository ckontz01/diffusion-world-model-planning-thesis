"""No task may start before its parent assigns this worker to its owned job."""
import os,subprocess,sys

def main():
    if os.name!='nt' or sys.stdin.buffer.readline(4)!=b'GO\n':raise RuntimeError('native owned-job parent handshake required')
    if len(sys.argv)<2:raise ValueError('explicit trusted command')
    return subprocess.call(sys.argv[1:],stdin=subprocess.DEVNULL)

if __name__=='__main__':sys.exit(main())
