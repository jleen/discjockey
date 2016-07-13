# Copyright (c) 2014-2016 John Leen

import argparse
import json
import platform
import subprocess
import sys
import urllib.request, urllib.parse, urllib.error
import urllib.request, urllib.error, urllib.parse
from xml.etree import ElementTree

import djconfig
import djplatform

toc = djplatform.read_toc()

cid = djconfig.gracenote_client
uid = djconfig.gracenote_user

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

if not djconfig.nometa:
    sys.stdout.buffer.write(('~g %s\n' % genre).encode('utf-8'))
    sys.stdout.buffer.write(('~r %s\n' % artist).encode('utf-8'))
    sys.stdout.buffer.write(('~a %s\n' % title).encode('utf-8'))
    sys.stdout.buffer.write('\n'.encode('utf-8'))
for track in tracks: sys.stdout.buffer.write(('%s\n' % track).encode('utf-8'))
