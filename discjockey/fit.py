# Copyright (c) 2016 John Leen

import os
import shlex

from discjockey import config, ident, platform, rip


def fit():
    album = config.args[0]
    num_discs = 1
    if len(config.args) > 1:
        num_discs = int(config.args[1])

    print('--- Insert first disc ---')
    platform.wait_for_disc()

    if not os.path.exists(album):
        ident.ident()

        if config.editor:
            os.system(config.editor + ' ' + shlex.quote(album))
        else:
            raise Exception('Default editor not implemented')

        if num_discs > 1:
            print()
            print()
            print('--- Re-insert first disc ---')
            platform.wait_for_disc()

    rip.rip()
