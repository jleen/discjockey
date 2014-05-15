# Copyright (c) 2014 John Leen

import argparse
import json
import platform
import subprocess
import sys
import urllib
import urllib2
from xml.etree import ElementTree

parser = argparse.ArgumentParser()
parser.add_argument('--client')
parser.add_argument('--user')
args = parser.parse_args()


# Read the CD TOC

if platform.system() == 'Darwin':
    p = subprocess.Popen(['drutil', 'trackinfo'],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
else:
    p = subprocess.Popen(['/usr/bin/cdrecord', '-toc'],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
out, err = p.communicate()


toc = ''
if platform.system() == 'Darwin':
    for line in out.splitlines():
        if line[8:18] == 'trackStart':
            last_start = int(line[27:]) + 150
            toc += str(last_start) + ' '
        elif line[16:25] == 'trackSize':
            last_length = int(line[27:])
        elif line.startswith('  Please insert a disc to get track info.'):
            print "You don't seem to have given me a disc."
            sys.exit(1)
    # drutil doesn't report the leadout, but Gracenote needs it for ID.
    toc += str(last_start + last_length) + ' '
else:
    for line in out.splitlines():
        if line.startswith('track'):
            toc += str(int(line[17:26]) + 150) + ' '
    

# Query Gracenote

cid = args.client
uid = args.user

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

responseObj = urllib2.urlopen(url, ElementTree.tostring(root))
responseText = responseObj.read()
responseTree = ElementTree.fromstring(responseText)
response = responseTree.find('RESPONSE')

status = response.attrib['STATUS']
if status != 'OK':
    print "Gracenote couldn't find that disc."
    print
    print "Queried for %s" % toc
    print "Got response %s" % status
    sys.exit(2)

album = response.find('ALBUM')
artist = urllib.unquote(album.findall('ARTIST')[0].text)
title = urllib.unquote(album.findall('TITLE')[0].text)
genre = urllib.unquote(album.findall('GENRE')[0].text)

tracks = []
trackTree = album.findall('TRACK')
for track in trackTree:
    tracks.append(urllib.unquote(track.findall('TITLE')[0].text))

print '~g %s' % genre
print '~r %s' % artist
print '~a %s' % title
print
for track in tracks: print track.encode('utf-8')
