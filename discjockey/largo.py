import argparse
import os
import re

from itertools import chain
from zipfile import ZipFile

from discjockey import beautify
from discjockey import rip


DELIM = ' - '
PATTERN = r'.*/\d* - (.*)'


def get_common_dir(paths):
    prefix = paths[0].split('/')[0]
    for path in paths:
        if not path.startswith(f'{prefix}/'):
            raise Exception(f'Failed to verify dir prefix {prefix}')
    return prefix


def bandcamp_prefix(strings):
    first = strings[0]
    skip = 0
    candidate = ''
    found = ''
    for _ in range(0, first.count(DELIM)):
        skip = first.find(DELIM, skip) + len(DELIM)
        candidate = first[0:skip]
        for s in strings:
            if s.endswith('.flac') and not s.startswith(candidate):
                # Me go too far.
                return found
        found = candidate
    return found


def largo():
    parser = argparse.ArgumentParser()
    parser.add_argument('-n', action='store_true')
    parser.add_argument('filename')
    args = parser.parse_args()

    with ZipFile(args.filename) as zipfile:
        paths = zipfile.namelist()
        target_dir = get_common_dir(paths)
        track_paths = [path for path in paths if path.endswith('.flac')]
        tracks = [re.match(PATTERN, path)[1] for path in track_paths]
        extra_paths = [path for path in paths if not path.endswith('.flac')]
        extras = [path.split('/')[1] for path in extra_paths]
        playlists = rip.make_playlists(target_dir, beautify.beautify(tracks),
                                       os.path.join('-', '-', '-'), '')
        track_names = [t['filename'] for t in playlists[0]['tracks']]

        rip.write_playlists(playlists, target_dir, dry_run=args.n)

        track_jobs = zip(track_paths, track_names)
        extra_jobs = zip(extra_paths, extras)
        for (source, dest) in chain(track_jobs, extra_jobs):
            dest = os.path.join(target_dir, dest)
            if os.path.lexists(dest):
                raise Exception('Quitting now instead of overwriting')
            if args.n:
                print(f'Would extract {source} as {dest}')
            else:
                print(f'Extracting {dest}')
                with open(dest, 'wb') as out:
                    out.write(zipfile.read(source))
