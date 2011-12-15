# neubot/probe/bittorrent.py

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

''' Probe the network using the BitTorrent protocol '''

import collections
import os
import random
import sys

if __name__ == '__main__':
    sys.path.insert(0, '.')

from neubot.bittorrent.bitfield import Bitfield
from neubot.bittorrent.bitfield import make_bitfield
from neubot.bittorrent.config import NUMPIECES
from neubot.bittorrent.stream import StreamBitTorrent
from neubot.net.poller import POLLER
from neubot.net.stream import StreamHandler
from neubot.utils.blocks import RandomBlocks

from neubot.log import LOG

from neubot import utils

#
# Length of the pieces we send on the
# wire.
#
PIECE_LEN = int(os.environ.get('PIECE_LEN', 1 << 17))
BTPIECES = RandomBlocks(PIECE_LEN)

#
# The number of requests sent at the beginning of
# the download phase of the test.
#
BURST = int(os.environ.get('BURST', 4))

#
# The minimum duration of the download phase,
# expressed in RTTs.
#
MINRTT = int(os.environ.get('MINRTT', 100))

#
# Maximum delay in the algorithm to control
# the delay.
#
MAXDELAY = int(os.environ.get('MAXDELAY', 1))

sys.stdout.write('PIECE_LEN %d BURST %d MINRTT %d MAXDELAY %d\n' % (
                  PIECE_LEN, BURST, MINRTT, MAXDELAY))

#
# Remarks on the test implementation:
#
# 1. The download starts with the following handshake: the downloader
#    sends INTERESTED and the uploader responds with UNCHOKE;
#
# 2. to keep the pipeline full, the downloader sends BURST initial
#    REQUESTs and injects K new REQUEST messages per incoming PIECE,
#    where K = 2 when the REQUEST-PIECE latency is less than one
#    second and K = 1 otherwise;
#
# 3. the downloader stops sending new REQUESTs when (a) either it
#    does not know the expected test duration and the peer has sent
#    a CHOKE message or (b) it knows the duration and the test has
#    run for more than that;
#
# 4. the download ends when there are no pending REQUESTs.
#
# Note that the connector knows the expected duration, while the
# listener does not.
#

class ProbeBitTorrentCommon(StreamHandler):

    ''' Common code for BitTorrent probe '''

    def __init__(self, poller):
        ''' Initialize common BitTorrent code '''
        StreamHandler.__init__(self, poller)
        self.saved_ticks = collections.deque()
        self.bitfield = None
        self.unchoked = False
        self.interested = False
        self.duration = 0
        self.begin = 0

        # XXX BitTorrent stream assumes they exist
        # TODO Here we should use the proper infohash and my_id
        self.infohash = ''.join([chr(0) for _ in range(20)])
        self.my_id = ''.join([chr(0) for _ in range(20)])
        self.numpieces = NUMPIECES

    @staticmethod
    def connection_ready(stream):
        ''' When the connection is ready, send BITFIELD '''
        stream.send_bitfield(str(make_bitfield(NUMPIECES)))
        LOG.info('BitTorrent: start receiving bitfield')

    def got_bitfield(self, stream, bitfield):
        ''' When we got BITFIELD, we can start the test '''
        LOG.info('BitTorrent: receiving bitfield complete')
        self.bitfield = Bitfield(NUMPIECES, bitfield)

    @staticmethod
    def start_download(stream):
        ''' Initiates the download test '''
        stream.send_interested()

    def got_unchoke(self, stream):
        ''' We received the UNCHOKE message '''
        self.unchoked = True
        LOG.info('BitTorrent: start download')
        for _ in range(BURST):
            self._send_next_request(stream)

    def got_piece(self, stream, index, begin, block):
        ''' We received the PIECE message '''
        ticks = self.saved_ticks.popleft()
        now = utils.ticks()
        LOG.info('delay: %f' % (now - ticks))
        if not self.begin:
            stream.bytes_recv = 0
            self.begin = utils.ticks()
        if (not self.duration and not self.unchoked) or (self.duration and
                                       now - self.begin > self.duration):
            if not self.saved_ticks:
                LOG.info('  BitTorrent: elapsed %f' % (now - self.begin))
                LOG.info('  BitTorrent: bytes %d' % stream.bytes_recv)
                LOG.info('  BitTorrent: speed %s' % (
                  stream.bytes_recv/(now - self.begin)))
                LOG.info('BitTorrent: download complete')
                stream.send_not_interested()
                self.download_complete(stream)
            return
        self._send_next_request(stream)
        elapsed = now - ticks
        if elapsed < 1:
            self._send_next_request(stream)

    def _send_next_request(self, stream):
        ''' Convenience function to send next request '''
        self.saved_ticks.append(utils.ticks())
        stream.send_request(int(random.random() % NUMPIECES), 0, PIECE_LEN)

    def got_choke(self, stream):
        ''' We have received the CHOKE message '''
        self.unchoked = False

    def download_complete(self, stream):
        ''' Invoked when the download test is complete '''

    def got_interested(self, stream):
        ''' We received the INTERESTED message '''
        self.interested = True
        LOG.info('BitTorrent: start upload')
        self.begin = 0                          # reset
        stream.send_unchoke()

    def got_request(self, stream, index, begin, length):
        ''' We received the REQUEST message '''
        assert(length == PIECE_LEN and begin == 0)
        if self.duration:
            now = utils.ticks()
            if not self.begin:
                self.begin = now
            if utils.ticks() - self.begin > self.duration:
                stream.send_choke()
        stream.send_piece(index, begin,
          BTPIECES.get_block())

    def got_not_interested(self, stream):
        ''' We received the NOT_INTERESTED message '''
        self.interested = False
        LOG.info('BitTorrent: upload complete')
        self.upload_complete(stream)

    def upload_complete(self, stream):
        ''' Invoked when the upload is complete '''

    def got_have(self, stream):
        ''' We have received the HAVE message '''

class ProbeBitTorrentConnector(ProbeBitTorrentCommon):

    ''' Client-side code for BitTorrent probe '''

    def connection_made(self, sock, rtt=0):
        ''' Invoked when the new connection is made '''
        LOG.info('BitTorrent: start test')
        self.duration = rtt * MINRTT
        LOG.info('  BitTorrent: rtt %f' % rtt)
        LOG.info('  BitTorrent: exp duration %f' % self.duration)
        stream = StreamBitTorrent(self.poller)
        stream.attach(self, sock, self.conf)

    def got_bitfield(self, stream, bitfield):
        ''' Invoked when we can start the test '''
        ProbeBitTorrentCommon.got_bitfield(self, stream, bitfield)
        self.start_download(stream)

    def upload_complete(self, stream):
        ''' Invoked when the upload is complete '''
        LOG.info('BitTorrent: test complete')
        stream.close()

class ProbeBitTorrentListener(ProbeBitTorrentCommon):

    ''' Server-side code for BitTorrent probe '''

    def connection_made(self, sock, rtt=0):
        ''' Invoked when the new connection is made '''
        LOG.info('BitTorrent: start test')
        stream = StreamBitTorrent(self.poller)
        # Because ``self`` may be a subclass of ProbeBitTorrentListener
        server = self.__class__(self.poller)
        server.configure(self.conf)
        stream.attach(server, sock, server.conf)

    def upload_complete(self, stream):
        ''' Invoked when the upload is complete '''
        self.start_download(stream)

    def download_complete(self, stream):
        ''' Invoked when the download test is complete '''
        LOG.info('BitTorrent: test complete')
        stream.close()

def main(args):
    ''' main function '''
    if len(args) == 2 and args[1] == '--client':
        client = ProbeBitTorrentConnector(POLLER)
        client.connect(('127.0.0.1', 6882))
    elif len(args) == 2 and args[1] == '--server':
        server = ProbeBitTorrentListener(POLLER)
        server.listen(('0.0.0.0', 6882))
    else:
        sys.exit('Usage: probe/bittorrent.py [--client|--server]')
    POLLER.loop()

if __name__ == '__main__':
    main()
