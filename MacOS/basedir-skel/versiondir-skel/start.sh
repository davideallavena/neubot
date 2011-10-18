#!/bin/sh

#
# Copyright (c) 2011 Alessio Palmero Aprosio <alessio@apnetwork.it>
#  Universita` degli Studi di Milano
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

#
# start.sh -- Really start this version of neubot under MacOSX
#

set -e

#
# The caller will use an absolute PATH so we can easily get
# the place where Neubot is installed using dirname.
#
VERSIONDIR=$(dirname $0)

logger -p daemon.info -t $0 "Neubot versiondir: $VERSIONDIR"

#
# Invoke the prerun.sh script which will make sure that Neubot
# will run (for example it will check that the required users and
# groups exist and so on and so forth).
# We invoke it unconditionally and it's up to the script to see
# whether it needs to do something or not.
#
$VERSIONDIR/prerun.sh

#
# Start the current version of Neubot, indirectly via the
# launchctl(1) command.  This is needed because the job
# must run in the context of the ``_neubot`` user, while
# this script is running as root.
# We also load the PLIST for the two components of the
# updater process.  They will not start immediately: the
# core component will run every 30 minutes while the
# dload one is started when someone connects to the well-
# know socket ``/var/run/neubot-dload.sock``.
#
/bin/launchctl load $VERSIONDIR/org.neubot.agent.plist
/bin/launchctl load $VERSIONDIR/updater/org.neubot.updater.dload.plist
/bin/launchctl load $VERSIONDIR/updater/org.neubot.updater.core.plist
