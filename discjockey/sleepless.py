# Copyright (c) 2013-2014 John Leen

import platform
import subprocess
import sys


def sleepless():
    if platform.system() == 'Darwin':
        from discjockey import pmset
        pmset.prevent_idle_sleep('Disc Jockey Rip')
    elif platform.system() == 'Windows':
        import ctypes
        ES_CONTINUOUS = 0x80000000
        ES_SYSTEM_REQUIRED = 0x00000001
        ctypes.windll.kernel32.SetThreadExecutionState(
                ES_CONTINUOUS | ES_SYSTEM_REQUIRED)

    subprocess.call(sys.argv[1:])
