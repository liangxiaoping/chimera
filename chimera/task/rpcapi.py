#!/usr/bin/env python
# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Author: liangxiaoping
#

from oslo.config import cfg
from oslo import messaging

from chimera.openstack.common import log as logging
from chimera import rpc


LOG = logging.getLogger(__name__)


class TaskAPI(object):
    """
    Client side of the Task Rpc API.

    API version history:

        1.0 - Initial version
    """
    RPC_API_VERSION = '1.0'

    def __init__(self, topic=None):
        topic = topic if topic else cfg.CONF.tm_topic

        target = messaging.Target(topic=topic, version=self.RPC_API_VERSION)
        self.client = rpc.get_client(target, version_cap='1.0')

    def ping(self, context):
        LOG.info("ping: Calling TM's ping.")
        return self.client.call(context, 'ping')
