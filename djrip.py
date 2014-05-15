# Copyright (c) 2013-2014 John Leen

import argparse
import logging
import os
import platform
import subprocess
import sys
import unicodedata

parser = argparse.ArgumentParser()
parser.add_argument('--music', metavar='DIR')
parser.add_argument('--catalog', metavar='PATH')
parser.add_argument('--album', metavar='ALBUM')
parser.add_argument('--cdparanoia_bin', metavar='PATH',
                    default='/usr/bin/cdparanoia')
parser.add_argument('--flac_bin', metavar='PATH', default='/usr/bin/flac')
parser.add_argument('--metaflac_bin', metavar='PATH',
                        default='/usr/bin/metaflac')
parser.add_argument('--umount_cmd', metavar='CMD')
parser.add_argument('--discid_cmd', metavar='CMD', default='/usr/bin/cd-discid')
parser.add_argument('--eject_cmd', metavar='CMD', default='/usr/bin/eject')
parser.add_argument('-v', '--verbose', action='count')
parser.add_argument('--nocreate_playlists', dest='create_playlists',
                    action='store_false')
parser.add_argument('--norip', dest='rip', action='store_false')
parser.add_argument('--rename', action='store_true')
parser.add_argument('-f', '--allow_wrong_length', action='store_true')
parser.add_argument('--first_disc', metavar='N', type=int, default=1)

args = parser.parse_args()

if args.verbose >= 2: log_level = logging.DEBUG
elif args.verbose >= 1: log_level = logging.INFO
else: log_level = logging.WARNING
logging.basicConfig(level=log_level, format='%(message)s')

playlist_extension = '.m3u'
track_extension = '.flac'

DISC_DELIMITER = '~~~END~OF~LINE~~~'
SKIPPED_TRACK = '~~~NOTHING~TO~SEE~HERE~~~'

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

def sanitize_filename(filename):
    """Given a candidate filename, replace all bad characters with wholesome
    characters."""

    filename = filename.replace('"', "'")
    filename = filename.replace('/', ' - ')
    filename = filename.replace(':', ' -')
    filename = filename.replace('?', '~')
    filename = filename.replace('*', '-')

    return filename

def make_playlists(filename):
    """Given the path to an album spec, returns a data structure containing all
    the playlists to generate, including the master playlist containing all
    tracks."""

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

    # Get some default metadata from the album pathname.
    (genre, artist, album) = dissect_track_path(args.album)

    # Generate an array of all track data.  Each entry is either DISC_DELIMITER
    # or a list [name, track number within its set, set number].  Also generate
    # a separate array (in the same format) for each individual sub-playlist.
    for line in track_list:
        line = line.strip()

        if line.startswith('~~~'):
            master_set.append(DISC_DELIMITER)

        elif line.startswith('---'):
            master_set.append(SKIPPED_TRACK)

        elif line.startswith('*'):
            set_name = sanitize_filename(line[1:].strip())
            set_num += 1
            track_num = 0
            current_set = [ [set_name, set_num] ]
            sets.append(current_set)

        elif line.startswith('~'):
            [code, value] = line.split(' ', 1)
            if code == '~g': genre = value
            if code == '~a': album = value
            if code == '~r': artist = value

        elif line == "":
            set_name = None
            current_set = None

        else:
            track_name = sanitize_filename(line)
            if current_set == None:
                track_num = 0
                set_num += 1
            else:
                track_num += 1
                max_track = max(max_track, track_num)

            track = {
                'track_name': track_name,
                'track_num': track_num,
                'set_num': set_num,
                'genre': genre,
                'artist': artist,
                'album': album,
                'title': line
                }
            master_set.append(track)
            if current_set != None: current_set.append(track)

    max_set = set_num

    # Generate a filename for each playlist.
    for set in sets:
        (name, num) = set[0]
        set[0][0] = make_set_filename(name, num, max_track, max_set)
        set[0][0] += playlist_extension

    # Generate a filename for each track by combining its set and track number
    # with its name.
    for track in sets[0][1:]:
        if not is_metatrack(track):
            track['filename'] = make_track_filename(
                    track['track_name'], track['track_num'],
                    track['set_num'], max_track, max_set) + track_extension

    # Generate the data structure to return.  It is an array of playlists,
    # where each playlist is a tuple whose first element is the playlist
    # filename and whose second element is an array of track dicts.
    playlists = []
    is_master = True
    for set in sets:
        playlist = set[0][0]
        tracks = []
        for track in set[1:]:
            if is_metatrack(track):
                if is_master: tracks.append(track)
            else: tracks.append(track)
            playlists.append((playlist, tracks))
        is_master = False

    return playlists
    
def is_metatrack(track_name):
    return track_name == DISC_DELIMITER or track_name == SKIPPED_TRACK

def write_playlists(playlists):
    all_tracks = []

    if not args.rename: os.makedirs(os.path.join(args.music, args.album))
    for (filename, tracks) in playlists:
        path = os.path.join(args.music, args.album, filename)
        if args.rename and os.path.exists(path): os.remove(path)
        f = open(path, 'w')
        for track in tracks:
            if not is_metatrack(track): f.write(track['filename'] + '\n');
        f.close

def divide_tracks_by_disc(tracks):
    track_sets = []
    current_tracks = []
    for track in tracks:
        if track == DISC_DELIMITER:
            track_sets.append(current_tracks)
            current_tracks = []
        else: current_tracks.append(track)
    track_sets.append(current_tracks)
    return track_sets

def rename_files(tracks):
    tracks = [track for track in tracks if not is_metatrack(track)]
    path = os.path.join(args.music, args.album)
    files = [f for f in os.listdir(path) if f.endswith(track_extension)]
    if len(files) != len(tracks):
        raise Exception('Album has %d tracks but directory has %d files' %
                            (len(tracks), len(files)))
    files.sort()

    for (linear_num, (old_name, track)) in enumerate(zip(files, tracks), 1):
        new_name = track['filename']
        # Don't try to rename a file if the old and new names are Unicode
        # equivalents, because OS X canonicalizes Unicode filenames.
        old_name_nfc = unicodedata.normalize('NFC', old_name.decode('utf-8'))
        new_name_nfc = unicodedata.normalize('NFC', new_name.decode('utf-8'))
        if old_name_nfc != new_name_nfc:
            if os.path.exists(os.path.join(path, new_name)):
                raise Exception('Trying to rename %s to already-existing %s' %
                                    (old_name, new_name))
            os.rename(os.path.join(path, old_name),
                      os.path.join(path, new_name))
        subprocess.check_output([
                args.metaflac_bin,
                '--set-tag=GENRE=%s' % track['genre'],
                '--set-tag=ARTIST=%s' % track['artist'],
                '--set-tag=ALBUM=%s' % track['album'],
                '--set-tag=TITLE=%s' % track['title'],
                '--set-tag=TRACKNUMBER=%d' % linear_num,
                os.path.join(path, new_name)])
            
    
def dissect_track_path(track_path):
    comps = track_path.split(os.path.sep)
    return (comps[0], comps[-2], comps[-1])

def rip_and_encode(tracks):

    first_disc = True
    linear_num = 1
    for disc_tracks in divide_tracks_by_disc(tracks)[args.first_disc-1:]:
        if not first_disc:
            print "--- Insert next disc and hit Enter ---"
            sys.stdin.readline()
        first_disc = False

        if (args.umount_cmd):
            with open(os.devnull, 'w') as dev_null:
                subprocess.call(args.umount_cmd.split(' '), stdout=dev_null)
        discid = subprocess.check_output(args.discid_cmd.split(' '))
        num_tracks = int(discid.split(' ')[1])
        if not args.allow_wrong_length and num_tracks != len(disc_tracks):
            raise Exception('Playlist length %d does not match disc length %d'
                            % (len(disc_tracks), num_tracks))

        for (track_num, track) in enumerate(disc_tracks, start=1):
            track_name = track['track_name']
            if track_name == SKIPPED_TRACK: continue

            output_file = os.path.join(args.music, args.album,
                                       track['filename'])
            try:
                rip_proc = subprocess.Popen(
                        [args.cdparanoia_bin, '%d' % (track_num), '-'],
                        stdout=subprocess.PIPE)
                encode_proc = subprocess.Popen(
                        [args.flac_bin, '-s', '-', '-o', output_file,
                         '-T', 'TITLE=%s' % (track['title']),
                         '-T', 'ALBUM=%s' % (track['album']),
                         '-T', 'ARTIST=%s' % (track['artist']),
                         '-T', 'GENRE=%s' % (track['genre']),
                         '-T', 'TRACKNUMBER=%d' % (linear_num)],
                            stdin=rip_proc.stdout, stdout=subprocess.PIPE)
                rip_proc.stdout.close()
                encode_proc.communicate()
                rip_proc.poll()
                if rip_proc.returncode != 0:
                    raise Exception('Abnormal cdparanoia termination')
                if encode_proc.returncode != 0:
                    raise Exception('Abnormal flac termination')
            except:
                encode_proc.terminate()
                rip_proc.terminate()
                os.remove(output_file)
                raise
            linear_num += 1

        subprocess.check_output(args.eject_cmd.split(' '))

if platform.system() == 'Darwin':
    import pmset
    pmset.prevent_idle_sleep('Disc Jockey Rip')

playlists = make_playlists(os.path.join(args.catalog, args.album))
if (args.create_playlists): write_playlists(playlists)

if (args.rename): rename_files(playlists[0][1])
elif (args.rip): rip_and_encode(playlists[0][1])
