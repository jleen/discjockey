# Copyright (c) 2012 John Leen

import argparse
import math
import os

parser = argparse.ArgumentParser()
parser.add_argument('--music', metavar='DIR')
parser.add_argument('--cache', metavar='DIR')

args = parser.parse_args()

transcode_formats = [ '.flac' ]
okay_formats = [ '.mp3', '.ogg' ]

def zeroes(num): return '0' * int(1 + math.floor(math.log10(num)))

def munge_m3u(rel_dir, file):
    # TODO(jleen): Hard link if no changes needed.
    print 'Munging playlist %s in %s' % (file, rel_dir)
    f = open(os.path.join(args.music, rel_dir), 'r')
    for line in f:
        ext = os.path.splitext(line)[1].lower()
        if ext in transcode_formats:
            print '   Adding %s' % (transcoded_filename(line))
        else:
            print '   Passing through %s' % (line)

def create_m3u(rel_dir, files):
    music_files = [x for x in files if os.path.splitext(x)[1].lower() in
            okay_formats + transcode_formats]
    m3u_filename = '%s %s.m3u' % (zeroes(len(music_files)),
                                  os.path.basename(rel_dir))
    print 'Creating playlist %s in %s' % (m3u_filename, rel_dir)
    for music_file in music_files: print '   Adding %s' % (music_file)

def transcode_flac(rel_dir, file):
    # TODO(jleen): We'll probably have to shell out for this.
    print 'Transcoding %s in %s' % (file, rel_dir)

def create_link(rel_dir, file):
    print 'Linking %s in %s' % (file, rel_dir)


for dir, dirs, files in os.walk(args.music):
    assert dir[0:len(args.music)] == args.music
    rel_dir = dir[1 + len(args.music):]
    did_music = False; did_playlist = False
    for file in files:
        ext = os.path.splitext(file)[1].lower()
        if ext == '.m3u': munge_m3u(rel_dir, file); did_playlist = True
        if ext == '.flac': transcode_flac(rel_dir, file); did_music = True
        if ext in okay_formats: create_link(rel_dir, file); did_music = True
    if did_music and not did_playlist: create_m3u(rel_dir, files)
