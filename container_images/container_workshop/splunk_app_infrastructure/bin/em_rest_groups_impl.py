# Copyright 2019 Splunk Inc. All rights reserved.

import json
import httplib
from service_manager.splunkd.kvstore import KVStoreManager
from service_manager.splunkd.savedsearch import SavedSearchManager
from rest_handler.exception import BaseRestException
import em_constants
import em_common
from em_search_manager import EMSearchManager
from em_correlation_filters import serialize, create_group_log_filter
from em_model_group import EMGroup
# Splunk packages
from splunk.appserver.mrsparkle.lib import i18n

_ = i18n.ugettext


class GroupAlreadyExistsException(BaseRestException):
    def __init__(self, msg):
        super(GroupAlreadyExistsException, self).__init__(httplib.BAD_REQUEST, msg)


class GroupInternalException(BaseRestException):
    def __init__(self, msg):
        super(GroupInternalException, self).__init__(httplib.INTERNAL_SERVER_ERROR, msg)


class GroupNotFoundException(BaseRestException):
    def __init__(self, msg):
        super(GroupNotFoundException, self).__init__(httplib.BAD_REQUEST, msg)


class GroupArgValidationException(BaseRestException):
    def __init__(self, msg):
        super(GroupArgValidationException, self).__init__(httplib.BAD_REQUEST, msg)


class EmGroupsInterfaceImpl(object):

    def __init__(self, session_key, logger):
        self.session_key = session_key
        self.logger = logger
        self._setup_kv_store()
        self._setup_savedsearch_manager()
        self._setup_search_manager()

    def _setup_kv_store(self):
        # Sets up the Entity KV Store
        self.logger.info('Setting up KV Store...')
        self.groups_store = KVStoreManager(collection=em_constants.STORE_GROUPS,
                                           server_uri=em_common.get_server_uri(),
                                           session_key=self.session_key,
                                           app=em_constants.APP_NAME)
        self.entity_store = KVStoreManager(collection=em_constants.STORE_ENTITIES,
                                           server_uri=em_common.get_server_uri(),
                                           session_key=self.session_key,
                                           app=em_constants.APP_NAME)
        self.collector_store = KVStoreManager(collection=em_constants.STORE_COLLECTORS,
                                              server_uri=em_common.get_server_uri(),
                                              session_key=self.session_key,
                                              app=em_constants.APP_NAME)

    def _setup_savedsearch_manager(self):
        self.logger.info('Setting up Savedsearch manager...')
        self.savedsearch_manager = SavedSearchManager(server_uri=em_common.get_server_uri(),
                                                      session_key=self.session_key,
                                                      app=em_constants.APP_NAME)

    def _setup_search_manager(self):
        self.logger.info('Setting up search manager...')
        self.search_manager = EMSearchManager(em_common.get_server_uri(), self.session_key, em_constants.APP_NAME)

    def handle_get_group(self, request, group_id):
        selected_group = self._handle_list_key(group_id)
        if selected_group is None:
            raise GroupNotFoundException(_('Group with id %(group_id)s cannot be found'))
        group_entity_info = self._get_entities_and_dimensions_in_single_group(group_id)
        collector_names_with_entities = self._get_collector_names_and_entities_in_group(group_id)
        response = self._extract_relevant_fields(
            selected_group,
            {},
            collector_entities_match=collector_names_with_entities,
            group_entities=group_entity_info
        )
        return response

    def handle_list_groups(self, request):
        fields = request.query.get('fields', '')
        count = int(request.query.get('count', 0))
        offset = int(request.query.get('offset', 0))
        filter_entity_ids = request.query.get('filter_by_entity_ids', '')
        filter_entity_names = request.query.get('filter_by_entity_names', '')
        sort_key = request.query.get('sort_key', 'title')
        sort_dir = request.query.get('sort_dir', 'asc')

        kvstore_query = em_common.get_query_from_request_args(request.query.get('query', ''))

        group_entities_count = {}
        groups = []
        # If entity ids or entity names are provided, search groups using whichever (names or ids) is provided.
        # group_entities_count is the count of active, inactive, and disabled entities
        # group_keys is the keyset of group_entities_count.
        if filter_entity_ids != '' or filter_entity_names != '':
            if filter_entity_ids != '':
                group_keys, group_entities_count = self._get_group_filtered_by_entity(
                    EMSearchManager.BY_ENTITY_IDS, filter_entity_ids
                )
            else:
                group_keys, group_entities_count = self._get_group_filtered_by_entity(
                    EMSearchManager.BY_ENTITY_NAMES, filter_entity_names
                )

            if group_keys:
                kvstore_query = {'$or': [{'_key': group_key} for group_key in group_keys]}
                query_params = self._build_params_object_for_load(json.dumps(kvstore_query))
                groups = self._handle_list_all(fields, query_params, count, offset, sort_key, sort_dir)
        else:
            query_params = self._build_params_object_for_load(kvstore_query)
            groups = self._handle_list_all(fields, query_params, count, offset, sort_key, sort_dir)

        response = map(lambda group: self._extract_relevant_fields(group, {}), groups)

        return response

    def _get_group_entities_count(self, request):
        # This get called when create and update the group
        filters = EMGroup.convert_filter_string_to_dictionary(request.data.get('filter'), append_key='dimensions.')
        query = {'query': em_common.get_query_from_request_args(json.dumps(filters))}
        entities = self.entity_store.load_all(
                 count=em_constants.KVSTORE_SINGLE_FETCH_LIMIT, fields='_key', params=query
            )
        return len(entities)

    def handle_create_group(self, request):
        # Get the name of the group the user wants to create
        group_id = request.data.get('name', '')
        group_title = request.data.get('title', '')
        if not group_id:
            raise GroupArgValidationException(_('id is missing from request body.'))
        existing_group = self._handle_list_key(group_id)
        if existing_group is not None:
            raise GroupAlreadyExistsException(_('Group id %(group_id)s already exists'))
        self._check_group_title_validity(group_title)
        try:
            data = self._setup_data_payload(request)
            group = self.groups_store.create(group_id, data)
            response = self.handle_get_group(request, group['_key'])
            return response
        except Exception as e:
            self.logger.error('Failed to create group - error: %s' % e)
            raise GroupInternalException(_('Failed to create the group %(group_title)s.'))

    def handle_update_group(self, request, group_id):
        group_title = request.data.get('title', '')
        existing_group = self._handle_list_key(group_id)
        # Make sure that the group we're trying to edit exists
        if existing_group is None:
            raise GroupNotFoundException(_('Cannot modify a group that does not exist'))
        else:
            self._check_group_title_validity(group_title, existing_group)
            try:
                data = self._setup_data_payload(request)
                group = self.groups_store.update(group_id, data)
                response = self.handle_get_group(request, group['_key'])
                return response
            except Exception as e:
                self.logger.error('Failed to update group - error: %s' % e)
                raise GroupInternalException(_('Failed to update the group %(group_title)s.'))

    def handle_remove(self, request, group_id):
        # Get the name of the group the user wants to fetch
        existing_group = self._handle_list_key(group_id)
        # Make sure that the group we're trying to edit exists
        if existing_group is None:
            raise GroupNotFoundException(_('Cannot delete a group that does not exist'))

        try:
            return self.groups_store.delete(group_id)
        except Exception as e:
            self.logger.error('Failed to remove group - error: %s' % e)
            raise GroupNotFoundException(_('Cannot find the group with id %(group_id)s'))

    def handle_bulk_delete_groups(self, request):
        """
        Under most scenarios, we delete either a list of groups supplied to
        the endpoint or delete a search. In the edge case that we want to
        delete all groups in a search except certain groups, we supply
        both a list of groups and a search, and we add the "invert_delete"
        flag which tells us to *not* delete the list of groups.
        """
        invert_flag = int(request.query.get('invert_delete', ''))
        filter_delete_query = em_common.get_query_from_request_args(
            request.query.get('query', ''))
        kvstore_delete_query = em_common.get_query_from_request_args(
            request.query.get('delete_query', ''))
        """
        Bulk deletion of some, but not all, groups
        * {"$or":... } is the format of supplied list of groups
        * {"foo":... } is the format of a supplied filter
        * {} is the format of no filter or list supplied
        """

        if invert_flag and kvstore_delete_query.startswith("{\"$or\""):
            kvstore_delete_query = em_common.negate_special_mongo_query(kvstore_delete_query)
            kvstore_delete_query = "{\"$and\": [%s, %s]}" % (filter_delete_query, kvstore_delete_query)
        if not kvstore_delete_query:
            raise GroupArgValidationException(_('Delete query can not be empty'))
        delete_query = {
            'query': kvstore_delete_query
        }
        groups_deleted_list = self._handle_list_all(fields='_key',
                                                    query_params=delete_query)
        savedsearch_delete_query = em_common.get_list_of_admin_managedby(
            groups_deleted_list, em_constants.APP_NAME)
        self.logger.info('User triggered action "bulk_delete" on groups: %s' % kvstore_delete_query)
        self.groups_store.bulk_delete(query=delete_query)
        self.savedsearch_manager.bulk_delete(savedsearch_query=savedsearch_delete_query)

    def handle_metadata(self, request):
        """
        Return metadata about the groups
        """
        query = {'query': em_common.get_query_from_request_args(request.query.get('query', ''))}
        total_groups = self._handle_list_all(fields='title', query_params=query, count=0, offset=0)
        response = {
            'groups': {
                'titles': list({group['title'] for group in total_groups}),
            }
        }
        return response

    def handle_count(self, request):
        """
        Return count about the groups
        """
        query = {'query': em_common.get_query_from_request_args(request.query.get('query', ''))}
        groups_with_filters = self._handle_list_all(fields='title', query_params=query, count=0, offset=0)
        group_count_filter = len(groups_with_filters)
        response = {
                'total_count': group_count_filter,
        }
        return response

    def _check_group_title_validity(self, group_title, existing_group=None):
        query = {'title': group_title}
        if existing_group is not None:
            query['_key'] = {'$ne': existing_group['_key']}
        has_groups_with_title = len(self._handle_list_all('_id',
                                                          self._build_params_object_for_load(json.dumps(query)))) > 0
        if has_groups_with_title:
            raise GroupAlreadyExistsException(_('%(group_title)s already exists'))
        if '|' in group_title or '=' in group_title or group_title is '' or group_title is None:
            raise GroupArgValidationException(
                _('%(group_title)s: group name cannot contain | or = or left empty')
            )

    def _setup_data_payload(self, request):
        data = {}
        data['name'] = request.data.get('name', '')
        data['title'] = request.data.get('title', '')
        data['filter'] = request.data.get('filter', '')
        data['entities_count'] = self._get_group_entities_count(request)
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
            return self.groups_store.load(count=count, offset=offset, fields=fields, sort=sort, params=query_params)
        except Exception:
            raise GroupInternalException(_('Cannot list all of the groups saved'))

    def _handle_list_key(self, key):
        try:
            return self.groups_store.get(key)
        except Exception:
            raise GroupNotFoundException(_('Cannot find the group with id %(group_id)s'))

    def _get_entities_and_dimensions_in_single_group(self, group_name):
        try:
            return self.search_manager.get_entities_and_dimensions_within_selected_group(group_name)
        except Exception:
            raise GroupInternalException(_("Cannot get entities within group '%(group_name)s'"))

    def _get_collector_names_and_entities_in_group(self, group_name):
        try:
            return self.search_manager.get_entities_and_collector_names_by_group(group_name)
        except Exception:
            raise GroupInternalException(
                _("Cannot get collector or entities info from group '%(group_name)s'"))

    def _extract_relevant_fields(self, group, response, collector_entities_match=None, group_entities=None):
        if group is not None:
            response['name'] = group.get('name', '')
            response['filter'] = group.get('filter', '')
            response['title'] = group.get('title', '')
            response['entities_count'] = int(group.get('entities_count', 0))
            response['active_entities_count'] = int(group.get('active_entities', 0))
            response['inactive_entities_count'] = int(group.get('inactive_entities', 0))
            # Currently no way to disable entities, keep here for future reference
            response['disabled_entities_count'] = group.get('disabled_entities', 0)
            if group_entities:
                entity_state_info = group_entities.get(group.get('_key', ''), {})
                response['entities_count'] = entity_state_info.get('count', 0)
                response['inactive_entities_count'] = entity_state_info.get('inactive', 0)
                response['active_entities_count'] = entity_state_info.get('active', 0)
                if 'entities_mapping' in entity_state_info:
                    response['entities_in_group'] = json.dumps(entity_state_info.get('entities_mapping', {}))

            if collector_entities_match:
                collector_configs = self._handle_list_allcollectorconfigs(collector_entities_match.keys())
                group_logs_filter = create_group_log_filter(collector_entities_match, collector_configs)
                response['log_search'] = serialize(group_logs_filter) if group_logs_filter else None
        return response

    def _handle_list_allcollectorconfigs(self, collector_names, fields='', count=0, offset=0):
        try:
            kvstore_query = {'$or': [{'_key': collector_name} for collector_name in collector_names]}
            query_params = self._build_params_object_for_load(json.dumps(kvstore_query))
            return self.collector_store.load(count, offset, fields, params=query_params)
        except Exception as e:
            self.logger.error('Cannot list collector configs: %s' % e.message)
            raise GroupInternalException(_('Cannot list collector configs'))

    def _get_group_filtered_by_entity(self, criteria=EMSearchManager.BY_ENTITY_IDS, entity_info=None):
        if criteria != EMSearchManager.BY_ENTITY_IDS:
            criteria = EMSearchManager.BY_ENTITY_NAMES

        filter_search = self.search_manager.filter_groups_by(criteria)

        try:
            entity_info_list = map(lambda e: e.strip(), entity_info.split(','))
            groups_with_count = filter_search(entity_info_list)
            group_keys = groups_with_count.keys()
            return group_keys, groups_with_count
        except Exception:
            raise GroupInternalException(
                _('Cannot get matching groups with given entity information')
            )
