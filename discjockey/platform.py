# Copyright (c) 2016 John Leen

import platform
import subprocess
import time

import sys
from discjockey import config

MAC_OS = platform.system() == 'Darwin'
LINUX = platform.system() == 'Linux'
CYGWIN = platform.system().startswith('CYGWIN_NT')

if not (MAC_OS or LINUX or CYGWIN):
    raise Exception('Unknown platform')


#
# prevent_sleep
#

def prevent_sleep():
    if MAC_OS:
        from discjockey import pmset
        pmset.prevent_idle_sleep('Disc Jockey Rip')


#
# wait_for_disc
#

def _get_cdrom_device_if_drive_ready():
    ret = subprocess.check_output(['/usr/bin/drutil', 'status']).split(b'\n')
    if len(ret) < 4:
        return None
    if b'Name' not in ret[3]:
        return None
    return ret[3][ret[3].find(b'/'):].decode('ascii')


def _disc_ready(cdrom_device):
    if MAC_OS:
        if not _get_cdrom_device_if_drive_ready():
            return False
        ret = subprocess.check_output(['/sbin/mount'])
        if cdrom_device.encode('utf-8') in ret:
            subprocess.check_output(['/usr/sbin/diskutil', 'umount',
                                     cdrom_device])
        return True
    elif LINUX:
        ret = subprocess.call(
                ['/usr/bin/cd-discid', config.dev_cdrom],
                stderr=subprocess.DEVNULL)
        return not ret
    elif CYGWIN:
        ret = subprocess.check_output(
                ['/usr/bin/cdrecord', '-toc'],
                stderr=subprocess.STDOUT)
        return b'Cannot load media' not in ret


def wait_for_disc():
    if config.bin_wait:
        subprocess.check_output(config.bin_wait.split(' '))
        return

    cdrom_device = None
    if MAC_OS:
        while True:
            cdrom_device = _get_cdrom_device_if_drive_ready()
            if cdrom_device:
                break
            time.sleep(1)

    while not _disc_ready(cdrom_device):
        time.sleep(1)


#
# eject_disc
#

def eject_disc():
    if config.bin_eject:
        subprocess.check_output(config.bin_eject.split(' '))
    elif MAC_OS:
        subprocess.check_output(['/usr/bin/drutil', 'eject'])
    elif LINUX:
        subprocess.check_output(['/usr/bin/eject', '/dev/cdrom'])
    elif CYGWIN:
        subprocess.check_output(['/usr/bin/cdrecord', '-eject'])


#
# read_toc
#

def read_toc():
    if MAC_OS:
        p = subprocess.Popen(['/usr/bin/drutil', 'trackinfo'],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate()
        toc = ''
        last_start = None
        last_length = None
        for line in out.splitlines():
            if line[8:18] == b'trackStart':
                last_start = int(line[27:]) + 150
                toc += str(last_start) + ' '
            elif line[16:25] == b'trackSize':
                last_length = int(line[27:])
            elif line.startswith(b'  Please insert a disc to get track info.'):
                print("You don't seem to have given me a disc.")
                sys.exit(1)
        # drutil doesn't report the leadout, but Gracenote needs it for ID.
        toc += str(last_start + last_length) + ' '
    else:
        p = subprocess.Popen(['/usr/bin/cdrecord', '-toc'],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate()
        toc = ''
        for line in out.splitlines():
            if line.startswith(b'track'):
                toc += str(int(line[17:26]) + 150) + ' '
    return toc


#
# get_discid
#

def get_discid():
    if config.bin_discid:
        return subprocess.check_output(config.bin_discid.split(' '))

    if MAC_OS:
        cdrom_device = _get_cdrom_device_if_drive_ready()
        return subprocess.check_output(['/usr/local/bin/cd-discid',
                                        cdrom_device])
    else:
        cdrom_device = config.dev_cdrom
        return subprocess.check_output(['/usr/bin/cd-discid', cdrom_device])


def _usr_bin(binary):
    if MAC_OS:
        return '/usr/local/bin/' + binary
    else:
        return '/usr/bin/' + binary


def bin_flac():
    if config.bin_flac:
        return config.bin_flac
    else:
        return _usr_bin('flac')


def bin_metaflac():
    if config.bin_metaflac:
        return config.bin_metaflac
    else:
        return _usr_bin('metaflac')


def bin_cdparanoia():
    if config.bin_cdparanoia:
        return config.bin_cdparanoia
    else:
        return _usr_bin('cdparanoia')


def translate_afp_path(specibus):
    # Maybe this isn't an afp path at all.
    if ':' not in specibus:
        return specibus

    # It is! Make sure we can handle it.
    if not MAC_OS:
        raise Exception('afp is only supported on Mac OS')

    sylladex = specibus.split(':')
    afp_host = sylladex[0]
    afp_share = sylladex[1]
    afp_dir = ''
    if len(sylladex) > 2:
        afp_dir = '/' + sylladex[2]

    # TODO(jleen): Can we do this through some Cocoa API?
    mounts = subprocess.check_output('/sbin/mount').decode('utf-8')
    for line in mounts.split('\n'):
        if 'auto' in line:
            continue
        if afp_host not in line:
            continue
        if afp_share not in line:
            continue
        return line.split(' ')[2] + afp_dir


catalog_path = translate_afp_path(config.catalog_path)
music_path = translate_afp_path(config.music_path)
