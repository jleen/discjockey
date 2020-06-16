# Copyright (c) 2014-2020 John Leen

import discid
import musicbrainzngs as mbz
import os
import sys
import urllib.error
import urllib.error
import urllib.parse
import urllib.parse
import urllib.request
import urllib.request
from xml.etree import ElementTree

from discjockey import config
from discjockey import platform as djplatform

mbz.set_useragent("Saturn Valley Disc Jockey", "1.0",
                  "https://github.com/jleen/discjockey")


def find_track_list(disc_id, medium_list):
    for medium in medium_list:
        for disc in medium['disc-list']:
            if disc['id'] == disc_id:
                return medium['track-list']


def get_tracks_from_musicbrainz(exit_on_fail):
    disc_id = discid.read().id
    disc_data = mbz.get_releases_by_discid(
            disc_id, includes=['recordings', 'artists'])

    # There could be more than one release that includes this disc.  Since
    # we're just going to traverse back to the disc's representation within the
    # release, it doesn't really matter which one we choose.  So choose the
    # first one.
    release = disc_data['disc']['release-list'][0]

    title = release['title']
    artist = release['artist-credit-phrase']
    # TODO: Can MusicBrainz give us a genre tag?

    track_list = find_track_list(disc_id, release['medium-list'])
    sorted_tracks = sorted(track_list, key=lambda t: int(t['position']))
    tracks = [track['recording']['title'] for track in sorted_tracks]

    lines = []
    if not config.nometa:
        #lines.append('~g %s' % genre)
        lines.append('~r %s' % artist)
        lines.append('~a %s' % title)
        lines.append('')
    for track in tracks:
        lines.append('%s' % track)

    for line in lines:
        print(line)

    return lines


def ident(exit_on_fail = True):
    album = None
    if len(config.args) >= 1:
        album = os.path.join(config.catalog_path, config.args[0])
    num_discs = 1
    if len(config.args) >= 2:
        num_discs = int(config.args[1])

    if album and os.path.exists(album):
        raise Exception('Already exists: ' + album)

    djplatform.wait_for_disc()

    for disc in range(num_discs):
        if disc > 0:
            djplatform.eject_disc()
            print()
            print()
            print('--- Insert disc %d of %d ---' % (disc + 1, num_discs))
            djplatform.wait_for_disc()

        lines = get_tracks_from_musicbrainz(exit_on_fail)

        if album:
            if not os.path.exists(os.path.dirname(album)):
                os.makedirs(os.path.dirname(album))
            with open(album, 'a', encoding='utf-8') as f:
                if disc > 0:
                    f.write('~~~\n')
                for line in lines:
                    f.write(line)
                    f.write('\n')

    if num_discs > 1:
        djplatform.eject_disc()
