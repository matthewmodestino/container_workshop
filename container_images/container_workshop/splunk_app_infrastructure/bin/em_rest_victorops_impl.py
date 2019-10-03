from em_model_victorops import EMVictorOps, SPLUNK_ALERT_CODE_TO_VICTOROPS_INCIDENT_LEVEL, MONITORING_TOOL
import em_declare  # noqa
from service_manager.victorops import VictorOpsManager
from em_model_victorops import VictorOpsUsernameAlreadyExistsException, VictorOpsInvalidArgumentsException, \
    VictorOpsNotExistException

# Splunk packages
from splunk.appserver.mrsparkle.lib import i18n

_ = i18n.ugettext


class EmVictorOpsInterfaceImpl(object):
    """ Interface which allows CRUD operations on the API key / routing keys for the VictorOps integration """

    def __init__(self, session_key, logger):
        self.logger = logger
        EMVictorOps.setup(session_key)

    def handle_list(self, request):
        all_vos = EMVictorOps.load()
        return all_vos

    def handle_create(self, request):
        # Pull the data we will use to create a VO setting
        name, api_key, routing_key = self._retrieve_vo_args(request)
        # check for any VO setting existence
        all_vos = EMVictorOps.load()
        if len(all_vos):
            raise VictorOpsUsernameAlreadyExistsException(
                _('Cannot create more than one VictorOps settings')
            )
        # check for duplicate VO setting existence
        existing_vo = EMVictorOps.get(name)
        if existing_vo:
            raise VictorOpsUsernameAlreadyExistsException(
                _('VictorOps setting with name %(name)s already exists')
            )
        new_vo = EMVictorOps.create(name, api_key, routing_key)
        return new_vo

    def handle_get(self, request, vo_id):
        vo = EMVictorOps.get(vo_id)
        return vo

    def handle_edit(self, request, vo_id):
        _unused, api_key, routing_key = self._retrieve_vo_args(request)
        vo = EMVictorOps.get(vo_id)
        if not vo:
            raise VictorOpsNotExistException(
                _('VictorOps setting with name %(vo_id)s does not exist')
            )
        vo.update(api_key, routing_key)
        return vo

    def handle_remove(self, request, vo_id):
        vo = EMVictorOps.get(vo_id)
        if not vo:
            raise VictorOpsNotExistException(
                _('VictorOps setting with name %(vo_id)s does not exist')
            )
        vo.delete()
        return True

    def _retrieve_vo_args(self, request):
        name = request.data.get('name')
        api_key = request.data.get('api_key')
        routing_key = request.data.get('routing_key')
        # validate format of VO args
        EMVictorOps.validate_format(name, api_key, routing_key)
        # check validity
        self._check_key_validity(api_key, routing_key)
        return name, api_key, routing_key

    def _check_key_validity(self, api_key, routing_key):
        try:
            EmVictorOpsInterfaceImpl._send_test_notification(api_key, routing_key)
        except Exception:
            raise VictorOpsInvalidArgumentsException(
                _('Credentials could not be authenticated with VictorOps')
            )

    @staticmethod
    def _send_test_notification(api_key, routing_key):
        # create the body of the test notification
        incident = {
            'message_type': SPLUNK_ALERT_CODE_TO_VICTOROPS_INCIDENT_LEVEL['1'],
            'entity_id': 'Test verification integration'
        }
        VictorOpsManager(api_key, routing_key, MONITORING_TOOL).send_incident(incident)
