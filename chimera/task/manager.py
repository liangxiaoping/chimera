#!/usr/bin/env python
# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Author: liangxiaoping
#

import eventlet
import traceback
from oslo.config import cfg

from chimera.openstack.common import log as logging
from chimera.common import client

LOG = logging.getLogger(__name__)
CONF = cfg.CONF

cfg.CONF.register_opts([
    cfg.ListOpt('ofc_endpoints',
                default=['127.0.0.1:18989'],
                help='Endpoints where the ofc service is running'),
    cfg.StrOpt('ofc_service', default='OFCManager',
               help='OFC Manager service class name'),
], group='tm')


class TaskManager(object):
    def __init__(self, *args, **kwargs):
        self.clients = {}
        ofc_endpoints = CONF['tm'].ofc_endpoints
        ofc_service = CONF['tm'].ofc_service
        for ofc in ofc_endpoints:
            self.clients[ofc] = client.TCPClient([ofc], service=ofc_service)

    def ping(self):
        LOG.debug("ping task test")
        ofc = CONF['tm'].ofc_endpoints[0]
        cli = self.clients[ofc]
        func_name = 'ping'
        kwargs = dict(body='ping test')
        body = {'args': [], 'kwargs': kwargs}
        pong = cli.do_request(func_name, body)
        LOG.debug(pong)
        return pong