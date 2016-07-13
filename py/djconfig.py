# Copyright (c) 2016 John Leen

import argparse
import configparser
import os


_parser = argparse.ArgumentParser()
_parser.add_argument('--music', metavar='DIR')
_parser.add_argument('--catalog', metavar='PATH')
_parser.add_argument('--album', metavar='ALBUM')
_parser.add_argument('--cdparanoia_bin', metavar='PATH',
                    default='/usr/bin/cdparanoia')
_parser.add_argument('--flac_bin', metavar='PATH', default='/usr/bin/flac')
_parser.add_argument('--metaflac_bin', metavar='PATH',
                        default='/usr/bin/metaflac')
_parser.add_argument('--umount_cmd', metavar='CMD')
_parser.add_argument('--cdrom', metavar='PATH')
_parser.add_argument('--discid_cmd', metavar='CMD', default='/usr/bin/cd-discid')
_parser.add_argument('--eject_cmd', metavar='CMD', default='/usr/bin/eject')
_parser.add_argument('--wait_cmd', metavar='CMD')
_parser.add_argument('-v', '--verbose', action='count')
_parser.add_argument('--nocreate_playlists', dest='create_playlists',
                    action='store_false')
_parser.add_argument('--norip', dest='rip', action='store_false')
_parser.add_argument('--rename', action='store_true')
_parser.add_argument('-f', '--allow_wrong_length', action='store_true')
_parser.add_argument('--first_disc', metavar='N', type=int, default=1)
_parser.add_argument('--nometa', action='store_true')

_args = _parser.parse_args()


dev_cdrom = _args.cdrom

bin_wait = _args.wait_cmd
bin_eject = _args.eject_cmd
bin_discid = _args.discid_cmd
bin_metaflac = _args.metaflac_bin
bin_cdparanoia = _args.cdparanoia_bin
bin_flac = _args.flac_bin

album_path = _args.album
music_path = _args.music
catalog_path = _args.catalog

rip = _args.rip
rename = _args.rename
create_playlists = _args.create_playlists
allow_wrong_length = _args.allow_wrong_length
first_disc = _args.first_disc
nometa = _args.nometa


def _parse_afp(specibus):
    return specibus

_config = configparser.ConfigParser()
_config.read(os.path.expanduser('~/.djrc'))

gracenote_client = _config['Gracenote']['client']
gracenote_user = _config['Gracenote']['user']

if not catalog_path: catalog_path = _parse_afp(_config['Paths']['catalog'])
if not music_path: music_path = _parse_afp(_config['Paths']['music'])
