# neubot/http/stream.py

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

import collections

from neubot.net.stream import MAXBUF
from neubot.net.stream import Stream
from neubot.log import LOG

# Accepted HTTP protocols
PROTOCOLS = [ "HTTP/1.0", "HTTP/1.1" ]

# Maximum allowed line length
MAXLINE = 1<<15

# Possible states of the receiver
(IDLE, BOUNDED, UNBOUNDED, CHUNK, CHUNK_END, FIRSTLINE,
 HEADER, CHUNK_LENGTH, TRAILER, ERROR) = range(0,10)

# receiver state names
STATES = ["IDLE", "BOUNDED", "UNBOUNDED", "CHUNK", "CHUNK_END", "FIRSTLINE",
          "HEADER", "CHUNK_LENGTH", "TRAILER", "ERROR"]

#
# When messages are not bigger than SMALLMESSAGE we join headers
# and body in a single buffer and we send that buffer.  If the buffer
# happens to be very small, it might fit a single L2 packet.
#
SMALLMESSAGE = 8000

#
# Specializes stream in order to handle the Hyper-Text Transfer
# Protocol (HTTP).  See also the finite state machine documented
# at `doc/protocol.png`.
#
class StreamHTTP(Stream):
    def __init__(self, poller):
        Stream.__init__(self, poller)
        self.incoming = []
        self.state = FIRSTLINE
        self.left = 0

    def connection_made(self):
        self.start_recv()

    # Close

    def connection_lost(self, exception):
        # it's possible for body to be `up to end of file`
        if self.eof and self.state == UNBOUNDED:
            self.got_end_of_body()
        self.incoming = None

    # Send

    def send_message(self, m, smallmessage=SMALLMESSAGE):
        if m.length >= 0 and m.length <= smallmessage:
            vector = []
            vector.append(m.serialize_headers().read())
            body = m.serialize_body()
            if not isinstance(body, basestring):
                vector.append(body.read())
            else:
                vector.append(body)
            data = "".join(vector)
            self.start_send(data)
        else:
            self.start_send(m.serialize_headers())
            self.start_send(m.serialize_body())

    # Recv

    def recv_complete(self, data):
        if self.close_complete or self.close_pending:
            return

        #This one should be debug2 as well
        #LOG.debug("HTTP receiver: got %d bytes" % len(data))

        # merge with previous fragments (if any)
        if self.incoming:
            self.incoming.append(data)
            data = "".join(self.incoming)
            del self.incoming[:]

        # consume the current fragment
        offset = 0
        length = len(data)
        while length > 0:
            #ostate = self.state        # needed by commented-out code below

            # when we know the length we're looking for a piece
            if self.left > 0:
                count = min(self.left, length)
                piece = buffer(data, offset, count)
                self.left -= count
                offset += count
                length -= count
                self._got_piece(piece)

            # otherwise we're looking for the next line
            elif self.left == 0:
                index = data.find("\n", offset)
                if index == -1:
                    if length > MAXLINE:
                        raise RuntimeError("Line too long")
                    break
                index = index + 1
                line = data[offset:index]
                length -= (index - offset)
                offset = index
                self._got_line(line)

            # robustness
            else:
                raise RuntimeError("Left become negative")

            # robustness
            if self.close_complete or self.close_pending:
                return

#           Should be debug2() not debug()
#           LOG.debug("HTTP receiver: %s -> %s" %
#             (STATES[ostate], STATES[self.state]))

        # keep the eventual remainder for later
        if length > 0:
            remainder = data[offset:]
            self.incoming.append(remainder)
            LOG.debug("HTTP receiver: remainder %d" % len(remainder))

        # get the next fragment
        self.start_recv()

    def _got_line(self, line):
        if self.state == FIRSTLINE:
            line = line.strip()
            LOG.debug("< %s" % line)
            vector = line.split(None, 2)
            if len(vector) == 3:
                if line.startswith("HTTP"):
                    protocol, code, reason = vector
                    if protocol in PROTOCOLS:
                        self.got_response_line(protocol, code, reason)
                else:
                    method, uri, protocol = vector
                    if protocol in PROTOCOLS:
                        self.got_request_line(method, uri, protocol)
                if protocol not in PROTOCOLS:
                    raise RuntimeError("Invalid protocol")
                else:
                    self.state = HEADER
            else:
                raise RuntimeError("Invalid first line")
        elif self.state == HEADER:
            if line.strip():
                LOG.debug("< %s" % line)
                # not handling mime folding
                index = line.find(":")
                if index >= 0:
                    key, value = line.split(":", 1)
                    self.got_header(key.strip(), value.strip())
                else:
                    raise RuntimeError("Invalid header line")
            else:
                LOG.debug("<")
                self.state, self.left = self.got_end_of_headers()
                if self.state == ERROR:
                    # allow upstream to filter out unwanted requests
                    self.close()
                elif self.state == FIRSTLINE:
                    # this is the case of an empty body
                    self.got_end_of_body()
        elif self.state == CHUNK_LENGTH:
            vector = line.split()
            if vector:
                length = int(vector[0], 16)
                if length < 0:
                    raise RuntimeError("Negative chunk-length")
                elif length == 0:
                    self.state = TRAILER
                else:
                    self.left = length
                    self.state = CHUNK
            else:
                raise RuntimeError("Invalid chunk-length line")
        elif self.state == CHUNK_END:
            if line.strip():
                raise RuntimeError("Invalid chunk-end line")
            else:
                self.state = CHUNK_LENGTH
        elif self.state == TRAILER:
            if not line.strip():
                self.state = FIRSTLINE
                self.got_end_of_body()
            else:
                # Ignoring trailers
                pass
        else:
            raise RuntimeError("Not expecting a line")

    def _got_piece(self, piece):
        if self.state == BOUNDED:
            self.got_piece(piece)
            if self.left == 0:
                self.state = FIRSTLINE
                self.got_end_of_body()
        elif self.state == UNBOUNDED:
            self.got_piece(piece)
            self.left = MAXBUF
        elif self.state == CHUNK:
            self.got_piece(piece)
            if self.left == 0:
                self.state = CHUNK_END
        else:
            raise RuntimeError("Not expecting a piece")

    # Events for upstream

    def got_request_line(self, method, uri, protocol):
        raise RuntimeError("Not expecting a request-line")

    def got_response_line(self, protocol, code, reason):
        raise RuntimeError("Not expecting a reponse-line")

    def got_header(self, key, value):
        pass

    def got_end_of_headers(self):
        pass

    def got_piece(self, piece):
        pass

    def got_end_of_body(self):
        pass

    def message_sent(self):
        pass
