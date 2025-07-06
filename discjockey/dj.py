import sys

from . import beautify, transcode, ident, fit, rip

def main():
    cmd, *sys.argv[1:] = sys.argv[1:]
    if cmd == 'beautify':
        beautify.cosmetize()
    elif cmd == 'transcode':
        transcode.transcode()
    elif cmd == 'ident':
        ident.ident()
    elif cmd == 'intake':
        fit.fit()
    elif cmd == 'rename':
        rip.rename()
    else:
        raise Exception('Unknown command ' + cmd)

if __name__ == '__main__':
    main()
