# Copyright (c) 2013-2023 John Leen

import os
import subprocess
import sys
import unicodedata
import uuid


playlist_extension = '.m3u'

DISC_DELIMITER = uuid.uuid4()
SKIPPED_TRACK = uuid.uuid4()


def make_set_filename(name, num, max_track, max_set):
    return (make_track_filename(name, 0, num, max_track, max_set)
            + playlist_extension)


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


def make_playlists(master_name, track_list, album_path, track_extension):
    """Given an album spec, returns a data structure containing all
    the playlists to generate, including the master playlist containing all
    tracks."""

    set_name = None
    track_num = 0
    set_num = 0

    master_set = {
        'set_name': master_name,
        'set_num': 0,
        'tracks': []
    }
    sets = [master_set]
    max_track = 0

    current_set = None

    # Get some default metadata from the album pathname.
    (genre, artist, album) = dissect_track_path(album_path)

    # Generate an array of all track data.  Each entry is either DISC_DELIMITER
    # or a list [name, track number within its set, set number].  Also generate
    # a separate array (in the same format) for each individual sub-playlist.
    for line in track_list:
        line = line.strip()

        if line.startswith('~~~'):
            # We care about disc boundaries because we want to use the track
            # count as a way to detect if the wrong disc is inserted.
            master_set['tracks'].append(DISC_DELIMITER)

        elif line.startswith('---'):
            # We need to remember if the catalog entry tells us to skip a
            # track,
            # so we won't rip it.
            # TODO(jleen): Should we also end the current trackset?
            master_set['tracks'].append(SKIPPED_TRACK)

        elif line.startswith('*'):
            # This is the beginning of a new trackset.
            set_name = sanitize_filename(line[1:].strip())
            set_num += 1
            track_num = 0
            current_set = {
                'set_name': set_name,
                'set_num': set_num,
                'tracks': []
            }
            sets.append(current_set)

        elif line.startswith('~'):
            # Metadata!
            [code, value] = line.split(' ', 1)
            if code == '~g':
                genre = value
            if code == '~a':
                album = value
            if code == '~r':
                artist = value

        elif line == "":
            # Blank line.  End the current trackset, if we were working on one.
            set_name = None
            current_set = None

        else:
            # A track entry.  Add it to the master trackset, and also the
            # current trackset if we're working on one.
            track_name = sanitize_filename(line)
            if current_set is None:
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
                'title': line,
                'set': set_name
            }
            master_set['tracks'].append(track)
            if current_set is not None:
                current_set['tracks'].append(track)

    max_set = set_num

    # Generate a filename for each playlist.  We couldn't do this earlier,
    # because we need the track count for each set in order to determine the
    # number of leading zeroes in the numerical part of the filename.
    for trackset in sets:
        trackset['filename'] = make_set_filename(
                trackset['set_name'], trackset['set_num'], max_track, max_set)

    # Generate a filename for each track by combining its set and track number
    # with its name.  Again, we couldn't do this earlier, because we need the
    # track count.
    #
    # We take advantage of the fact that the non-master tracksets consist of
    # references to the same data structures that are also in the master
    # trackset, so we only have to traverse the master trackset.
    for track in master_set['tracks']:
        if not is_metatrack(track):
            track['filename'] = make_track_filename(
                    track['track_name'], track['track_num'],
                    track['set_num'], max_track, max_set) + track_extension

    return sets


def is_metatrack(track_name):
    return track_name == DISC_DELIMITER or track_name == SKIPPED_TRACK


def write_playlists(playlists, album_path='', dry_run=False, rename=False):
    if not dry_run and not rename and album_path:
        os.makedirs(album_path)
    for playlist in playlists:
        path = os.path.join(album_path, playlist['filename'])
        if not dry_run:
            if rename and os.path.exists(path):
                os.remove(path)
            with open(path, 'w', encoding='UTF-8') as f:
                for track in playlist['tracks']:
                    if not is_metatrack(track):
                        f.write(track['filename'] + '\n')
        else:
            print(f'Would write playlist {path} with tracks:')
            for track in playlist['tracks']:
                if not is_metatrack(track):
                    print(f'   {track["filename"]}')


def divide_tracks_by_disc(tracks):
    track_sets = []
    current_tracks = []
    for track in tracks:
        if track == DISC_DELIMITER:
            track_sets.append(current_tracks)
            current_tracks = []
        else:
            current_tracks.append(track)
    track_sets.append(current_tracks)
    return track_sets


def rename_files(tracks, album_path, track_extension):
    tracks = [track for track in tracks if not is_metatrack(track)]
    path = os.path.join(platform.music_path, album_path)
    files = [f for f in os.listdir(path) if f.endswith(track_extension)]
    if len(files) != len(tracks):
        raise Exception('Album has %d tracks but directory has %d files' %
                        (len(tracks), len(files)))
    files.sort()

    for (linear_num, (old_name, track)) in enumerate(zip(files, tracks), 1):
        new_name = track['filename']
        # Don't try to rename a file if the old and new names are Unicode
        # equivalents, because OS X canonicalizes Unicode filenames.
        # TODO(jleen): Is this right?  Python 3 made it weird.
        old_name_nfc = unicodedata.normalize('NFC', old_name)
        new_name_nfc = unicodedata.normalize('NFC', new_name)
        if old_name_nfc != new_name_nfc:
            if os.path.exists(os.path.join(path, new_name)):
                raise Exception('Trying to rename %s to already-existing %s' %
                                (old_name, new_name))
            os.rename(os.path.join(path, old_name),
                      os.path.join(path, new_name))
        if track_extension == '.flac':
            subprocess.check_output([
                platform.bin_metaflac(),
                '--remove-all-tags',
                '--set-tag=GENRE=%s' % track['genre'],
                '--set-tag=ARTIST=%s' % track['artist'],
                '--set-tag=ALBUM=%s' % track['album'],
                '--set-tag=TITLE=%s' % track['title'],
                '--set-tag=TRACKNUMBER=%d' % linear_num,
                os.path.join(path, new_name)])


def dissect_track_path(track_path):
    comps = track_path.split(os.path.sep)
    if len(comps) < 3:
        raise Exception(
                'Album path %s should be Genre/Collection/Album or deeper'
                % track_path)
    return comps[0], comps[-2], comps[-1]


def assert_disc_length(disc_len):
    discid = platform.get_discid()
    num_tracks = int(discid.split(b' ')[1])
    if not config.allow_wrong_length and num_tracks != disc_len:
        print(('Playlist length %d does not match disc length %d'
               % (disc_len, num_tracks)))
        sys.exit(1)


def assert_first_disc_length(tracks):
    disc_tracksets = divide_tracks_by_disc(tracks)
    first_disc_tracks = disc_tracksets[config.first_disc - 1]
    assert_disc_length(len(first_disc_tracks))


def rip_and_encode(tracks, album_path):
    disc_tracksets = divide_tracks_by_disc(tracks)

    num_discs = len(disc_tracksets)
    disc_num = config.first_disc
    linear_num = 1

    for disc_tracks in disc_tracksets[disc_num - 1:]:
        if disc_num > config.first_disc:
            print(("--- Insert disc %d of %d ---" % (disc_num, num_discs)))
            platform.wait_for_disc()
        disc_num += 1

        assert_disc_length(len(disc_tracks))

        if config.rip_bin:
            subprocess.check_output(
                    [config.rip_bin] + config.rip_args.split(' '))

        for (track_num, track) in enumerate(disc_tracks, start=1):
            if track == SKIPPED_TRACK:
                continue

            fraction = f'[{track_num}/{len(disc_tracks)}]'
            print(f'{fraction} Ripping {track["title"]}')
            if track['set']:
                print(f'{" " * len(fraction)} from {track["set"]}')
            print()

            output_file = os.path.join(
                    platform.music_path, album_path,
                    track['filename'])
            rip_proc = None
            encode_proc = None
            try:
                if config.rip_bin:
                    scratch_wav = os.path.join(
                            config.scratch_dir, '%02d.wav' % track_num)
                    rip_fd = open(scratch_wav, 'rb')
                else:
                    rip_cmd = [platform.bin_cdparanoia(),
                               '%d' % track_num, '-']
                    rip_proc = subprocess.Popen(rip_cmd,
                            stdout=subprocess.PIPE)
                    rip_fd = rip_proc.stdout
                encode_proc = subprocess.Popen(
                        [platform.bin_flac(), '-s', '-', '-o', output_file,
                         '-T', 'TITLE=%s' % (track['title']),
                         '-T', 'ALBUM=%s' % (track['album']),
                         '-T', 'ARTIST=%s' % (track['artist']),
                         '-T', 'GENRE=%s' % (track['genre']),
                         '-T', 'TRACKNUMBER=%d' % linear_num],
                        stdin=rip_fd, stdout=subprocess.PIPE)
                if rip_proc:
                    rip_proc.stdout.close()
                encode_proc.communicate()
                if rip_proc and rip_proc.wait() != 0:
                    raise Exception('Abnormal cdparanoia termination')
                if encode_proc.returncode != 0:
                    raise Exception('Abnormal flac termination')

                if config.rip_bin:
                    rip_fd.close()
                    os.remove(scratch_wav)
            except (Exception, KeyboardInterrupt):
                if encode_proc is not None:
                    encode_proc.terminate()
                if rip_proc is not None:
                    rip_proc.terminate()
                if os.path.exists(output_file):
                    os.remove(output_file)
                raise
            linear_num += 1

        platform.eject_disc()


# TODO: This is so sad.
def load_eagerly_initialized_modules():
    global config, platform
    from discjockey import config, platform


def rename():
    load_eagerly_initialized_modules()
    # HACK HACK HACK
    config.rename = True
    main()


def rip():
    load_eagerly_initialized_modules()
    main()


def main():
    # TODO(jleen): Is it worth dispatching to wrip automatically?
    if platform.CYGWIN:
        raise Exception('Please use wrip instead')
    platform.prevent_sleep()

    album_path = config.args[0]
    filename = os.path.join(platform.catalog_path, album_path)
    master_name = os.path.split(filename)[1]
    f = open(filename, 'r', encoding='UTF-8')
    track_list = f.readlines()
    f.close()
    playlists = make_playlists(master_name, track_list, album_path,
                               config.extension)

    if not config.rename:
        assert_first_disc_length(playlists[0]['tracks'])
    if config.create_playlists:
        write_playlists(playlists,
                        os.path.join(platform.music_path, album_path),
                        rename=config.rename)

    if config.rename:
        rename_files(playlists[0]['tracks'], album_path,
                     config.extension)
    elif config.rip:
        rip_and_encode(playlists[0]['tracks'], album_path)
