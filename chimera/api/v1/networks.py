#!/usr/bin/env python
# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Author: liangxiaoping
#
import flask

from chimera.openstack.common import log as logging
from chimera.api import get_task_api


LOG = logging.getLogger(__name__)
blueprint = flask.Blueprint('networks', __name__)


@blueprint.route('/networks/ping', methods=['GET'])
def ping():
    context = flask.request.environ.get('context')
    pong = get_task_api().ping(context)
    
    return flask.jsonify(pong=pong)


@blueprint.route('/networks', methods=['GET'])
def get_networks():
    context = flask.request.environ.get('context')

    return flask.jsonify(code=0)