import functools
import urllib
from service_manager.splunkd.license import LicenseManager


def internalize_rest_exception(exception_type):
    """
    Decorator function that internalizes custom exception type to EAI compatible exceptions

    Usage:
        @internalize_rest_exception(RestHandlerException)
        def your_rest_handler(self, args):
            .....
        # any exception raised inside of your_rest_handler will be converted to RestHandlerException

    :param exception_type: Exception class, preferrably subclass of em_rh_exceptions.EmRestException
    """
    def rest_exception_decorator(rest_handler_func):
        @functools.wraps(rest_handler_func)
        def wrapper(*args):
            try:
                rest_handler_func(*args)
            except Exception as e:
                raise exception_type(e.message)
        return wrapper
    return rest_exception_decorator


def get_check_internal_log_message(is_light=False):
    if is_light:
        return ('[[/app/splunk_app_infrastructure/metrics_analysis?ts=true|'
                'SAI internal logs.]]')
    else:
        query = urllib.quote('search index=_internal sourcetype="splunk_app_infrastructure"')
        return ('[[/app/splunk_app_infrastructure/search?q=%s|'
                'SAI internal logs.]]') % query


def is_splunk_light(server_uri, session_key, app):
    license_manager = LicenseManager(server_uri=server_uri,
                                     session_key=session_key,
                                     app=app)
    licenses = license_manager.load()['entry']
    for license in licenses:
        if license['content']['label'] != 'Splunk Insights for Infrastructure':
            return False
    return True
