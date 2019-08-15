import urllib
import urllib2
import httplib
import json
from . import BaseSplunkdServiceManager, SplunkdServiceManagerException


class SavedsearchInternalException(SplunkdServiceManagerException):
    def __init__(self, msg):
        super(SavedsearchInternalException, self).__init__(msg)


class SavedSearchManager(BaseSplunkdServiceManager):

    logger_name = 'monitoring_savedsearch_manager'

    def __init__(self, session_key, server_uri, app, owner='nobody'):
        super(SavedSearchManager, self).__init__(session_key, server_uri, app, owner)

    def _build_uri(self, name='', query_params=None):
        # need to set user to 'nobody' because creating savedsearch
        # with wildcard user or app name is not allowed
        url_template = '{base_uri}/saved/searches/{name}?{query_params}'
        query_params = {} if not query_params else query_params
        query_params.update({
            'output_mode': 'json'
        })
        base_uri = self.base_uri()
        url = url_template.format(base_uri=base_uri,
                                  name=urllib.quote(name),
                                  query_params=urllib.urlencode(query_params))
        return url

    def _build_send_req(self, url, method='GET', data=None):
        h = {
            'Authorization': 'Splunk %s' % self.session_key,
            'Content-Type': 'application/json'
        }
        try:
            encoded_data = urllib.urlencode(data) if data else None
            # Note: cannot use json.dumps on data because splunk savedsearch REST doesn't like it
            request = urllib2.Request(url, data=encoded_data, headers=h)
            request.get_method = lambda: method
            response = urllib2.urlopen(request)
            return json.loads(response.read())
        except urllib2.HTTPError as e:
            if e.code == httplib.NOT_FOUND:
                return None
            else:
                raise SavedsearchInternalException(e)

    def load(self, count=-1, offset=0, search=None):
        params = dict(
            count=count,
            offset=offset
        )
        if search:
            params.update(search=search)
        url = self._build_uri(query_params=params)
        response = self._build_send_req(url, 'GET')
        return response

    def get(self, name):
        url = self._build_uri(name)
        response = self._build_send_req(url, 'GET')
        return response

    def create(self, data):
        url = self._build_uri()
        response = self._build_send_req(url, 'POST', data=data)
        return response

    def update(self, name, data):
        url = self._build_uri(name)
        response = self._build_send_req(url, 'POST', data=data)
        return response

    def delete(self, name):
        url = self._build_uri(name)
        response = self._build_send_req(url, 'DELETE')
        return response

    def bulk_delete(self, savedsearch_query):
        """
        Yeah, I know this doesn't exactly make use of a more efficient way, but let's
        abstract out the bulk logic here

        There is no bulk delete endpoint for saved searches, so the only way we can do this is
        make 1 call and delete each search individually.
        """
        search_stanza = ' OR '.join(savedsearch_query)
        query_params = {
            'output_mode': 'json',
            'search': search_stanza,
            'count': -1
        }
        fetch_searches_url = self._build_uri(query_params=query_params, name='')
        associated_saved_searches = self._build_send_req(fetch_searches_url, 'GET')
        searches = associated_saved_searches['entry']
        for search in searches:
            search_name = search.get('name')
            delete_search_url = self._build_uri(name=search_name)
            self.logger.info('Deleting the saved search %s...' % search_name)
            self._build_send_req(delete_search_url, 'DELETE')
