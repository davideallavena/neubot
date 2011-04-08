# neubot/system/unix.py

#
# Copyright (c) 2010-2011 Simone Basso <bassosimone@gmail.com>,
#  NEXA Center for Internet & Society at Politecnico di Torino
#
# This file is part of Neubot <http://www.neubot.org/>.
#
# Neubot is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Neubot is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Neubot.  If not, see <http://www.gnu.org/licenses/>.
#

#
# Code for UNIX
#

import pwd
import os.path
import signal
import syslog

class BackgroundLogger(object):

    """We don't use logging.handlers.SysLogHandler because that class
       does not know the name of the UNIX domain socket in use for the
       current operating system.  In many Unices the UNIX domain socket
       name is /dev/log, but this is not true, for example, under the
       Mac.  A better solution seems to use syslog because this is just
       a wrapper to the host syslog library.  And who wrote such lib
       for sure knows the UNIX domain socket location for the current
       operating system."""

    def __init__(self):
        syslog.openlog("neubot", syslog.LOG_PID)

    def error(self, message):
        syslog.syslog(syslog.LOG_DAEMON|syslog.LOG_ERR, message)

    def warning(self, message):
        syslog.syslog(syslog.LOG_DAEMON|syslog.LOG_WARNING, message)

    def info(self, message):
        syslog.syslog(syslog.LOG_DAEMON|syslog.LOG_INFO, message)

    def debug(self, message):
        syslog.syslog(syslog.LOG_DAEMON|syslog.LOG_DEBUG, message)

#
# We need to be the owner of /var/neubot because otherwise
# sqlite3 fails to lock the database for writing.
#
# Read more at http://www.neubot.org/node/14
#

def change_dir():
    if os.getuid() != 0:
        homedir = os.environ["HOME"]
        datadir = os.sep.join([homedir, ".neubot"])
    else:
        datadir = "/var/neubot"

    if not os.path.isdir(datadir):
        os.mkdir(datadir, 0755)

    if os.getuid() == 0:
        passwd = pwd.getpwnam("_neubot")
        os.chown(datadir, passwd.pw_uid, passwd.pw_gid)

    os.chdir(datadir)

def go_background():
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    if os.fork() > 0:
        os._exit(0)

    os.setsid()

    if os.fork() > 0:
        os._exit(0)

def drop_privileges():
    if os.getuid() == 0:
        passwd = pwd.getpwnam("_neubot")
        os.setgid(passwd.pw_gid)
        os.setuid(passwd.pw_uid)

def redirect_to_dev_null():
    for fd in range(0,3):
        os.close(fd)
    os.open("/dev/null", os.O_RDWR)
    os.open("/dev/null", os.O_RDWR)
    os.open("/dev/null", os.O_RDWR)

def want_rw_file(file):
    open(file, "ab+").close()
    if os.getuid() == 0:
        passwd = pwd.getpwnam("_neubot")
        os.chown(file, passwd.pw_uid, passwd.pw_gid)
    os.chmod(file, 0644)
