# Copyright (c) 2016 John Leen

import platform
import subprocess
import time

import djconfig

MAC_OS = platform.system() == 'Darwin'
LINUX = platform.system() == 'Linux'
CYGWIN = platform.system().startswith('CYGWIN_NT')

if not (MAC_OS or LINUX or CYGWIN): raise 'Unknown platform'



##
## prevent_sleep
##

def prevent_sleep():
    if MAC_OS:
        import pmset
        pmset.prevent_idle_sleep('Disc Jockey Rip')


##
## wait_for_disc
##

def _get_cdrom_device_if_drive_ready():
    ret = subprocess.check_output(['/usr/bin/drutil', 'status'])
    if 0 > ret.find(b'Name'): return None
    return ret[1 + ret.find(b'/') :]

def _disc_ready(cdrom_device):
    if MAC_OS:
        ret = subprocess.check_output(['/sbin/mount'])
        if 0 > ret.find(cdrom_device):
            subprocess.check_output(['/usr/sbin/diskutil', 'umount',
                                     cdrom_device])
            return False
        else:
            return True
    elif LINUX:
        ret = subprocess.check_output(
                ['/usr/bin/cd-discid', djconfig.dev_cdrom],
                stderr=subprocess.STDOUT)
        return 0 > ret.find(b'No medium found')
    elif CYGWIN:
        ret = subprocess.check_output(
                ['/usr/bin/cdrecord', '-toc'],
                stderr=subprocess.STDOUT)
        return 0 > ret.find(b'Cannot load media')

def wait_for_disc():
    if djconfig.bin_wait:
        subprocess.check_output(djconfig.bin_wait.split(' '))
        return

    if MAC_OS:
        cdrom_device = None
        while True:
            cdrom_device = _get_cdrom_device_if_drive_ready()
            if cdrom_device: break
            time.sleep(1)

    while not _disc_ready(cdrom_device):
        time.sleep(1)


##
## eject_disc
##

def eject_disc():
    if djconfig.bin_eject:
        subprocess.check_output(djconfig.bin_eject.split(' '))
    elif MAC_OS: 
        subprocess.check_output(['/usr/bin/drutil', 'eject'])
    elif LINUX:
        subprocess.check_output(['/usr/bin/eject', '/dev/cdrom'])
    elif CYGWIN:
        subprocess.check_output(['/usr/bin/cdrecord', '-eject'])


##
## read_toc
##

def read_toc():
    if MAC_OS:
        p = subprocess.Popen(['/usr/bin/drutil', 'trackinfo'],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate()
        toc = ''
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


##
## get_discid
##

def get_discid():
    if djconfig.bin_discid:
        return subprocess.check_output(djconfig.bin_discid.split(' '))

    if MAC_OS:
        cdrom_device = _get_cdrom_device_if_drive_ready()
    else:
        cdrom_device = djconfig.dev_cdrom
    return subprocess.check_output(['/usr/bin/cd-discid', cdrom_device])
