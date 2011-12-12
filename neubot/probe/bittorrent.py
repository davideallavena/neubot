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
import random
import sys

if __name__ == '__main__':
    sys.path.insert(0, '.')

from neubot.bittorrent.bitfield import Bitfield
from neubot.bittorrent.bitfield import make_bitfield
from neubot.bittorrent.config import NUMPIECES
from neubot.bittorrent.config import PIECE_LEN
from neubot.bittorrent.stream import StreamBitTorrent
from neubot.net.poller import POLLER
from neubot.net.stream import StreamHandler
from neubot.utils.blocks import BTPIECES

from neubot.log import LOG

from neubot import utils

BURST = 4
MINRTT = 100

class ProbeBitTorrentCommon(StreamHandler):

    ''' Common code for BitTorrent probe '''

    def __init__(self, poller):
        ''' Initialize common BitTorrent code '''
        StreamHandler.__init__(self, poller)
        self.saved_ticks = collections.deque()
        self.unchoked = False
        self.interested = False
        self.exp_duration = 0
        self.begin_download = 0
        self.begin_upload = 0

        # BitTorrent stream assumes they exist
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
        # Just to make sure the bitfield is valid
        Bitfield(NUMPIECES, bitfield)
        self.start_test(stream)

    def start_test(self, stream):
        ''' Invoked when we can start the test '''

    #
    # To initiate the download, the downloader sends INTERESTED and
    # waits for UNCHOKE.  Then, it sends BURST requests in a row
    # and waits for PIECEs to come back.  For each incoming PIECE,
    # the downloader injects one or two new REQUESTS, depending
    # on the request-response time.
    # The download terminates when (1) the unchoked variable becomes
    # False and (2) there are no pending REQUESTs in flight.  When
    # this happens the downloader sends a NOT_INTERESTED message
    # to notify the uploader.
    # If the downloader is the client, it knows the maximum time the
    # test must take.  In this case the unchoked variable is set to
    # False when a given timeout expires.  OTOH, if the downloader is
    # the server, the client will send an UNCHOKE message when the
    # upload has run for enough seconds.
    #

    @staticmethod
    def start_download(stream):
        ''' Initiates the download test '''
        stream.send_interested()

    def got_unchoke(self, stream):
        ''' We received the UNCHOKE message '''
        assert(self.unchoked == False)
        self.unchoked = True
        self.begin_download = utils.ticks()
        for _ in range(BURST):
            self._send_next_request(stream)

    def got_piece(self, stream, index, begin, block):
        ''' We received the PIECE message '''
        ticks = self.saved_ticks.popleft()
        #print len(self.saved_ticks), self.unchoked
        if self.unchoked:
            self._send_next_request(stream)
            now = utils.ticks()
            if now - self.begin_download > self.exp_duration:
                self.unchoked = False
            if now - ticks < 1:
                self._send_next_request(stream)
        elif not self.saved_ticks:
            stream.send_not_interested()
            self.download_complete(stream)

    def _send_next_request(self, stream):
        ''' Convenience function to send next request '''
        self.saved_ticks.append(utils.ticks())
        stream.send_request(random.random() % NUMPIECES, 0, PIECE_LEN)

    def got_choke(self, stream):
        ''' We have received the CHOKE message '''
        self.unchoked = False

    def download_complete(self, stream):
        ''' Invoked when the download test is complete '''

    #
    # The uploader is passive and the upload starts when it
    # receives an INTERESTED message.  When this happens the
    # uploader responds with an UNCHOKE message.  From then
    # on, it responds to each REQUEST with a PIECE, until it
    # receives the NOT_INTERESTED message.
    # If the maximum duration is known, i.e. we are the
    # client, we stop the upload when it has run for too
    # much time.  Otherwise, we rely on the other peer
    # to do so.
    #

    def got_interested(self, stream):
        ''' We received the INTERESTED message '''
        self.interested = True
        stream.send_unchoke()

    def got_request(self, stream, index, begin, length):
        ''' We received the REQUEST message '''
        if not self.interested:
            raise RuntimeError('Peer not interested')
        elif length != PIECE_LEN:
            raise RuntimeError('Invalid request length')
        else:
            if self.exp_duration:
                now = utils.ticks()
                if not self.begin_upload:
                    self.begin_upload = now
                if now - self.begin_upload > self.exp_duration:
                    stream.send_choke()
            stream.send_piece(index, begin,
              BTPIECES.get_block())

    def got_not_interested(self, stream):
        ''' We received the NOT_INTERESTED message '''
        self.interested = False
        self.upload_complete(stream)

    def upload_complete(self, stream):
        ''' Invoked when the upload is complete '''

    #
    # The HAVE message is not used by Neubot and we
    # just ignore it.
    #

    def got_have(self, stream):
        ''' We have received the HAVE message '''

class ProbeBitTorrentClient(ProbeBitTorrentCommon):

    ''' Client-side code for BitTorrent probe '''

    def connection_made(self, sock, rtt=0):
        self.exp_duration = rtt * MINRTT
        stream = StreamBitTorrent(self.poller)
        stream.attach(self, sock, self.conf)

    def start_test(self, stream):
        ''' Invoked when we can start the test '''
        LOG.info('BitTorrent: start download')
        self.start_download(stream)

    def upload_complete(self, stream):
        ''' Invoked when the upload is complete '''
        LOG.info('BitTorrent: test complete')
        stream.close()

class ProbeBitTorrentServer(ProbeBitTorrentCommon):

    ''' Server-side code for BitTorrent probe '''

    def connection_made(self, sock, rtt=0):
        stream = StreamBitTorrent(self.poller)
        server = self.__class__(self.poller)
        server.configure(self.conf)
        stream.attach(server, sock, server.conf)

    def upload_complete(self, stream):
        ''' Invoked when the upload is complete '''
        LOG.info('BitTorrent: upload complete')
        self.start_download(stream)

    def download_complete(self, stream):
        ''' Invoked when the download test is complete '''
        LOG.info('BitTorrent: download complete')
        stream.close()

def main():
    ''' main function '''
    if sys.argv[1] == '--client':
        client = ProbeBitTorrentClient(POLLER)
        client.connect(('127.0.0.1', 6882))
    else:
        server = ProbeBitTorrentServer(POLLER)
        server.listen(('127.0.0.1', 6882))
    #LOG.verbose()
    POLLER.loop()

if __name__ == '__main__':
    main()
