# VERSIONDIR/updater/core.py

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
 Core component of Neubot MacOSX updater.

 The core component is run periodically by launchd(8) and checks
 whether there are updates.  It runs as ``root`` and it doesn't
 communicate directly with the network.  When it needs to download
 a file, it connects to the ``/var/run/neubot-dload.sock`` and
 writes the URI, followed by a newline, to the socket.  The request
 is handled by the download component, which manages the socket
 and does not run as root.  It will perform the request and write
 the result back on the connected socket.

 When there is an update, the core component installs it, then
 stops the running Neubot instance using launchctl(1) and finally
 starts the new version using BASEDIR/start.sh.
'''

import getopt
import subprocess
import hashlib
import tarfile
import compileall
import decimal
import asyncore
import syslog
import socket
import re
import sys
import os

# Note: BASEDIR/VERSIONDIR/updater/core.py
VERSIONDIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASEDIR = os.path.dirname(VERSIONDIR)

# Version number in numeric representation
VERSION = "0.004002999"

#
# Launchd(8) takes care of this socket and spawns the
# dload component whenever we connect to it.
#
try:
    DLOAD_SOCK = os.environ['NEUBOT_UPDATER_SOCKET']
except KeyError:
    sys.exit('Missing NEUBOT_UPDATER_SOCKET environment variable')

#
# This is the maximum response lenght that we will accept
# from the dload component.
#
MAXLENGTH = 67108864

#
# This is the maximum chunk of data that we're willing to
# read from the UNIX domain socket at a time.
#
MAXCHUNK = 262144

#
# Download
#

def __printable_only(string):
    ''' Remove non-printable characters from string '''
    string = re.sub(r'[\0-\31]', '', string)
    return re.sub(r'[\x7f-\xff]', '', string)

def __download(address, rpath, tofile=False, https=False, maxbytes=MAXLENGTH):

    ''' Download @rpath from @address.  If @tofile is True the result
        is saved to a file and then file name is returned.  If @tofile
        is False returns the downloaded content. '''

    #
    # The real work is performed by the dload component of
    # the updater, which runs on behalf of the unprivileged
    # user ``_neubot_update``.
    #

    syslog.syslog(syslog.LOG_INFO,
                  '__download: address=%s rpath=%s tofile=%d '
                  'https=%d maxbytes=%d' % (address, rpath,
                  tofile, https, maxbytes))

    # Connect to the socket
    sockfd = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sockfd.settimeout(30)
    sockfd.connect(DLOAD_SOCK)

    # Send request
    if https:
        scheme = 'https'
    else:
        scheme = 'http'
    if rpath.startswith('/'):
        rpath = rpath[1:]
    if sys.version_info[0] == 3:
        uri = bytes('%s://%s/%s\n' % (scheme, address, rpath), 'utf-8')
    else:
        uri = '%s://%s/%s\n' % (scheme, address, rpath)
    sockfd.send(uri)

    syslog.syslog(syslog.LOG_INFO, 'Request sent...')

    # Recv response
    total, body = 0, []
    while True:
        data = sockfd.recv(MAXCHUNK)
        if not data:
            break

        total += len(data)
        if total > MAXLENGTH:
            raise RuntimeError('Response too big')

        body.append(data)

    body = b''.join(body)

    # Close the socket
    sockfd.close()

    # Extract first line
    index = body.find(b'\n')
    if index == -1:
        raise ValueError('Cannot find first line')
    firstline = body[:index]
    remainder = body[index + 1:]

    # Validate first line
    if sys.version_info[0] == 3:
        firstline = str(firstline, 'utf-8')
    match = re.match('^OK ([0-9]+)$', firstline)
    if not match:
        raise ValueError('Invalid response line')
    total = int(match.group(1))
    if len(remainder) != total:
        raise ValueError('Invalid content length')

    #
    # Simple case: we must return the raw
    # data to the caller -- which is supposed
    # to validate it, by the way.
    #
    if not tofile:
        if sys.version_info[0] == 3:
            remainder = str(remainder, 'utf-8')
        syslog.syslog(syslog.LOG_ERR, 'Response is: %s' %
                             __printable_only(remainder))
        return remainder

    #
    # Otherwise we must save the result into
    # a file and then return the file name to
    # the caller.
    #

    # Build output file name
    lpath = os.sep.join([BASEDIR, os.path.basename(rpath)])

    #
    # If the output file exists and is a regular file
    # unlink it because it might be an old -possibly failed-
    # download attempt.
    # DO NOT remove this code because it guarantees that
    # the file gets the right permissions below.
    #
    if os.path.exists(lpath):
        if not os.path.isfile(lpath):
            raise RuntimeError('%s: not a file' % lpath)
        os.unlink(lpath)

    #
    # Open the output file (384 == 0600)
    # We know the file will get the right permissions
    # because of the unlink call above.
    #
    lfdesc = os.open(lpath, os.O_RDWR|os.O_CREAT, 384)

    #
    # Write into file
    # Use os.fdopen() to wrap the filedesc so we save
    # a loop and some string copies.
    #
    lfptr = os.fdopen(lfdesc, 'wb')
    lfptr.write(remainder)

    # Close the file
    lfptr.close()

    # Return its path
    syslog.syslog(syslog.LOG_ERR, 'Response saved to: %s' % lpath)
    return lpath

def __download_version_info(address):
    '''
     Download the latest version number.  The version number here
     is in numeric representation, i.e. a floating point number with
     exactly nine digits after the radix point.
    '''
    version = __download(address, "/updates/latest")
    version = version.strip()
    match = re.match('^([0-9]+)\.([0-9]{9})$', version)
    if not match:
        raise ValueError('Invalid version: %s' % __printable_only(version))
    else:
        return version

def __download_sha256sum(version, address):
    '''
     Download the SHA256 sum of a tarball.  Note that the tarball
     name is a version number in numeric representation.  Note
     that the sha256 file contains just one SHA256 entry.
    '''
    sha256 = __download(address, '/updates/%s.tar.gz.sha256' % version)
    sha256 = sha256.strip()
    match = re.match('^([a-fA-F0-9]{64})  %s.tar.gz$' % version, sha256)
    if not match:
        raise ValueError('Invalid sha256: %s' % __printable_only(sha256))
    else:
        return match.group(1)

def __verify_sig(signature, tarball):

    '''
     Call OpenSSL to verify the signature.  The public key
     is ``VERSIONDIR/pubkey.pem``.  We assume the signature
     algorithm is SHA256.
    '''

    #
    # Note that OpenSSL is part of the base MacOS
    # system.
    #

    cmdline = ['/usr/bin/openssl', 'dgst', '-sha256',
               '-verify', '%s/pubkey.pem' % VERSIONDIR,
               '-signature', signature, tarball]

    syslog.syslog(syslog.LOG_INFO, 'Cmdline: %s' % str(cmdline))

    retval = subprocess.call(cmdline)

    if retval != 0:
        raise ValueError('Signature does not match')

def __really_check_for_updates(server):

    ''' Returns the version of the available update, if any,
        or returns None. '''

    syslog.syslog(syslog.LOG_INFO,
                  'Checking for updates (current version: %s)' %
                  VERSION)

    # Get latest version number
    nversion = __download_version_info(server)
    if decimal.Decimal(nversion) <= decimal.Decimal(VERSION):
        syslog.syslog(syslog.LOG_INFO, 'No updates available')
        return None

    syslog.syslog(syslog.LOG_INFO,
                  'Update available: %s -> %s' %
                  (VERSION, nversion))

    return nversion

def __download_and_verify_update(server, nversion):

    '''
     If an update is available, download the updated tarball and
     verify its sha256sum.  Returns the name of the downloaded file
     or None.
    '''

    # Get checksum
    sha256 = __download_sha256sum(nversion, server)
    syslog.syslog(syslog.LOG_INFO, 'Expected sha256sum: %s' % sha256)

    # Get tarball
    tarball = __download(
                         server,
                         '/updates/%s.tar.gz' % nversion,
                         tofile=True
                        )

    # Calculate tarball checksum
    filep = open(tarball, 'rb')
    hashp = hashlib.new('sha256')
    content = filep.read()
    hashp.update(content)
    digest = hashp.hexdigest()
    filep.close()

    syslog.syslog(syslog.LOG_INFO, 'Tarball sha256sum: %s' % digest)

    # Verify checksum
    if digest != sha256:
        raise RuntimeError('SHA256 mismatch')

    # Download signature
    signature = __download(
                           server,
                           '/updates/%s.tar.gz.sig' % nversion,
                           tofile=True
                          )

    # Verify signature
    __verify_sig(signature, tarball)

    # Yu-hu!
    syslog.syslog(syslog.LOG_INFO, 'Tarball OK')
    return nversion

#
# Install
#

def __install_new_version(version):
    ''' Install a new version of Neubot '''

    # Make file names
    targz = os.sep.join([BASEDIR, '%s.tar.gz' % version])
    sigfile = '%s.sig' % targz
    newsrcdir = os.sep.join([BASEDIR, '%s' % version])

    # Extract from the tarball
    archive = tarfile.open(targz, mode='r:gz')
    archive.extractall(BASEDIR)
    archive.close()

    #
    # WARNING The compileall module does not fail if it's not
    # possible to compile the sources.  So we won't notice the
    # problem is MacOSX suddendly upgrades to Python 3.  At
    # the same time, we cannot deploy a static check because
    # that would prevent upgrading Neubot forever.
    #

    # Compile all modules
    compileall.compile_dir(newsrcdir, quiet=1)

    # Write .neubot-installed-ok file
    filep = open('%s/.neubot-installed-ok' % newsrcdir, 'wb')
    filep.close()

    # Call sync
    os.system('sync')

    # Cleanup
    os.unlink(targz)
    os.unlink(sigfile)

def __switch_to_new_version():
    ''' Switch to the a new version of Neubot '''

    #
    # The job should be stopped but the extra stop command
    # here won't hurt anyone.
    #
    cmdline = ['/bin/launchctl', 'stop', 'org.neubot']
    retval = subprocess.call(cmdline)
    if retval != 0:
        syslog.syslog(syslog.LOG_INFO, 'Failed to stop `org.neubot`, most '
                      'likely because it was already stopped')

    #
    # Restart the job.  Which means basically that the new
    # version VERSIONDIR/start.sh will remove existing Neubot
    # jobs and will register new version ones.
    # There is not much we can do here to repair if this
    # command fails.
    #
    cmdline = ['/bin/launchctl', 'start', 'org.neubot']
    reval = subprocess.call(cmdline)
    if retval != 0:
        syslog.syslog(syslog.LOG_ERR, 'Failed to start `org.neubot`')

def __check_for_updates():

    '''
     Check for updates and eventually install the new version,
     stop the running version and launch the new one.
    '''

    syslog.openlog('neubot [updater/core]', syslog.LOG_PID,
                   syslog.LOG_DAEMON)

    syslog.syslog(syslog.LOG_INFO, 'Checking for updates')
    nversion = __really_check_for_updates('releases.neubot.org')
    if not nversion:
        return

    __download_and_verify_update('releases.neubot.org', nversion)
    __install_new_version(nversion)
    __switch_to_new_version()

def __main():

    '''
     Check for updates and eventually install the new version,
     stop the running version and launch the new one.
    '''

    #
    # This functions adds some command line options to
    # make this script more testable.
    #

    if len(sys.argv) == 1:
        __check_for_updates()

    else:

        syslog.openlog('neubot [updater/core]',
                       syslog.LOG_PID|syslog.LOG_NDELAY|syslog.LOG_PERROR,
                       syslog.LOG_DAEMON)

        avail_opts = [ 'check', 'download=', 'get-latest', 'get-sha256sum=',
                       'install=' ]

        opts_help = '--check|--download=V|--get-latest|' \
                    '--get-sha256sum=V|--install=V'

        # Get command line options
        try:
            options, arguments = getopt.getopt(sys.argv[1:], '', avail_opts)
        except getopt.error:
            sys.exit('Usage: %s [%s]' % (sys.argv[0], opts_help))
        if arguments:
            sys.exit('Usage: %s [%s]' % (sys.argv[0], opts_help))

        # Process command line options
        for name, value in options:
            if name == '--check':
                result = __really_check_for_updates('releases.neubot.org')
                print(result)
                sys.exit(0)
            elif name == '--download':
                __download_and_verify_update('releases.neubot.org', value)
                sys.exit(0)
            elif name == '--get-latest':
                version = __download_version_info('releases.neubot.org')
                print(version)
                sys.exit(0)
            elif name == '--get-sha256sum':
                sha256 = __download_sha256sum(value, 'releases.neubot.org')
                print(sha256)
                sys.exit(0)
            elif name == '--install':
                __install_new_version(value)
                sys.exit(0)

def main():

    '''
     Check for updates and eventually install the new version,
     stop the running version and launch the new one.
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
