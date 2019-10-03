# Copyright 2018 Splunk Inc. All rights reserved.
# Environment configuration
import em_declare  # noqa
# Standard Python Libraries
import os
import sys
import time
import json
import urllib
# Third-Party Libraries
import modinput_wrapper.base_modinput
from splunklib import modularinput as smi
from splunklib.client import Service
from itoamodels import Entity, MigrationError, ValidationError
# Splunk packages
from splunk.appserver.mrsparkle.lib import i18n
import splunk.rest
# Custom Libraries
import em_common
import logging_utility
from service_manager.splunkd.kvstore import KVStoreManager
from em_exceptions import ArgValidationException
from em_constants import STORE_ENTITIES, APP_NAME, DEFAULT_BATCH_SIZE, DEFAULT_PUBLISH_URL, DISABLE_INPUTS_ENDPOINT,\
 RELOAD_INPUTS_ENDPOINT, ENTITY_MIGRATION_INPUT
import logging
from em_utils import get_check_internal_log_message, is_splunk_light

_ = i18n.ugettext

logger = logging_utility.getLogger()


class EMEntityMigration(modinput_wrapper.base_modinput.SingleInstanceModInput):
    """
    Entity Migration modular input
    This ModInput is responsible for:
        - Entity Migration: convert em_entity to itsi model then post to message bus
            specified in publish_url
    """

    def __init__(self):
        """
        Init modular input for entity migration
        """
        super(EMEntityMigration, self).__init__('em', 'entity_migration')
        self.splunkd_messages_service = None
        # set log level to WARNING to make our logging less verbose
        self.set_log_level(logging.WARNING)

    def get_scheme(self):
        """
        Overloaded splunklib modularinput method
        """
        scheme = smi.Scheme('em_entity_migraton')
        scheme.title = (
            'Splunk App for Infrastructure - Entity Migration')
        scheme.description = (
            'Entity Migration with conversion from SAI to ITSI entities')
        scheme.add_argument(smi.Argument('log_level', title='Log Level',
                                         description='The logging level of the modular input. Defaults to DEBUG',
                                         required_on_create=False))
        scheme.add_argument(smi.Argument('publish_url', title='Publish URL',
                                         description='The publish URL of the message bus',
                                         required_on_create=False))

        return scheme

    def get_app_name(self):
        """
        Overloaded splunklib modularinput method
        """
        return APP_NAME

    def validate_input(self, definition):
        """
        Overloaded splunklib modularinput method
        """
        pass

    def convert_entities(self):
        """
        convert entities to itoa
        :return: itoa_entities
        """
        entities_store = KVStoreManager(
            STORE_ENTITIES,
            em_common.get_server_uri(),
            self.session_key,
            app=APP_NAME)
        # passing all available entities from KVStore
        return self._convert_to_itoa(entities_store.load())

    def _convert_to_itoa(self, sii_entities):
        """
        Get all available entities from KVStore

        :return: List of entities in KVSTore
        """
        itoa_entities = []
        for sii_entity in sii_entities:
            try:
                dims = sii_entity.get('dimensions', {})

                # convert each dimension to list
                for d in dims:
                    if type(dims[d]) is not list:
                        dims[d] = [dims[d]]

                id_dim = sii_entity.get('identifier_dimensions', [])
                aliases = {}
                if type(id_dim) is list:
                    aliases = {k: dims[k] for k in id_dim}
                elif isinstance(id_dim, basestring) and len(id_dim) > 0:
                    aliases = {id_dim: dims[id_dim]}

                ex = Entity({
                    'unique_id': sii_entity['_key'],
                    'aliases': aliases,
                    'title': sii_entity['title'],
                    'informational': dims,
                    'creation_time': sii_entity.get('imported_date', 0),
                    'updated_time': sii_entity.get('updated_date', 0),
                })
                itoa_entities.append(ex)
            except ValidationError as e:
                logger.error('Invalid entity values provided -- Error: %s' % e)
            except MigrationError:
                logger.error('Given entity values failed to migrate to latest schema version')
            except Exception as e:
                logger.error('Invalid entity record from KVStore -- Error: %s' % e)

        return itoa_entities

    def publish_to_mbus(self, itoa_entities, url):
        entities_list = [entity.raw_data() for entity in itoa_entities]
        self._batch_save_to_mbus(data=entities_list, url=url)

    def _batch_save_to_mbus(self, data, url):
        """
        Perform multiple save operations in a batch
        """
        if not data:
            raise ArgValidationException(_('Batch saving failed: Batch is empty.'))

        batches = (data[x:x + DEFAULT_BATCH_SIZE]
                   for x in xrange(0, len(data), DEFAULT_BATCH_SIZE))
        for batch in batches:
            try:
                payload = {
                    "publisher": "Splunk App for Infrastructure", "entities": batch}
                response, content = splunk.rest.simpleRequest(url, method='POST', sessionKey=self.session_key,
                                                              jsonargs=json.dumps(payload))
                if response.status != 200:
                    logger.error("Entities failed to migrate to message bus. status:%s content:%s" %
                                 (response.status, content))
            except Exception as e:
                logger.error(e)
                raise e

    def collect_events(self, inputs_conf, ew):
        """
        Main loop function, run every "interval" seconds
        :return: void
        """
        try:
            self.session_key = self._input_definition.metadata['session_key']
            self.splunkd_messages_service = Service(token=self.session_key, app=APP_NAME, owner='nobody').messages
            if not em_common.modular_input_should_run(self.session_key, logger=logger):
                logger.info("em_entity_manager modinput will not run on this non-captain node.")
                return

            input_stanza, stanza_args = inputs_conf.inputs.popitem()
            # use hard coded url if not found
            url = stanza_args.get('publish_url', DEFAULT_PUBLISH_URL)
            log_level = stanza_args.get('log_level', 'DEBUG')
            logger.setLevel(os.environ.get("LOGLEVEL", log_level))
            logger.info('publish to url: %s' % url)

            inputs_url = DISABLE_INPUTS_ENDPOINT % (APP_NAME, urllib.quote_plus(ENTITY_MIGRATION_INPUT))
            # check if url exists
            if em_common.is_url_valid(self.session_key, url):
                # Initialize stores and covert all entities to itoa models
                itoa_entities = self.convert_entities()
                if itoa_entities:
                    self.publish_to_mbus(itoa_entities, url)
                else:
                    logger.warning("There is no SAI entities for migration.")
            else:
                # By default, input is enabled, here disable the input if no itsi present
                response, content = splunk.rest.simpleRequest(inputs_url,
                                                              method='POST',
                                                              sessionKey=self.session_key)
                logger.warning(
                    "Publish URL is invalid. Disable em_entity_migration response.status: %s" % response.status
                )
                response, content = splunk.rest.simpleRequest(RELOAD_INPUTS_ENDPOINT, sessionKey=self.session_key)
                logger.info("Reload inputs.conf to splunkd with response.status: %s" % response.status)
        except Exception as e:
            logger.error('Failed to run entity migration modular input -- Error: %s' % e)
            is_light = is_splunk_light(server_uri=em_common.get_server_uri(),
                                       session_key=self.session_key,
                                       app=APP_NAME)
            link_to_error = get_check_internal_log_message(is_light)
            self.splunkd_messages_service.create(
                'entity-migration-failure',
                severity='warn',
                value='Failed to migrate entities to ITSI. ' + link_to_error
            )

if __name__ == '__main__':
    # Wait till KVStore's ready
    time.sleep(3)

    exitcode = EMEntityMigration().run(sys.argv)
    sys.exit(exitcode)
    pass
