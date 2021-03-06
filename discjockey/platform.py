# Copyright (c) 2016 John Leen

import platform
import shlex
import subprocess
import time

import sys
from discjockey import config

REDBOOK_FRAMES_PER_SEC = 75

# LINUX and WSL aren't mutually exclusive.
# They're similar enough that this is worth it.
MAC_OS = platform.system() == 'Darwin'
LINUX = platform.system() == 'Linux'
CYGWIN = platform.system().startswith('CYGWIN_NT')
WINDOWS = platform.system() == 'Windows'
WSL = 'Microsoft' in platform.release()

if not (MAC_OS or LINUX or CYGWIN or WINDOWS):
    raise Exception('Unknown platform')


#
# prevent_sleep
#

def prevent_sleep():
    if MAC_OS:
        from discjockey import pmset
        pmset.prevent_idle_sleep('Disc Jockey Rip')
    elif WINDOWS:
        import ctypes
        ES_CONTINUOUS = 0x80000000
        ES_SYSTEM_REQUIRED = 0x00000001
        ctypes.windll.kernel32.SetThreadExecutionState(
                ES_CONTINUOUS | ES_SYSTEM_REQUIRED)


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
    elif WINDOWS:
        ret = get_discid()
        return b'There is a problem with your media device' not in ret


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
    elif WINDOWS:
        subprocess.check_output(['powershell', '-executionpolicy', 'bypass',
                                 '-File', config.ps1_eject])


#
# get_discid
#

def get_discid():
    if WINDOWS:
        p = subprocess.Popen(config.bin_discid.split(' '),
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate()
        return out + err
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
    if not (MAC_OS or WSL):
        raise Exception('Network paths are only supported on Mac OS and WSL')

    sylladex = specibus.split(':')
    afp_host = sylladex[0]
    afp_share = sylladex[1]
    afp_dir = ''
    if len(sylladex) > 2:
        afp_dir = '/' + sylladex[2]

    if MAC_OS:
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
    else:
        print( '/mnt/' + afp_share.lower() + afp_dir)
        return '/mnt/' + afp_share.lower() + afp_dir

def shell_escape(arg):
    escaped = shlex.quote(arg)
    if WINDOWS:
        escaped = escaped.replace("'", '"')
    return escaped


catalog_path = translate_afp_path(config.catalog_path)
music_path = translate_afp_path(config.music_path)
