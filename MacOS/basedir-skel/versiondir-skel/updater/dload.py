# VERSIONDIR/updater/dload.py

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
 Download component of Neubot MacOSX updater.

 To communicate with the network, the core component of the updater
 connects to ``/var/run/neubot-dload.sock``.  In turn launchd(8),
 which manages the socket, accepts the connection and invokes this
 component.  The standard input, output and error are redirected
 to the connected socket, because launchd runs this component
 in inetd-compatibility mode.  Only running-as-root processes can
 connect to the socket, because of its permissions, which are
 guaranteed by launchd.

 This component reads the first line of its standard input, which
 should containt the URI to download.  It performs the download
 and then writes to the standard output an heading line followed
 by the downloaded content.  The heading line contains the word
 "OK" followed by the lenght of the content.  In case of error
 the component exits without writing anything on the stdout.
'''

import asyncore
import collections
import os
import signal
import syslog
import sys

if sys.version_info[0] == 3:
    import http.client as __httplib
    import urllib.parse as __urlparse
else:
    import httplib as __httplib
    import urlparse as __urlparse

#
# This is the maximum response lenght that we're willing to
# bufferize and copy on the standard output.
#
MAXLENGTH = 67108864

#
# This is the maximum chunk of data that we're willing to
# read from the network at a time.
#
MAXCHUNK = 262144

def __main():

    '''
     Read from standard input the URI to download and write to
     standard output the downloaded file.
    '''

    #
    # We must bufferize the whole response because if we pass
    # the bytes to the standard output as they flow we have not
    # a way to signal the reader that there was an error.
    #

    syslog.openlog('neubot [updater/dload]', syslog.LOG_PID,
                   syslog.LOG_DAEMON)

    #
    # Reopen standard input and standard output as binary
    # streams, which is the proper way to deal with sockets
    # and simplifies the copy-back code.
    #
    sys.stdin = os.fdopen(sys.stdin.fileno(), 'rb')
    sys.stdout = os.fdopen(sys.stdout.fileno(), 'wb')

    #
    # We cannot set a timeout on stdio sockets in a simple
    # way because they are not sockets when testing.  So
    # we set alarm to avoid being stuck forever while reading
    # the URI.
    #
    signal.alarm(30)

    syslog.syslog(syslog.LOG_INFO, 'Waiting for URI...')

    # Read URI from stdin
    uri = sys.stdin.readline().strip()
    sys.stdin.close()
    if sys.version_info[0] == 3:
        uri = str(uri, 'utf-8')

    syslog.syslog(syslog.LOG_INFO, 'Received URI: %s' % uri)

    #
    # Remove alarm and rely on the socket code from
    # this point on.
    #
    signal.alarm(0)

    # Parse URI
    scheme, netloc, path = __urlparse.urlsplit(uri)[0:3]

    # Connect
    if scheme == 'https':
        connection = __httplib.HTTPSConnection(netloc, timeout=30)
    elif scheme == 'http':
        connection = __httplib.HTTPConnection(netloc, timeout=30)
    else:
        syslog.syslog(syslog.LOG_ERR, 'Unknown scheme: %s' % scheme)
        sys.exit(1)

    syslog.syslog(syslog.LOG_INFO, 'scheme: %s, address: %s, path: %s' %
                  (scheme, netloc, path))

    # Request-response
    connection.request('GET', path)
    response = connection.getresponse()

    syslog.syslog(syslog.LOG_INFO, 'Received reponse: %d' % response.status)

    # Check response
    if response.status != 200:
        syslog.syslog(syslog.LOG_ERR, 'Bad HTTP response: %d' % response.status)
        sys.exit(1)

    # Bufferize
    length, body = 0, collections.deque()
    while True:
        data = response.read(MAXCHUNK)
        if not data:
            break

        length += len(data)
        if length > MAXLENGTH:
            syslog.syslog(syslog.LOG_ERR, 'Response too big')
            sys.exit(1)

        body.append(data)

    # Close connection with remote host
    connection.close()

    syslog.syslog(syslog.LOG_INFO, 'Body is %d bytes' % length)

    #
    # Re-add alarm since we don't want to get stuck
    # while copying back.
    #
    signal.alarm(30)

    # Copy back
    if sys.version_info[0] == 3:
        header = bytes('OK %d\n' % length, 'utf-8')
    else:
        header = 'OK %d\n' % length
    body.appendleft(header)
    sys.stdout.write(b''.join(body))

    syslog.syslog(syslog.LOG_INFO, 'Copied body to stdout')

def main():

    '''
     Read from standard input the URI to download and write to
     standard output the downloaded file.
    '''

    #
    # This function is just a wrapper that catches all the
    # possible exceptions.
    #

    try:
        __main()
    except SystemExit:
        raise
    except:
        try:
            why = asyncore.compact_traceback()
            syslog.syslog(syslog.LOG_ERR, 'Unhandled exception: %s' % str(why))
        except:
            pass
        sys.exit(1)

if __name__ == '__main__':
    main()
