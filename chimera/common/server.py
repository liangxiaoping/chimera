#!/usr/bin/env python
# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Author: liangxiaoping
#

import eventlet
eventlet.patcher.monkey_patch(all=False, socket=True)

import os
import socket
import time
import errno

from eventlet import wsgi
from oslo.config import cfg

from chimera.openstack.common import service
from chimera.openstack.common import log as logging
from chimera.openstack.common import sslutils
from chimera.i18n import _

CONF = cfg.CONF

LOG = logging.getLogger(__name__)

CONF.register_opts([
    cfg.IntOpt('backlog',
               default=4096,
               help="Number of backlog requests to configure the socket with"),
    cfg.IntOpt('tcp_keepidle',
               default=600,
               help="Sets the value of TCP_KEEPIDLE in seconds for each "
                    "server socket. Not supported on OS X."),
    cfg.IntOpt('server_threads', default=1024,
               help='The maximum number of greenthreads that will be open at any time'
                    'handling requests. When the server hits the concurrency limit,'
                    'it stops accepting new connections until the existing ones complete'),
])


class Service(service.Service):
    """
    Provides a SocketServer API for common servers.

    """

    def __init__(self, application, port,
                 host='0.0.0.0', backlog=4096, threads=1000):
        self.application = application
        self._port = port
        self._host = host
        self._backlog = backlog if backlog else CONF.backlog
        self._socket = self._get_socket(self._host, self._port, self._backlog)
        self._pid = os.getpid()
        super(Service, self).__init__(threads)

    def _get_socket(self, host, port, backlog):
        # TODO(dims): eventlet's green dns/socket module does not actually
        # support IPv6 in getaddrinfo(). We need to get around this in the
        # future or monitor upstream for a fix
        info = socket.getaddrinfo(host,
                                  port,
                                  socket.AF_UNSPEC,
                                  socket.SOCK_STREAM)[0]
        family = info[0]
        bind_addr = info[-1]

        sock = None
        retry_until = time.time() + 30
        while not sock and time.time() < retry_until:
            try:
                sock = eventlet.listen(bind_addr,
                                       backlog=backlog,
                                       family=family)
                if sslutils.is_enabled():
                    sock = sslutils.wrap(sock)

            except socket.error, err:
                if err.args[0] != errno.EADDRINUSE:
                    raise
                eventlet.sleep(0.1)
        if not sock:
            raise RuntimeError(_("Could not bind to %(host)s:%(port)s "
                               "after trying for 30 seconds") %
                               {'host': host, 'port': port})
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # sockets can hang around forever without keepalive
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

        # This option isn't available in the OS X version of eventlet
        if hasattr(socket, 'TCP_KEEPIDLE'):
            sock.setsockopt(socket.IPPROTO_TCP,
                            socket.TCP_KEEPIDLE,
                            CONF.tcp_keepidle)

        return sock

    def start(self):
        """Start serving this service using the provided server instance.

        :returns: None

        """
        super(Service, self).start()
        self.tg.add_thread(self._run, self.application, self._socket)

    @property
    def backlog(self):
        return self._backlog

    @property
    def host(self):
        return self._socket.getsockname()[0] if self._socket else self._host

    @property
    def port(self):
        return self._socket.getsockname()[1] if self._socket else self._port

    def stop(self):
        """Stop serving this API.

        :returns: None

        """
        super(Service, self).stop()

    def _run(self, application, socket):
        pass

        
class SocketServer(Service):
    def _run(self, application, socket):
        """Runs a server on the supplied socket in a new green thread."""
        LOG.info(_('(%(pid)s) Server starting up on %(host)s:%(port)s') %
                 {'pid': self._pid, 'host': self._host, 'port': self._port})
        eventlet.serve(socket, application, concurrency=CONF.server_threads)


class WSGIServer(Service):
    """
    Service class to be shared by all Chimera WSGI Services
    """
    def _run(self, application, socket):
        """Start a WSGI server in a new green thread."""
        logger = logging.getLogger('eventlet.wsgi')
        eventlet.wsgi.server(socket,
                             application,
                             custom_pool=self.tg.pool,
                             log=logging.WritableLogger(logger))
