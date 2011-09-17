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

echo 'http://releases.neubot.org/_packages/neubot-0.4.1-setup.exe' \
    | python3 MacOS/basedir-skel/versiondir-skel/updater/dload.py > \
        __dload__.py3.data

echo 'http://releases.neubot.org/_packages/neubot-0.4.1-setup.exe' \
    | python MacOS/basedir-skel/versiondir-skel/updater/dload.py > \
        __dload__.py.data

cmp __dload__.py3.data __dload__.py.data

#
# Download with curl and then compare with the above files, taking
# into account the header line, which must be removed.
#
curl -o __dload__.curl.data \
    http://releases.neubot.org/_packages/neubot-0.4.1-setup.exe

/usr/bin/python << EOF
inputfp = open('__dload__.py.data', 'r')
outputfp = open('__dload__.py.nohdr.data', 'w')
inputfp.readline()
outputfp.write(inputfp.read())
EOF

cmp __dload__.py.nohdr.data __dload__.curl.data
