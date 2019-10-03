import httplib
import sys
from splunk.clilib.bundle_paths import make_splunkhome_path
sys.path.append(make_splunkhome_path(['etc', 'apps', 'splunk_app_infrastructure', 'bin']))  # noqa
# common packages
import em_declare  # noqa
from em_rest_groups_impl import EmGroupsInterfaceImpl
from rest_handler import rest_interface_splunkd
from rest_handler.rest_interface_splunkd import route
from rest_handler.session import session


class EmGroupsInterface(rest_interface_splunkd.BaseRestInterfaceSplunkd):

    logger_name = 'rest_group'

    @route('/data', methods=['GET', 'POST'])
    def list_or_create_group(self, request):
        interface_impl = EmGroupsInterfaceImpl(session['authtoken'], self.logger)
        if request.method == 'GET':
            self.logger.info('User triggered list groups')
            response = interface_impl.handle_list_groups(request)
            return httplib.OK, response
        else:
            self.logger.info('User triggered create group')
            group = interface_impl.handle_create_group(request)
            return httplib.CREATED, group

    @route('/data/{group_id}', methods=['GET', 'POST', 'DELETE'])
    def operate_on_single_group(self, request, group_id):
        interface_impl = EmGroupsInterfaceImpl(session['authtoken'], self.logger)
        if request.method == 'GET':
            self.logger.info('User triggered get group with key %s' % group_id)
            response = interface_impl.handle_get_group(request, group_id)
            return httplib.OK, response
        elif request.method == 'POST':
            self.logger.info('User triggered update group with key %s' % group_id)
            response = interface_impl.handle_update_group(request, group_id)
            return httplib.OK, response
        else:
            self.logger.info('User triggered delete group with key %s' % group_id)
            response = interface_impl.handle_remove(request, group_id)
            return httplib.OK, response

    @route('/metadata', methods=['GET'])
    def handle_group_metadata(self, request):
        interface_impl = EmGroupsInterfaceImpl(session['authtoken'], self.logger)
        self.logger.info('User requested metadata for group')
        response = interface_impl.handle_metadata(request)
        return httplib.OK, response

    @route('/count', methods=['GET'])
    def handle_group_metadata_count(self, request):
        interface_impl = EmGroupsInterfaceImpl(session['authtoken'], self.logger)
        self.logger.info('User requested count for group')
        response = interface_impl.handle_count(request)
        return httplib.OK, response

    @route('/bulk_delete', methods=['DELETE'])
    def handle_entity_bulk_delete(self, request):
        interface_impl = EmGroupsInterfaceImpl(session['authtoken'], self.logger)
        self.logger.info('User triggered bulk delete on groups')
        response = interface_impl.handle_bulk_delete_groups(request)
        return httplib.NO_CONTENT, response
