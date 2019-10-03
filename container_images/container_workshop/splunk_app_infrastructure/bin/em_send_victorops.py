import em_common as EMCommon
import em_constants as EMConstants
import em_declare  # noqa
from service_manager.splunkd.kvstore import KVStoreManager
from em_abstract_custom_alert_action import AbstractCustomAlertAction
from em_exceptions import VictorOpsCouldNotSendAlertException, VictorOpsNotExistException
from em_model_victorops import EMVictorOps, SPLUNK_ALERT_CODE_TO_VICTOROPS_INCIDENT_LEVEL
from em_model_group import EMGroup
import urllib
import logging_utility

# Splunk packages
from splunk.appserver.mrsparkle.lib import i18n

_ = i18n.ugettext

logger = logging_utility.getLogger()

WORKSPACE_URL_BODY = '%s/app/splunk_app_infrastructure/metrics_analysis?%s'
ALERT_TYPE_GROUP = 'group'
ALERT_TYPE_ENTITY = 'entity'


class EMSendVictorOpsAlertAction(AbstractCustomAlertAction):

    def execute(self, results, payload):
        try:
            configuration_state_change_conditions = payload['configuration']['victorops_when'].split(',')
            session_key = payload['session_key']
            vo = self._fetch_vo_setting(session_key)
            for result in results:
                state_change = result['state_change']
                if state_change in configuration_state_change_conditions:
                    incident = self.make_incident_from_alert(result, session_key)
                    vo.send_incident(incident)
        except Exception as e:
            logger.error('Failed to send alert to VictorOps: %s', e.message)
            raise VictorOpsCouldNotSendAlertException(e.message)

    def _fetch_vo_setting(self, session_key):
        EMVictorOps.setup(session_key)
        vo_list = EMVictorOps.load()
        if len(vo_list):
            return vo_list[0]
        raise VictorOpsNotExistException(_('VictorOps setting does not exist'))

    def _fetch_kvstore(self, collection_name, session_key):
        store = KVStoreManager(collection=collection_name,
                               server_uri=EMCommon.get_server_uri(),
                               session_key=session_key,
                               app=EMConstants.APP_NAME)
        return store

    def make_incident_from_alert(self, result, session_key):

        incident = {}
        # name of alert triggered
        alert_name = result['ss_id']
        incident['Alert Name'] = alert_name
        # metric being alerted on
        metric_name = result['metric_name']
        incident['Metric Name'] = metric_name
        # State of metric at time of alert. If metric is info, warn, or critical. This is same as 'message_type'
        alert_state_and_incident_level = SPLUNK_ALERT_CODE_TO_VICTOROPS_INCIDENT_LEVEL[result['current_state']]
        incident['Metric State'] = alert_state_and_incident_level
        # if metric improved or degraded
        state_change = result['state_change']
        incident['Metric State Change'] = state_change

        # value of metric at time of alert
        metric_value = str(round(float(result['current_value']), 1))
        incident['Metric Value'] = metric_value

        # Now setting entity and group specific information
        # Fetching some variables which are necessary in multiple places later
        managed_by_id = result['managed_by_id']
        managed_by_type = result.get('managed_by_type', '')
        entity_title = result.get('entity_title', '')
        aggregation = result.get('aggregation_method', '').lower()
        metric_filters_incl = result.get('metric_filters_incl', '')
        metric_filters_excl = result.get('metric_filters_excl', '')
        split_by = result.get('split_by', '')
        split_by_value = result.get(split_by, '')
        # Split-by identifier dimensions gives no split_by_value but adds entity_title
        if (split_by and not split_by_value):
            split_by_value = entity_title

        if (metric_filters_incl):
            incident['Metric Filters (Inclusive)'] = metric_filters_incl
        if (metric_filters_excl):
            incident['Metric Filters (Exclusive)'] = metric_filters_excl

        # If alert is coming from GROUP...
        if result['managed_by_type'] == ALERT_TYPE_GROUP:
            # fetch and format necessary info
            kvstore = self._fetch_kvstore(EMConstants.STORE_GROUPS, session_key)
            kvstore_output = kvstore.get(managed_by_id)
            filter_dimensions = kvstore_output.get('filter', '')
            title = kvstore_output.get('title', '')

            filter_dimensions_dict = EMGroup.convert_filter_string_to_dictionary(filter_dimensions)
            filter_dimensions_formatted = EMSendVictorOpsAlertAction._format_filter_dimensions(filter_dimensions_dict)
            workspace_link = EMSendVictorOpsAlertAction._make_workspace_url(ALERT_TYPE_GROUP,
                                                                            managed_by_id,
                                                                            alert_name)
            incident['Group Triggering Alert'] = title
            incident['Dimensions on Originating Group'] = filter_dimensions_formatted
            incident['Link to Alert Workspace'] = workspace_link
        else:
            # If alert is coming from ENTITY...
            # fetch and format the info
            kvstore = self._fetch_kvstore(EMConstants.STORE_ENTITIES, session_key)
            kvstore_output = kvstore.get(managed_by_id)
            filter_dimensions = kvstore_output.get('dimensions', {})
            title = entity_title

            # convert dim value to list so that filter URL param is in correct format
            for key, value in filter_dimensions.iteritems():
                if not isinstance(value, list):
                    filter_dimensions[key] = [value]

            filter_dimensions_formatted = EMSendVictorOpsAlertAction._format_filter_dimensions(filter_dimensions)
            workspace_link = EMSendVictorOpsAlertAction._make_workspace_url(ALERT_TYPE_ENTITY,
                                                                            managed_by_id,
                                                                            alert_name)
            incident['Host Triggering Alert'] = entity_title
            incident['Dimensions on Originating Host'] = filter_dimensions_formatted
            incident['Link to Alert Workspace'] = workspace_link

        # Lastly, setting victorops-specific info
        # message_type tells VO whether incident is info, warn, or critical
        incident['message_type'] = alert_state_and_incident_level
        # entity_id is incident's uuid. It lets you update the incident. It has nothing to do with SII entity concept.
        incident['entity_id'] = '%s_%s' % (managed_by_id, metric_name)
        # VO uses message to populate emails, service now tickets, slack etc
        # Group (or entity) split-by alert
        if (split_by != 'None'):
            split_by_clause = (
                ' ({aggregation}) on {managed_by_type}: {title}, {split_by}: '
                '{split_by_value}'
                ).format(
                    managed_by_type=managed_by_type,
                    title=title,
                    split_by=split_by,
                    split_by_value=split_by_value,
                    aggregation=aggregation
                )
        # Entity or group aggregation alert
        else:
            split_by_clause = (
                ' ({aggregation}) on {managed_by_type}: {title}'
                ).format(
                    managed_by_type=managed_by_type,
                    title=title,
                    aggregation=aggregation
                )

        message = '{metric_name} {state_change}s to {metric_value}{split_by_clause}'.format(
            metric_name=metric_name,
            state_change=state_change,
            metric_value=metric_value,
            split_by_clause=split_by_clause
        )
        incident['state_message'] = message
        incident['entity_display_name'] = message
        return incident

    @staticmethod
    def _make_workspace_url(group_or_entity_label, group_or_entity_id, alert_name):
        id_and_alert_params = {
            group_or_entity_label: group_or_entity_id,
            'alert_name': alert_name
        }
        id_and_alert_encoded = urllib.urlencode(id_and_alert_params)
        splunkweb_fqdn = EMCommon.get_splunkweb_fqdn()
        workspace_url = WORKSPACE_URL_BODY % (splunkweb_fqdn, id_and_alert_encoded)
        return workspace_url

    @staticmethod
    def _format_filter_dimensions(filter_dimensions_dict):
        formatted_strings = []
        for key, value in filter_dimensions_dict.iteritems():
            formatted_strings.append('%s: %s' % (key, ', '.join(value)))

        return '; '.join(formatted_strings)


instance = EMSendVictorOpsAlertAction()


if __name__ == '__main__':
    instance.run()
