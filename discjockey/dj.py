import sys

def main():
    cmd, *sys.argv[1:] = sys.argv[1:]
    if cmd == 'beautify':
        from . import beautify
        beautify.cosmetize()
    elif cmd == 'catalog':
        from . import catalog
        catalog.catalog()
    elif cmd == 'ident':
        from . import ident
        ident.ident()
    elif cmd == 'intake':
        from . import fit
        fit.fit()
    elif cmd == 'rename':
        from . import rip
        rip.rename()
    elif cmd == 'rip':
        from . import rip
        rip.rip()
    elif cmd == 'transcode':
        from . import transcode
        transcode.transcode()
    else:
        raise Exception('Unknown command ' + cmd)

if __name__ == '__main__':
    main()
