#!/usr/bin/env python
# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Author: liangxiaoping
#

import inspect
import itertools
import xmlrpclib
import datetime
import eventlet
import urlparse
import functools

from yarpc.client import Client
from yarpc.error import TimeoutError

from oslo.config import cfg
from oslo.utils import timeutils
from oslo.serialization import jsonutils

from chimera.openstack.common import log as logging
from chimera import exceptions
from chimera.i18n import _


client_opts = [
    cfg.IntOpt('tcp_buffer_size',
               default=256,
               help="TCP Buffer Size"),
    cfg.IntOpt('tcp_heartbeat_time',
               default=5,
               help="TCP Heartbeat Time"),
    cfg.IntOpt('client_retry_interval',
               default=1,
               help='how frequently to retry connecting with client'),
    cfg.IntOpt('client_retry_backoff',
               default=2,
               help='how long to backoff for between retries when connecting '
                    'to chimera'),
    cfg.IntOpt('client_max_retries',
               default=3,
               help='maximum retries with trying to connect to server'
                    '(the default of 0 implies an infinite retry count)'),
    cfg.IntOpt('client_timeout',
               default=120,
               help='timeout for chimera request'),
    cfg.BoolOpt('log_tcp_client',
                default=False,
                help="Log tcp request or response"),
    cfg.BoolOpt('enable_heartbeat',
                default=True,
                help="Enable heartbeat or not"),
]


CONF = cfg.CONF
CONF.register_opts(client_opts)
LOG = logging.getLogger(__name__)


class AttrDict(dict):
    """
    http://stackoverflow.com/questions/4984647/\
    accessing-dict-keys-like-an-attribute-in-python
    http://bugs.python.org/issue1469629
    """
    def __init__(self, source):
        super(AttrDict, self).__init__(source)

    def __getattr__(self, key):
        return self[key]

    def __setattr__(self, key, value):
        self[key] = value


DATETIME_KEYS = ('created_at', 'deleted_at', 'updated_at', 'launched_at',
                 'scheduled_at', 'terminated_at', 'attach_time', 'expire',
                 'start_period', 'last_refreshed')


def convert_datetimes(values, *datetime_keys):
    for key in values:
        if key in datetime_keys and isinstance(values[key], basestring):
            values[key] = timeutils.parse_strtime(values[key])
    return values


def convert_results(values, to_datetime=True, level=0, max_depth=3):
    if level > max_depth:
        return '?'

    try:
        recursive = functools.partial(convert_results,
                                      to_datetime=to_datetime,
                                      level=level,
                                      max_depth=max_depth)

        if isinstance(values, (list, tuple)):
            return [recursive(v) for v in values]
        elif isinstance(values, dict):
            values = convert_datetimes(values, *DATETIME_KEYS)
            return AttrDict((k, recursive(v)) for k, v in values.iteritems())
        elif hasattr(values, 'iteritems'):
            return recursive(dict(values.iteritems()), level=level + 1)
        elif hasattr(values, '__iter__'):
            return recursive(list(values))
        else:
            return values

    except TypeError:
        return values


def raise_exception(exce_dict):
    try:
        classname = exce_dict['classname']
        message = exce_dict['message']
        kwargs = exce_dict['kwargs']
        exce_class = getattr(exceptions, classname)
    except (KeyError, TypeError):
        LOG.error("exceptions dict error %s" % exce_dict)
        raise
    except AttributeError:
        LOG.error("AttributeError error: %s" % exce_dict)
        raise

    raise exce_class(message, **kwargs)


class TCPClient(object):
    def __init__(self, endpoints, **kwargs):
        self.param_list = []
        if not endpoints:
            LOG.error('must set endpoints configuration')

        for endpoint in endpoints:
            if not endpoint.startswith('http'):
                endpoint = 'http://' + endpoint
            endpoint_parts = urlparse.urlparse(endpoint)
            self.param_list.append(endpoint_parts)
        
        self.timeout = kwargs.get('timeout', CONF.client_timeout)
        self.service = kwargs.get('service', CONF.client_timeout)
        self.interval_max = 30
        self.max_retries = CONF.client_max_retries
        self.interval_start = CONF.client_retry_interval
        self.interval_stepping = CONF.client_retry_backoff

        addresses = [(param.hostname, param.port) for param in self.param_list]

        self.client = Client(address=addresses,
                             buffer_size=CONF.tcp_buffer_size,
                             heartbeat_time=CONF.tcp_heartbeat_time,
                             log=logging.WritableLogger(LOG),
                             enable_heartbeat=CONF.enable_heartbeat)

    def call(self, method, body):
        body = jsonutils.to_primitive(body, convert_instances=True)
        args = body.get('args', ())
        kwargs = body.get('kwargs', {})
        result = []

        self.log_tcp_request(method, body)

        attempt = 0
        while 1:
            attempt += 1
            try:
                result = self.client.call(self.timeout, self.service, method,
                                          *args, **kwargs)

                if isinstance(result, TimeoutError):
                    raise Exception('tcp request chimera_api, %s Timeout' % method)

                break
            except Exception as e:
                if self.max_retries and attempt == self.max_retries:
                    LOG.error(_('Call %s failed after'
                                ' %d tries.') % (method, attempt))
                    raise e

                if attempt == 1:
                    sleep_time = self.interval_start
                elif attempt > 1:
                    sleep_time = sleep_time + self.interval_stepping
                if self.interval_max:
                    sleep_time = min(sleep_time, self.interval_max)

                LOG.info(_('Call %s :%s. Trying again in '
                           '%d seconds.') % (method, unicode(e), sleep_time))
                
                eventlet.sleep(sleep_time)

        self.log_tcp_response(method, result)

        return result

    def cast(self, method, body):
        body = jsonutils.to_primitive(body, convert_instances=True)
        args = body.get('args', ())
        kwargs = body.get('kwargs', {})

        future = self.client.call_async(self.timeout, 'chimera_api',
                                        method, *args, **kwargs)
        return future

    def log_tcp_request(self, method, body):
        if not CONF.log_tcp_client:
            return

        LOG.info("Call %(method)s with: %(body)s" % locals())

    def log_tcp_response(self, method, result):
        if not CONF.log_tcp_client:
            return

        LOG.info("Call %(method)s return: %(result)s" % locals())

    def do_request(self, func_name, body=None):
        resp_body = self.call(func_name, body)

        if resp_body:
            if 'result' in resp_body:
                result = resp_body.get('result', None)
                return convert_results(result)
            elif 'status' in resp_body:
                status = resp_body['status']
                message = resp_body['exception'].get('message', '')
                raise Exception('Server ERROR: %s, status=%d' % (message, status))
            else:
                if isinstance(resp_body, str):
                    if 'timeout' in resp_body.lower():
                        LOG.debug(resp_body)
                    else:
                        raise Exception(resp_body)
                else:
                    exe = resp_body.get('exception', None)
                    raise_exception(exe)
        else:
            LOG.error("resp_body is None when call %s" % func_name)
