# Copyright (c) 2012 John Leen

import argparse
import logging
import math
import os

parser = argparse.ArgumentParser()
parser.add_argument('--music', metavar='DIR')
parser.add_argument('--cache', metavar='DIR')
parser.add_argument('-v', '--verbose', action='store_true')

args = parser.parse_args()
if args.verbose: logging.basicConfig(level=logging.INFO)

transcode_formats = [ '.flac' ]
okay_formats = [ '.mp3', '.ogg' ]

def base(filename): return os.path.splitext(filename)[0]
def extension(filename): return os.path.splitext(filename)[1].lower()
def zeroes(num): return '0' * int(1 + math.floor(math.log10(num)))

def transcoded_filename(filename):
    return base(filename) + '.ogg'

def munge_m3u(rel_dir, file):
    # TODO(jleen): Hard link if no changes needed.
    logging.info('Munging playlist %s in %s' % (file, rel_dir))
    f = open(os.path.join(args.music, rel_dir, file), 'r')
    for line in f:
        line = line.rstrip()
        if extension(line) in transcode_formats:
            logging.info('   Adding %s' % (transcoded_filename(line)))
        else:
            logging.info('   Passing through %s' % (line))

def create_m3u(rel_dir, files):
    music_files = [x for x in files if extension(x) in
            okay_formats + transcode_formats]
    m3u_filename = '%s %s.m3u' % (zeroes(len(music_files)),
                                  os.path.basename(rel_dir))
    logging.info('Creating playlist %s in %s' % (m3u_filename, rel_dir))
    for music_file in music_files:
        if extension(music_file) in transcode_formats:
            music_file = transcoded_filename(music_file)
        logging.info('   Adding %s' % (music_file))

def transcode_flac(rel_dir, file):
    # TODO(jleen): We'll probably have to shell out for this.
    logging.info('Transcoding %s in %s' % (file, rel_dir))

def create_link(rel_dir, file):
    logging.info('Linking %s in %s' % (file, rel_dir))


for dir, dirs, files in os.walk(args.music):
    assert dir[0:len(args.music)] == args.music
    rel_dir = dir[1 + len(args.music):]
    did_music = False; did_playlist = False
    for file in files:
        ext = extension(file)
        if ext == '.m3u': munge_m3u(rel_dir, file); did_playlist = True
        if ext == '.flac': transcode_flac(rel_dir, file); did_music = True
        if ext in okay_formats: create_link(rel_dir, file); did_music = True
    if did_music and not did_playlist: create_m3u(rel_dir, files)
