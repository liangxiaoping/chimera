#!/usr/bin/env python
# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Author: liangxiaoping
#

from paste import deploy
from oslo.config import cfg

from chimera.openstack.common import log as logging
from chimera.i18n import _LI
from chimera import exceptions
from chimera import utils
from chimera import service

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class Service(service.WSGIService):
    def __init__(self, backlog=4096, threads=1000):
        config_paths = utils.find_config(CONF.api_paste_config)

        if len(config_paths) == 0:
            msg = 'Unable to determine appropriate api-paste-config file'
            raise exceptions.ConfigurationError(msg)

        LOG.info(_LI('Using api-paste-config found at: %s') % config_paths[0])

        application = deploy.loadapp("config:%s" % config_paths[0],
                                     name='osapi_sdn')

        super(Service, self).__init__(application=application,
                                         host=cfg.CONF['api'].api_host,
                                         port=cfg.CONF['api'].api_port,
                                         backlog=backlog,
                                         threads=threads)
