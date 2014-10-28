#!/usr/bin/env python
# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Author: liangxiaoping
#

import flask
from oslo.config import cfg


def factory(global_config, **local_conf):
    app = flask.Flask('chimera.api.versions')

    versions = []

    base = cfg.CONF['api'].api_base_uri.rstrip('/')

    def _version(version, status):
        versions.append({
            'id': 'v%s' % version,
            'status': status,
            'links': [{
                'href': base + '/v' + version,
                'rel': 'self'
            }]
        })

    if cfg.CONF['api'].enable_api_v1:
        _version('1', 'CURRENT')

    @app.route('/', methods=['GET'])
    def version_list():

        return flask.jsonify({
            "versions": {
                "values": versions
            }
        })

    return app
