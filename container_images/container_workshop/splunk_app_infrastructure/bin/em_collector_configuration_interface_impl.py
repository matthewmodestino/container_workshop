import em_declare  # noqa
from service_manager.splunkd.kvstore import KVStoreManager
import json
import em_constants
import em_common as EMCommon
import logging_utility
from em_exceptions import CollectorConfigurationInternalException, CollectorConfigurationNotFoundException
from em_common import get_locale_specific_display_names

# Splunk packages
from splunk.appserver.mrsparkle.lib import i18n

_ = i18n.ugettext

log = logging_utility.getLogger()


class EmCollectorConfigurationInterfaceImpl(object):
    """Collector configuration interface"""

    def _setup_kv_store(self, handler):
        log.info('Setting up the Collector Configuration KV Store...')
        self.collector_store = KVStoreManager(collection=em_constants.STORE_COLLECTORS,
                                              server_uri=EMCommon.get_server_uri(),
                                              session_key=handler.getSessionKey(),
                                              app=em_constants.APP_NAME)

    def handleList(self, handler, confInfo):
        collector_id = handler.callerArgs.id
        locale = handler.callerArgs.get('locale', ['en-us'])[0]
        count = handler.callerArgs.get('count', 0)
        offset = handler.callerArgs.get('offset', 0)
        fields = handler.callerArgs.get('fields', '')

        input_fields = handler.callerArgs.data.get('fields', [''])[0]
        fields = ''
        if len(input_fields) > 0:
            fields = self._modifyFieldsRequested(input_fields)

        log.info('User triggered action "list" with key=%s' % collector_id)
        self._setup_kv_store(handler)

        if collector_id is not None:
            selected_collector = self._handleListKey(confInfo, collector_id)
            if selected_collector is not None:
                self._extractRelevantFields(selected_collector, locale, confInfo)
        else:
            query_params = self._buildParamsObjectForLoad(fields)
            all_collectors = self._handleListAll(confInfo, fields, query_params, count, offset)
            if all_collectors is not None:
                [self._extractRelevantFields(collector, locale, confInfo) for collector in all_collectors]

    def _modifyFieldsRequested(self, fields):
        fields_array = fields.split(',')

        # Always need the field "_key" regardless
        if len(fields_array) > 0:
            fields_array.append('_key')

        return ','.join(fields_array)

    def _buildParamsObjectForLoad(self, fields):
        query_params = {}
        if fields:
            query_params['fields'] = fields
        return query_params

    def _extractRelevantFields(self, collector_config, locale, confInfo):
        fields = [
            'title',
            'source_predicate',
            'title_dimension',
            'identifier_dimensions',
            'informational_dimensions',
            'blacklisted_dimensions',
            'monitoring_lag',
            'monitoring_calculation_window',
            'disabled',
            'vital_metrics'
        ]
        for field in fields:
            if field in collector_config:
                confInfo[collector_config['_key']][field] = collector_config.get(field)

        # Choose the right display names based on the language code
        dimension_display_names = collector_config.get('dimension_display_names', [])
        display_names = get_locale_specific_display_names(dimension_display_names, locale)
        confInfo[collector_config['_key']]['dimension_display_names'] = json.dumps(display_names)

    def _handleListKey(self, confInfo, key):
        try:
            return self.collector_store.get(key)
        except Exception:
            log.error('Cannot find the collector configuration with id %s!' % key)
            raise CollectorConfigurationNotFoundException(
                _('Cannot find the collector configuration with id %(id)s!')
            )

    def _handleListAll(self, confInfo, fields, query_params, count=0, offset=0):
        try:
            return self.collector_store.load(count=count, offset=offset, fields=fields, params=query_params)
        except Exception:
            log.error('Cannot list all of the collector configurations saved!')
            raise CollectorConfigurationInternalException(
                _('Cannot list all of the collector configurations saved!')
            )
