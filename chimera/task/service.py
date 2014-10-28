#!/usr/bin/env python
# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Author: liangxiaoping
#

from oslo.config import cfg

from chimera.openstack.common import log as logging
from chimera import service
from chimera.task import manager
from chimera import policy


LOG = logging.getLogger(__name__)


class Service(service.RPCService):
    def __init__(self, *args, **kwargs):
        super(Service, self).__init__(*args, **kwargs)
        self.manager = manager.TaskManager()

    def start(self):
        super(Service, self).start()

    def wait(self):
        super(Service, self).wait()

    def stop(self):
        super(Service, self).stop()

    def ping(self, context):
        #policy.check('diagnostics_ping', context)
        status = False

        try:
            pong = self.manager.ping()
        except Exception as e:
            status = {'status': False, 'message': str(e)}
            pong = None

        return {
            'host': cfg.CONF.host,
            'status': status,
            'pong': pong
        }
