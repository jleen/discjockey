# Copyright (c) 2014-2016 John Leen

import json
import os
import platform
import subprocess
import sys
import urllib.request, urllib.parse, urllib.error
import urllib.request, urllib.error, urllib.parse
from xml.etree import ElementTree

from discjockey import config
from discjockey import platform as djplatform

def get_tracks_from_gracenote():
    toc = djplatform.read_toc()

    cid = config.gracenote_client
    uid = config.gracenote_user

    url = 'https://c' + cid.split('-')[0] + '.web.cddbp.net/webapi/xml/1.0/'

    root = ElementTree.Element('QUERIES')

    auth = ElementTree.SubElement(root, 'AUTH')
    client = ElementTree.SubElement(auth, 'CLIENT')
    user = ElementTree.SubElement(auth, 'USER')
    client.text = cid
    user.text = uid

    query = ElementTree.SubElement(root, 'QUERY')
    query.attrib['CMD'] = 'ALBUM_TOC'
    mode = ElementTree.SubElement(query, 'MODE')
    mode.text = 'SINGLE_BEST'  # or SINGLE_BEST_COVER

    tocNode = ElementTree.SubElement(query, 'TOC')
    offset = ElementTree.SubElement(tocNode, 'OFFSETS')
    offset.text = toc

    responseObj = urllib.request.urlopen(url, ElementTree.tostring(root))
    responseText = responseObj.read()
    responseTree = ElementTree.fromstring(responseText)
    response = responseTree.find('RESPONSE')

    status = response.attrib['STATUS']
    if status != 'OK':
        print("Gracenote couldn't find that disc.")
        print()
        print("Queried for %s" % toc)
        print("Got response %s" % status)
        sys.exit(2)

    album = response.find('ALBUM')
    artist = urllib.parse.unquote(album.findall('ARTIST')[0].text)
    title = urllib.parse.unquote(album.findall('TITLE')[0].text)
    genre = urllib.parse.unquote(album.findall('GENRE')[0].text)

    tracks = []
    trackTree = album.findall('TRACK')
    for track in trackTree:
        tracks.append(urllib.parse.unquote(track.findall('TITLE')[0].text))

    lines = []
    if not config.nometa:
        lines.append('~g %s' % genre)
        lines.append('~r %s' % artist)
        lines.append('~a %s' % title)
        lines.append('')
    for track in tracks:
        lines.append('%s' % track)

    for line in lines:
        print(line)

    return lines


def ident():
    album = None
    if len(config.args) >= 1: album = config.args[0]
    num_discs = 1
    if len(config.args) >= 2: num_discs = int(config.args[1])

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

        lines = get_tracks_from_gracenote()

        if album:
            with open(album, 'a', encoding='utf-8') as f:
                if disc > 0:
                    f.write('~~~\n')
                for line in lines:
                    f.write(line)
                    f.write('\n')

    if num_discs > 1: djplatform.eject_disc()
