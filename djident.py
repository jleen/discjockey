from xml.etree import ElementTree
import urllib2, urllib, json, subprocess

parser = argparse.ArgumentParser()
parser.add_argument('--client')
parser.add_argument('--user')
args = parser.parse_args()

# Read the CD TOC

p = subprocess.Popen(['/usr/bin/cdrecord', '-toc'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
out, err = p.communicate()

toc = ''
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

if response.attrib['STATUS'] != 'OK': raise 'uh oh'

album = response.find('ALBUM')
artist = urllib.unquote(album.findall('ARTIST')[0].text)
title = urllib.unquote(album.findall('TITLE')[0].text)

tracks = []
trackTree = album.findall('TRACK')
for track in trackTree:
    tracks.append(urllib.unquote(track.findall('TITLE')[0].text))

print 'Rock/%s/%s' % (artist, title)
for track in tracks: print track
