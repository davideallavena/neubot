# neubot/bittorrent/client.py

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
# This file contains the negotiator client of the
# BitTorrent test, i.e. the code that negotiates with
# the test server and collects the results.
#

import StringIO
import hashlib
import sys

from neubot.bittorrent.peer import PeerNeubot
from neubot.http.client import ClientHTTP
from neubot.http.message import Message

from neubot.bittorrent import estimate
from neubot.compat import json
from neubot.database import DATABASE
from neubot.database import table_bittorrent
from neubot.utils.version import LibVersion
from neubot.log import LOG
from neubot.notify import NOTIFIER
from neubot.state import STATE

from neubot import privacy
from neubot import utils

TESTDONE = "testdone"

class BitTorrentClient(ClientHTTP):
    def __init__(self, poller):
        ClientHTTP.__init__(self, poller)
        STATE.update("test_name", "bittorrent")
        self.negotiating = True
        self.http_stream = None
        self.success = False
        self.my_side = {}

    def connect_uri(self, uri=None, count=None):
        if not uri:
            address = self.conf["bittorrent.address"]
            port = self.conf["bittorrent.negotiate.port"]
            uri = "http://%s:%s/" % (address, port)

        LOG.start("BitTorrent: connecting to %s" % uri)

        ClientHTTP.connect_uri(self, uri, 1)

    def connection_ready(self, stream):
        LOG.complete()

        STATE.update("negotiate")
        LOG.start("BitTorrent: negotiating")

        request = Message()
        body = json.dumps({"target_bytes": self.conf["bittorrent.bytes.up"]})
        request.compose(method="GET", pathquery="/negotiate/bittorrent",
          host=self.host_header, body=body, mimetype="application/json")
        request["authorization"] = self.conf.get("_authorization", "")
        stream.send_request(request)

    def got_response(self, stream, request, response):
        if self.negotiating:
            self.got_response_negotiating(stream, request, response)
        else:
            self.got_response_collecting(stream, request, response)

    def got_response_negotiating(self, stream, request, response):
        m = json.loads(response.body.read())

        PROPERTIES = ("authorization", "queue_pos", "real_address", "unchoked")
        for k in PROPERTIES:
            self.conf["_%s" % k] = m[k]

        if not self.conf["_unchoked"]:
            LOG.complete("done (queue_pos %d)" % m["queue_pos"])
            STATE.update("negotiate", {"queue_pos": m["queue_pos"]})
            self.connection_ready(stream)
        else:
            LOG.complete("done (unchoked)")

            sha1 = hashlib.sha1()
            sha1.update(m["authorization"])
            self.conf["bittorrent.my_id"] = sha1.digest()
            LOG.debug("* My ID: %s" % sha1.hexdigest())
            self.http_stream = stream
            self.negotiating = False
            peer = PeerNeubot(self.poller)
            peer.complete = self.peer_test_complete
            peer.connection_lost = self.peer_connection_lost
            peer.connection_failed = self.peer_connection_failed
            peer.configure(self.conf)
            peer.connect((self.http_stream.peername[0],
                          self.conf["bittorrent.port"]))

    def peer_connection_failed(self, connector, exception):
        stream = self.http_stream
        # TODO signal the other end something went wrong?
        stream.close()

    def peer_connection_lost(self, stream):
        if not self.success:
            stream = self.http_stream
            # TODO signal the other end something went wrong?
            stream.close()

    def peer_test_complete(self, stream, download_speed, rtt, target_bytes):
        self.success = True
        stream = self.http_stream

        # Update the downstream channel estimate
        estimate.DOWNLOAD = target_bytes

        self.my_side = {
            # The server will override our timestamp
            "timestamp": utils.timestamp(),
            "uuid": self.conf.get("uuid"),
            "internal_address": stream.myname[0],
            "real_address": self.conf.get("_real_address", ""),
            "remote_address": stream.peername[0],

            "privacy_informed": self.conf.get("privacy.informed", 0),
            "privacy_can_collect": self.conf.get("privacy.can_collect", 0),
            "privacy_can_publish": self.conf.get("privacy.can_publish", 0),

            # Upload speed measured at the server
            "connect_time": rtt,
            "download_speed": download_speed,

            # OS and version info
            "neubot_version": LibVersion.to_numeric("0.4.6-rc3"),
            "platform": sys.platform,
        }

        LOG.start("BitTorrent: collecting")
        STATE.update("collect")

        s = json.dumps(self.my_side)
        stringio = StringIO.StringIO(s)

        request = Message()
        request.compose(method="POST", pathquery="/collect/bittorrent",
          body=stringio, mimetype="application/json", host=self.host_header)
        request["authorization"] = self.conf.get("_authorization", "")

        stream.send_request(request)

    def got_response_collecting(self, stream, request, response):
        LOG.complete()

        if self.success:
            #
            # Always measure at the receiver because there is more
            # information at the receiver and also to make my friend
            # Enrico happier :-P.
            # The following is not a bug: it's just that the server
            # returns a result using the point of view of the client,
            # i.e. upload_speed is _our_ upload speed.
            #
            m = json.loads(response.body.read())
            self.my_side["upload_speed"] = m["upload_speed"]

            upload = utils.speed_formatter(m["upload_speed"])
            STATE.update("test_upload", upload)

            if privacy.collect_allowed(self.my_side):
                table_bittorrent.insert(DATABASE.connection(), self.my_side)

            # Update the upstream channel estimate
            target_bytes = int(m["target_bytes"])
            if target_bytes > 0:
                estimate.UPLOAD = target_bytes

        stream.close()

    def connection_lost(self, stream):
        NOTIFIER.publish(TESTDONE)

    def connection_failed(self, connector, exception):
        LOG.complete("failure (error: %s)" % str(exception))
        NOTIFIER.publish(TESTDONE)
