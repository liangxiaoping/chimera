# Copyright 2012 Managed I.T.
#
# Author: Kiall Mac Innes <kiall@managedit.ie>
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


class Base(Exception):
    error_code = 500
    error_type = None
    error_message = None
    errors = None

    def __init__(self, *args, **kwargs):
        self.errors = kwargs.pop('errors', None)

        super(Base, self).__init__(*args, **kwargs)

        if len(args) > 0 and isinstance(args[0], basestring):
            self.error_message = args[0]


class Backend(Exception):
    pass

class NotImplemented(Base, NotImplementedError):
    pass


class ConfigurationError(Base):
    error_type = 'configuration_error'


class UnknownFailure(Base):
    error_code = 500
    error_type = 'unknown_failure'


class CommunicationFailure(Base):
    error_code = 504
    error_type = 'communication_failure'


class NoServersConfigured(ConfigurationError):
    error_code = 500
    error_type = 'no_servers_configured'



class InvalidObject(Base):
    error_code = 400
    error_type = 'invalid_object'


class BadRequest(Base):
    error_code = 400
    error_type = 'bad_request'


class InvalidUUID(BadRequest):
    error_type = 'invalid_uuid'


class NetworkEndpointNotFound(BadRequest):
    error_type = 'no_endpoint'
    error_code = 403


class MarkerNotFound(BadRequest):
    error_type = 'marker_not_found'


class ValueError(BadRequest):
    error_type = 'value_error'


class InvalidMarker(BadRequest):
    error_type = 'invalid_marker'


class InvalidSortDir(BadRequest):
    error_type = 'invalid_sort_dir'


class InvalidLimit(BadRequest):
    error_type = 'invalid_limit'


class InvalidSortKey(BadRequest):
    error_type = 'invalid_sort_key'


class InvalidJson(BadRequest):
    error_type = 'invalid_json'


class InvalidOperation(BadRequest):
    error_code = 400
    error_type = 'invalid_operation'


class UnsupportedAccept(BadRequest):
    error_code = 406
    error_type = 'unsupported_accept'


class UnsupportedContentType(BadRequest):
    error_code = 415
    error_type = 'unsupported_content_type'


class Forbidden(Base):
    error_code = 403
    error_type = 'forbidden'
    expected = True


class Duplicate(Base):
    expected = True
    error_code = 409
    error_type = 'duplicate'


class MethodNotAllowed(Base):
    expected = True
    error_code = 405
    error_type = 'method_not_allowed'

    
class NotFound(Base):
    expected = True
    error_code = 404
    error_type = 'not_found'

    
class ResourceNotFound(NotFound):
    # TODO(kiall): Should this be extending NotFound??
    pass
