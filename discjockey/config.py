# Copyright (c) 2016 John Leen

import argparse
import configparser
import os

_parser = argparse.ArgumentParser()
_parser.add_argument('--music', metavar='DIR')
_parser.add_argument('--catalog', metavar='PATH')
_parser.add_argument('--album', metavar='ALBUM')
_parser.add_argument('--cdparanoia_bin', metavar='PATH')
_parser.add_argument('--flac_bin', metavar='PATH')
_parser.add_argument('--metaflac_bin', metavar='PATH')
_parser.add_argument('--umount_cmd', metavar='CMD')
_parser.add_argument('--cdrom', metavar='PATH')
_parser.add_argument('--discid_cmd', metavar='CMD')
_parser.add_argument('--eject_cmd', metavar='CMD')
_parser.add_argument('--wait_cmd', metavar='CMD')
_parser.add_argument('-v', '--verbose', action='count')
_parser.add_argument('--nocreate_playlists', dest='create_playlists',
                     action='store_false')
_parser.add_argument('--norip', dest='rip', action='store_false')
_parser.add_argument('--rename', action='store_true')
_parser.add_argument('-f', '--allow_wrong_length', action='store_true')
_parser.add_argument('-d', '--first_disc', metavar='N', type=int, default=1)
_parser.add_argument('--nometa', action='store_true')
_parser.add_argument('--extension', metavar='EXT', default='.flac')
_parser.add_argument('args', nargs='*')

_args = _parser.parse_args()

args = _args.args

dev_cdrom = _args.cdrom
if not dev_cdrom:
    dev_cdrom = '/dev/cdrom'

bin_wait = _args.wait_cmd
bin_eject = _args.eject_cmd
bin_discid = _args.discid_cmd
bin_metaflac = _args.metaflac_bin
bin_cdparanoia = _args.cdparanoia_bin
bin_flac = _args.flac_bin

music_path = _args.music
catalog_path = _args.catalog

rip = _args.rip
rename = _args.rename
create_playlists = _args.create_playlists and _args.first_disc == 1
allow_wrong_length = _args.allow_wrong_length
first_disc = _args.first_disc
nometa = _args.nometa
extension = _args.extension


def _parse_afp(specibus):
    return specibus


djrc = os.environ.get('DJRC', os.path.expanduser('~/.djrc'))
_config = configparser.ConfigParser()
_config.read(djrc)

gracenote_client = _config['Gracenote']['client']
gracenote_user = _config['Gracenote']['user']

rip_bin = None
rip_args = ''
ps1_eject = None

if 'Binaries' in _config:
    binaries = _config['Binaries']
    editor = binaries['editor']
    if not bin_discid:
        bin_discid = binaries['discid']
    if not bin_discid:
        bin_discid = binaries['discid']
    if not bin_flac:
        bin_flac = binaries['flac']
    if not bin_metaflac:
        bin_metaflac = binaries['metaflac']
    if 'rip' in binaries:
        rip_bin = binaries['rip']
    if 'rip_args' in binaries:
        rip_args = binaries['rip_args']
    if 'ps1_eject' in binaries:
        ps1_eject = binaries['ps1_eject']

else:
    editor = 'vi'

if not catalog_path:
    catalog_path = _config['Paths']['catalog']
if not music_path:
    music_path = _config['Paths']['music']

scratch_dir = None
if 'Paths' in _config and 'scratch' in _config['Paths']:
    scratch_dir = _config['Paths']['scratch']
