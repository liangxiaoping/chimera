#!/usr/bin/env python
# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Author: liangxiaoping
#

from oslo.config import cfg

cfg.CONF.register_group(cfg.OptGroup(
    name='tm', title="Configuration for TM Service"
))

cfg.CONF.register_opts([
    cfg.IntOpt('workers', default=None,
               help='Number of worker processes to spawn'),
], group='tm')
