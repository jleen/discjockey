# Copyright (c) 2016 John Leen

import os
import subprocess

import djconfig
import djplatform

album = djconfig.args[0]
num_discs = 1
if len(djconfig.args) > 1: djconfig.args[1]

print('--- Insert first disc ---')
djplatform.wait_for_disc()

if not os.path.exists(album):
    import djident

    if djconfig.editor:
        subprocess.check_output(djconfig.editor.split(' ') + [ album ])
    else:
        raise Exception('Default editor not implemented')

if num_discs > 1:
    print()
    print()
    print('--- Re-insert first disc ---')
    djplatform.wait_for_disc()

import djrip
