# neubot/net/streams.py
# Copyright (c) 2010 NEXA Center for Internet & Society

# This file is part of Neubot.
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
# Asynchronous I/O for non-blocking sockets (and SSL)
#

from neubot.net.pollers import Pollable
from types import UnicodeType
from neubot import log

SUCCESS, ERROR, WANT_READ, WANT_WRITE = range(0,4)
TIMEOUT = 300

ISCLOSED = 1<<0
SEND_PENDING = 1<<1
SENDBLOCKED = 1<<2
RECV_PENDING = 1<<3
RECVBLOCKED = 1<<4
ISSENDING = 1<<5
ISRECEIVING = 1<<6
EOF = 1<<7

class Stream(Pollable):
    def __init__(self, poller, fileno, myname, peername, logname):
        self.poller = poller
        self._fileno = fileno
        self.myname = myname
        self.peername = peername
        self.logname = logname
        self.handleReadable = None
        self.handleWritable = None
        self.send_octets = None
        self.send_success = None
        self.send_ticks = 0
        self.send_pos = 0
        self.send_error = None
        self.recv_maxlen = 0
        self.recv_success = None
        self.recv_ticks = 0
        self.recv_error = None
        self.eof = False
        self.timeout = TIMEOUT
        self.notify_closing = None
        self.context = None
        self.stats = []
        self.stats.append(self.poller.stats)
        self.flags = 0

    def __del__(self):
        pass

    def fileno(self):
        return self._fileno

    #
    # When you keep a reference to the stream in your class,
    # remember to point stream.notify_closing to a function
    # that removes such reference.
    #

    def closing(self):
        self._do_close()

    def close(self):
        self._do_close()

    def _do_close(self):
        if not (self.flags & ISCLOSED):
            log.debug("* Closing connection %s" % self.logname)
            self.flags |= ISCLOSED
            if self.recv_error:
                self.recv_error(self)
                self.recv_error = None
            if self.send_error:
                self.send_error(self)
                self.send_error = None
            if self.notify_closing:
                self.notify_closing()
                self.notify_closing = None
            self.send_octets = None
            self.send_success = None
            self.send_ticks = 0
            self.send_pos = 0
            self.recv_maxlen = 0
            self.recv_success = None
            self.recv_ticks = 0
            self.handleReadable = None
            self.handleWritable = None
            self.soclose()
            self.poller.close(self)

    def readtimeout(self, now):
        return (self.flags & RECV_PENDING and
         (now - self.recv_ticks) > self.timeout)

    def writetimeout(self, now):
        return (self.flags & SEND_PENDING and
         (now - self.send_ticks) > self.timeout)

    #
    # Make sure that we set/unset readable/writable only if
    # needed, because the operation is a bit expensive (you
    # add/remove entries to/from an hash table).
    #

    def readable(self):
        self.handleReadable()

    def writable(self):
        self.handleWritable()

    def set_readable(self, func):
        if not self.handleReadable:
            self.poller.set_readable(self)
        if self.handleReadable != func:
            self.handleReadable = func

    def set_writable(self, func):
        if not self.handleWritable:
            self.poller.set_writable(self)
        if self.handleWritable != func:
            self.handleWritable = func

    def unset_readable(self):
        if self.handleReadable:
            self.poller.unset_readable(self)
            self.handleReadable = None

    def unset_writable(self):
        if self.handleWritable:
            self.poller.unset_writable(self)
            self.handleWritable = None

    def recv(self, maxlen, recv_success, recv_error=None):
        if not (self.flags & ISCLOSED):
            self.recv_maxlen = maxlen
            self.recv_success = recv_success
            self.recv_ticks = self.poller.get_ticks()
            self.flags |= RECV_PENDING
            self.recv_error = recv_error
            #
            # ISRECEIVING means we're already inside _do_recv().
            # We don't want to invoke _do_recv() again, in this
            # case, because there' the risk of infinite recursion.
            #
            if not (self.flags & ISRECEIVING):
                self._do_recv()

    def _do_recv(self):
        #
        # RECVBLOCKED means that the underlying socket is SSL,
        # _and_ that SSL_write() returned WANT_READ, so we need
        # to wait for the underlying socket to become readable
        # to invoke SSL_write() again--and of course we can't
        # recv() until this happens.
        #
        if not (self.flags & RECVBLOCKED):
            self.flags |= ISRECEIVING
            panic = ""
            if self.flags & SENDBLOCKED:
                #
                # SENDBLOCKED is the symmetrical of RECVBLOCKED.
                # If we're here it means that SSL_read() returned
                # WANT_WRITE and we temporarily needed to block
                # send().
                #
                if self.flags & SEND_PENDING:
                    self.set_writable(self._do_send)
                else:
                    self.unset_writable()
                self.flags &= ~SENDBLOCKED
            status, octets = self.sorecv(self.recv_maxlen)
            if status == SUCCESS:
                if octets:
                    for stats in self.stats:
                        stats.recv.account(len(octets))
                    notify = self.recv_success
                    self.recv_maxlen = 0
                    self.recv_success = None
                    self.recv_ticks = 0
                    #
                    # Unset RECV_PENDING but wait before unsetting
                    # readable because notify() might invoke recv()
                    # again--and so we check RECV_PENDING again
                    # after notify().
                    #
                    self.flags &= ~RECV_PENDING
                    self.recv_error = None
                    if notify:
                        notify(self, octets)
                    #
                    # Be careful because notify() is an user-defined
                    # callback that might invoke send()--which might
                    # need to block recv()--or close().
                    #
                    if not (self.flags & (RECVBLOCKED|ISCLOSED)):
                        if self.flags & RECV_PENDING:
                            self.set_readable(self._do_recv)
                        else:
                            self.unset_readable()
                else:
                    log.debug("* Connection %s: EOF" % self.logname)
                    self.flags |= EOF
                    self.eof = True
                    self._do_close()
            elif status == WANT_READ:
                self.set_readable(self._do_recv)
            elif status == WANT_WRITE:
                self.set_writable(self._do_recv)
                self.flags |= SENDBLOCKED
            elif status == ERROR:
                log.error("* Connection %s: recv error" % self.logname)
                log.exception()
                self._do_close()
            else:
                panic = "Unexpected status value"
            self.flags &= ~ISRECEIVING
            if panic:
                raise Exception(panic)

    #
    # send() is symmetrical to recv() and so to the comments
    # to recv()'s implementation are also applicable here.
    #

    def send(self, octets, send_success, send_error=None):
        if not (self.flags & ISCLOSED):
            #
            # Make sure we don't start sending an Unicode string
            # because _do_send() assumes 8 bits encoding and would
            # go very likely to 'Internal error' state if passed
            # an unicode encoding.
            #
            if type(octets) == UnicodeType:
                log.warning("* send: Working-around Unicode input")
                octets = octets.encode("utf-8")
            self.send_octets = octets
            self.send_pos = 0
            self.send_success = send_success
            self.send_ticks = self.poller.get_ticks()
            self.flags |= SEND_PENDING
            self.send_error = send_error
            if not (self.flags & ISSENDING):
                self._do_send()

    def _do_send(self):
        if not (self.flags & SENDBLOCKED):
            self.flags |= ISSENDING
            panic = ""
            if self.flags & RECVBLOCKED:
                if self.flags & RECV_PENDING:
                    self.set_readable(self._do_recv)
                else:
                    self.unset_readable()
                self.flags &= ~RECVBLOCKED
            subset = buffer(self.send_octets, self.send_pos)
            status, count = self.sosend(subset)
            if status == SUCCESS:
                if count > 0:
                    for stats in self.stats:
                        stats.send.account(count)
                    self.send_pos += count
                    if self.send_pos < len(self.send_octets):
                        self.send_ticks = self.poller.get_ticks()
                        self.set_writable(self._do_send)
                    elif self.send_pos == len(self.send_octets):
                        notify = self.send_success
                        octets = self.send_octets
                        self.send_octets = None
                        self.send_pos = 0
                        self.send_success = None
                        self.send_ticks = 0
                        self.flags &= ~SEND_PENDING
                        self.send_error = None
                        if notify:
                            notify(self, octets)
                        if not (self.flags & (SENDBLOCKED|ISCLOSED)):
                            if self.flags & SEND_PENDING:
                                self.set_writable(self._do_send)
                            else:
                                self.unset_writable()
                    else:
                        panic = "Internal error"
                else:
                    panic = "Unexpected count value"
            elif status == WANT_WRITE:
                self.set_writable(self._do_send)
            elif status == WANT_READ:
                self.set_readable(self._do_send)
                self.flags |= RECVBLOCKED
            elif status == ERROR:
                log.error("* Connection %s: send error" % self.logname)
                log.exception()
                self._do_close()
            else:
                panic = "Unexpected status value"
            self.flags &= ~ISSENDING
            if panic:
                raise Exception(panic)

    #
    # These are the methods that an "underlying socket"
    # implementation should override.
    #

    def soclose(self):
        raise NotImplementedError

    def sorecv(self, maxlen):
        raise NotImplementedError

    def sosend(self, octets):
        raise NotImplementedError

HAVE_SSL = True
try:
    from ssl import SSLError
    from ssl import SSL_ERROR_WANT_READ
    from ssl import SSL_ERROR_WANT_WRITE
except ImportError:
    HAVE_SSL = False

if HAVE_SSL:
    class StreamSSL(Stream):
        def __init__(self, ssl_sock, poller, fileno, myname, peername, logname):
            self.ssl_sock = ssl_sock
            Stream.__init__(self, poller, fileno, myname, peername, logname)
            self.need_handshake = True

        def __del__(self):
            Stream.__del__(self)

        def soclose(self):
            self.ssl_sock.close()

        def sorecv(self, maxlen):
            try:
                if self.need_handshake:
                    self.ssl_sock.do_handshake()
                    self.need_handshake = False
                octets = self.ssl_sock.read(maxlen)
                return SUCCESS, octets
            except SSLError, (code, reason):
                if code == SSL_ERROR_WANT_READ:
                    return WANT_READ, ""
                elif code == SSL_ERROR_WANT_WRITE:
                    return WANT_WRITE, ""
                else:
                    return ERROR, ""

        def sosend(self, octets):
            try:
                if self.need_handshake:
                    self.ssl_sock.do_handshake()
                    self.need_handshake = False
                count = self.ssl_sock.write(octets)
                return SUCCESS, count
            except SSLError, (code, reason):
                if code == SSL_ERROR_WANT_READ:
                    return WANT_READ, 0
                elif code == SSL_ERROR_WANT_WRITE:
                    return WANT_WRITE, 0
                else:
                    return ERROR, 0

from socket import error as SocketError
from errno import EAGAIN, EWOULDBLOCK

class StreamSocket(Stream):
    def __init__(self, sock, poller, fileno, myname, peername, logname):
        self.sock = sock
        Stream.__init__(self, poller, fileno, myname, peername, logname)

    def __del__(self):
        Stream.__del__(self)

    def soclose(self):
        self.sock.close()

    def sorecv(self, maxlen):
        try:
            octets = self.sock.recv(maxlen)
            return SUCCESS, octets
        except SocketError, (code, reason):
            if code in [EAGAIN, EWOULDBLOCK]:
                return WANT_READ, ""
            else:
                return ERROR, ""

    def sosend(self, octets):
        try:
            count = self.sock.send(octets)
            return SUCCESS, count
        except SocketError, (code, reason):
            if code in [EAGAIN, EWOULDBLOCK]:
                return WANT_WRITE, 0
            else:
                return ERROR, 0

if HAVE_SSL:
    from ssl import SSLSocket
from socket import SocketType

def create_stream(sock, poller, fileno, myname, peername, logname):
    if HAVE_SSL:
        if type(sock) == SSLSocket:
            stream = StreamSSL(sock, poller, fileno, myname, peername, logname)
            return stream
    if type(sock) == SocketType:
        stream = StreamSocket(sock, poller, fileno, myname, peername, logname)
    else:
        raise ValueError("Unknown socket type")
    return stream
