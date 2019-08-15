import re
import httplib
import logging_utility
import em_declare  # noqa
from rest_handler.exception import BaseRestException
from service_manager.victorops import VictorOpsManager
from solnlib import conf_manager
import em_constants

# Splunk packages
from splunk.appserver.mrsparkle.lib import i18n

_ = i18n.ugettext

# set up logger
logger = logging_utility.getLogger()


VICTOROPS_CONF_FILE = 'victorops'
# default monitoring tool to use for alerts from SII
MONITORING_TOOL = "splunk_sii"
SPLUNK_ALERT_CODE_TO_VICTOROPS_INCIDENT_LEVEL = {
    "1": "INFO",
    "3": "WARNING",
    "5": "CRITICAL"
}


class VictorOpsUsernameAlreadyExistsException(BaseRestException):

    def __init__(self, message):
        super(VictorOpsUsernameAlreadyExistsException, self).__init__(httplib.BAD_REQUEST, message)


class VictorOpsNotExistException(BaseRestException):

    def __init__(self, message):
        super(VictorOpsNotExistException, self).__init__(httplib.BAD_REQUEST, message)


class VictorOpsInvalidArgumentsException(BaseRestException):

    def __init__(self, message):
        super(VictorOpsInvalidArgumentsException, self).__init__(httplib.BAD_REQUEST, message)


class EMVictorOps(object):

    SESSION_KEY = None

    def __init__(self, name, api_key, routing_key):
        self.name = name
        self.api_key = api_key
        self.routing_key = routing_key
        self.vo_manager = VictorOpsManager(api_key, routing_key, MONITORING_TOOL)

    @staticmethod
    def validate_format(name, api_key, routing_key):
        # validate name
        if not name:
            raise VictorOpsInvalidArgumentsException(_('Name cannot be empty'))
        # validate that the API key
        api_key_valid = re.search(em_constants.VICTOROPS_API_KEY, api_key)
        if not api_key_valid:
            raise VictorOpsInvalidArgumentsException(_('Invalid API key'))
        # validate the routing key
        routing_key_valid = re.search(em_constants.VICTOROPS_ROUTING_KEY, routing_key)
        if not routing_key_valid:
            raise VictorOpsInvalidArgumentsException(_('Invalid routing key'))

    # TODO: this can be refactored into a base model class applied everywhere
    # TODO: add a decorator function in base class to check for session key existence
    @classmethod
    def setup(cls, session_key):
        """
        Set up sesison key and conf manager.
        NOTE: Must be done before performing any further actions
        """
        EMVictorOps.SESSION_KEY = session_key
        cls.conf_manager = conf_manager.ConfManager(EMVictorOps.SESSION_KEY, em_constants.APP_NAME)
        try:
            cls.conf = cls.conf_manager.get_conf(VICTOROPS_CONF_FILE)
        except Exception as e:
            logger.warning(e)
            # create if file doesn't exist
            cls.conf = cls.conf_manager.create_conf(VICTOROPS_CONF_FILE)

    @classmethod
    def load(cls):
        """
        load VictorOps settings

        :return a list of EMVictorOps objects
        """
        try:
            resp = cls.conf.get_all()
            data_list = cls._parse_eai_response(resp)
            return map(lambda d: EMVictorOps(**d), data_list)
        except Exception as e:
            logger.error("Failed to load VO stanzas: %s" % e)
            return []

    @classmethod
    def get(cls, name):
        """
        get a single VictorOps setting

        :param name: name indicating which stanza load
        :return a EMVictorOps object
        """
        try:
            resp = cls.conf.get(name)
            resp = {name: resp}
            data = cls._parse_eai_response(resp)
            if len(data):
                return EMVictorOps(**data[0])
            return None
        except Exception as e:
            logger.error("Failed to load VO stanza with name %s: %s" % (name, e))
            return None

    @classmethod
    def create(cls, name, api_key, routing_key):
        """
        save VictorOps setting to conf file
        """
        new_vo_setting = EMVictorOps(name, api_key, routing_key)
        data = {
            'api_key': api_key,
            'routing_key': routing_key
        }
        cls.conf.update(name, data, ['api_key'])
        return new_vo_setting

    def update(self, api_key='', routing_key=''):
        """
        update VictorOps setting

        :param data: key, value pair of data to update, should contain api_key and routing_key
        """
        self.api_key = api_key
        self.routing_key = routing_key
        updated_cred = {
            'api_key': self.api_key,
            'routing_key': self.routing_key
        }
        self.conf.update(self.name, updated_cred, ['api_key'])

    def delete(self):
        """
        delete VictorOps setting
        """
        self.conf.delete(self.name)

    def send_incident(self, incident):
        """
        send incident to VictorOps

        :param incident: json object that contains information of the incident
        """
        return self.vo_manager.send_incident(incident)

    @staticmethod
    def _parse_eai_response(resp):
        """
        parse EAI response and return information needed to construct an EMVictorOps object

        :return a list of json object containing name, api_key, routing_key corresponds
        to each response entry
        """
        res = []
        if resp:
            for key, value in resp.items():
                name = key
                api_key = value.get('api_key', '')
                routing_key = value.get('routing_key', '')
                res.append({
                    'name': name,
                    'api_key': api_key,
                    'routing_key': routing_key
                })
        return res

    def raw(self):
        return {
            'name': self.name,
            'api_key': self.api_key,
            'routing_key': self.routing_key
        }

    def __repr__(self):
        return 'EMVictorOps <name=%s, api_key=%s, routing_key=%s>' % (
            self.name, self.api_key, self.routing_key
        )

    def __eq__(self, other):
        return self.name == other.name and self.api_key == other.api_key and self.routing_key == other.routing_key
