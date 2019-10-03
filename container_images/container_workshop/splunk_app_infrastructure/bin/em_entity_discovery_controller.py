# Copyright 2019 Splunk Inc. All rights reserved.

from em_model_collector import EMCollector, InvalidCollectorException
from em_model_entity import EMEntity
from em_model_group import EMGroup
import em_declare  # noqa
from service_manager.splunkd.kvstore import KVStoreManager
import em_constants
import em_common
import logging_utility
from utils.instrument import Instrument
from collections import Counter

logger = logging_utility.getLogger()


class EMEntityDiscoveryController(object):
    """
    This class is the controller of the entity discovery process. It's responsible
    for scheduling collectors to do the actual discovery job.

    Attributes:
      session_key: session key of the current process. used to communicate with splunk.
    """

    def __init__(self, session_key=''):
        self.session_key = session_key
        self.entity_store = KVStoreManager(
            em_constants.STORE_ENTITIES,
            em_common.get_server_uri(),
            self.session_key,
            app=em_constants.APP_NAME)
        self.group_store = KVStoreManager(
            em_constants.STORE_GROUPS,
            em_common.get_server_uri(),
            self.session_key,
            app=em_constants.APP_NAME)
        self.collector_store = KVStoreManager(
            em_constants.STORE_COLLECTORS,
            em_common.get_server_uri(),
            self.session_key,
            app=em_constants.APP_NAME)
        self.all_collectors = self._get_all_collectors()

    def _get_all_collectors(self):
        """
        Get all available collectors from KVStore
        """
        collectors = []
        for c in self.collector_store.load():
            try:
                cx = EMCollector(session_key=self.session_key, **c)
                if not cx.disabled:
                    collectors.append(cx)
            except InvalidCollectorException as e:
                logger.error('Invalid collector record from KVStore: -- Record: %s Error: %s' % (c, e))
        return collectors

    def _get_all_entities(self):
        """
        Get all available entities

        :return: List of entities
        """
        # This is heavv load but there is no way to update
        # entity state if we don't load all entities
        entities = []
        for entity in self.entity_store.load():
            try:
                ex = EMEntity(**entity)
                entities.append(ex)
            except Exception as e:
                logger.error('Invalid entity record from KVStore -- Record: %s Error: %s' % (entity, e))
        return entities

    def _get_all_groups(self):
        """
        Get all available groups

        :return: List of groups
        """
        groups = []
        for g in self.group_store.load():
            try:
                ex = EMGroup(**g)
                groups.append(ex)
            except Exception as e:
                logger.error('Invalid group record from KVStore -- Record: %s Error: %s' % (g, e))
        return groups

    @Instrument(step='collect entities', process='entity_discovery')
    def discover_entities(self):
        logger.info('Starting entity discovery...')
        for c in self.all_collectors:
            c.start()
        for c in self.all_collectors:
            c.join()
        logger.info('Finished entity discovery...')

    @Instrument(step='update group membership', process='entity_discovery')
    def update_group_membership(self):
        logger.info('Starting group membership update...')
        # reload all the entities after discovery are done
        all_entities = self._get_all_entities()
        all_groups = self._get_all_groups()
        data_list = []
        # go through each group and update entities count
        for group in all_groups:
            entities = filter(lambda en: group.check_entity_membership(en), all_entities)
            entity_status_breakdown = Counter(en.state for en in entities)
            group.entities_count = len(entities)
            group.active_entities = entity_status_breakdown.get('active', 0)
            group.inactive_entities = entity_status_breakdown.get('inactive', 0)
            data_list.append(group.get_raw_data())

        self.group_store.batch_save(data_list)
        logger.info('Finished group membership update...')
