# neubot/http/protocols.py
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

import logging

import neubot

PROTOCOLS = [ "HTTP/1.1", "HTTP/1.0" ]
TIMEOUT   = 300

class protocol:
	def __init__(self, adaptor):
		self.adaptor = adaptor
		self.adaptor.attach(self)
		self.message = None
		self.application = None
		self.sockname = reduce(neubot.network.concatname,
		    adaptor.connection.myname)
		self.peername = reduce(neubot.network.concatname,
		    adaptor.connection.peername)
		self.begin = neubot.utils.ticks()
		self.poller = self.adaptor.connection.poller
		self.poller.register_periodic(self.periodic)
		self.have_body = True

	def __str__(self):
		return self.peername

	def periodic(self, now):
		if now - self.begin > TIMEOUT:
			logging.warning("Watchdog timeout")
			self.poller.register_func(self.close)

	def closing(self):
		self.poller.unregister_periodic(self.periodic)
		self.adaptor = None
                if self.application:
			self.application.closing(self)

	def got_body(self):
		if self.application:
			self.application.got_message(self)

	def got_body_part(self, octets):
		self.message.body.write(octets)

	def got_metadata(self, metadata):
		self.message = neubot.http.message()
		headers = metadata.split("\r\n")
		for line in headers:
			if (line == ""):
				break
			if (not self.message.protocol):
				vector = line.split(" ", 2)
				if (len(vector) != 3):
					raise (Exception("Invalid line"))
				if (vector[0] in PROTOCOLS):
					self.message.protocol = vector[0]
					self.message.code = vector[1]
					self.message.reason = vector[2]
				elif (vector[2] in PROTOCOLS):
					self.message.method = vector[0]
					self.message.uri = vector[1]
					self.message.protocol = vector[2]
				else:
					raise (Exception("Invalid line"))
			else:
				vector = line.split(":", 1)		# XXX
				if (len(vector) != 2):
					raise (Exception("Invalid line"))
				key, value = vector
				key, value = key.strip(), value.strip()
				self.message[key] = value
		self.application.got_metadata(self)
		if self.have_body:
			if (self.message["transfer-encoding"] == "chunked"):
				self.adaptor.get_chunked_body()
				return
			if (self.message["content-length"]):
				value = self.message["content-length"]
				try:
					length = int(value)
				except ValueError:
					length = -1
				if (length < 0):
					raise (Exception("Invalid line"))
				self.adaptor.get_bounded_body(length)
				return
			if (self.application.is_message_unbounded(self)):
				self.adaptor.get_unbounded_body()
				return
		self.application.got_message(self)

	def sent_all(self):
		self.application.message_sent(self)

	def attach(self, application):
		self.application = application

	def close(self):
		self.adaptor.close()

	def sendmessage(self, msg):
		self.adaptor.send(msg.serialize_headers())
		self.adaptor.send(msg.serialize_body())

	def donthavebody(self):
		self.have_body = False

	def recvmessage(self):
		self.adaptor.get_metadata()

	def __del__(self):
		pass
