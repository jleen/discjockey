import re
import sys

from collections import Counter
from pathlib import Path
from zipfile import ZipFile


def track_info(filename):
    parts = filename.split(' - ')
    artist = parts[0]
    parts = parts[1:]

    album_parts = []
    while not re.match('^\\d+ ', parts[0]):
        album_parts += [parts[0]]
        parts = parts[1:]
    album = ' - '.join(album_parts)

    track = ' - '.join(parts)

    return [filename, artist, album, track]


def decamp():
    with ZipFile(sys.argv[1]) as zipfile:
        files = zipfile.namelist()
        tracks = [track_info(f) for f in files if f.endswith('.flac')]
        extra = [f for f in files if not f.endswith('.flac')]
        if len(set([x[2] for x in tracks])) != 1:
            raise Exception("Multiple album names? I can't even")

        artists = Counter(x[1] for x in tracks)
        (primary_artist, count) = artists.most_common(1)[0]
        if count <= len(tracks) / 2:
            primary_artist = 'Anthology'

        dest_dir = Path(primary_artist, tracks[1][2])
        dest_dir.mkdir(parents=True)

        for (filename, artist, _, title) in tracks:
            if artist != primary_artist:
                dest = f'{Path(title).stem} ({artist}).flac'
            else:
                dest = title
            unzip_to(dest_dir / dest, zipfile, filename)

        for filename in extra:
            unzip_to(dest_dir / filename, zipfile, filename)


def unzip_to(dest, zipfile, content):
    if Path(dest).exists():
        raise Exception('Quitting now instead of overwriting')
    with open(dest, 'wb') as out:
        out.write(zipfile.read(content))
