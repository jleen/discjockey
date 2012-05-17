# Copyright (c) 2012 John Leen

import argparse
import logging
import math
import os
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('--music', metavar='DIR')
parser.add_argument('--cache', metavar='DIR')
parser.add_argument('--ogg_bin', metavar='PATH',
                    default='/opt/local/bin/oggenc')
parser.add_argument('--flac_bin', metavar='PATH',
                    default='/opt/local/bin/flac')
parser.add_argument('-v', '--verbose', action='store_true')

args = parser.parse_args()

if args.verbose: log_level = logging.INFO
else: log_level = logging.WARNING
logging.basicConfig(level=log_level, format='%(message)s')

transcode_formats = [ '.flac' ]
okay_formats = [ '.mp3', '.ogg' ]

def music_path(*pathcomps): return os.path.join(args.music, *pathcomps)
def cache_path(*pathcomps): return os.path.join(args.cache, *pathcomps)

def base(filename): return os.path.splitext(filename)[0]
def extension(filename): return os.path.splitext(filename)[1].lower()
def zeroes(num): return '0' * int(1 + math.floor(math.log10(num)))

def ensure_dir(dirname):
    if not os.path.isdir(dirname): os.makedirs(dirname)

def transcoded_filename(filename):
    return base(filename) + '.ogg'

def munge_m3u(rel_dir, file):
    logging.info('Munging playlist %s in %s' % (file, rel_dir))
    with open(music_path(rel_dir, file), 'r') as f:
        lines = [x.rstrip() for x in f.readlines()]

    if any(extension(line) in transcode_formats for line in lines):
        ensure_dir(cache_path(rel_dir))
        with open(cache_path(rel_dir, file), 'w') as out_f:
            for line in lines:
                if extension(line) in transcode_formats:
                    logging.info('   Munging %s' % (transcoded_filename(line)))
                out_f.write('%s\n' % (transcoded_filename(line)))
            else:
                logging.info('   Passing through %s' % (line))
                out_f.write('%s\n' % (line))
    else: create_link(rel_dir, file)

def create_m3u(rel_dir, files):
    music_files = [x for x in files if extension(x) in
            okay_formats + transcode_formats]
    m3u_filename = '%s %s.m3u' % (zeroes(len(music_files)),
                                  os.path.basename(rel_dir))
    logging.info('Creating playlist %s in %s' % (m3u_filename, rel_dir))

    ensure_dir(cache_path(rel_dir))
    with open(cache_path(rel_dir, m3u_filename), 'w') as out_f:
        for music_file in music_files:
            if extension(music_file) in transcode_formats:
                music_file = transcoded_filename(music_file)
            logging.info('   Adding %s' % (music_file))
            out_f.write('%s\n' % (music_file))

def transcode_flac(rel_dir, file):
    print 'Transcoding %s' % (os.path.join(rel_dir, file))
    ensure_dir(cache_path(rel_dir))
    flac_path = music_path(rel_dir, file)
    ogg_path = cache_path(rel_dir, transcoded_filename(file))

    with open(os.devnull, 'w') as dev_null:
        decode_proc = subprocess.Popen([args.flac_bin, '-d', '-c', flac_path],
                                       stdout=subprocess.PIPE, stderr=dev_null)
        encode_proc = subprocess.Popen([args.ogg_bin, '-', '-o', ogg_path],
                                       stdin=decode_proc.stdout,
                                       stdout=subprocess.PIPE, stderr=dev_null)
        decode_proc.stdout.close()
        encode_proc.communicate()
        # TODO(jleen): Is poll() exactly what we want? Is there a race here if
        # flac sits around after oggenc terminates?
        decode_proc.poll()
    if encode_proc.returncode != 0:
        raise Exception('Abnormal oggenc termination')
    if decode_proc.returncode != 0:
        raise Exception('Abnormal flac termination')

def create_link(rel_dir, file):
    logging.info('Linking %s in %s' % (file, rel_dir))
    ensure_dir(cache_path(rel_dir))
    os.link(music_path(rel_dir, file), cache_path(rel_dir, file))

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
