#!/usr/bin/env python
# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Author: liangxiaoping
#

import flask
import webob.dec
from oslo.config import cfg
from oslo import messaging
from oslo.middleware import base
from oslo.middleware import request_id
from oslo.serialization import jsonutils as json
from oslo.utils import strutils

from chimera import exceptions
from chimera import notifications
from chimera import context
from chimera.openstack.common import log as logging
from chimera.i18n import _LI
from chimera.i18n import _LW
from chimera.i18n import _LE
from chimera.i18n import _LC


LOG = logging.getLogger(__name__)

cfg.CONF.register_opts([
    cfg.BoolOpt('maintenance-mode', default=False,
                help='Enable API Maintenance Mode'),
    cfg.StrOpt('maintenance-mode-role', default='admin',
               help='Role allowed to bypass maintaince mode'),
], group='api')


def auth_pipeline_factory(loader, global_conf, **local_conf):
    """
    A paste pipeline replica that keys off of auth_strategy.

    Code nabbed from cinder.
    """
    pipeline = local_conf[cfg.CONF['api'].auth_strategy]
    pipeline = pipeline.split()
    LOG.info(_LI('Getting auth pipeline: %s') % pipeline[:-1])
    filters = [loader.get_filter(n) for n in pipeline[:-1]]
    app = loader.get_app(pipeline[-1])
    filters.reverse()
    for filter in filters:
        app = filter(app)
    return app


class ContextMiddleware(base.Middleware):
    def make_context(self, request, *args, **kwargs):
        req_id = request.environ.get(request_id.ENV_REQUEST_ID)
        kwargs.setdefault('request_id', req_id)

        ctxt = context.ChimeraContext(*args, **kwargs)

        headers = request.headers
        params = request.params

        if headers.get('X-Auth-All-Projects'):
            ctxt.all_tenants = \
                strutils.bool_from_string(headers.get('X-Auth-All-Projects'))
        elif 'all_projects' in params:
            ctxt.all_tenants = \
                strutils.bool_from_string(params['all_projects'])
        elif 'all_tenants' in params:
            ctxt.all_tenants = \
                strutils.bool_from_string(params['all_tenants'])
        else:
            ctxt.all_tenants = False

        request.environ['context'] = ctxt

        return ctxt


class KeystoneContextMiddleware(ContextMiddleware):
    def __init__(self, application):
        super(KeystoneContextMiddleware, self).__init__(application)

        LOG.info(_LI('Starting chimera keystonecontext middleware'))

    def process_request(self, request):
        headers = request.headers

        try:
            if headers['X-Identity-Status'] is 'Invalid':
                # TODO(graham) fix the return to use non-flask resources
                return flask.Response(status=401)
        except KeyError:
            # If the key is valid, Keystone does not include this header at all
            pass

        if headers.get('X-Service-Catalog'):
            catalog = json.loads(headers.get('X-Service-Catalog'))
        else:
            catalog = None

        roles = headers.get('X-Roles').split(',')

        self.make_context(
            request,
            auth_token=headers.get('X-Auth-Token'),
            user=headers.get('X-User-ID'),
            tenant=headers.get('X-Tenant-ID'),
            roles=roles,
            service_catalog=catalog)


class NoAuthContextMiddleware(ContextMiddleware):
    def __init__(self, application):
        super(NoAuthContextMiddleware, self).__init__(application)

        LOG.info(_LI('Starting chimera noauthcontext middleware'))

    def process_request(self, request):
        headers = request.headers

        self.make_context(
            request,
            auth_token=headers.get('X-Auth-Token', None),
            user=headers.get('X-Auth-User-ID', 'noauth-user'),
            tenant=headers.get('X-Auth-Project-ID', 'noauth-project'),
            roles=headers.get('X-Roles', 'admin').split(',')
        )


class TestContextMiddleware(ContextMiddleware):
    def __init__(self, application, tenant_id=None, user_id=None):
        super(TestContextMiddleware, self).__init__(application)

        LOG.critical(_LC('Starting chimera testcontext middleware'))
        LOG.critical(_LC('**** DO NOT USE IN PRODUCTION ****'))

        self.default_tenant_id = tenant_id
        self.default_user_id = user_id

    def process_request(self, request):
        headers = request.headers

        all_tenants = strutils.bool_from_string(
            headers.get('X-Test-All-Tenants', 'False'))

        self.make_context(
            request,
            user=headers.get('X-Test-User-ID', self.default_user_id),
            tenant=headers.get('X-Test-Tenant-ID', self.default_tenant_id),
            all_tenants=all_tenants)


class MaintenanceMiddleware(base.Middleware):
    def __init__(self, application):
        super(MaintenanceMiddleware, self).__init__(application)

        LOG.info(_LI('Starting chimera maintenance middleware'))

        self.enabled = cfg.CONF['api'].maintenance_mode
        self.role = cfg.CONF['api'].maintenance_mode_role

    def process_request(self, request):
        # If maintaince mode is not enabled, pass the request on as soon as
        # possible
        if not self.enabled:
            return None

        # If the caller has the bypass role, let them through
        if ('context' in request.environ
                and self.role in request.environ['context'].roles):
            LOG.warn(_LW('Request authorized to bypass maintenance mode'))
            return None

        # Otherwise, reject the request with a 503 Service Unavailable
        return flask.Response(status=503, headers={'Retry-After': 60})


class NormalizeURIMiddleware(base.Middleware):
    @webob.dec.wsgify
    def __call__(self, request):
        # Remove any trailing /'s.
        request.environ['PATH_INFO'] = request.environ['PATH_INFO'].rstrip('/')

        return request.get_response(self.application)


class FaultWrapperMiddleware(base.Middleware):
    def __init__(self, application):
        super(FaultWrapperMiddleware, self).__init__(application)

        LOG.info(_LI('Starting chimera faultwrapper middleware'))

    @webob.dec.wsgify
    def __call__(self, request):
        try:
            return request.get_response(self.application)
        except exceptions.Base as e:
            # Handle Chimera Exceptions
            status = e.error_code if hasattr(e, 'error_code') else 500

            # Start building up a response
            response = {
                'code': status
            }

            if e.error_type:
                response['type'] = e.error_type

            if e.error_message:
                response['message'] = e.error_message

            if e.errors:
                response['errors'] = e.errors

            return self._handle_exception(request, e, status, response)
        except messaging.MessagingTimeout as e:
            # Special case for RPC timeout's
            response = {
                'code': 504,
                'type': 'timeout',
            }

            return self._handle_exception(request, e, 504, response)
        except Exception as e:
            # Handle all other exception types
            return self._handle_exception(request, e)

    def _handle_exception(self, request, e, status=500, response=None):

        response = response or {}
        # Log the exception ASAP unless it is a 404 Not Found
        if not getattr(e, 'expected', False):
            LOG.exception(e)

        headers = [
            ('Content-Type', 'application/json'),
        ]

        url = getattr(request, 'url', None)

        # Set a response code and type, if they are missing.
        if 'code' not in response:
            response['code'] = status

        if 'type' not in response:
            response['type'] = 'unknown'

        # Return the new response
        if 'context' in request.environ:
            response['request_id'] = request.environ['context'].request_id

            notifications.send_api_fault(request.environ['context'], url,
                                         response['code'], e)
        else:
            # TODO(ekarlso): Remove after verifying that there's actually a
            # context always set
            LOG.error(_LE('Missing context in request, please check.'))

        return flask.Response(status=status, headers=headers,
                              response=json.dumps(response))
