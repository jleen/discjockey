# Copyright (c) 2012 John Leen

import argparse
import logging
import os
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('--music', metavar='DIR')
parser.add_argument('--catalog', metavar='PATH')
parser.add_argument('--album', metavar='ALBUM')
parser.add_argument('--cdparanoia_bin', metavar='PATH',
                    default='/usr/bin/cdparanoia')
parser.add_argument('--flac_bin', metavar='PATH', default='/usr/bin/flac')
parser.add_argument('-v', '--verbose', action='count')
parser.add_argument('--nocreate_playlists', dest='create_playlists',
                    action='store_false')
parser.add_argument('--norip', dest='rip', action='store_false')

args = parser.parse_args()

if args.verbose >= 2: log_level = logging.DEBUG
elif args.verbose >= 1: log_level = logging.INFO
else: log_level = logging.WARNING
logging.basicConfig(level=log_level, format='%(message)s')

playlist_extension = '.m3u'
track_extension = '.flac'

def make_set_filename(name, num, max_track, max_set):
    return make_track_filename(name, 0, num, max_track, max_set)

def make_track_filename(name, track_num, set_num, max_track, max_set):
    slen = '%d' % len('%d' % max_set)
    tlen = '%d' % len('%d' % max_track)
    if max_track == 0:
        return ('%0' + slen + 'd %s') % (set_num, name)
    else:
        fmt = '%0' + slen + 'd.%0' + tlen + 'd %s'
        return fmt % (set_num, track_num, name)

def make_playlists(filename):
    f = open(filename, 'r')
    track_list = f.readlines()
    f.close()

    master_name = os.path.split(filename)[1]
    set_name = None
    track_num = 0
    set_num = 0

    master_set = [ [master_name, 0] ]
    tracks = []
    sets = [ master_set ]
    max_track = 0

    current_set = None

    for line in track_list:
        line = line.strip()

        if line.startswith('*'):
            set_name = line[1:].strip()
            set_num += 1
            track_num = 0
            current_set = [ [set_name, set_num] ]
            sets.append(current_set)

        elif line == "":
            set_name = None
            current_set = None

        else:
            track_name = line
            if current_set == None:
                track_num = 0
                set_num += 1
            else:
                track_num += 1
                max_track = max(max_track, track_num)
            track = [track_name, track_num, set_num]
            master_set.append(track)
            if current_set != None: current_set.append(track)

    max_set = set_num

    for set in sets:
        (name, num) = set[0]
        set[0][0] = make_set_filename(name, num, max_track, max_set)
        set[0][0] += playlist_extension

    for track in sets[0][1:]:
        (name, num, set_num) = track
        track[0] = make_track_filename(name, num, set_num, max_track, max_set)
        track[0] += track_extension

    playlists = []
    for set in sets:
        playlist = set[0][0]
        tracks = []
        for track in set[1:]:
            tracks.append(track[0])
        yield (playlist, tracks)
    
def write_playlists(playlists):
    all_tracks = []

    os.makedirs(os.path.join(args.music, args.album))
    for (filename, tracks) in playlists:
        f = open(os.path.join(args.music, args.album, filename), 'w')
        for track in tracks:
            f.write(track + '\n');
        f.close

def rip_and_encode(tracks):
    for (track_num, track_name) in enumerate(tracks, start=1):
        try:
            rip_proc = subprocess.Popen(
                    [args.cdparanoia_bin, '%d' % (track_num), '-'],
                    stdout=subprocess.PIPE)
            encode_proc = subprocess.Popen(
                    [args.flac_bin, '-s', '-', '-o',
                        os.path.join(args.music, args.album, track_name)],
                        stdin=rip_proc.stdout, stdout=subprocess.PIPE)
            rip_proc.stdout.close()
            encode_proc.communicate()
            rip_proc.poll()
            if rip_proc.returncode != 0:
                raise Exception('Abnormal cdparanoia termination')
            if encode_proc.returncode != 0:
                raise Exception('Abnormal flac termination')
        except:
            # TODO(jleen): Clean up whatever we were doing.
            raise

def all_tracks(playlists):
    for (filename, tracks) in playlists:
        for track in tracks: yield track

playlists = make_playlists(os.path.join(args.catalog, args.album))
if (args.create_playlists): write_playlists(playlists)
if (args.rip): rip_and_encode(all_tracks(playlists))
