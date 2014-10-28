#!/usr/bin/env python
# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Author: liangxiaoping
#

from oslo.config import cfg

from chimera.task import rpcapi


cfg.CONF.register_group(cfg.OptGroup(
    name='api', title="Configuration for API Service"
))

cfg.CONF.register_opts([
    cfg.IntOpt('workers', default=None,
               help='Number of worker processes to spawn'),
    cfg.StrOpt('api-base-uri', default='http://127.0.0.1:9001/'),
    cfg.StrOpt('api_host', default='0.0.0.0',
               help='API Host'),
    cfg.IntOpt('api_port', default=9001,
               help='API Port Number'),
    cfg.StrOpt('api_paste_config', default='api-paste.ini',
               help='File name for the paste.deploy config for chimera-api'),
    cfg.StrOpt('auth_strategy', default='keystone',
               help='The strategy to use for auth. Supports noauth or '
                    'keystone'),
    cfg.BoolOpt('enable-api-v1', default=True),
], group='api')


TASK_API = None

def get_task_api(topic=None):
    """
    The rpc.get_client() which is called upon the API object initialization
    will cause a assertion error if the chimera.rpc.TRANSPORT isn't setup by
    rpc.init() before.

    This fixes that by creating the rpcapi when demanded.
    """
    global TASK_API
    if not TASK_API:
        TASK_API = rpcapi.TaskAPI(topic)
    return TASK_API
