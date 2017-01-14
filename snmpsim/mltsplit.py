#
# This file is part of snmpsim software.
#
# Copyright (c) 2010-2017, Ilya Etingof <etingof@gmail.com>
# License: http://snmpsim.sf.net/license.html
#
# Like string.split but first tries to use composite separator as an
# escaping aid

def split(val, sep):
    for x in (3, 2, 1):
        if val.find(sep * x) != -1:
            return val.split(sep * x)
    return [val]
