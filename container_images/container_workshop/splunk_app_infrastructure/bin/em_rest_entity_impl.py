from splunk.util import normalizeBoolean
import em_declare  # noqa
from service_manager.splunkd.kvstore import KVStoreManager
from service_manager.splunkd.savedsearch import SavedSearchManager
from rest_handler.exception import BaseRestException
import em_constants
import em_common
from em_search_manager import EMSearchManager
from em_common import get_locale_specific_display_names
from em_correlation_filters import serialize, create_entity_log_filter
import json
import math
import time
import httplib

# Splunk packages
from splunk.appserver.mrsparkle.lib import i18n

_ = i18n.ugettext


class EntityAlreadyExistsException(BaseRestException):
    def __init__(self, msg):
        super(EntityAlreadyExistsException, self).__init__(httplib.BAD_REQUEST, msg)


class EntityInternalException(BaseRestException):
    def __init__(self, msg):
        super(EntityInternalException, self).__init__(httplib.INTERNAL_SERVER_ERROR, msg)


class EntityNotFoundException(BaseRestException):
    def __init__(self, msg):
        super(EntityNotFoundException, self).__init__(httplib.BAD_REQUEST, msg)


class EntityArgValidationException(BaseRestException):
    def __init__(self, msg):
        super(EntityArgValidationException, self).__init__(httplib.BAD_REQUEST, msg)


class EmEntityInterfaceImpl(object):
    """The Entity Interface that allows CRUD operations on entities."""
    VALID_ENTITY_STATES = ['active', 'inactive', 'disabled']
    DIMENSION_TYPES = ['informational_dimensions', 'identifier_dimensions']

    def __init__(self, session_key, logger):
        self.session_key = session_key
        self.logger = logger
        self._setup_kv_store()
        self._setup_savedsearch_manager()
        self._setup_search_manager()

    def _setup_kv_store(self):
        # Sets up the Entity KV Store
        self.logger.info('Setting up KV Store...')
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

    def handle_list_entities(self, request):

        count = request.query.get('count', 0)
        offset = request.query.get('offset', 0)
        display_name_locale = request.query.get('display_name_locale', 'en-us')
        sort_key = request.query.get('sort_key', '')
        sort_dir = request.query.get('sort_dir', 'asc')
        # Make sure that if informational or identifier dimensions requested, to also request
        # "dimensions" to KV Store
        fields = request.query.get('fields', '')
        if fields:
            fields = self._update_requested_fields(fields)
        # get collectors information
        collector_configs = self._handle_list_collector_configs()
        # build kvstore query
        kvstore_query = em_common.get_query_from_request_args(request.query.get('query', ''))
        query_params = {'query': kvstore_query}
        all_entities = self._handle_list_all(fields, query_params, count, offset, sort_key, sort_dir)
        # build response
        response = map(lambda entity: self._build_entity_response(entity, collector_configs, display_name_locale),
                       all_entities)
        return response

    def handle_get_entity(self, request, entity_id):
        selected_entity = self._handle_list_key(entity_id)
        if selected_entity is None:
            raise EntityNotFoundException(_('Entity with id %(entity_id)s not found.'))
        collector_configs = self._handle_list_collector_configs()
        display_name_locale = request.query.get('display_name_locale', 'en-us')
        response = self._build_entity_response(selected_entity, collector_configs, display_name_locale)
        return response

    def handle_create_entity(self, request):
        entity_id = request.data.get('name')
        if not entity_id:
            raise EntityArgValidationException(_('id is missing from request body.'))
        existing_entity = self.entity_store.get(entity_id)
        if existing_entity is not None:
            raise EntityAlreadyExistsException(_('Entity with id %(entity_id)s already exists.'))
        # process dimension information
        identifier = request.data.get('identifier_dimensions', '[]')
        informational = request.data.get('informational_dimensions', '[]')
        dimensions = request.data.get('dimensions', '{}')
        dimensions, informational_dimensions, identifier_dimensions = \
            self._validate_dimension_json(identifier, informational, dimensions)
        self._validate_dimension_exists(dimensions, informational_dimensions)
        self._validate_dimension_exists(dimensions, identifier_dimensions)
        # build data payload
        data_payload = {}
        entity_state = request.data.get('state', 'disabled')
        self._validate_entity_state(entity_state)
        data_payload['state'] = entity_state
        data_payload['title'] = request.data.get('title', '')
        data_payload['identifier_dimensions'] = identifier_dimensions
        data_payload['informational_dimensions'] = informational_dimensions
        data_payload['dimensions'] = dimensions
        data_payload['imported_date'] = time.time()
        # Time created is the same as time updated for a new entity
        data_payload['updated_date'] = data_payload['imported_date']
        try:
            return self.entity_store.create(entity_id, data_payload)
        except Exception as e:
            self.logger.error('Failed to create entity - error: %s' % e)
            raise EntityInternalException(_('Failed to create entity %(entity_id)s.'))

    def handle_update_entity(self, request, entity_id):
        existing_entity = self.entity_store.get(entity_id)
        if existing_entity is None:
            raise EntityNotFoundException(_('Entity with id %(entity_id)s not found.'))
        # process dimension information
        identifier = request.data.get('identifier_dimensions', '[]')
        informational = request.data.get('informational_dimensions', '[]')
        dimensions = request.data.get('dimensions', '{}')
        dimensions, informational_dimensions, identifier_dimensions = \
            self._validate_dimension_json(
                identifier, informational, dimensions)
        self._validate_dimension_exists(dimensions, informational_dimensions)
        self._validate_dimension_exists(dimensions, identifier_dimensions)
        # build data payload
        data_payload = {}
        entity_state = request.data.get('state', 'disabled')
        self._validate_entity_state(entity_state)
        data_payload['state'] = entity_state
        data_payload['title'] = request.data.get('title', '')
        data_payload['identifier_dimensions'] = identifier_dimensions
        data_payload['informational_dimensions'] = informational_dimensions
        data_payload['dimensions'] = dimensions
        data_payload['updated_date'] = time.time()
        try:
            return self.entity_store.update(entity_id, data_payload)
        except Exception as e:
            self.logger.error('Failed to update entity - error %s' % e)
            raise EntityInternalException(_('Failed to update entity %(entity_id)s.'))

    def handle_bulk_delete_entities(self, request):
        """
        Under most scenarios, we delete either a list of entities supplied to
        the endpoint or delete a search. In the edge case that we want to
        delete all entities in a search except certain entities, we supply
        both a list of entities and a search, and we add the "invert_delete"
        flag which tells us to *not* delete the list of entities.
        """
        invert_flag = int(request.query.pop('invert_delete', '0'))
        filter_delete_query = em_common.get_query_from_request_args(request.query.pop('query', ''))
        kvstore_delete_query = em_common.get_query_from_request_args(request.query.pop('delete_query', ''))
        """
        Bulk deletion of some, but not all, entities
        * {"$or":... } is the format of supplied list of entities
        * {"foo":... } is the format of a supplied filter
        * {} is the format of no filter or list supplied
        """
        if invert_flag and kvstore_delete_query.startswith("{\"$or\""):
            kvstore_delete_query = em_common.negate_special_mongo_query(kvstore_delete_query)
            kvstore_delete_query = "{\"$and\": [%s, %s]}" % (filter_delete_query, kvstore_delete_query)
        if not kvstore_delete_query:
            raise EntityArgValidationException(_('Delete query can not be empty'))
        delete_query = {'query': kvstore_delete_query}
        entities_to_delete_list = self._handle_list_all(fields='_key', query_params=delete_query)
        savedsearch_delete_query = em_common.get_list_of_admin_managedby(entities_to_delete_list, em_constants.APP_NAME)
        try:
            # delete entities
            self.entity_store.bulk_delete(query=delete_query)
            # delete related alerts
            if savedsearch_delete_query:
                # Split up saved search deletion to avoid hitting the max length of a URI
                for i in range(int(math.ceil(len(savedsearch_delete_query) / 1000.0))):
                    savedsearch_delete_query_partial = savedsearch_delete_query[
                        i * 1000: (i + 1) * 1000]
                    self.savedsearch_manager.bulk_delete(savedsearch_query=savedsearch_delete_query_partial)
        except Exception as e:
            self.logger.error('Failed to bulk delete entities - error: %s' % e)
            raise EntityInternalException(_('Failed to bulk delete entities'))

    def handle_delete_entity(self, request, entity_id):
        existing_entity = self.entity_store.get(entity_id)
        if existing_entity is None:
            raise EntityNotFoundException(_('Entity with id %(entity_id)s not found.'))
        try:
            self.entity_store.delete(entity_id)
        except Exception as e:
            self.logger.error('Failed to delete entity %s -  error: %s' % (entity_id, e))
            raise EntityInternalException(_('Cannot delete entity with id %(entity_id)s'))

    def handle_metadata(self, request):
        query = {'query': em_common.get_query_from_request_args(request.query.get('query', ''))}
        entities = self._handle_list_all(
                fields='_key', count=em_constants.KVSTORE_SINGLE_FETCH_LIMIT, offset=-1, query_params=query
        )
        response = {
            'total_count': len(entities)
        }
        return response

    def handle_dimension_summary(self, request):
        query_params = {'query': em_common.get_query_from_request_args(request.query.get('query', ''))}
        entities = self._handle_list_all(fields='dimensions,state', query_params=query_params)
        dimensions = [entity['dimensions'] for entity in entities if 'dimensions' in entity]
        states = [entity['state'] for entity in entities if 'state' in entity]
        dimensions_map = self._build_dimensions_map(dimensions)
        # Add entity state as fake dimensions
        dimensions_map['Status'] = list(set(states))
        response = {
            'dimensions': dimensions_map,
        }
        return response

    def handle_metric_name(self, request):
        count = request.query.get('count', 0)
        query = request.query.get('query')
        if query:
            query = self._load_valid_metric_names_query_param(query)
        results_list = self.search_manager.get_metric_names_by_dim_names(dimensions=query, count=count)
        metrics_list = [{em_constants.DEFAULT_METRIC_FOR_COLOR_BY: {'min': '0.00', 'max': '1.00'}}]
        if results_list:
            for r in results_list:
                metrics_list.append({
                    r.get('metric_name'): {'min': r.get('min'), 'max': r.get('max')}
                })
        return metrics_list

    def handle_metric_data(self, request):
        count = request.query.get('count', 0)
        # get entities based on dimensions query
        query = request.query.get('query', '')
        if not query:
            raise EntityArgValidationException(_('Missing required query parameter: query'))
        query_params = self._load_valid_metric_data_query(query)
        dimensions = query_params.get('dimensions', {})
        dimensions = {'dimensions.{}'.format(key): value for key, value in dimensions.iteritems()}
        dimensions_kvstore_query = em_common.get_query_from_request_args(json.dumps(dimensions))
        filtered_entities = self._handle_list_all(fields='_key,dimensions,collectors.name',
                                                  query_params={'query': dimensions_kvstore_query})
        # get collectors
        collectors = self._handle_list_collector_configs(fields='name,title_dimension')
        collectors_map = {collector.get('name'): collector.get('title_dimension') for collector in collectors}
        # run search
        should_execute_search = normalizeBoolean(query_params.get('executeSearch', True))
        search_res = self.search_manager.get_avg_metric_val_by_entity(execute_search=should_execute_search,
                                                                      metric_name=query_params['metric_name'],
                                                                      entities=filtered_entities,
                                                                      collector_config=collectors_map,
                                                                      count=count)
        response = {
            res.get('key'): res.get('value') for res in search_res
        } if isinstance(search_res, list) else search_res
        return response

    def _build_dimensions_map(self, dimensions):
        """
        Format the data to remove duplicates and return a map of dimensions with values
        ex : {
            "host": ["a", "b"],
            "location": ["seattle"]
        }
        :param dimensions {dict} dimensions on each entity from kvstore:
        :return:
        """
        merged_dimensions = {}
        for dimension in dimensions:
            for key, value in dimension.iteritems():
                value = value if isinstance(value, list) else [value]
                merged_dimensions.setdefault(key, []).extend(value)
        # deduplicate merged dimensions value in the end
        for dim in merged_dimensions:
            merged_dimensions[dim] = list(set(merged_dimensions[dim]))
        return merged_dimensions

    def _validate_entity_state(self, entity_state):
        if entity_state not in self.VALID_ENTITY_STATES:
            raise EntityArgValidationException(_('Invalid entity state'))

    def _update_requested_fields(self, fields):
        fields_array = map(lambda f: f.strip(), fields.split(','))
        # Always need the field "_key" regardless
        if len(fields_array) > 0:
            fields_array.append('_key')
        if 'informational_dimensions' in fields_array or 'identifier_dimensions' in fields_array:
            fields_array.append('dimensions')
        return ','.join(fields_array)

    def _get_mapped_dimensions(self, dimension_type, dimensions_list, dimensions_obj):
        dimensions_mapped = {}
        for dimension in dimensions_list:
            if type(dimensions_obj[dimension]) is not list:
                dimensions_obj[dimension] = [dimensions_obj[dimension]]
            dimensions_mapped[dimension] = dimensions_obj[dimension]
        dimensions_mapped = json.dumps(dimensions_mapped)
        return dimensions_mapped

    def _validate_dimension_json(self, identifier, informational, dimensions):
        try:
            identifier_dims = json.loads(identifier) if isinstance(identifier, basestring) else identifier
            informational_dims = json.loads(informational) if isinstance(informational, basestring) else informational
            dimensions = json.loads(dimensions) if isinstance(dimensions, basestring) else dimensions
        except Exception:
            raise EntityArgValidationException(_('Invalid JSON supplied to REST handler!'))

        # Make sure the correct arg types are provided for the endpoint
        if type(dimensions) is not dict:
            raise EntityArgValidationException(
                _('Dimensions provided should be JSON object')
            )
        if type(informational_dims) is not list:
            raise EntityArgValidationException(_('Informational dimensions provided should be list'))
        if type(identifier_dims) is not list:
            raise EntityArgValidationException(_('Identifier dimensions provided should be list'))

        # If all the checks pass without exception, return the dimensions as
        # valid objects
        return (dimensions, informational_dims, identifier_dims)

    def _validate_dimension_exists(self, dimensionsObj, dimensionList):
        for dimension in dimensionList:
            if dimension not in dimensionsObj:
                message = _('Dimension provided does not exist in dimensions object')
                raise EntityArgValidationException(message)

    def _get_related_collector_configs(self, entity, collector_configs):
        collector_names = set(collector['name']
                              for collector in entity.get('collectors'))
        return filter(lambda cc: cc['_key'] in collector_names, collector_configs)

    def _extract_dimension_information(self, entity):
        # Parse and validate the dimensions JSON
        informational = entity.get('informational_dimensions', [])
        identifier = entity.get('identifier_dimensions', [])
        dimensions = entity.get('dimensions', {})

        identifier_dimensions, informational_dimensions = {}, {}
        if 'informational_dimensions' in entity or 'identifier_dimensions' in entity:
            dimensions, informational_dimensions, identifier_dimensions = \
                self._validate_dimension_json(identifier, informational, dimensions)

            if 'informational_dimensions' in entity:
                informational_dimensions = self._get_mapped_dimensions(
                    'informational_dimensions',
                    informational_dimensions,
                    dimensions
                )

            if 'identifier_dimensions' in entity:
                identifier_dimensions = self._get_mapped_dimensions(
                    'identifier_dimensions',
                    identifier_dimensions,
                    dimensions
                )
        return {
            'identifier_dimensions': identifier_dimensions,
            'informational_dimensions': informational_dimensions
        }

    def _build_entity_response(self, entity, collector_configs, locale):
        entity_info = {
            '_key': entity['_key'],
            'title': entity.get('title'),
            'state': entity.get('state'),
            'imported_date': entity.get('imported_date'),
            'updated_date': entity.get('updated_date'),
        }
        # get dimensions info
        dimensions_info = self._extract_dimension_information(entity)
        entity_info.update(dimensions_info)
        # get collectors information
        if 'collectors' in entity:
            # From the collector(s), get the display names by locale and the vital metrics.
            all_display_names = []
            all_vital_metrics = []
            related_collector_configs = self._get_related_collector_configs(entity, collector_configs)
            for collector_config in related_collector_configs:
                dimension_display_names = collector_config.get(
                    'dimension_display_names', [])
                display_names = get_locale_specific_display_names(dimension_display_names,
                                                                  locale,
                                                                  collector_config['_key'])
                all_display_names.extend(display_names)
                vital_metrics = collector_config.get('vital_metrics', [])
                all_vital_metrics.extend(vital_metrics)
            # Add event search filter
            search_filter = create_entity_log_filter(entity, related_collector_configs)
            collector_related_info = {
                'collectors': json.dumps(entity['collectors']),
                'dimension_display_names': json.dumps(all_display_names),
                'vital_metrics': json.dumps(all_vital_metrics),
                'log_search': serialize(search_filter) if search_filter else None
            }
            entity_info.update(collector_related_info)
        return entity_info

    def _load_valid_metric_names_query_param(self, query_param):
        """
        Query params are expected to be a dictionary with dimension name as key, list of dimension values as value
        """
        message = _(
            'Cannot parse query parameter. Expected format is {<dimension name>: '
            '[ <dimension values, wildcards>]}'
        )
        # Check if it's a valid json string
        try:
            query_param = json.loads(query_param)
        except Exception as e:
            self.logger.error('Failed to parse query parameters - query: %s, error: %s' % (query_param, e))
            raise EntityArgValidationException(message)
        if isinstance(query_param, dict):
            # Check if key is string and value is list
            is_query_param_valid = all(
                isinstance(key, basestring) and isinstance(value, list) for key, value in query_param.items())
            if is_query_param_valid is False:
                raise EntityArgValidationException(message)
        else:
            raise EntityArgValidationException(message)
        return query_param

    def _load_valid_metric_data_query(self, query_param):
        # {metric_name:cpu.idle, dimensions:{os:["ubuntu"]}}
        message = _(
            'Cannot parse query parameter. Expected format is {metric_name: <metric_name>, '
            'dimensions: {<dimension name>: [<dimension values, wildcards>]}}'
        )
        # Check if it's a valid json string
        try:
            query_param = json.loads(query_param)
        except Exception as e:
            self.logger.error('Failed to parse query parameters - query: %s, error: %s' % (query_param, e))
            raise EntityArgValidationException(message)
        if isinstance(query_param, dict):
            # Check if both metric_name and dimensions exist
            if 'metric_name' not in query_param:
                raise EntityArgValidationException(_('Missing required key: metric_name'))
            metric_name = query_param['metric_name']
            dimensions = query_param.get('dimensions')
            # Check type for required key - metric_name
            if not isinstance(metric_name, basestring):
                raise EntityArgValidationException(_('Expected metric name to be a string.'))
            if dimensions:
                # Check type for optional key - dimensions
                if not isinstance(dimensions, dict):
                    raise EntityArgValidationException(_('Expected dimensions to be a dict.'))
                # Check if each key in dimensions is a string and each value is a list
                is_query_param_valid = all(
                    isinstance(key, basestring) and isinstance(value, list) for key, value in dimensions.iteritems())
                if is_query_param_valid is False:
                    raise EntityArgValidationException(
                        _('Expected each key in dimensions to be a string, each value to be a list')
                    )
        else:
            raise EntityArgValidationException(_('Expected query param to be a dict'))

        return query_param

    def _handle_list_collector_configs(self, count=0, offset=0, fields='', params={}):
        try:
            return self.collector_store.load(count=count, offset=offset, fields=fields, params=params)
        except Exception as e:
            self.logger.error(e)
            raise EntityInternalException(_('Cannot list all of the collector configurations saved.'))

    def _handle_list_key(self, key):
        try:
            return self.entity_store.get(key)
        except Exception as e:
            self.logger.error(e)
            raise EntityNotFoundException(_('Cannot find the entity with id %(entity_id)s.'))

    def _handle_list_all(self, fields='', query_params={}, count=0, offset=0, sort_key='', sort_dir='asc'):
        """
            Get all the entities in batch when offset is -1
        """
        try:
            sort = ''
            if sort_key:
                sort = '%s:%s' % (
                    sort_key,
                    1 if sort_dir == 'asc' else -1
                )
            if offset == -1:
                return self.entity_store.load_all(count=count, fields=fields, sort=sort, params=query_params)
            else:
                return self.entity_store.load(count=count, offset=offset, fields=fields, sort=sort, params=query_params)
        except Exception as e:
            self.logger.error(e)
            raise EntityInternalException(_('Cannot list all of the entities saved.'))
