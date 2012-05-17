# Copyright (c) 2012 John Leen

import argparse
import logging
import math
import os
import shutil
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('--music', metavar='DIR')
parser.add_argument('--cache', metavar='DIR')
parser.add_argument('--ogg_bin', metavar='PATH', default='/usr/bin/oggenc')
parser.add_argument('--flac_bin', metavar='PATH', default='/usr/bin/flac')
parser.add_argument('-v', '--verbose', action='store_true')

args = parser.parse_args()

if args.verbose: log_level = logging.INFO
else: log_level = logging.WARNING
logging.basicConfig(level=log_level, format='%(message)s')

transcode_formats = [ '.flac' ]
okay_formats = [ '.mp3', '.ogg' ]
misc_extensions = [ '.sync' ]

music_formats = okay_formats + transcode_formats
link_extns = okay_formats + misc_extensions

def music_path(*pathcomps): return os.path.join(args.music, *pathcomps)
def cache_path(*pathcomps): return os.path.join(args.cache, *pathcomps)

def base(filename): return os.path.splitext(filename)[0]
def extension(filename): return os.path.splitext(filename)[1].lower()
def zeroes(num): return '0' * int(1 + math.floor(math.log10(num)))

def ensure_dir(dirname):
    if not os.path.isdir(dirname): os.makedirs(dirname)

def remove_spurious_file(path):
    logging.info('Removing spurious file %s' % (path))
    os.unlink(path)

def remove_spurious_dir(path):
    logging.info('Removing spurious directory %s' % (path))
    shutil.rmtree(path)

def nuke_non_file(path):
    if not os.path.exists(path): return
    if os.path.islink(path): remove_spurious_file(path)
    elif os.path.isdir(path): remove_spurious_dir(path)
    elif not os.path.isfile(path): remove_spurious_file(path)

def transcoded_filename(filename):
    if extension(filename) in transcode_formats: return base(filename) + '.ogg'
    else: return filename

def munge_m3u(rel_dir, filename):
    src = music_path(rel_dir, filename)
    dst = cache_path(rel_dir, filename)

    nuke_non_file(dst)
    if (os.path.isfile(dst) and
            os.stat(dst).st_mtime >= os.stat(src).st_mtime):
        logging.info('Not re-munging %s' % dst)
        return

    logging.info('Munging playlist %s in %s' % (filename, rel_dir))
    with open(src, 'r') as f:
        lines = [x.rstrip() for x in f.readlines()]

    if any(extension(line) in transcode_formats for line in lines):
        ensure_dir(cache_path(rel_dir))
        with open(dst, 'w') as out_f:
            for line in lines:
                if extension(line) in transcode_formats:
                    logging.info('   Munging %s' % (transcoded_filename(line)))
                out_f.write('%s\n' % (transcoded_filename(line)))
            else:
                logging.info('   Passing through %s' % (line))
                out_f.write('%s\n' % (line))
    else: create_link(rel_dir, filename)

def create_m3u(rel_dir, files):
    """Creates or updates a playlist, and returns its basename."""
    music_files = [x for x in files if extension(x) in music_formats]
    m3u_filename = '%s %s.m3u' % (zeroes(len(music_files)),
                                  os.path.basename(rel_dir))

    src_dir = music_path(rel_dir)
    m3u_path = cache_path(rel_dir, m3u_filename)

    nuke_non_file(m3u_path)
    if (os.path.isfile(m3u_path) and
            os.stat(m3u_path).st_mtime >= os.stat(src_dir).st_mtime):
        logging.info('Not recreating %s' % m3u_path)
        return m3u_filename

    logging.info('Creating playlist %s in %s' % (m3u_filename, rel_dir))
    ensure_dir(cache_path(rel_dir))
    with open(m3u_path, 'w') as out_f:
        for music_file in music_files:
            if extension(music_file) in transcode_formats:
                music_file = transcoded_filename(music_file)
            logging.info('   Adding %s' % (music_file))
            out_f.write('%s\n' % (music_file))
    return m3u_filename

def transcode_flac(rel_dir, filename):
    ensure_dir(cache_path(rel_dir))
    flac_path = music_path(rel_dir, filename)
    ogg_path = cache_path(rel_dir, transcoded_filename(filename))

    nuke_non_file(ogg_path)
    if (os.path.isfile(ogg_path) and
            os.stat(ogg_path).st_mtime >= os.stat(flac_path).st_mtime):
        logging.info('Not re-transcoding %s' % ogg_path)
        return

    print 'Transcoding %s' % (os.path.join(rel_dir, filename))
    try:
        with open(os.devnull, 'w') as dev_null:
            decode_proc = subprocess.Popen(
                    [args.flac_bin, '-d', '-c', flac_path],
                    stdout=subprocess.PIPE, stderr=dev_null)
            encode_proc = subprocess.Popen(
                    [args.ogg_bin, '-', '-o', ogg_path],
                    stdin=decode_proc.stdout,
                    stdout=subprocess.PIPE, stderr=dev_null)
            decode_proc.stdout.close()
            encode_proc.communicate()
            # TODO(jleen): Is poll() exactly what we want? Is there a race here
            # if flac sits around after oggenc terminates?
            decode_proc.poll()
        if encode_proc.returncode != 0:
            raise Exception('Abnormal oggenc termination')
        if decode_proc.returncode != 0:
            raise Exception('Abnormal flac termination')
    except:
        # Remove the (presumably incomplete) Vorbis if we crash during
        # transcoding.
        logging.debug('Removing %s' % ogg_path)
        os.unlink(ogg_path)
        raise

def create_link(rel_dir, filename):
    ensure_dir(cache_path(rel_dir))
    src = music_path(rel_dir, filename); dst = cache_path(rel_dir, filename)

    nuke_non_file(dst)
    if os.path.isfile(dst):
        # Nothin' to do if src and dst are already hard link buddies.
        if os.stat(src).st_ino == os.stat(dst).st_ino:
            logging.info('Not re-linking %s' % dst)
            return
        else: os.unlink(dst)

    logging.info('Linking %s in %s' % (filename, rel_dir))
    os.link(src, dst)

def update_cache():
    """Ensure that everything in the master is reflected in the cache.  Mostly
    this is done by creating hard links, but FLAC is transcoded to Vorbis."""
    for path, dirs, files in os.walk(args.music):
        assert path[0:len(args.music)] == args.music
        rel_dir = path[1 + len(args.music):]

        # Build cache files that are missing or outdated.
        did_music = False; did_playlist = False; file_set = set()
        for filename in files:
            ext = extension(filename)
            if ext == '.m3u':
                munge_m3u(rel_dir, filename)
                file_set.add(filename)
                did_playlist = True
            if ext == '.flac':
                transcode_flac(rel_dir, filename)
                file_set.add(transcoded_filename(filename))
            if ext in link_extns:
                create_link(rel_dir, filename)
                file_set.add(filename)
            if ext in music_formats: did_music = True
        if did_music and not did_playlist:
            file_set.add(create_m3u(rel_dir, files))

        # Remove files and directories from the cache that aren't in the master.
        dir_set = frozenset(dirs)
        if os.path.isdir(cache_path(rel_dir)):
            for filename in os.listdir(cache_path(rel_dir)):
                path = cache_path(rel_dir, filename)
                if os.path.isdir(path):
                    if filename not in dir_set:
                        if os.path.islink(path): remove_spurious_file(path)
                        else: remove_spurious_dir(path)
                elif filename not in file_set: remove_spurious_file(path)


update_cache()
