#!/usr/bin/env python
# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Author: liangxiaoping
#

from oslo.config import cfg

cfg.CONF.register_group(cfg.OptGroup(
    name='ofc', title="Configuration for OFC Service"
))

cfg.CONF.register_opts([
    cfg.StrOpt('host', default='0.0.0.0',help='OFC Host'),
    cfg.IntOpt('port', default=18989, help='OFC Port Number'),
    cfg.IntOpt('workers', default=None,
               help='Number of worker processes to spawn'),
    cfg.StrOpt('ofc_driver', default='pox',
               help='The backend ofc driver to use'),
    cfg.StrOpt('inspect_host', default='0.0.0.0',
               help='Inspect host'),
    cfg.IntOpt('inspect_port', default=18080,
               help='Inspect port number'),
    cfg.IntOpt('concurrency', default=1024,
               help='Concurrency for handling one connection'),
    cfg.IntOpt('timeout', default=3600,
               help='Timeout for handling one method'),
], group='ofc')
