# Copyright (c) 2014-2019 John Leen

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


def register_gracenote_user():
    cid = config.gracenote_client

    url = 'https://c' + cid.split('-')[0] + '.web.cddbp.net/webapi/xml/1.0/'

    root = ElementTree.Element('QUERIES')

    query = ElementTree.SubElement(root, 'QUERY')
    query.attrib['CMD'] = 'REGISTER'
    client = ElementTree.SubElement(query, 'CLIENT')
    client.text = cid

    response_obj = urllib.request.urlopen(url, ElementTree.tostring(root))
    response_text = response_obj.read()
    response_tree = ElementTree.fromstring(response_text)
    response = response_tree.find('RESPONSE')

    status = response.attrib['STATUS']
    if status != 'OK':
        print(response_tree.find('MESSAGE').text)
        sys.exit(2)

    user = response.find('USER').text
    print(user)


register_gracenote_user()
