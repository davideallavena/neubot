# neubot/async/__init__.py

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

'''
 Asynchronous network
'''

import asyncore
import sched
import time
import logging
import os

#
# XXX The problem with time.time() is that if the user
# changes radically the current time we cannot detect
# that and repair.  I am not sure whether such problem
# exists under Windows too, but I suspect it doesn't.
#
if os.name == 'nt':
    _timefunc = time.clock
else:
    _timefunc = time.time

class Poller(sched.scheduler):

    ''' I/O events dispatcher  '''

    #
    # The _check_timeout method is always scheduler and
    # that keeps the scheduler alive.  Between each iteration
    # the scheduler invokes self._poll with the number of
    # seconds to use as timeout in select as the first
    # argument.
    # 

    def __init__(self):
        ''' Initializer '''
        self._again = True
        sched.scheduler.__init__(self, _timefunc, self._poll)
        self._check_timeout()

    def sched(self, delay, action, argument=None):
        ''' Schedule a new event '''
        return self.enter(delay, 0, action, argument)

    def break_loop(self):
        ''' Break out of the event loop '''
        self._again = False

    def loop(self):
        ''' Event loop '''
        while self._again:
            try:
                self.run()
            except (KeyboardInterrupt, SystemExit):
                raise
            except Exception:
                logging.warning(aynscore.compact_traceback())

    def _check_timeout(self, *argument):
        ''' Periodic check for timedout streams '''
        self.sched(10, self._check_timeout, argument)
        timenow = _timefunc()
        for stream in list(asyncore.socket_map.values()):
            if stream.istimedout(timenow):
                logging.warning('%s: timeout' % repr(stream))
                stream.close()

    def _poll(self, timeo):
        ''' Poll registered sockets for I/O events '''
        if asyncore.socket_map:
            asyncore.poll(timeo, asyncore.socket_map)
        else:
            time.sleep(timeo)

POLLER = Poller()

sched = POLLER.sched
loop = POLLER.loop
break_loop = POLLER.break_loop
