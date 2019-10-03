# Copyright 2016 Splunk Inc. All rights reserved.
# Standard Python Libraries
import time
import re
import json
from threading import Thread
# Third-Party Libraries
# N/A
# Custom Libraries
from em_search_manager import EMSearchManager
from splunklib.client import Service
import em_declare  # noqa
from service_manager.splunkd.conf import ConfManager
from service_manager.splunkd.kvstore import KVStoreManager
from utils.instrument import Instrument
from em_model_entity import EMEntity
import em_constants
import em_common
import em_model_entity
import logging_utility
from em_constants import DIM_KEYS_BLACKLIST
from em_utils import get_check_internal_log_message, is_splunk_light

logger = logging_utility.getLogger()

COLLECTORS_CONF_FILE = 'collectors'


class InvalidCollectorException(Exception):
    def __init__(self, msg):
        super(InvalidCollectorException, self).__init__(msg)


class EMCollector(Thread):
    """
    Collector Model

    Attributes:
        session_key: Splunkd session_key
        _key: Primary key of collector in KVStore.
        _user: Owner of collector in KVStore.
        name: An unique string representing identifier of this collector in KVStore collection
        title: Title of entity.
        source_predicate: Predicate to discover entities from metric index.
          i.e. cpu.* (i.e. all metrics has metric_name start with cpu is OS metrics)
        title_dimension: Dimension to identify title field in entity model. i.e. host
        identifier_dimensions: Dimensions to identify identifier fields in entity model
        informational_dimensions: An array of dimension's name
            or '*' for everything except identifier dimensions.
            Dimensions to informational identifier fields in entity model
        monitoring_lag: It's possible there is a lag time
          when events hit HEC endpoint until events are indexed. Default is 15 seconds
        monitoring_calculation_window: Search timerange, how long does the search look back.
            Default is 3 minutes.
        dimension_display_names: array of dimension value to display names by dimension->locale
        disabled: Enabled or Disabled
        vital_metrics: Vital metrics for associated entities.
        correlated_event_data: object specifies base search filter and entity filter to get correlated
        log data to this collector
    """

    # Invalid dimension name regex
    InvalidDimensionRegex = re.compile('^_|[^a-zA-Z_\-\d]')
    monitoring_lag_default = 15
    monitoring_calculation_window_default = 270

    def __init__(self,
                 session_key=None,
                 _key=None,
                 _user=None,
                 name='',
                 title='',
                 source_predicate='',
                 title_dimension='',
                 identifier_dimensions=None,
                 informational_dimensions=None,
                 blacklisted_dimensions=None,
                 monitoring_lag=monitoring_lag_default,
                 monitoring_calculation_window=monitoring_calculation_window_default,
                 dimension_display_names=None,
                 disabled=1,
                 correlated_event_data=None,
                 vital_metrics=None):
        """
        Return collector object
        """
        super(EMCollector, self).__init__()
        self.session_key = session_key
        self.name = name
        self.title = title
        self.source_predicate = source_predicate
        self.title_dimension = title_dimension
        self.identifier_dimensions = identifier_dimensions
        self.informational_dimensions = informational_dimensions
        self.blacklisted_dimensions = blacklisted_dimensions
        self.monitoring_lag = int(monitoring_lag)
        self.monitoring_calculation_window = int(monitoring_calculation_window)
        self.disabled = int(disabled)
        self.dimension_display_names = dimension_display_names if dimension_display_names else []
        self.correlated_event_data = correlated_event_data if correlated_event_data else {}
        self.vital_metrics = vital_metrics if vital_metrics else []
        if _key is None:
            self._key = name
        else:
            self._key = _key
        self._entities_cache = None
        self._validate()
        self._setup_managers()

    @classmethod
    def setup(cls, session_key):
        """
        Set up sesison key and conf manager.
        NOTE: Must be done before performing any further actions
        """
        cls.conf_manager = ConfManager(
            conf_file=COLLECTORS_CONF_FILE,
            server_uri=em_common.get_server_uri(),
            session_key=session_key,
            app=em_constants.APP_NAME
        )

    @staticmethod
    def _parse_eai_response(resp):
        """
        :return a list of dict containing collector_rules for each entry
        """
        res = []
        if resp and 'entry' in resp:
            for e in resp['entry']:
                name = e.get('name', '')
                content = e.get('content', {})
                title = content.get('title', '')
                source_predicate = content.get('source_predicate', '')
                title_dimension = content.get('title_dimension', '')
                identifier_dimensions = json.loads(content.get('identifier_dimensions', 'null'))
                informational_dimensions = json.loads(content.get('informational_dimensions', 'null'))
                blacklisted_dimensions = json.loads(content.get('blacklisted_dimensions', 'null'))
                monitoring_lag = int(content.get('monitoring_lag', EMCollector.monitoring_lag_default))
                monitoring_calculation_window = int(content.get('monitoring_calculation_window',
                                                    EMCollector.monitoring_calculation_window_default))
                dimension_display_names = json.loads(content.get('dimension_display_names', 'null'))
                disabled = int(content.get('disabled', 1))
                correlated_event_data = json.loads(content.get('correlated_event_data', 'null'))
                vital_metrics = json.loads(content.get('vital_metrics', 'null'))

                res.append({
                    'name': name,
                    'title': title,
                    'source_predicate': source_predicate,
                    'title_dimension': title_dimension,
                    'identifier_dimensions': identifier_dimensions,
                    'informational_dimensions': informational_dimensions,
                    'blacklisted_dimensions': blacklisted_dimensions,
                    'monitoring_lag': monitoring_lag,
                    'monitoring_calculation_window': monitoring_calculation_window,
                    'dimension_display_names': dimension_display_names,
                    'disabled': disabled,
                    'correlated_event_data': correlated_event_data,
                    'vital_metrics': vital_metrics

                })
        return res

    @classmethod
    def load(cls, count=0, offset=0):
        """
        load Collectors Conf settings

        :return a list of collector dict
        """
        try:
            resp = cls.conf_manager.load_stanzas(count, offset)
            data_list = cls._parse_eai_response(resp)
            return map(lambda d: EMCollector(**d), data_list)
        except Exception as e:
            logger.error("Failed to load Collector stanzas: %s" % e)
            return []

    def _setup_managers(self):
        self.entity_store = KVStoreManager(em_constants.STORE_ENTITIES,
                                           em_common.get_server_uri(),
                                           self.session_key,
                                           app=em_constants.APP_NAME)
        self.search_manager = EMSearchManager(em_common.get_server_uri(),
                                              self.session_key,
                                              em_constants.APP_NAME)
        self.splunkd_messages_service = Service(token=self.session_key,
                                                app=em_constants.APP_NAME,
                                                owner='nobody').messages

    def _validate(self):
        """
        Validate collector
        """
        is_valid = True
        if not isinstance(self.name, basestring):
            logger.error('EMCollector::Invalid type of name, string or unicode is required.')
            is_valid = False
        if not isinstance(self.title, basestring):
            logger.error('EMCollector::Invalid type of title, string or unicode is required.')
            is_valid = False
        if not isinstance(self.source_predicate, basestring):
            logger.error('EMCollector::Invalid type of source_predicate, string or unicode is required.')
            is_valid = False
        if not isinstance(self.title_dimension, basestring):
            logger.error('EMCollector::Invalid type of title_dimension, string or unicode is required.')
            is_valid = False
        if not (isinstance(self.identifier_dimensions, list) or self.identifier_dimensions == '*'):
            logger.error('EMCollector::Invalid type of identifier_dimensions, array or "*" is required.')
            is_valid = False
        if not (isinstance(self.informational_dimensions, list) or self.informational_dimensions in ('*', '')):
            logger.error('EMCollector::Invalid type of informational_dimensions, array or "*" or "" is required.')
            is_valid = False
        if not (isinstance(self.blacklisted_dimensions, list) or self.blacklisted_dimensions == ''):
            logger.error('EMCollector::Invalid type of blacklisted_dimensions, array or "" is required.')
            is_valid = False
        if type(self.monitoring_lag) is not int:
            logger.error('EMCollector::Invalid type of monitoring_lag, number is required.')
            is_valid = False
        if type(self.monitoring_calculation_window) is not int:
            logger.error('EMCollector::Invalid type of monitoring_calculation_window, number is required.')
            is_valid = False
        if type(self.dimension_display_names) is not list:
            logger.error('EMCollector::Invalid type of dimension_display_names, must be a list')
            is_valid = False
        if not (type(self.disabled) is int or (self.disabled < 0 or self.disabled > 1)):
            logger.error('EMCollector::Invalid type of disabled, 0 or 1 is required.')
            is_valid = False
        if type(self.vital_metrics) is not list:
            logger.error('EMCollector::Invalid type of vital_metrics, must be a list')
            is_valid = False
        if not type(self.correlated_event_data) is dict:
            logger.error('EMCollector::Invalid type of correlated_event_data, dict is required')
            is_valid = False
        if not is_valid:
            raise InvalidCollectorException('Provided Collector info is invalid. Check splunk logs for details.')

    def _dump_invalid_entity_dimensions(self, entity_dims):
        """
        dump entity dimension names that contains violating chracters (kvstore doesn't
        allow field names to contain "." and "$")
        """
        res = {}
        for dim in entity_dims:
            if not EMCollector.InvalidDimensionRegex.findall(dim):
                res[dim] = entity_dims[dim]
        return res

    def load_related_entities(self):
        """
        load and cache all existing entities discovered by this collector.
        """
        if self._entities_cache is None:
            entity_filter = {'collectors.name': [self.name]}
            kvstore_query = {'query': json.dumps(em_common.build_mongodb_query(entity_filter))}
            raw_entities = self.entity_store.load(params=kvstore_query)
            entities = [EMEntity(**e) for e in raw_entities]
            self._entities_cache = {entity._key: entity for entity in entities}
            return self._entities_cache
        return self._entities_cache

    def filter_entity_dimension_names(self, dimension_names, filtering_dimension_names):
        """
        filter dimension names based on the given list of dimensions

        :param dimension_names an array of dimension names to be filtered on
        :param filtering_dimension_names an array of dimension names that's used as reference
        """
        if isinstance(filtering_dimension_names, list):
            filtered_dims = list(set(filtering_dimension_names) & set(dimension_names))
        elif filtering_dimension_names == '*':
            filtered_dims = dimension_names
        else:
            filtered_dims = []
        return filtered_dims

    def get_updated_entity_collectors(self, entity):
        """
        update and return collectors information of given entity based on this collector's existence.

        :param entity an entity object
        """
        current_time = time.time()
        collectors = [] if entity is None else entity.collectors
        try:
            self_collector_index = [x['name'] for x in collectors].index(self.name)
            collectors[self_collector_index]['updated_date'] = current_time
        except ValueError:
            collectors.append({'name': self.name, 'updated_date': current_time})
        return collectors

    def get_imported_and_updated_date(self, entity):
        """
        update and return updated time information of the given entity

        :param entity an entity object
        """
        updated_date = time.time()
        imported_date = entity.imported_date if entity is not None else updated_date
        return imported_date, updated_date

    def get_entity(self, entity_dimensions):
        """
        Get entity object from dimensions from metric data

        :param entity_dimensions: All dimensions (including identifier_dimensions) that are
            associated with a specific entity
            i.e. {
                    'host': 'wyoming.sa.com',
                    'server': 'staging',
                    'tag': ['USA', 'datagen', 'states'],
                    'ip': '10.10.0.49',
                    'os_version': '11.0',
                    'location': 'north americas',
                    'os': 'ubuntu'
                 }
        :return: EMEntity object
        """
        if entity_dimensions is None or self.session_key is None:
            return None

        related_entities = self.load_related_entities()

        entity_dimensions = self._dump_invalid_entity_dimensions(entity_dimensions)

        dimension_names = entity_dimensions.keys()

        # get existing entity with same set of identifier dimensions
        id_dims = {id_dim: entity_dimensions.get(id_dim) for id_dim in self.identifier_dimensions}
        entity_id = em_common.get_key_from_dims(id_dims)
        entity = related_entities.get(entity_id)

        imported_date, updated_date = self.get_imported_and_updated_date(entity)

        entity_id_dims = self.filter_entity_dimension_names(dimension_names, self.identifier_dimensions)
        entity_info_dims = self.filter_entity_dimension_names(
            list(set(dimension_names) - set(entity_id_dims)),
            self.informational_dimensions
        )

        collectors = self.get_updated_entity_collectors(entity)

        entity_title = entity_dimensions.get(self.title_dimension)

        return em_model_entity.EMEntity(title=entity_title,
                                        dimensions=entity_dimensions,
                                        identifier_dimensions=entity_id_dims,
                                        informational_dimensions=entity_info_dims,
                                        state='active',
                                        imported_date=imported_date,
                                        updated_date=updated_date,
                                        collectors=collectors)

    @Instrument(step='collector_discover', process='entity_discovery')
    def discover_entities(self):
        """
        discover and return entities from data
        """
        earliest = '-%ss' % (self.monitoring_calculation_window +
                             self.monitoring_lag)
        latest = '-%ss' % self.monitoring_lag

        dims_list = self.search_manager.get_dimension_names_by_id_dims(predicate=self.source_predicate,
                                                                       id_dims_name=self.identifier_dimensions,
                                                                       earliest=earliest,
                                                                       latest=latest,
                                                                       count=0)
        dimension_names = []
        for dims in dims_list:
            dimension_names += dims.get('dims', [])
        dimension_names = list(set(dimension_names))
        # Filter out black_listed dimensions
        dimension_names = filter(
            lambda d: d.lower() not in self.blacklisted_dimensions + DIM_KEYS_BLACKLIST,
            dimension_names
        )

        # | mcatalog values(_dims) doesn't return native splunk dimensions.
        # There are 3 native dimensions: host, source, sourcetype,
        # and if user wants to identify entity by those host then this search won't work.
        # Hence, we need to add host to the list as dimension.
        # Kubernetes objects lack host
        if (('host' not in dimension_names) and
           (self.name not in em_constants.KUBERNETES_COLLECTORS)):
            dimension_names += ['host']

        # Get dimension name-value pairs for all entities
        entities_dimensions_list = self.search_manager.get_all_dims_from_dims_name(
            predicate=self.source_predicate,
            id_dims_name=self.identifier_dimensions,
            dims_name=dimension_names,
            earliest=earliest,
            latest=latest
        )
        entities = []
        for entity_dimensions in entities_dimensions_list:
            entities.append(self.get_entity(entity_dimensions))
        return entities

    @Instrument(step='update_availability', process='entity_discovery')
    def update_entities_availability(self, available_entities=None):
        """
        Update availability of entities in KVStore. Mark entities as active if they are available (we have received
        data related to it), and as inactive if they are not available.

        :params available_entities: available entities discovered from data
        """
        existing_related_entities = self.load_related_entities()
        data_list = []
        inactive_entity_keys = set(existing_related_entities.keys()) - \
            set([aval_entity._key for aval_entity in available_entities])

        # If there are no entities, don't do anything
        if (not available_entities and not inactive_entity_keys):
            return

        # Update all available entities
        for entity in available_entities:
            data_list.append(entity.get_raw_data())

        # Update all inactive entities
        for entity in existing_related_entities.values():
            if entity._key in inactive_entity_keys:
                # Don't waste CPU updating inactive or disabled entities
                if (entity.state == "active"):
                    entity.set_inactive()
                    data_list.append(entity.get_raw_data())
        self.entity_store.batch_save(data_list)

    def run(self):
        """
        @overwrite Thread.run
        """
        try:
            discovered_entities = self.discover_entities()
            self.update_entities_availability(discovered_entities)
        except Exception as e:
            logger.error('%s failed to execute -- Error: %s' % (self.title, e))
            is_light = is_splunk_light(server_uri=em_common.get_server_uri(),
                                       session_key=self.session_key,
                                       app=em_constants.APP_NAME)
            link_to_error = get_check_internal_log_message(is_light)
            self.splunkd_messages_service.create(
                '%s-collector-discovery-failure' % self.name,
                severity='error',
                value='%s failed to discover entities. %s' % (self.title, link_to_error)
            )

    def getName(self):
        """
        @overwrite Thread.getName
        """
        return self.name

    def raw(self):
        return {
            'name': self.name,
            'title': self.title,
            'source_predicate': self.source_predicate,
            'title_dimension': self.title_dimension,
            'identifier_dimensions': self.identifier_dimensions,
            'informational_dimensions': self.informational_dimensions,
            'blacklisted_dimensions': self.blacklisted_dimensions,
            'monitoring_lag': self.monitoring_lag,
            'monitoring_calculation_window': self.monitoring_calculation_window,
            'dimension_display_names': self.dimension_display_names,
            'disabled': self.disabled,
            'correlated_event_data': self.correlated_event_data,
            'vital_metrics': self.vital_metrics
        }
