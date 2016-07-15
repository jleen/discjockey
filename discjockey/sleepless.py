# Copyright (c) 2013-2014 John Leen

import platform
import subprocess
import sys

if platform.system() == 'Darwin':
    import pmset
    pmset.prevent_idle_sleep('Disc Jockey Rip')

subprocess.call(sys.argv[1:])
