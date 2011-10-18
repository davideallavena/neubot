#!/bin/sh

#
# Copyright (c) 2011 Simone Basso <bassosimone@gmail.com>,
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

set -e

VERSIONDIR=MacOS/basedir-skel/versiondir-skel

#
# Allow for nonroot testing too.
# Instruct core.py to use an alternative UNIX domain socket
# and register the dload.py component using an alternative
# property list file.
# Testing as root is possible when/if Neubot is already
# correctly installed.  Note that testing as root is closer
# to actual operating conditions.
#
if [ `id -u` -ne 0 ]; then
    export NEUBOT_UPDATER_SOCKET=__SOCKET.sock
    cp regress/$VERSIONDIR/updater/dload.plist __DLOAD.plist
    ./scripts/sed_inplace "s|@PWD@|`pwd`|g" __DLOAD.plist
    launchctl unload __DLOAD.plist
    launchctl load __DLOAD.plist
else
    export NEUBOT_UPDATER_SOCKET=/var/run/neubot-dload.sock
fi

python $VERSIONDIR/updater/core.py --get-latest
python $VERSIONDIR/updater/core.py --get-sha256sum=0.004002999
python $VERSIONDIR/updater/core.py --check
python $VERSIONDIR/updater/core.py --download=0.004002999
python $VERSIONDIR/updater/core.py --install=0.004002999

if [ `id -u` -ne 0 ]; then
    launchctl unload __DLOAD.plist
    rm -f __SOCKET.sock __DLOAD.plist
fi
