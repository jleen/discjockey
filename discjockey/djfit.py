# Copyright (c) 2016 John Leen

import os
import subprocess

from discjockey import djconfig, djident, djplatform, djrip

def fit():
    album = djconfig.args[0]
    num_discs = 1
    if len(djconfig.args) > 1: djconfig.args[1]

    print('--- Insert first disc ---')
    djplatform.wait_for_disc()

    if not os.path.exists(album):
        djident.ident()

        if djconfig.editor:
            subprocess.check_output(djconfig.editor.split(' ') + [ album ])
        else:
            raise Exception('Default editor not implemented')

    if num_discs > 1:
        print()
        print()
        print('--- Re-insert first disc ---')
        djplatform.wait_for_disc()

    djrip.rip()
