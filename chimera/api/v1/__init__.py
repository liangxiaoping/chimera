#!/usr/bin/env python
# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Author: liangxiaoping
#

import flask
from stevedore import extension
from stevedore import named
from werkzeug import exceptions as wexceptions
from werkzeug import wrappers
from werkzeug.routing import BaseConverter
from werkzeug.routing import ValidationError
from oslo.config import cfg
from oslo.serialization import jsonutils

from chimera.openstack.common import log as logging
from chimera import exceptions
from chimera import utils


LOG = logging.getLogger(__name__)

cfg.CONF.register_opts([
    cfg.ListOpt('enabled-extensions-v1', default=[],
                help='Enabled API Extensions'),
], group='api')


class ChimeraRequest(flask.Request, wrappers.AcceptMixin,
                       wrappers.CommonRequestDescriptorsMixin):
    def __init__(self, *args, **kwargs):
        super(ChimeraRequest, self).__init__(*args, **kwargs)

        self._validate_content_type()
        self._validate_accept()

    def _validate_content_type(self):
        if (self.method in ['POST', 'PUT', 'PATCH']
                and self.mimetype != 'application/json'):

            msg = 'Unsupported Content-Type: %s' % self.mimetype
            raise exceptions.UnsupportedContentType(msg)

    def _validate_accept(self):
        if 'accept' in self.headers and not self.accept_mimetypes.accept_json:
            msg = 'Unsupported Accept: %s' % self.accept_mimetypes
            raise exceptions.UnsupportedAccept(msg)


class JSONEncoder(flask.json.JSONEncoder):
    @staticmethod
    def default(o):
        return jsonutils.to_primitive(o)


def factory(global_config, **local_conf):
    if not cfg.CONF['api'].enable_api_v1:
        def disabled_app(environ, start_response):
            status = '404 Not Found'
            start_response(status, [])
            return []

        return disabled_app

    app = flask.Flask('chimera.api.v1')
    app.request_class = ChimeraRequest
    app.json_encoder = JSONEncoder
    app.config.update(
        PROPAGATE_EXCEPTIONS=True
    )

    # Install custom converters (URL param varidators)
    app.url_map.converters['uuid'] = UUIDConverter

    # Ensure all error responses are JSON
    def _json_error(ex):
        code = ex.code if isinstance(ex, wexceptions.HTTPException) else 500

        response = {
            'code': code
        }

        if code == 405:
            response['type'] = 'invalid_method'

        response = flask.jsonify(**response)
        response.status_code = code

        return response

    for code in wexceptions.default_exceptions.iterkeys():
        app.error_handler_spec[None][code] = _json_error

    # TODO(kiall): Ideally, we want to make use of the Plugin class here.
    #              This works for the moment though.
    def _register_blueprint(ext):
        app.register_blueprint(ext.plugin)

    # Add all in-built APIs
    mgr = extension.ExtensionManager('chimera.api.v1')
    mgr.map(_register_blueprint)

    # Add any (enabled) optional extensions
    extensions = cfg.CONF['api'].enabled_extensions_v1

    if len(extensions) > 0:
        extmgr = named.NamedExtensionManager('chimera.api.v1.extensions',
                                             names=extensions)
        extmgr.map(_register_blueprint)

    return app


class UUIDConverter(BaseConverter):
    """Validates UUID URL paramaters"""

    def to_python(self, value):
        if not utils.is_uuid_like(value):
            raise ValidationError()

        return value

    def to_url(self, value):
        return str(value)


def load_values(request, valid_keys):
    """Load valid atributes from request"""
    result = {}
    error_keys = []
    values = request.json
    for k in values:
        if k in valid_keys:
            result[k] = values[k]
        else:
            error_keys.append(k)

    if error_keys:
        error_msg = 'Provided object does not match schema. Keys {0} are not \
                     valid in the request body', error_keys
        raise exceptions.InvalidObject(error_msg)

    return result
