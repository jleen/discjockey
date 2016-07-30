# Copyright (c) 2013-2014 John Leen

import platform
import subprocess
import sys


def sleepless():
    if platform.system() == 'Darwin':
        from discjockey import pmset
        pmset.prevent_idle_sleep('Disc Jockey Rip')

    subprocess.call(sys.argv[1:])
