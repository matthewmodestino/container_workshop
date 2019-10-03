from os import path
import sys
lib_dir = path.dirname(path.dirname(path.abspath(__file__)))  # noqa
sys.path.append(lib_dir)  # noqa

from splunkd_logging.log import SplunkdLogType
from time import time
from functools import wraps


class Instrument(object):
    """
    This is a decorator class for instrumenting calls and log the instrumented data
    to a designated log file. Usage examples:

    >>> @Instrument()
    >>> def func():
    >>>     pass
    >>> # or set log level and add additional info
    >>> @Instrument('DEBUG', operation='discovery')
    >>> def func():
    >>>     pass
    """

    __metaclass__ = SplunkdLogType
    logger_name = 'instrument'
    log_message_template = 'class={class_name} method={method_name} start_time={start} end_time={end} total_time={diff}'

    def __init__(self, is_log_debug=False, **additional_info):
        """
        :param is_log_debug: a boolean indicating if log level should be 'DEBUG' or not, otherwise log level is 'INFO'
        :param additional_info: additional information in key-value pairs to be logged with instrument message
        """
        self.log_level = 'DEBUG' if is_log_debug else 'INFO'
        self.logger.setLevel(self.log_level)
        self.additional_info_dict = additional_info

    def log_message(self, msg):
        """
        this method should be used to handle logging of messages inside of Instrument class
        instead of using `self.logger` directly. It determines log method based on the level set
        """
        log_method = self.logger.info
        if self.log_level == 'DEBUG':
            log_method = self.logger.debug
        log_method(msg)

    def get_log_message(self, class_name, method_name, start_time, end_time, time_diff):
        message = Instrument.log_message_template.format(
            class_name=class_name,
            method_name=method_name,
            start=start_time,
            end=end_time,
            diff=time_diff
        )
        if self.additional_info_dict != {}:
            additional_info_message = ' '.join(
                ['%s=%s' % (k, v) for k, v in self.additional_info_dict.iteritems()]
            )
            message += ' ' + additional_info_message
        return message

    def __call__(self, f):
        @wraps(f)
        def wrapper(decorated_self=None, *args, **kwargs):
            start_time = time()
            class_name = None
            if decorated_self:
                retval = f(decorated_self, *args, **kwargs)
                class_name = decorated_self.__class__.__name__
                # if it's a classmethod
                if class_name == 'type':
                    class_name = decorated_self.__name__
            else:
                retval = f(*args, **kwargs)
            end_time = time()
            time_diff = end_time - start_time

            method_name = f.__name__ if hasattr(f, '__name__') else str(f)
            log_message = self.get_log_message(class_name, method_name, start_time, end_time, time_diff)
            self.log_message(log_message)
            return retval
        return wrapper
