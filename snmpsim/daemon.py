#
# This file is part of snmpsim software.
#
# Copyright (c) 2010-2019, Ilya Etingof <etingof@gmail.com>
# License: http://snmplabs.com/snmpsim/license.html
#
import sys
from snmpsim import error


if sys.platform[:3] == 'win':
    def daemonize(pidfile):
        raise error.SnmpsimError('Windows is not inhabited with daemons!')


    class PrivilegesOf(object):
        """Context manager performing nothing on Windows"""

        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            pass

        def __exit__(self, *args):
            pass

else:
    import os
    import pwd
    import grp
    import atexit
    import signal
    import tempfile


    def daemonize(pidfile):
        try:
            pid = os.fork()
            if pid > 0:
                # exit first parent
                os._exit(0)
        except OSError:
            raise error.SnmpsimError('ERROR: fork #1 failed: %s' % sys.exc_info()[1])

        # decouple from parent environment
        try:
            os.chdir('/')
            os.setsid()
        except OSError:
            pass
        os.umask(0)

        # do second fork
        try:
            pid = os.fork()
            if pid > 0:
                # exit from second parent
                os._exit(0)
        except OSError:
            raise error.SnmpsimError('ERROR: fork #2 failed: %s' % sys.exc_info()[1])

        def signal_cb(s, f):
            raise KeyboardInterrupt

        for s in signal.SIGTERM, signal.SIGINT, signal.SIGHUP, signal.SIGQUIT:
            signal.signal(s, signal_cb)

        # write pidfile
        def atexit_cb():
            try:
                if pidfile:
                    os.remove(pidfile)
            except OSError:
                pass

        atexit.register(atexit_cb)

        try:
            if pidfile:
                fd, nm = tempfile.mkstemp(dir=os.path.dirname(pidfile))
                os.write(fd, ('%d\n' % os.getpid()).encode('utf-8'))
                os.close(fd)
                os.rename(nm, pidfile)
        except Exception:
            raise error.SnmpsimError(
                'Failed to create PID file %s: %s' % (pidfile, sys.exc_info()[1]))

        # redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()
        si = open(os.devnull, 'r')
        so = open(os.devnull, 'a+')
        se = open(os.devnull, 'a+')

        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())


    class PrivilegesOf(object):
        """Context manager executing under reduced privileges"""

        def __init__(self, uname, gname, final=False):
            self._uname = uname
            self._gname = gname
            self._final = final
            self._olduid = self._oldgid = None

        def __enter__(self):
            if os.getuid() != 0:
                if (self._uname and self._uname != pwd.getpwnam(self._uname).pw_name or
                        self._gname and self._gname != grp.getgrnam(self._gname).gr_name):
                    raise error.SnmpsimError('Process is running under different UID/GID')
                else:
                    return
            else:
                if not self._uname or not self._gname:
                    raise error.SnmpsimError('Must drop privileges to a non-privileged user&group')

            try:
                runningUid = pwd.getpwnam(self._uname).pw_uid
                runningGid = grp.getgrnam(self._gname).gr_gid

            except Exception:
                raise error.SnmpsimError(
                    'getpwnam()/getgrnam() failed for %s/%s: %s' % (
                        self._uname, self._gname, sys.exc_info()[1]))

            try:
                os.setgroups([])

            except Exception:
                raise error.SnmpsimError('setgroups() failed: %s' % sys.exc_info()[1])

            try:
                if self._final:
                    os.setgid(runningGid)
                    os.setuid(runningUid)

                else:
                    self._olduid = os.getuid()
                    self._oldgid = os.getgid()

                    os.setegid(runningGid)
                    os.seteuid(runningUid)

            except Exception:
                raise error.SnmpsimError(
                    '%s failed for %s/%s: %s' % (
                        self._final and 'setgid()/setuid()' or 'setegid()/seteuid()',
                        runningGid, runningUid, sys.exc_info()[1]))

            os.umask(63)  # 0077

        def __exit__(self, *args):
            if self._olduid is None or self._oldgid is None:
                return

            try:
                os.setegid(self._oldgid)
                os.seteuid(self._olduid)

            except Exception:
                raise error.SnmpsimError(
                    'setegid()/seteuid() failed for %s/%s: %s' % (
                        self._oldgid, self._olduid, sys.exc_info()[1]))
