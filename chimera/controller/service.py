#!/usr/bin/env python
# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Author: liangxiaoping
#

from oslo.config import cfg

from yarpc import server as rpc_server

from chimera.openstack.common import log as logging
from chimera import utils
from chimera import service
from chimera import exceptions
from chimera.controller import manager

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


def response_data(e):
    resp_data = {}
    try:
        resp_data['classname'] = e.__class__.__name__
        resp_data['message'] = unicode(e)
        resp_data['kwargs'] = e.kwargs
    except AttributeError:
        pass
    
    return resp_data


class RPCServer(rpc_server.RPCService):
    def handle(self, client_sock, client_addr):
        try:
            super(RPCServer, self).handle(client_sock, client_addr)
        except Exception as e:
            LOG.exception("error occurs when handling the request: %s" % e)

    def dispatch(self, service_name, method, args, kwargs):
        try:
            ret = super(RPCServer, self).dispatch(service_name, method,
                                                  args, kwargs)
            return dict(result=ret)
        except Exception as e:
            LOG.exception("Execute method[%s] error[%s]" % (method, unicode(e)))
            return dict(exception=response_data(e), status=500)


class Service(service.SocketService):
    def __init__(self, backlog=4096, threads=1000):
        config_paths = utils.find_config(CONF.api_paste_config)

        if len(config_paths) == 0:
            msg = 'Unable to determine appropriate api-paste-config file'
            raise exceptions.ConfigurationError(msg)

        LOG.info('Using api-paste-config found at: %s' % config_paths[0])

        logger = logging.getLogger('yarpc')
        httpaddress = (CONF['ofc'].inspect_host, CONF['ofc'].inspect_port)
        ofc_server = RPCServer(httpaddress=httpaddress,
                               concurrency=CONF['ofc'].concurrency,
                               timeout=CONF['ofc'].timeout,
                               log=logging.WritableLogger(logger))
        ofc_server.registerService(manager.OFCManager)

        super(Service, self).__init__(application=ofc_server.handle,
                                      host=CONF['ofc'].host,
                                      port=CONF['ofc'].port,
                                      backlog=backlog,
                                      threads=threads)

