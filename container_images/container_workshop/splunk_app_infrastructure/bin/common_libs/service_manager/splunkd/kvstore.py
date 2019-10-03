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


class KVStoreManager(BaseSplunkdServiceManager):
    """
    KVStore access
    """

    logger_name = 'monitoring_kvstore_manager'

    DEFAULT_BATCH_SIZE = 200

    def __init__(self, collection, server_uri,
                 session_key, app, owner='nobody'):
        """
        Return KVStore Manager object
        """
        self.collection = collection
        super(KVStoreManager, self).__init__(session_key, server_uri, app, owner)

    def _build_uri(self, name=None, query=None):
        """
        Create uri for kvstore request

        :param name: name after collection, usually _key
        :param query: query params
        :return: uri for kvstore request
        """
        qs = dict(output_mode='json')
        base_uri = self.base_uri()
        if query is not None:
            qs.update(query)
        if name is not None:
            return '%s/storage/collections/data/%s/%s?%s' % (
                base_uri, urllib.quote(self.collection), urllib.quote(name), urllib.urlencode(qs))
        else:
            return '%s/storage/collections/data/%s?%s' % (
                base_uri, urllib.quote(self.collection), urllib.urlencode(qs))

    def _build_req(self, method, data=None, name=None, query=None):
        """
        Build request object

        :param method: HTTP Method
        :param data: body data
        :param name: key,etc.
        :param query: query params
        :return: request object
        """
        h = {'Authorization': 'Splunk %s' % self.session_key}
        if h is not None:
            h['Content-Type'] = 'application/json'
        req = urllib2.Request(self._build_uri(name, query=query), json.dumps(data), h)
        req.get_method = lambda: method
        return req

    def load(self, count=0, offset=0, fields='', sort='', params={}):
        """
        Load records with limit

        :param count: limitation
        :return: dict of records
        """
        req = self._build_req('GET', query=dict(limit=count, skip=offset, fields=fields, sort=sort, **params))
        res = urllib2.urlopen(req)
        return json.loads(res.read())

    def load_all(self, count=0, fields='', sort='', params={}):
        """
        Load all records by calling load in batch
        :param count:batch size
        :return: dict of records
        """
        max_batch_count = count
        current_number = 0
        total_count = 0
        results = []
        while True:
            result = self.load(count=max_batch_count, offset=total_count, fields=fields, sort=sort, params=params)
            results.extend(result)
            current_number = len(result)
            total_count += current_number
            if current_number < max_batch_count:
                break
        return results

    def get(self, key):
        """
        Get records by _key

        :param key: record's key
        :return: dict of records
        """
        req = self._build_req('GET', name=key)
        try:
            res = urllib2.urlopen(req)
            return json.loads(res.read())
        except urllib2.HTTPError as e:
            if e.code == httplib.NOT_FOUND:
                return None
            else:
                raise e

    def update(self, key, data):
        """
        Update record by _key

        :param key: record's key
        :param data: body data dict
        :return: result object
        """
        req = self._build_req('PUT', name=key, data=data)
        res = urllib2.urlopen(req)
        return json.loads(res.read())

    def create(self, key, data):
        """
        Create record by _key

        :param key: record's key
        :param data: body data dict
        :return: result object
        """
        data.update({'_key': key})
        req = self._build_req('POST', data=data)
        res = urllib2.urlopen(req)
        return json.loads(res.read())

    def upsert(self, key, data):
        """
        Insert if it doesn't exist
        Update if it exists
        """
        r = self.get(key)
        if r is None:
            return self.create(key, data)
        else:
            return self.update(key, data)

    def delete(self, key):
        """
        Delete record by _key

        :param key: record's key
        :return: void
        """
        req = self._build_req('DELETE', name=key)
        urllib2.urlopen(req)

    def bulk_delete(self, query):
        """
        Bulk delete operation

        :param query: query
        :return: void
        """
        if not query:
            raise ValueError("Query is required for bulk_delete")
        try:
            req = self._build_req('DELETE', query=query)
            urllib2.urlopen(req)
        except urllib2.HTTPError as e:
            raise e

    def batch_save(self, data):
        """
        Perform multiple save operations in a batch
        """
        self.logger.debug('Batch saving data: {}'.format(data))
        if not data:
            self.logger.warning("Batch saving skipped: Batch is empty.")
        batches = (data[x:x + KVStoreManager.DEFAULT_BATCH_SIZE]
                   for x in xrange(0, len(data), KVStoreManager.DEFAULT_BATCH_SIZE))
        for batch in batches:
            try:
                req = self._build_req('POST', name='batch_save', data=batch)
                urllib2.urlopen(req)
            except urllib2.HTTPError as e:
                self.logger.error("Batching saving failed: %s - %s", e, e.read())
                raise e
