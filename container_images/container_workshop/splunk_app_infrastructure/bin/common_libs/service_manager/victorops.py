import urllib2
import json
from . import BaseServiceManager, BaseServiceManagerException

INTEGRATION_URL = "https://alert.victorops.com/integrations/generic/20131114/alert"


class VictorOpsCouldNotSendAlertException(BaseServiceManagerException):
    def __init__(self, message):
        super(BaseServiceManagerException, self).__init__(message)


class VictorOpsManager(BaseServiceManager):

    logger_name = 'monitoring_victorops_manager'

    """
    Manager class that handles all kinds of communication
    with VictorOps REST API
    """
    def __init__(self, api_key, routing_key, monitoring_tool):
        self.api_key = api_key
        self.routing_key = routing_key
        self.monitoring_tool = monitoring_tool

    def send_incident(self, incident):
        """
        send incident to VictorOps

        :param incident: a dict that contains key/value info of the incident
        """
        try:
            url = "%s/%s/%s" % (INTEGRATION_URL, self.api_key, self.routing_key)
            headers = {
                'content-type': 'application/json',
            }
            incident.update({
                'monitoring_tool': self.monitoring_tool
            })
            req = urllib2.Request(url, json.dumps(incident), headers)
            response = urllib2.urlopen(req)
            message, status_code = response.msg, response.code
            if status_code != 200:
                raise VictorOpsCouldNotSendAlertException("status_code=%s, message=%s" % (status_code, message))
        except Exception as e:
            self.logger.error("Failed to send incident to VictorOps because: %s", e.message)
            raise VictorOpsCouldNotSendAlertException(e.message)
