# Copyright (c) 2015 John Leen

import re
import sys

MIN_PREFIX_LEN = 10
END_OF_SET = '~~~END~OF~SET~~~'
DISC_DELIMITER = '~~~'


def longest_common_prefix(foo, bar):
    result = ''
    for (f, b) in zip(foo, bar):
        if f == b:
            result += f
        else:
            return result
    return result


CRUFTY = re.compile(r'[:\-, ]*(I*|No. \d*)$')


def sanitize_prefix(prefix):
    cruft = CRUFTY.search(prefix)
    return (prefix[:-len(cruft.group(0))],
            len(prefix) - len(cruft.group(1)))


SUBS = [('1.', 'I.'),
        ('2.', 'II.'),
        ('3.', 'III.'),
        ('3.', 'III.'),
        ('4.', 'IV.'),
        ('5.', 'V.'),
        ('6.', 'VI.'),
        ('7.', 'VII.'),
        ('8.', 'VIII.'),
        ('9.', 'IX.'),
        ('10.', 'X.')]


def beautify_line(line):
    for (old, new) in SUBS:
        line = re.sub('^' + re.escape(old), new, line)
    return line


def decrement_index(i, lines):
    while True:
        i -= 1
        if i < 0:
            break
        if not lines[i][0] == DISC_DELIMITER:
            break
    return i


def beautify(tracks):
    # We're gonna follow the "array of strings as an output stream" pattern.
    out = []

    # First, trim any common prefix of the whole set,
    # because it's probably just the composer or something else redundant.
    boring_prefix = tracks[0]
    for track in tracks[1:]:
        boring_prefix = longest_common_prefix(boring_prefix, track)

    if ' - ' in boring_prefix:
        where = boring_prefix.rindex(' - ')
        tracks = [track[where+3:] for track in tracks]

    # TODO: Ugh.
    lines = [[track, None, 0] for track in tracks]

    prefix = None

    for (i, line) in enumerate(lines[1:], 1):
        if line[0] == DISC_DELIMITER:
            continue
        i_minus_1 = decrement_index(i, lines)

        if prefix:
            if line[0].startswith(prefix):
                # This is another track in the current set.
                lines[i][2] = lines[i_minus_1][2]
            else:
                # The set has ended.
                prefix = None
                lines[i_minus_1][1] = END_OF_SET
        else:
            new_prefix = longest_common_prefix(line[0], lines[i_minus_1][0])
            if new_prefix and len(new_prefix) > MIN_PREFIX_LEN:
                # This track and the previous look like the beginning of a
                # new set.
                (prefix, strip_len) = sanitize_prefix(new_prefix)
                i_minus_2 = decrement_index(i_minus_1, lines)
                if i_minus_2 >= 0:
                    lines[i_minus_2][1] = END_OF_SET
                if i_minus_1 >= 0:
                    lines[i_minus_1][1] = prefix
                    lines[i_minus_1][2] = strip_len
                lines[i][2] = strip_len

    prefix = None
    for (line, new_prefix, strip_len) in lines:
        if line == DISC_DELIMITER:
            out += [DISC_DELIMITER]
            assert not new_prefix
            assert not strip_len
        else:
            if new_prefix and new_prefix != END_OF_SET:
                prefix = new_prefix
                out += ['* %s' % prefix]

            if prefix:
                assert line.startswith(prefix)
                out += [beautify_line(line[strip_len:])]
            else:
                out += [beautify_line(line)]

        if new_prefix == END_OF_SET:
            prefix = None
            out += ['']

    return out


def sets(tracks):
    raw = beautify(tracks)

    out = []
    cur = out

    for line in raw:
        if len(line) == 0:
            if id(cur) != id(out):
                out += [cur]
                cur = out
        elif line.startswith('* '):
            if id(cur) != id(out):
                out += [cur]
            cur = [line[2:]]
        else:
            cur += [line]
    if id(cur) != id(out):
        out += [cur]

    return out

def cosmetize():
    lines = []

    for line in sys.stdin:
        if len(line) > 1 and not re.match(r'^~\w', line):
            lines += line.rstrip()

    for line in beautify(lines):
        print(line)


if __name__ == '__main__':
    cosmetize()
