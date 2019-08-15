# standard packages
import httplib
import sys
from splunk.clilib.bundle_paths import make_splunkhome_path
sys.path.append(make_splunkhome_path(['etc', 'apps', 'splunk_app_infrastructure', 'bin']))  # noqa
# app sepcific packages
from em_rest_alert_impl import EmAlertInterfaceImpl
# common packages
import em_declare  # noqa
from rest_handler import rest_interface_splunkd
from rest_handler.rest_interface_splunkd import route
from rest_handler.session import session


class EmAlertInterface(rest_interface_splunkd.BaseRestInterfaceSplunkd):

    logger_name = 'rest_alert'

    @route('/data', methods=['GET', 'POST'])
    def list_or_create_alerts(self, request):
        '''
        Use-cases:
            1. multiple alert definitions retrieval (GET)
            2. alert creation (POST)

        :param request an request object
        :return tuple<http status code, json response>
        '''
        interface_impl = EmAlertInterfaceImpl(session['authtoken'], self.logger)
        if request.method == 'GET':
            self.logger.info('User triggered LIST alerts')
            response = interface_impl.handle_list_alerts(request)
            return httplib.OK, response
        else:
            self.logger.info('User triggered CREATE alert')
            alert = interface_impl.handle_create_alert(request)
            return httplib.CREATED, alert

    @route('/data/{alert_name}', methods=['GET', 'POST', 'DELETE'])
    def operate_on_single_alert(self, request, alert_name):
        '''
        Use-cases:
            1. individual alert data retrieval by alert name (GET)
            2. individual alert update for given alert name(POST)
            3. individual alert deletion by alert name (DELETE)

        :param request an request object
        :return tuple<http status code, json response>
        '''
        interface_impl = EmAlertInterfaceImpl(session['authtoken'], self.logger)
        if request.method == 'GET':
            self.logger.info('User triggered GET for alert with name %s' % alert_name)
            response = interface_impl.handle_get_alert(request, alert_name)
            return httplib.OK, response
        elif request.method == 'POST':
            self.logger.info('User triggered UPDATE for alert with name %s' % alert_name)
            response = interface_impl.handle_update_alert(request, alert_name)
            return httplib.OK, response
        else:
            self.logger.info('User triggered DELETE for alert with name %s' % alert_name)
            response = interface_impl.handle_delete_alert(request, alert_name)
            return httplib.OK, response
