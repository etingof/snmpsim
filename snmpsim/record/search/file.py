#
# This file is part of snmpsim software.
#
# Copyright (c) 2010-2019, Ilya Etingof <etingof@gmail.com>
# License: http://snmplabs.com/snmpsim/license.html
#
from pyasn1.compat.octets import str2octs


# read lines from text file ignoring #comments and blank lines
def get_record(fileObj, line_no=None, offset=0):

    line = fileObj.readline()

    if line_no is not None and line:
        line_no += 1

    while line:
        tline = line.strip()

        # skip comment or blank line
        if not tline or tline.startswith(str2octs('#')):
            offset += len(line)
            line = fileObj.readline()
            if line_no is not None and line:
                line_no += 1

        else:
            break

    return line, line_no, offset


def find_eol(file_obj, offset, block_size=256, eol=str2octs('\n')):

    while True:
        if offset < block_size:
            offset, block_size = 0, offset

        else:
            offset -= block_size

        file_obj.seek(offset)

        chunk = file_obj.read(block_size)

        try:
            return offset + chunk.rindex(eol) + 1

        except ValueError:
            if offset == 0:
                return offset

            continue


# In-place, by-OID binary search
def search_record_by_oid(oid, file_obj, text_parser):

    lo = mid = 0;
    prev_mid = -1

    file_obj.seek(0, 2)

    hi = sz = file_obj.tell()

    while lo < hi:
        mid = (lo + hi) // 2
        file_obj.seek(mid)
        mid = find_eol(file_obj, mid)
        file_obj.seek(mid)
        if mid == prev_mid:  # loop condition due to stepping back pivot
            break

        if mid >= sz:
            return sz

        line, _, skipped_offset = get_record(file_obj)

        if not line:
            return hi

        midval, _ = text_parser.evaluate(line, oidOnly=True)

        if midval < oid:
            lo = mid + skipped_offset + len(line)

        elif midval > oid:
            hi = mid

        else:
            return mid

        prev_mid = mid

    if lo == mid:
        return lo

    else:
        return hi
