# Copyright 2016 Splunk Inc. All rights reserved.
# Environment configuration
import em_declare  # noqa
# Standard Python Libraries
import sys
# Third-Party Libraries
import modinput_wrapper.base_modinput
from splunklib import modularinput as smi
from splunklib.client import Service
# Custom Libraries
from em_entity_discovery_controller import EMEntityDiscoveryController
from em_model_collector import EMCollector
from service_manager.splunkd.kvstore import KVStoreManager
from utils.instrument import Instrument
import em_constants
import em_common
import logging_utility
import logging
from em_utils import get_check_internal_log_message, is_splunk_light
from solnlib.utils import retry
from urllib2 import HTTPError
logger = logging_utility.getLogger()


class EMEntityManager(modinput_wrapper.base_modinput.SingleInstanceModInput):
    """
    Entity Manager modular input
    This ModInput is responsible for:
        - Entity Discovery: By fetching metrics/dimensions from Metrics Catalog API

    """

    def __init__(self):
        """
        Init modular input for entity discovery
        """
        super(EMEntityManager, self).__init__('em', 'entity_manager')
        self.splunkd_messages_service = None
        # set log level to WARNING to make our logging less verbose
        self.set_log_level(logging.WARNING)

    def get_scheme(self):
        """
        Overloaded splunklib modularinput method
        """
        scheme = smi.Scheme('em_entity_manager')
        scheme.title = ('Splunk Insights for Infrastructure - Entity Manager')
        scheme.description = (
            'Entity Manager helps to discover and manage your entities')
        log_level = 'The logging level of the modular input. Defaults to DEBUG'
        scheme.add_argument(smi.Argument('log_level', title='Log Level',
                                         description=log_level,
                                         required_on_create=False))

        return scheme

    def get_app_name(self):
        """
        Overloaded splunklib modularinput method
        """
        return em_constants.APP_NAME

    def validate_input(self, definition):
        """
        Overloaded splunklib modularinput method
        """
        pass

    @Instrument(step='modinput_entry', process='entity_discovery')
    def collect_events(self, inputs, ew):
        """
        Main loop function, run every "interval" seconds

        :return: void
        """
        input_stanza, stanza_args = inputs.inputs.popitem()
        try:
            self.init()

            if not em_common.modular_input_should_run(self.session_key, logger=logger):
                logger.info("em_entity_manager modinput will not run on this non-captain node.")
                return
            # Initialize controller
            self.entity_discovery_controller = EMEntityDiscoveryController(self.session_key)
            # Discovery new entities
            self.entity_discovery_controller.discover_entities()
            # update entities group membership
            self.entity_discovery_controller.update_group_membership()
        except Exception as e:
            logger.error('Failed to execute entity discovery modular input -- Error: %s' % e)
            is_light = is_splunk_light(server_uri=em_common.get_server_uri(),
                                       session_key=self.session_key,
                                       app=em_constants.APP_NAME)
            link_to_error = get_check_internal_log_message(is_light)
            self.splunkd_messages_service.create(
                'entity-discovery-failure',
                severity='error',
                value='Entity discovery failed to run. ' + link_to_error
            )

    def init(self):
        """
        Initialize stores and services

        :return: void
        """
        self.session_key = self._input_definition.metadata['session_key']
        self.splunkd_messages_service = Service(token=self.session_key,
                                                app=em_constants.APP_NAME,
                                                owner='nobody').messages
        try:
            self._init_collector_stores()
        except HTTPError as e:
            # If we encounter HTTPError after multiple retries, we
            # simply log it and throw it back to Splunk - we will
            # skip posting it to the message portal since it's usually
            # a temporary issue during startup
            logger.error('Failed to initialize collectors kvstore - Error: %s' % e)
            raise
        except Exception as e:
            logger.error('Failed to initialize collectors kvstore - Error: %s' % e)
            is_light = is_splunk_light(server_uri=em_common.get_server_uri(),
                                       session_key=self.session_key,
                                       app=em_constants.APP_NAME)
            link_to_error = get_check_internal_log_message(is_light)
            self.splunkd_messages_service.create(
                'entity-discovery-failure',
                severity='error',
                value='Entity discovery failed to run. ' + link_to_error
            )

    @retry(retries=5, exceptions=[HTTPError])
    def _init_collector_stores(self):
        """
        Initialize collector kvstore
        Since kvstore may not have yet started,
        we reattempt few times on a HTTPError

        :return: void
        """
        collector_store = KVStoreManager(
            em_constants.STORE_COLLECTORS,
            em_common.get_server_uri(),
            self.session_key,
            app=em_constants.APP_NAME)
        EMCollector.setup(self.session_key)
        conf_collector_list = EMCollector.load()
        collectors = collector_store.load()
        existing_collector_names = set(c['name'] for c in collectors)
        all_collector_names = set(c.name for c in conf_collector_list)
        common = existing_collector_names.intersection(all_collector_names)
        # create new collectors
        for c in conf_collector_list:
            if c.name not in common:
                collector_store.create(key=c.name, data=c.raw())
        # delete outdated collectors
        for c in collectors:
            if c['name'] not in all_collector_names:
                collector_store.delete(key=c['name'])


if __name__ == '__main__':
    exitcode = EMEntityManager().run(sys.argv)
    sys.exit(exitcode)
    pass
