#!/usr/bin/env python
# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Author: liangxiaoping
#

import flask
from oslo import messaging

from chimera.openstack.common import log as logging
from chimera import rpc


LOG = logging.getLogger(__name__)
blueprint = flask.Blueprint('diagnostics', __name__)


@blueprint.route('/diagnostics/ping/<topic>/<host>', methods=['GET'])
def ping_host(topic, host):
    context = flask.request.environ.get('context')

    client = rpc.get_client(messaging.Target(topic=topic))
    cctxt = client.prepare(server=host, timeout=10)

    pong = cctxt.call(context, 'ping')

    return flask.jsonify(pong)
