# Like string.split but first tries to use composite separator as an
# escaping aid
def split(val, sep):
  for x in (3, 2, 1):
      if val.find(sep*x) != -1:
          return val.split(sep*x)
  return [ val ]
