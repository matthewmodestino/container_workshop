# Copyright 2016 Splunk Inc. All rights reserved.
# Environment configuration
# N/A
# Standard Python Libraries
import base64
import json
import socket
from collections import namedtuple
import time
from distutils.util import strtobool
import em_declare  # noqa
# Third-Party Libraries
from splunk.appserver.mrsparkle.lib import i18n
import splunk.clilib.cli_common as comm
import splunk.rest
from solnlib.server_info import ServerInfo
from solnlib.packages.splunklib.binding import HTTPError
# Custom Libraries
from em_exceptions import ArgValidationException
from utils.instrument import Instrument
import logging_utility

_ = i18n.ugettext

MONGODB_QUERY_OPTIONS = {"ignoreCase": True}


def merge_dicts(*dicts):
    """
    Merge two dict

    :param *dicts: list of dicts
    :return: dict after being merged
    """
    res = dict()
    for d in dicts:
        res.update(d)
    return res


def get_server_uri():
    """
    :return: current server uri
    """
    return splunk.rest.makeSplunkdUri().rstrip('/')


def is_splunk_cloud(url):
    """
    check whether url is for splunkcloud

    :param url: url to check
    :return: boolean
    """
    if url:
        return url.endswith('cloud.splunk.com') or url.endswith('splunkcloud.com')
    return False


def get_splunkweb_fqdn():
    """
    :return: current server fqdn
    """
    fqdn = socket.getfqdn()
    serverUri = comm.getWebUri()
    return serverUri.replace('127.0.0.1', fqdn)


def get_key_from_dims(dims=None):
    """
    Receive a dictionary, return an unique key

    :param dims: dictionary of dimension
    :return: base64 encoded key
    """
    if dims is None:
        return ''
    return base64.b64encode(json.dumps(dims, sort_keys=True))


def get_dims_from_key(key=None):
    """
    Receive a base64 encoded key, return its dims object

    :param key: base64 encoded key
    :return: dictionary object of dims
    """
    if key is None:
        return dict()
    return json.loads(base64.b64decode(key))


def always_list(v):
    """
    Return a list even it's a value
    """
    return v if isinstance(v, list) else [v]


def get_query_from_request_args(query):
    """
    Converts UI query to mongoDB format
    :param query query string from UI:
    :return:
    """
    if not query:
        return ''
    else:
        try:
            return json.dumps(build_mongodb_query(json.loads(query)))
        # Throws ArgalidationException when we provide invalid JSON for mongodb query, a cleaner
        # exception message than default ValueError returned
        except ValueError:
            raise ArgValidationException(_('Invalid JSON supplied as part of query!'))


def get_list_of_admin_managedby(query, app_name):
    """
    Converts UI query to a list of entities
    that are preceded by 'alert.managedBy:'
    :param query query string from UI
    :return
    """
    if not query:
        return []
    else:
        try:
            type_ids = []
            if type(query) is dict:
                type_ids = query.get('_key', [])
            # Getting a delete all call here, so take all entities
            else:
                type_ids = map(lambda type: type.get('_key'), query)
            return map(lambda type_id: 'alert.managedBy="%s:%s"' % (app_name, type_id), type_ids)
        except ValueError:
            raise ArgValidationException(_('Invalid JSON supplied as part of query!'))


def get_locale_specific_display_names(dimension_display_names, locale, collector_name=None):
    """
    Convert the collector config display name items to flattened locale-specific items
    """
    display_names = []
    for dimension_display_name in dimension_display_names:
        dimension = dimension_display_name.keys()[0]
        display_name = {}
        if collector_name is not None:
            display_name['collector_name'] = collector_name
        display_name['dimension_name'] = dimension
        display_name['display_name'] = dimension_display_name[dimension].get(locale, dimension)
        display_names.append(display_name)
    return display_names


def build_mongodb_query(filters, options=None):
    """
    Ex1: for a input  {"title": ["a*"]}
    this function would return  {"title": {"$regex": "a*", , "$options": "i"}}

    Ex2: for a input {"title": ["a*", "b"]}
    returns:  {"$or": [{"title": {"$regex": "a*", "$options": "i"}}, {"title": {"$regex": "b", , "$options": "i"}} ]}

    Ex3: for a input {"title": ["a*", "b"], "os": ["windows"]}
    returns:  {"$and": [
        {"$or": [{"title": {"$regex": "a*", "$options": "i"}},  {"$regex": "b", , "$options": "i"}} ]},
        {"os":  {"$regex": "windows", , "$options": "i"}}}
    ]}

    NOTE: This code needs to be updated when  https://jira.splunk.com/browse/PBL-9076 is implemented.

    :param filters dictionary, filters object passed by the UI
    :param options dictionary of supported options
    :return mongoDB format query dictionary:
    """

    # if filter is not a dict or options if passed in is not a dict a error will be thrown
    if not isinstance(filters, dict) or (options is not None and not isinstance(options, dict)):
        raise ArgValidationException(_('Filter/options are expected to be a dict'))

    # if filters is empty object return as no query constructions required
    if not bool(filters):
        return filters

    options = options if options else MONGODB_QUERY_OPTIONS
    mongo_options = _construct_mongo_options(options)
    sub_queries = [_construct_query_for(key, value, mongo_options) for key, value in filters.iteritems()]

    # if number of sub-queries is 1 return else wrap it around a "$and"
    return sub_queries[0] if len(sub_queries) == 1 else {"$and": sub_queries}


def _construct_query_for(key, value, options):
    """
    If values is a list it would return
        {"$or": [{"key":"a"}, {"key": "b"}]}

    else it would return
        {"key": "value"}
    :return:
    """
    if not (isinstance(value, list) or isinstance(value, basestring)):
        raise ArgValidationException(_('Value needs to be a string or list'))

    item = {}
    if isinstance(value, list):
        item['$or'] = [{key: _get_regex_search_string(v, options)} for v in value]
    else:
        item[key] = _get_regex_search_string(value, options)
    return item


def _get_regex_search_string(value, options):
    """
    - It is not a good idea to use regex for all searches , instead we should start storing
    data in lowercase always.
    - TO-DO: remove regex for all the searches once we start string data in a case insensitive way.
    """
    if '*' in value:
        # need to do this to to handle a filter like host:m*, .* will allow chars after the match
        value = value.replace('*', '.*')

    return {"$regex": '^%s$' % value, "$options": options}


def _construct_mongo_options(options):
    """
    :param options dictionary of options for regex:
    :return a string for mongo query:
    """
    options_str = ""
    if "ignoreCase" in options and options['ignoreCase']:
        options_str += "i"

    return options_str


def negate_special_mongo_query(query_str):
    """
    Turn a Mongo query in the form of {"$or": [ regex_expr1, regex_expr2, ... ]}
    to its negation: {"$and": [ not_regex_expr1, not_regex_expr2, ...]}
    :param query_str: Mongo query string
    :return: string

    $NOT is not allowed in Mongo for complex expressions
        https://jira.mongodb.org/browse/SERVER-10708
    $NOR is not allowed in Splunk for unknown reasons
        main/src/statestore/MongoStorageProvider.cpp
    Hence this weird hack with negating the Regex.
    """
    query_dict = json.loads(query_str)
    query_dict["$and"] = query_dict.pop("$or")
    for expression in query_dict["$and"]:
        orig_regex = expression["_key"]["$regex"]
        expression["_key"]["$regex"] = "^(?!%s).*$" % orig_regex[1:-1]
    return json.dumps(query_dict)


def Enum(**kwargs):
    """
    :param key=value pairs
    :return a namedtuple
    Sample usage:
    Numbers = Enum(One=1, Two=2)
    Numbers.One -> 1
    Numbers.Two -> 2
    for number in Numbers:
        number
    -> 2
    -> 1
    Note: The order is not guaranteed if you interate through Enum
    """
    return namedtuple('Enum', kwargs.keys())(*kwargs.values())


def string_to_list(string, sep=','):
    """
    Convert a 'sep' separated string into a list
    :param sep: separator, default to ','
    :param string: string to be converted
    :return: list
    """
    return map(lambda el: el.strip(), string.split(sep))


def is_url_valid(session_key, url):
    """
    Check if url is valid
    :param session_key
    :param url: string of url
    :return: boolean
    """
    try:
        response, content = splunk.rest.simpleRequest(url, method='GET', sessionKey=session_key)
        if response.status == 200 or response.status == 400:
            return True
        else:
            return False
    except:
        return False


@Instrument()
def modular_input_should_run(session_key, logger=None):
    """
    Determine if a modular input should run or not.
    Run if and only if:
    1. Node is not a SHC member
    2. Node is an SHC member and is Captain
    @return True if condition satisfies, False otherwise
    """
    if any([not isinstance(session_key, basestring), isinstance(session_key, basestring) and not session_key.strip()]):
        raise ValueError('Invalid session key')

    info = ServerInfo(session_key)
    logger = logging_utility.getLogger() if not logger else logger

    if not info.is_shc_member():
        return True

    timeout = 300  # 5 minutes
    while timeout > 0:
        try:
            # captain election can take time on a rolling restart.
            if info.is_captain_ready():
                break
        except HTTPError as e:
            if e.status == 503:
                logger.warning(
                    'SHC may be initializing on node `%s`. Captain is not ready. Will try again.', info.server_name)
            else:
                logger.exception('Unexpected exception on node `%s`', info.server_name)
                raise
        time.sleep(5)
        timeout -= 5

    # we can fairly be certain that even after 5 minutes if `is_captain_ready`
    # is false, there is a problem
    if not info.is_captain_ready():
        raise Exception(('Error. Captain is not ready even after 5 minutes. node=`%s`.'), info.server_name)

    return info.is_captain()


def convert_to_bool(val):
    try:
        if isinstance(val, bool):
            return val
        if isinstance(val, basestring):
            return bool(strtobool(val))
        return bool(val)
    except:
        raise ValueError('cannot convert %r to bool' % val)
    return False
