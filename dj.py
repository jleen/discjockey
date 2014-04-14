# Copyright (c) 2012 John Leen

import argparse
import logging
import math
import os
import re
import shutil
import subprocess
import sys

parser = argparse.ArgumentParser()
parser.add_argument('--music', metavar='DIR', action='append')
parser.add_argument('--cache', metavar='DIR')
parser.add_argument('--mp3', action='store_true')
parser.add_argument('--ogg_quality', type=int, default=5)
parser.add_argument('--mirror', action='store_true')
parser.add_argument('--ogg_bin', metavar='PATH', default='/usr/bin/oggenc')
parser.add_argument('--oggdec_bin', metavar='PATH', default='/usr/bin/oggdec')
parser.add_argument('--flac_bin', metavar='PATH', default='/usr/bin/flac')
parser.add_argument('--lame_bin', metavar='PATH', default='/usr/bin/lame')
parser.add_argument('--file_bin', metavar='PATH', default='/usr/bin/file')
parser.add_argument('-v', '--verbose', action='count')
parser.add_argument('--force_playlists', action='store_true')
parser.add_argument('--keep_sigil', metavar='FILENAME', action='append')
parser.add_argument('--sigil', metavar='FILENAME')
parser.add_argument('--skip_dir', metavar='DIR', action='append')

args = parser.parse_args()

if args.verbose >= 2: log_level = logging.DEBUG
elif args.verbose >= 1: log_level = logging.INFO
else: log_level = logging.WARNING
logging.basicConfig(level=log_level, format='%(message)s')

lossless_formats = [ '.flac', '.wav' ]
boring_formats = [ '.mp3', '.m4a', '.wma' ]

if args.mp3:
    if args.mirror: raise Exception("Can't have both --mirror and --mp3")
    transcode_formats = lossless_formats + [ '.ogg' ]
    okay_formats = boring_formats
    output_format = '.mp3'
elif args.mirror:
    transcode_formats = []
    okay_formats = boring_formats + lossless_formats + [ '.ogg' ]
    output_format = None
else:
    transcode_formats = lossless_formats
    okay_formats = boring_formats + [ '.ogg' ]
    output_format = '.ogg'

music_formats = okay_formats + transcode_formats
link_extns = okay_formats

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
    if extension(filename) in transcode_formats:
        return base(filename) + output_format
    else:
        return filename

def munge_m3u(music_path, rel_dir, filename):
    src = os.path.join(music_path, rel_dir, filename)
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
    else: create_link(music_path, rel_dir, filename)

def create_m3u(music_path, rel_dir, files):
    """Creates or updates a playlist, and returns its basename."""
    music_files = [x for x in files if extension(x) in music_formats]
    # TODO(jleen): Need a trickier heuristic for zeroes, to handle the case
    # where the music files already have leading zeroes that they don't need.
    m3u_filename = '%s %s.m3u' % (zeroes(len(music_files)),
                                  os.path.basename(rel_dir))

    src_dir = os.path.join(music_path, rel_dir)
    m3u_path = cache_path(rel_dir, m3u_filename)

    nuke_non_file(m3u_path)
    if (not args.force_playlists and os.path.isfile(m3u_path) and
            os.stat(m3u_path).st_mtime >= os.stat(src_dir).st_mtime):
        logging.info('Not recreating %s' % m3u_path)
        return m3u_filename

    logging.info('Creating playlist %s in %s' % (m3u_filename, rel_dir))
    ensure_dir(cache_path(rel_dir))
    with open(m3u_path, 'w') as out_f:
        music_files.sort()
        for music_file in music_files:
            if extension(music_file) in transcode_formats:
                music_file = transcoded_filename(music_file)
            logging.info('   Adding %s' % (music_file))
            out_f.write('%s\n' % (music_file))
    return m3u_filename

flac_header_re = re.compile('.+: FLAC audio bitstream data, ' +
                            '(16|24) bit, (mono|stereo), (44\.1|48) kHz, ' +
                            '\d+ samples')
ogg_header_re = re.compile('.+: Ogg data, Vorbis audio, (mono|stereo), ' +
                           '(11025|22050|37800|44100|48000)')

def flac_header(path):
    magic = subprocess.check_output([args.file_bin, path]).rstrip()
    m = flac_header_re.match(magic)

    if   m.group(2) == 'mono'  : channels = '1'
    elif m.group(2) == 'stereo': channels = '2'
    else: assert False

    if   m.group(3) == '44.1': frequency = '44100'
    elif m.group(3) == '48'  : frequency = '48000'
    else: assert False

    return { 'channels': channels, 'frequency': frequency,
             'bitwidth': m.group(1) }

def ogg_header(path):
    magic = subprocess.check_output([args.file_bin, path]).rstrip()
    m = ogg_header_re.match(magic)

    if   m.group(1) == 'mono'  : channels = '1'
    elif m.group(1) == 'stereo': channels = '2'
    else: assert False

    return { 'channels': channels, 'frequency': m.group(2), 'bitwidth': '16' }

def pipe_transcode(music_path, rel_dir, filename, in_format):
    ensure_dir(cache_path(rel_dir))
    in_path = os.path.join(music_path, rel_dir, filename)
    out_path = cache_path(rel_dir, transcoded_filename(filename))

    nuke_non_file(out_path)
    if (os.path.isfile(out_path) and
            os.stat(out_path).st_mtime >= os.stat(in_path).st_mtime):
        logging.info('Not re-transcoding %s' % out_path)
        return

    print 'Transcoding %s' % (os.path.join(rel_dir, filename))
    sys.stdout.flush()
    try:
        with open(os.devnull, 'w') as dev_null:
            if in_format == 'flac':
                header_data = flac_header(in_path)
                decode_proc = subprocess.Popen(
                        [args.flac_bin, '-d', '-c',
                         '--force-raw-format', '--endian=little',
                         '--sign=signed', in_path],
                        stdout=subprocess.PIPE, stderr=dev_null)
            elif in_format == 'ogg':
                header_data = ogg_header(in_path)
                decode_proc = subprocess.Popen(
                        [args.oggdec_bin, '-Q', '-R', '-b', '16',
                         '-o', '-', in_path],
                        stdout=subprocess.PIPE, stderr=dev_null)

            logging.debug('%s has channels=%s bitwidth=%s frequency=%s' %
                          (in_path, header_data['channels'],
                           header_data['bitwidth'], header_data['frequency']))
            
            if args.mp3:
                if header_data['channels'] == '1': channels = 'm'
                elif header_data['channels'] == '2': channels = 's'
                else: assert False

                if   header_data['frequency'] == '11025': frequency = '11.025'
                elif header_data['frequency'] == '22050': frequency = '22.05'
                elif header_data['frequency'] == '37800': frequency = '37.8'
                elif header_data['frequency'] == '44100': frequency = '44.1'
                elif header_data['frequency'] == '48000': frequency = '48'
                else: assert False

                encode_proc = subprocess.Popen(
                        [args.lame_bin,
                         '--quiet',
                         '--preset', 'standard',
                         '-r', '--little-endian',
                         '--bitwidth', header_data['bitwidth'],
                         '-s', frequency,
                         '-m', channels,
                         '-', out_path],
                        stdin=decode_proc.stdout,
                        stdout=subprocess.PIPE, stderr=dev_null)
            else:
                encode_proc = subprocess.Popen(
                        [args.ogg_bin,
                         '-r',
                         '-q', str(args.ogg_quality),
                         '-B', header_data['bitwidth'],
                         '-C', header_data['channels'],
                         '-R', header_data['frequency'],
                         '-o', out_path, '-'],
                        stdin=decode_proc.stdout,
                        stdout=subprocess.PIPE, stderr=dev_null)
            decode_proc.stdout.close()
            encode_proc.communicate()
            # TODO(jleen): Is poll() exactly what we want? Is there a race here
            # if decode_proc sits around after encode_proc terminates?
            decode_proc.poll()
        if encode_proc.returncode != 0:
            if args.mp3: encoder = 'lame'
            else:  encoder = 'oggenc'
            raise Exception('Abnormal %s termination' % encoder)
        if decode_proc.returncode != 0:
            raise Exception('Abnormal %s termination' % in_format)
    except ValueError:
        # Remove the (presumably incomplete) output file if we crash during
        # transcoding.
        logging.debug('Removing %s' % out_path)
        os.unlink(out_path)
        raise

def transcode_flac(music_path, rel_dir, filename):
    pipe_transcode(music_path, rel_dir, filename, 'flac')

def transcode_ogg(music_path, rel_dir, filename):
    pipe_transcode(music_path, rel_dir, filename, 'ogg')

# TODO(jleen): Refactor this and pipe_transcode.
def transcode_wav(music_path, rel_dir, filename):
    ensure_dir(cache_path(rel_dir))
    wav_path = os.path.join(music_path, rel_dir, filename)
    out_path = cache_path(rel_dir, transcoded_filename(filename))

    nuke_non_file(out_path)
    if (os.path.isfile(out_path) and
            os.stat(out_path).st_mtime >= os.stat(wav_path).st_mtime):
        logging.info('Not re-transcoding %s' % out_path)
        return

    print 'Transcoding %s' % (os.path.join(rel_dir, filename))
    sys.stdout.flush()
    try:
        with open(os.devnull, 'w') as dev_null:
            if args.mp3:
                encode_proc = subprocess.Popen(
                        [args.lame_bin, '--quiet', '--preset', 'standard',
                         wav_path, out_path],
                        stdout=subprocess.PIPE, stderr=dev_null)
            else:
                encode_proc = subprocess.Popen(
                        [args.ogg_bin, wav_path, '-q', '6', '-o', out_path],
                        stdout=subprocess.PIPE, stderr=dev_null)
            encode_proc.communicate()
        if encode_proc.returncode != 0:
            raise Exception('Abnormal oggenc termination')
    except:
        # Remove the (presumably incomplete) Vorbis if we crash during
        # transcoding.
        logging.debug('Removing %s' % out_path)
        os.unlink(out_path)
        raise

def create_link(music_path, rel_dir, filename):
    ensure_dir(cache_path(rel_dir))
    src = os.path.join(music_path, rel_dir, filename)
    dst = cache_path(rel_dir, filename)

    nuke_non_file(dst)
    if os.path.isfile(dst):
        # Nothin' to do if src and dst are already hard link buddies.
        if os.stat(src).st_ino == os.stat(dst).st_ino:
            logging.info('Not re-linking %s' % dst)
            return
        else: os.unlink(dst)

    logging.info('Linking %s in %s' % (filename, rel_dir))
    os.link(src, dst)

# TODO(jleen): With a bit of work, this could be done in the main loop as part
# of a single traversal that both pre- and post-visits each directory.
def contains_sigil(path):
    """Walk the tree from the given directory and return whether it or a
    descendant contains a sigil file."""
    for path, dirs, files in os.walk(path):
        if args.sigil in files: return True
    return False

# Takes a list of base directories and walks them as a single merged hierarchy.
def walk_path_with_sigil(bases):
    [base] = bases
    sigil_path = None
    for path, dirs, files in os.walk(base):
        assert path.startswith(base)
        rel_dir = path[1 + len(base):]

        # If we're in sigil mode, see if we're crossing a sigil boundary.
        # TODO(jleen): This is going to be fun in merge mode.
        if args.sigil:
            if sigil_path and not path.startswith(sigil_path):
                sigil_path = None
            if not sigil_path and args.sigil in files:
                sigil_path = path

        # Trim silly directories.
        if args.skip_dir:
            for dirname in args.skip_dir:
                if dirname in dirs: dirs.remove(dirname)

        in_sigil = sigil_path or not args.sigil
        yield base, rel_dir, dirs, files, in_sigil

def find_referents(music_path, rel_dir, m3u_filename):
    m3u = os.path.join(music_path, rel_dir, m3u_filename)
    referents = []

    with open(m3u, 'r') as f:
        lines = [x.rstrip() for x in f.readlines()]

    # TODO(jleen): Unify this with the eerily similar loop in update_cache.
    for line in lines:
        if line.startswith(".."):
            ref = os.path.normpath(os.path.join(rel_dir, line))
            assert(not ref.startswith(".."))
            logging.info('Handling referent %s of %s' % (ref, m3u))
            (ref_dir, ref_filename) = os.path.split(ref)

            # TODO(jleen): Refactor.
            ext = extension(ref_filename)
            if ext in transcode_formats:
                if ext == '.flac':
                    transcode_flac(music_path, ref_dir, ref_filename)
                    referents += [os.path.join(
                            ref_dir, transcoded_filename(ref_filename))]
                if ext == '.ogg':
                    transcode_ogg(music_path, ref_dir, ref_filename)
                    referents += [os.path.join(
                            ref_dir, transcoded_filename(ref_filename))]
                if ext == '.wav':
                    transcode_wav(music_path, ref_dir, ref_filename)
                    referents += [os.path.join(
                            ref_dir, transcoded_filename(ref_filename))]
            if ext in okay_formats:
                create_link(music_path, ref_dir, ref_filename)
                referents += [ref]

    return referents

def contains_referent(rel_dir, leaf_dir, m3u_referents):
    path = os.path.join(rel_dir, leaf_dir)
    return any(ref.startswith(path) for ref in m3u_referents)

def update_cache():
    """Ensure that everything in the master is reflected in the cache.  Mostly
    this is done by creating hard links, but FLAC is transcoded to Vorbis."""

    # First, do all m3u referents.  Need to do this in a preliminary pass,
    # because the main pass will delete any files it doesn't recognize, and
    # the files we find here could be anywhere in the tree.
    m3u_referents = set()
    for music_path, rel_dir, dirs, files, in_sigil in walk_path_with_sigil(
            args.music):
        if in_sigil:
            for filename in files:
                if extension(filename) == '.m3u':
                    m3u_referents.update(
                            find_referents(music_path, rel_dir, filename))

    for music_path, rel_dir, dirs, files, in_sigil in walk_path_with_sigil(
            args.music):
        # Build cache files that are missing or outdated.
        did_music = False; did_playlist = False; file_set = set()
        if in_sigil:
            files.sort()
            for filename in files:
                ext = extension(filename)
                if not filename.startswith('.'):
                    if ext == '.m3u':
                        munge_m3u(music_path, rel_dir, filename)
                        file_set.add(filename)
                        did_playlist = True
                    if ext in transcode_formats:
                        if ext == '.flac':
                            transcode_flac(music_path, rel_dir, filename)
                            file_set.add(transcoded_filename(filename))
                        if ext == '.ogg':
                            transcode_ogg(music_path, rel_dir, filename)
                            file_set.add(transcoded_filename(filename))
                        if ext == '.wav':
                            transcode_wav(music_path, rel_dir, filename)
                            file_set.add(transcoded_filename(filename))
                if ((ext in link_extns and not filename.startswith('.'))
                    or (args.keep_sigil and filename in args.keep_sigil)):
                    create_link(music_path, rel_dir, filename)
                    file_set.add(filename)
                if ext in music_formats: did_music = True
            if did_music and not did_playlist:
                file_set.add(create_m3u(music_path, rel_dir, files))

        # Remove files and directories from the cache that aren't in the master.
        dir_set = frozenset(d for d in dirs if in_sigil or
                                contains_referent(rel_dir, d, m3u_referents) or
                                any(contains_sigil(os.path.join(m, rel_dir, d))
                                        for m in args.music))
        if os.path.isdir(cache_path(rel_dir)):
            for filename in os.listdir(cache_path(rel_dir)):
                path = cache_path(rel_dir, filename)
                if os.path.isdir(path):
                    if filename not in dir_set:
                        if os.path.islink(path): remove_spurious_file(path)
                        else: remove_spurious_dir(path)
                elif (filename not in file_set and
                          os.path.join(rel_dir, filename) not in m3u_referents):
                    remove_spurious_file(path)


update_cache()
