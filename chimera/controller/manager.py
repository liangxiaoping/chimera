#!/usr/bin/env python
# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Author: liangxiaoping
#

import eventlet
import traceback
from oslo.config import cfg

from chimera.openstack.common import log as logging

LOG = logging.getLogger(__name__)
CONF = cfg.CONF


class OFCManager(object):
    def __init__(self, *args, **kwargs):
        pass

    def ping(self, body):
        LOG.debug("ping request is: %s" % str(body))
        pong = dict(pong='ok')
        return dict(result=pong)