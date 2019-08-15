# Copyright 2019 Splunk Inc. All rights reserved.

import json
import httplib
from service_manager.splunkd.kvstore import KVStoreManager
from rest_handler.exception import BaseRestException
import em_constants
import em_common
# Splunk packages
from splunk.appserver.mrsparkle.lib import i18n

_ = i18n.ugettext


class CloudConfigAlreadyExistsException(BaseRestException):
    def __init__(self, msg):
        super(CloudConfigAlreadyExistsException, self).__init__(httplib.BAD_REQUEST, msg)


class CloudConfigInternalException(BaseRestException):
    def __init__(self, msg):
        super(CloudConfigInternalException, self).__init__(httplib.INTERNAL_SERVER_ERROR, msg)


class CloudConfigNotFoundException(BaseRestException):
    def __init__(self, msg):
        super(CloudConfigNotFoundException, self).__init__(httplib.BAD_REQUEST, msg)


class CloudConfigArgValidationException(BaseRestException):
    def __init__(self, msg):
        super(CloudConfigArgValidationException, self).__init__(httplib.BAD_REQUEST, msg)


class EmCloudConfigsInterfaceImpl(object):

    def __init__(self, session_key, logger):
        self.session_key = session_key
        self.logger = logger
        self._setup_kv_store()

    def _setup_kv_store(self):
        # Sets up the Entity KV Store
        self.logger.info('Setting up KV Store...')
        self.cloud_configs_store = KVStoreManager(collection=em_constants.STORE_CLOUD_CONFIGS,
                                                  server_uri=em_common.get_server_uri(),
                                                  session_key=self.session_key,
                                                  app=em_constants.APP_NAME)

    def handle_get_cloud_config(self, request, cloud_config_id):
        selected_cloud_config = self._handle_list_key(cloud_config_id)
        if selected_cloud_config is None:
            raise CloudConfigNotFoundException(_('Cloud config with id %s cannot be found' % cloud_config_id))
        response = self._extract_relevant_fields(selected_cloud_config, {})
        return response

    def handle_list_cloud_configs(self, request):
        fields = request.query.get('fields', '')
        count = int(request.query.get('count', 0))
        offset = int(request.query.get('offset', 0))
        sort_key = request.query.get('sort_key', 'title')
        sort_dir = request.query.get('sort_dir', 'asc')

        kvstore_query = em_common.get_query_from_request_args(request.query.get('query', ''))

        query_params = self._build_params_object_for_load(kvstore_query)
        cloud_configs = self._handle_list_all(fields, query_params, count, offset, sort_key, sort_dir)

        response = map(lambda cloud_config: self._extract_relevant_fields(cloud_config, {}, fields), cloud_configs)
        return response

    def handle_create_cloud_config(self, request):
        cloud_config_id = request.data.get('id', '')
        cloud_config_name = request.data.get('account_name', '')
        cloud_provider = request.data.get('cloud_provider', '')
        if not cloud_config_name:
            raise CloudConfigArgValidationException(_('account_name is missing from request body.'))
        if not cloud_config_id:
            raise CloudConfigArgValidationException(_('id is missing from request body.'))
        if not cloud_provider:
            raise CloudConfigArgValidationException(_('cloud_provider is missing from request body.'))
        # Check if a cloud_config with this id exists
        existing_cloud_config = self._handle_list_key(cloud_config_id)
        if existing_cloud_config is not None:
            raise CloudConfigAlreadyExistsException(_('Cloud config id %s already exists' % cloud_config_id))

        self._check_cloud_config_title_validity(cloud_config_name)
        try:
            data = self._setup_data_payload(request)
            cloud_config = self.cloud_configs_store.create(cloud_config_id, data)
            response = self.handle_get_cloud_config(request, cloud_config['_key'])
            return response
        except Exception as e:
            self.logger.error('Failed to create cloud config - error: %s' % e)
            raise CloudConfigInternalException(_('Failed to create the cloud config %s.' % cloud_config_name))

    def handle_update_cloud_config(self, request, cloud_config_id):
        new_cloud_config_title = request.data.get('account_name', '')
        existing_cloud_config = self._handle_list_key(cloud_config_id)

        if existing_cloud_config is None:
            raise CloudConfigNotFoundException(_('Cannot modify a cloud config that does not exist'))
        else:
            # if request contains a account_name, validate it
            if new_cloud_config_title:
                self._check_cloud_config_title_validity(new_cloud_config_title, existing_cloud_config)
            try:
                data = self._setup_data_payload(request, existing_cloud_config)
                cloud_config = self.cloud_configs_store.update(cloud_config_id, data)
                response = self.handle_get_cloud_config(request, cloud_config['_key'])
                return response
            except Exception as e:
                self.logger.error('Failed to update cloud config - error: %s' % e)
                raise CloudConfigInternalException(_('Failed to update the cloud config %s.' % cloud_config_id))

    def handle_remove(self, request, cloud_config_id):
        existing_cloud_config = self._handle_list_key(cloud_config_id)
        # Make sure that the cloud config we're trying to edit exists
        if existing_cloud_config is None:
            raise CloudConfigNotFoundException(_('Cannot delete a cloud config that does not exist'))

        try:
            return self.cloud_configs_store.delete(cloud_config_id)
        except Exception as e:
            self.logger.error('Failed to remove cloud config - error: %s' % e)
            raise CloudConfigNotFoundException(_('Cannot find the cloud config with id %s' % cloud_config_id))

    def handle_bulk_delete_cloud_configs(self, request):
        kvstore_delete_query = em_common.get_query_from_request_args(request.query.get('delete_query', ''))
        """
        Example delete_query={"id": ["2", "3"]}
        * {"$or":... } is the format of supplied list of cloud configs
        * {} is the format to delete all the cloud configs
        """
        if not kvstore_delete_query:
            raise CloudConfigArgValidationException(_('Delete query can not be empty'))
        delete_query = {
            'query': kvstore_delete_query
        }
        self.logger.info('User triggered action "bulk_delete" on cloud_configs: %s' % kvstore_delete_query)
        try:
            return self.cloud_configs_store.bulk_delete(query=delete_query)
        except Exception:
            raise CloudConfigInternalException(_('Could not bulk delete cloud configs in the delete query'))

    def _check_cloud_config_title_validity(self, cloud_config_title, existing_cloud_config=None):
        query = {'account_name': cloud_config_title}
        if existing_cloud_config is not None:
            query['_key'] = {'$ne': existing_cloud_config['_key']}
        has_cloud_configs_with_title = len(self._handle_list_all('account_name',
                                                                 self._build_params_object_for_load(
                                                                     json.dumps(query)))) > 0
        if has_cloud_configs_with_title:
            raise CloudConfigAlreadyExistsException(_('%s already exists' % cloud_config_title))
        if '|' in cloud_config_title or '=' in cloud_config_title or cloud_config_title is '' or \
                cloud_config_title is None:
            raise CloudConfigArgValidationException(
                _('%s: cloud config name cannot contain | or = or left empty' % cloud_config_title)
            )

    def _setup_data_payload(self, request, existing_cloud_config=None):
        data = {}
        if existing_cloud_config:
            # this is an update request

            # cannot update the id for an existing cloud config, ignore request
            data['id'] = existing_cloud_config.get('id', '')

            # cannot update the cloud_provider for an existing cloud config, ignore request
            data['cloud_provider'] = existing_cloud_config.get('cloud_provider', '')

            # update following fields when request contains the field, else retain existing field value
            data['account_name'] = request.data.get('account_name', existing_cloud_config.get('account_name', ''))
            data['external_id'] = request.data.get('external_id', existing_cloud_config.get('external_id', ''))
            data['iam_arn'] = request.data.get('iam_arn', existing_cloud_config.get('iam_arn', ''))
            data['disabled'] = request.data.get('disabled', existing_cloud_config.get('disabled', 0))
            data['cw_metrics'] = request.data.get('cw_metrics', existing_cloud_config.get('cw_metrics', []))
            data['cw_logs'] = request.data.get('cw_logs', existing_cloud_config.get('cw_logs', []))
            data['cw_events'] = request.data.get('cw_events', existing_cloud_config.get('cw_events', []))
            data['sqs_names'] = request.data.get('sqs_names', existing_cloud_config.get('sqs_names', []))

        else:
            # this is a create request
            data['id'] = request.data.get('id', '')
            data['account_name'] = request.data.get('account_name', '')
            data['cloud_provider'] = request.data.get('cloud_provider', 'aws')
            data['external_id'] = request.data.get('external_id', '')
            data['iam_arn'] = request.data.get('iam_arn', '')
            data['disabled'] = request.data.get('disabled', 0)
            data['cw_metrics'] = request.data.get('cw_metrics', [])
            data['cw_logs'] = request.data.get('cw_logs', [])
            data['cw_events'] = request.data.get('cw_events', [])
            data['sqs_names'] = request.data.get('sqs_names', [])
        return data

    def _build_params_object_for_load(self, kvstore_query):
        query_params = {}
        if kvstore_query:
            query_params['query'] = kvstore_query
        return query_params

    def _handle_list_all(self, fields='', query_params={}, count=0, offset=0, sort_key='', sort_dir='asc'):
        sort = ''
        if sort_key:
            sort = '%s:%s' % (
                sort_key,
                1 if sort_dir == 'asc' else -1
            )
        try:
            return self.cloud_configs_store.load(count=count, offset=offset, fields=fields, sort=sort,
                                                 params=query_params)
        except Exception:
            raise CloudConfigInternalException(_('Cannot list all of the cloud configs saved'))

    def _handle_list_key(self, key):
        try:
            return self.cloud_configs_store.get(key)
        except Exception:
            raise CloudConfigNotFoundException(_('Cannot find the cloud config with id %(key)s'))

    def _extract_relevant_fields(self, cloud_config, response, fields=''):
        if cloud_config is not None:
            response['id'] = cloud_config.get('id', '')
            response['account_name'] = cloud_config.get('account_name', '')
            response['cloud_provider'] = cloud_config.get('cloud_provider', 'aws')
            response['external_id'] = cloud_config.get('external_id', '')
            response['iam_arn'] = cloud_config.get('iam_arn', '')
            response['disabled'] = int(cloud_config.get('disabled', 0))
            response['cw_metrics'] = cloud_config.get('cw_metrics', [])
            response['cw_logs'] = cloud_config.get('cw_logs', [])
            response['cw_events'] = cloud_config.get('cw_events', [])
            response['sqs_names'] = cloud_config.get('sqs_names', [])

        # Remove fields that are not required based on the input fields arg
        if fields:
            field_names = fields.split(',')
            return {k: v for (k, v) in response.items() if k in field_names}

        return response
