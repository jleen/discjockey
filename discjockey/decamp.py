import os
import sys

from zipfile import ZipFile

DELIM = ' - '


def bandcamp_prefix(strings):
    first = strings[0]
    skip = 0
    candidate = ''
    found = ''
    for i in range(0, first.count(DELIM)):
        skip = first.find(DELIM, skip) + len(DELIM)
        candidate = first[0:skip]
        for s in strings:
            if s.endswith('.flac') and not s.startswith(candidate):
                # Me go too far.
                return found
        found = candidate
    return found


def decamp():
    with ZipFile(sys.argv[1]) as zipfile:
        files = zipfile.namelist()
        prefix = bandcamp_prefix(files)
        try:
            (artist, album) = prefix[:-len(DELIM)].split(DELIM, 1)
        except Exception as ex:
            print("Can't parse common file prefix " + prefix)
            print("Filenames are:\n" + "\n".join(files))
            raise ex
        print('Album is ' + album + ' by ' + artist)
        where = os.path.join(artist, album)
        os.makedirs(where, exist_ok=True)

        for name in files:
            new_name = name[len(prefix):] if name.endswith('.flac') else name
            print('Extracting ' + new_name)
            dest = os.path.join(where, new_name)
            if os.path.lexists(dest):
                raise Exception('Quitting now instead of overwriting')
            with open(dest, 'wb') as out:
                out.write(zipfile.read(name))
