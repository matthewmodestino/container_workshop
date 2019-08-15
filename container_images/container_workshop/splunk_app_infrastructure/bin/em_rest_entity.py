# standard packages
import httplib
import sys
from splunk.clilib.bundle_paths import make_splunkhome_path
sys.path.append(make_splunkhome_path(['etc', 'apps', 'splunk_app_infrastructure', 'bin']))  # noqa
# app sepcific packages
from em_rest_entity_impl import EmEntityInterfaceImpl
# common packages
import em_declare  # noqa
from rest_handler import rest_interface_splunkd
from rest_handler.rest_interface_splunkd import route
from rest_handler.session import session


class EmEntityInterface(rest_interface_splunkd.BaseRestInterfaceSplunkd):

    logger_name = 'rest_entity'

    @route('/data', methods=['GET', 'POST'])
    def list_or_create_entities(self, request):
        '''
        this handler handles:
            1. multiple or all entities data retrieval (GET)
            2. entity creation (POST)

        :param request an request object
        :return tuple<http status code, json response>
        '''
        interface_impl = EmEntityInterfaceImpl(session['authtoken'], self.logger)
        if request.method == 'GET':
            self.logger.info('User triggered LIST entities')
            response = interface_impl.handle_list_entities(request)
            return httplib.OK, response
        else:
            self.logger.info('User triggered CREATE entity')
            entity = interface_impl.handle_create_entity(request)
            return httplib.CREATED, entity

    @route('/data/{entity_id}', methods=['GET', 'POST', 'DELETE'])
    def operate_on_single_entity(self, request, entity_id):
        '''
        this handler handles:
            1. individual entity data retrieval (GET)
            2. individual entity update (POST)
            3. individual entity deletion (DELETE)

        :param request an request object
        :return tuple<http status code, json response>
        '''
        interface_impl = EmEntityInterfaceImpl(session['authtoken'], self.logger)
        if request.method == 'GET':
            self.logger.info('User triggered GET entity with key %s' % entity_id)
            response = interface_impl.handle_get_entity(request, entity_id)
            return httplib.OK, response
        elif request.method == 'POST':
            self.logger.info('User triggered UPDATE entity with key %s' % entity_id)
            response = interface_impl.handle_update_entity(request, entity_id)
            return httplib.OK, response
        else:
            self.logger.info('User triggered DELETE entity with key %s' % entity_id)
            response = interface_impl.handle_delete_entity(request, entity_id)
            return httplib.OK, response

    @route('/bulk_delete', methods=['DELETE'])
    def handle_entity_bulk_delete(self, request):
        '''
        this handler handles bulk deletion on entities based on filter

        :param request an request object
        :return tuple<http status code, json response>
        '''
        interface_impl = EmEntityInterfaceImpl(session['authtoken'], self.logger)
        self.logger.info('User triggered BULK DELETE on entities')
        response = interface_impl.handle_bulk_delete_entities(request)
        return httplib.NO_CONTENT, response

    @route('/metadata', methods=['GET'])
    def handle_entity_metadata(self, request):
        '''
        this handler handles entity metadata retrieval, metadata includes but not limited to:
            1. total entity count
            2. (more to be added)

        :param request an request object
        :return tuple<http status code, json response>
        '''
        interface_impl = EmEntityInterfaceImpl(session['authtoken'], self.logger)
        self.logger.info('User requested METADATA of entities')
        response = interface_impl.handle_metadata(request)
        return httplib.OK, response

    @route('/dimension_summary', methods=['GET'])
    def handle_entity_dimension_summary(self, request):
        '''
        this handler handles dimension summary of entities retrieval, dimension summary contains
        information about the list of dimensions and their corresponding value set presented in
        the entity collection

        :param request an request object
        :return tuple<http status code, json response>
        '''
        interface_impl = EmEntityInterfaceImpl(session['authtoken'], self.logger)
        self.logger.info('User requested DIMENSIONS SUMMARY of entities')
        response = interface_impl.handle_dimension_summary(request)
        return httplib.OK, response

    @route('/metric_name', methods=['GET'])
    def handle_entity_metric_names(self, request):
        '''
        this handler handles metric names retrieval, metric names are the names of all metric
        that are related to entities

        :param request an request object
        :return tuple<http status code, json response>
        '''
        interface_impl = EmEntityInterfaceImpl(session['authtoken'], self.logger)
        self.logger.info('User requested METRIC NAMES of entities')
        response = interface_impl.handle_metric_name(request)
        return httplib.OK, response

    @route('/metric_data', methods=['GET'])
    def handle_entity_metric_data(self, request):
        '''
        this handler handles metric data retrieval, which takes a metric name as part of query
        parameter, and returns its value of all entities.

        :param request an request object
        :return tuple<http status code, json response>
        '''
        interface_impl = EmEntityInterfaceImpl(session['authtoken'], self.logger)
        self.logger.info('User requested METRIC DATA of entities')
        response = interface_impl.handle_metric_data(request)
        return httplib.OK, response
