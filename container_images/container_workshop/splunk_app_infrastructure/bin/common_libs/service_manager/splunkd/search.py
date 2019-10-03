# Copyright 2016 Splunk Inc. All rights reserved.
# Environment configuration
# N/A
# Standard Python Libraries
import json
# Third-Party Libraries
import splunk.rest as rest
# Custom Libraries
# N/A
from . import BaseSplunkdServiceManager


class SearchManager(BaseSplunkdServiceManager):
    """
    Search REST Endpoint service
    """

    logger_name = 'monitoring_search_manager'

    def __init__(self,
                 server_uri,
                 session_key,
                 app,
                 owner='nobody'):
        """
        Return object of SearchManager service
        """
        super(SearchManager, self).__init__(session_key, server_uri, app, owner)

    def _build_uri(self):
        """
        :return: uri
        """
        base_uri = self.base_uri()
        return '%s/search/jobs' % (base_uri)

    def search(self,
               spl='',
               earliest='-24h',
               latest='now',
               count=0,
               exec_mode='oneshot',
               output_mode='json'):
        """
        Search and get results
        API reference see: https://docs.splunk.com/Documentation/Splunk/7.2.1/RESTREF/RESTsearch#search.2Fjobs

        :param spl: SPL query
        :param earliest: earliest time
        :param latest: latest time
        :param count: limit number of result
        :param exec_mode: exec mode of the search, possible values are 'oneshot' (default), 'blocking', 'normal'
        :param output_mode: output format of response, possible values are 'json' (default), 'xml'
        :return: result object
        """
        data = {
            'search': spl,
            'output_mode': output_mode,
            'exec_mode': exec_mode,
            'earliest_time': earliest,
            'latest_time': latest,
            'count': count,
        }
        self.logger.info('app: %s - execute: %s' % (self.app, data))
        response, content = rest.simpleRequest(
            self._build_uri(),
            sessionKey=self.session_key,
            method="POST",
            postargs=data)

        result = json.loads(content)
        return result
