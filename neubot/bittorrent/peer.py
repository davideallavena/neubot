# neubot/bittorrent/peer.py

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

import random

from neubot.blocks import RandomBody
from neubot.bittorrent.bitfield import make_bitfield
from neubot.bittorrent.sched import sched_req
from neubot.bittorrent.stream import StreamBitTorrent
from neubot.bittorrent.stream import SMALLMESSAGE
from neubot.log import LOG
from neubot.net.stream import StreamHandler

from neubot import utils

NUMPIECES = 1<<20
PIECE_LEN = SMALLMESSAGE
PIPELINE = 1<<20
TARGET_BYTES = 64000

LO_THRESH = 5
MAX_REPEAT = 7
TARGET = 8

def random_bytes(n):
    return "".join([chr(random.randint(32, 126)) for _ in range(n)])

class Peer(StreamHandler):
    def __init__(self, poller):
        StreamHandler.__init__(self, poller)
        self.interested = False
        self.choked = True
        self.saved_bytes = 0
        self.saved_ticks = 0
        self.inflight = 0
        self.dload_speed = 0
        self.repeat = MAX_REPEAT
        self.rtt = 0
        self.setup({})

    def configure(self, conf, measurer=None):
        StreamHandler.configure(self, conf, measurer)
        self.setup(conf)

    def setup(self, conf):
        self.numpieces = int(conf.get("bittorrent.numpieces", NUMPIECES))
        self.bitfield = make_bitfield(self.numpieces)
        self.peer_bitfield = make_bitfield(self.numpieces)
        self.infohash = conf.get("bittorrent.infohash", random_bytes(20))
        self.my_id = conf.get("bittorrent.my_id", random_bytes(20))
        self.target_bytes = int(self.conf.get("bittorrent.target_bytes",
                              TARGET_BYTES))
        self.seeder = conf.get("bittorrent.seeder", False)
        self.make_sched()

    def make_sched(self):
        self.sched_req = sched_req(self.bitfield, self.peer_bitfield,
          self.target_bytes, int(self.conf.get("bittorrent.piece_len",
          PIECE_LEN)), PIPELINE)

    #
    # Once the connection is ready immediately tell the
    # peer we're interested and unchoke it so we can start
    # the test without further delays.
    #
    def connection_ready(self, stream):
        if not self.seeder:
            stream.send_interested()
        stream.send_unchoke()

    #
    # Always handle the BitTorrent connection using a
    # new object, so we can use the same code both for
    # the connector and the listener.
    # Note that we use self.__class__() because the
    # current object might be an instance of a subclass
    # of Peer.
    #
    def connection_made(self, sock, rtt=0):
        if rtt:
            LOG.info("BitTorrent: latency: %s" % utils.time_formatter(rtt))
            self.rtt = rtt
        stream = StreamBitTorrent(self.poller)
        peer = self.__class__(self.poller)
        peer.configure(self.conf, self.measurer)
        stream.attach(peer, sock, peer.conf, peer.measurer)

    def got_bitfield(self, b):
        self.peer_bitfield = b

    # Upload

    #
    # XXX As suggested by BEP0003, we should keep blocks into
    # an application level queue and just pipe a few of them
    # into the socket buffer, so we can abort the upload in a
    # more easy way on NOT_INTERESTED.
    #
    def got_request(self, stream, index, begin, length):
        if not self.interested:
            raise RuntimeError("REQUEST but not interested")
        if length <= SMALLMESSAGE:
            block = chr(random.randint(32, 126)) * length
        else:
            block = RandomBody(length)
        stream.send_piece(index, begin, block)

    def got_interested(self, stream):
        self.interested = True

    def got_not_interested(self, stream):
        self.interested = False
        if self.seeder or self.dload_speed:
            LOG.info("BitTorrent: test complete")
            self.complete(self.dload_speed, self.rtt)

    # Download

    def got_choke(self, stream):
        self.choked = True

    #
    # When we're unchoked immediately pipeline a number
    # of requests and then put another request on the pipe
    # as soon as a piece arrives.  Note that the pipelining
    # is automagically done by the scheduler generator.
    # The idea of pipelining is that of filling with many
    # messages the space between us and the peer to do
    # something that approxymates a continuous download.
    #
    def got_unchoke(self, stream):
        if not self.seeder and self.choked:
            LOG.info("BitTorrent: using %d bytes" % self.target_bytes)
            self.choked = False
            burst = next(self.sched_req)
            for index, begin, length in burst:
                stream.send_request(index, begin, length)
                self.inflight += 1

    def got_have(self, index):
        self.peer_bitfield[index] = 1

    def got_piece(self, stream, index, begin, block):
        self.piece_start(stream, index, begin, "")
        self.piece_part(stream, index, begin, block)
        self.piece_end(stream, index, begin)

    def piece_start(self, stream, index, begin, block):
        if self.seeder:
            raise RuntimeError("Got unexpected piece")

    def piece_part(self, stream, index, begin, block):
        """Invoked when you receive a portion of a piece."""

    #
    # Time to put another piece on the wire, assuming
    # that we can do that.  Note that we start measuring
    # after the first PIECE message: at that point we
    # can assume the pipeline to be full (note that this
    # holds iff bdp < PIPELINE).
    #
    def piece_end(self, stream, index, begin):
        if not self.saved_ticks:
            self.saved_bytes = stream.bytes_recv_tot
            self.saved_ticks = utils.ticks()

        try:
            vector = next(self.sched_req)
        except StopIteration:
            vector = None

        if vector:
            index, begin, length = vector[0]
            stream.send_request(index, begin, length)

        else:
            self.inflight -= 1
            if self.inflight == 0:
                xfered = stream.bytes_recv_tot - self.saved_bytes
                elapsed = utils.ticks() - self.saved_ticks
                speed = xfered/elapsed

                LOG.info("BitTorrent: download speed: %s" %
                  utils.speed_formatter(speed))
                LOG.info("BitTorrent: measurement time: %s" %
                  utils.time_formatter(elapsed))

                #
                # Make sure that next test would take about
                # TARGET secs, under current conditions.
                # But, multiply by two below a given threshold
                # because we don't want to overestimate the
                # achievable bandwidth.
                # TODO If we're the connector, store somewhere
                # the target_bytes so we can reuse it later.
                #
                if elapsed > LO_THRESH/3:
                    self.target_bytes *= TARGET/elapsed
                else:
                    self.target_bytes *= 2

                #
                # The stopping rule is when the test has run
                # for more than LO_THRESH seconds or after some
                # number of runs (just to be sure that we can
                # not run forever due to unexpected network
                # conditions).
                #
                self.repeat -= 1
                if elapsed > LO_THRESH or self.repeat <= 0:
                    self.dload_speed = speed
                    LOG.info("BitTorrent: my side complete")
                    stream.send_not_interested()
                    if not self.interested:
                        LOG.info("BitTorrent: test complete")
                        self.complete(self.dload_speed, self.rtt)
                else:
                    self.saved_ticks = 0
                    self.make_sched()
                    self.choked = True          #XXX
                    self.got_unchoke(stream)

            elif self.inflight < 0:
                raise RuntimeError("Inflight became negative")

    def complete(self, speed, rtt):
        pass
