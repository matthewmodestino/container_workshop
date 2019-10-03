# Copyright 2016 Splunk Inc. All rights reserved.
# Environment configuration
# N/A
# Standard Python Libraries
import json
# Third-Party Libraries
import urllib
import urllib2
import httplib
from . import BaseSplunkdServiceManager


class LicenseManager(BaseSplunkdServiceManager):
    """
    License access
    """

    logger_name = 'monitoring_license_manager'

    def __init__(self, server_uri, session_key, app):
        """
        Return License Manager object
        """
        super(LicenseManager, self).__init__(session_key, server_uri, app)

    def base_uri(self):
        return '{server_uri}/services/licenser/licenses'.format(
            server_uri=self.server_uri,
        )

    def _build_uri(self):
        """
        Create uri for license request
        return: uri for license request
        """
        qs = dict(output_mode='json')
        base_uri = self.base_uri()
        return '%s?%s' % (base_uri, urllib.urlencode(qs))

    def _build_send_req(self, url, method='GET', data=None):
        h = {
            'Authorization': 'Splunk %s' % self.session_key,
            'Content-Type': 'application/json'
        }
        try:
            request = urllib2.Request(url, headers=h)
            request.get_method = lambda: method
            response = urllib2.urlopen(request)
            return json.loads(response.read())
        except urllib2.HTTPError as e:
            if e.code == httplib.NOT_FOUND:
                return None
            else:
                raise e

    def load(self):
        url = self._build_uri()
        response = self._build_send_req(url, 'GET')
        return response
