import httplib
import sys
from splunk.clilib.bundle_paths import make_splunkhome_path
sys.path.append(make_splunkhome_path(['etc', 'apps', 'splunk_app_infrastructure', 'bin']))  # noqa
# common packages
import em_declare  # noqa
from em_rest_cloud_configs_impl import EmCloudConfigsInterfaceImpl
from rest_handler import rest_interface_splunkd
from rest_handler.rest_interface_splunkd import route
from rest_handler.session import session


class EmCloudConfigsInterface(rest_interface_splunkd.BaseRestInterfaceSplunkd):

    logger_name = 'rest_cloud_configs'

    @route('/data', methods=['GET', 'POST'])
    def list_or_create_cloud_config(self, request):
        interface_impl = EmCloudConfigsInterfaceImpl(session['authtoken'], self.logger)
        if request.method == 'GET':
            self.logger.info('User triggered list cloud configs')
            response = interface_impl.handle_list_cloud_configs(request)
            return httplib.OK, response
        else:
            self.logger.info('User triggered create cloud config')
            cloud_config = interface_impl.handle_create_cloud_config(request)
            return httplib.CREATED, cloud_config

    @route('/data/{cloud_config_id}', methods=['GET', 'POST', 'DELETE'])
    def operate_on_single_cloud_config(self, request, cloud_config_id):
        interface_impl = EmCloudConfigsInterfaceImpl(session['authtoken'], self.logger)
        if request.method == 'GET':
            self.logger.info('User triggered get cloud config with key %s' % cloud_config_id)
            response = interface_impl.handle_get_cloud_config(request, cloud_config_id)
            return httplib.OK, response
        elif request.method == 'POST':
            self.logger.info('User triggered update cloud config with key %s' % cloud_config_id)
            response = interface_impl.handle_update_cloud_config(request, cloud_config_id)
            return httplib.OK, response
        else:
            self.logger.info('User triggered delete cloud config with key %s' % cloud_config_id)
            response = interface_impl.handle_remove(request, cloud_config_id)
            return httplib.OK, response

    @route('/bulk_delete', methods=['DELETE'])
    def handle_cloud_config_bulk_delete(self, request):
        interface_impl = EmCloudConfigsInterfaceImpl(session['authtoken'], self.logger)
        self.logger.info('User triggered bulk delete on cloud configs')
        response = interface_impl.handle_bulk_delete_cloud_configs(request)
        return httplib.NO_CONTENT, response
