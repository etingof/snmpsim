from pyasn1.compat.octets import str2octs

# In-place, by-OID binary search
def searchRecordByOid(oid, fileObj, textParser, eol=str2octs('\n')):
    lo = mid = 0; prev_mid = -1
    fileObj.seek(0, 2)
    hi = sz = fileObj.tell()
    while lo < hi:
        mid = (lo+hi)//2
        fileObj.seek(mid)
        while mid:
            c = fileObj.read(1)
            if c == eol:
                mid = mid + 1
                break
            mid = mid - 1    # pivot stepping back in search for full line
            fileObj.seek(mid)
        if mid == prev_mid:  # loop condition due to stepping back pivot
            break
        if mid >= sz:
            return sz
        line = fileObj.readline()
        midval, _ = textParser.evaluate(line, oidOnly=True)
        if midval < oid:
            lo = mid + len(line)
        elif midval > oid:
            hi = mid
        else:
            return mid
        prev_mid = mid
    if lo == mid:
        return lo
    else:
        return hi

