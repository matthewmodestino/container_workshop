import os
import logging
import logging.handlers
from splunk.clilib.bundle_paths import make_splunkhome_path

DEFAULT_LOGGING_FORMAT = "%(asctime)s - pid:%(process)d tid:%(threadName)s %(levelname)-s  %(module)s:%(lineno)d - %(message)s"  # noqa
DEFAULT_MAX_FILE_SIZE = 25*1024*1024  # 25 MB log size before rollover
# To change logging level globally for debugging purpose, change this to 'DEBUG'
DEFAULT_LOG_LEVEL = 'INFO'

DEFAULT_LOG_FILE_PREFIX = 'sai'


def setup_logger(logger_name,
                 level=DEFAULT_LOG_LEVEL,
                 max_file_size=DEFAULT_MAX_FILE_SIZE,
                 backup_count=5,
                 logging_foramt=DEFAULT_LOGGING_FORMAT):
    """
    set up and return a logger
    """
    log_file_name = '%s.log' % logger_name
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)
    base_log_dir = make_splunkhome_path(['var', 'log', 'splunk'])
    log_file_path = os.path.join(base_log_dir, log_file_name)
    if not os.path.exists(base_log_dir):
        os.makedirs(base_log_dir)
    splunk_log_handler = logging.handlers.RotatingFileHandler(log_file_path, mode='a',
                                                              maxBytes=max_file_size,
                                                              backupCount=backup_count)
    splunk_log_handler.setFormatter(logging.Formatter(logging_foramt))
    logger.addHandler(splunk_log_handler)
    return logger


class SplunkdLogType(type):
    """
    SplunkdLogType is a metaclass that creates a logger (and set it up with Splunk)
    for the class that uses it, if that class has not created a logger itself

    To set up a custom logger for a class, either:
    1. specify a class attribtue called 'logger_name' and its value is the
    log file name (without the .log file extension).
    2. the log file name will be the module name of the class,
    if module name is '__main__' the class name will be used.

    To change logging level of logger of a specific class:
    ```code
    self.logger.setLevel('DEBUG') # or any other level
    ```
    """
    def __init__(self, name, bases, dct):
        super(SplunkdLogType, self).__init__(name, bases, dct)
        if 'logger' not in dct:
            if 'logger_name' in dct:
                if self.logger_name.startswith(DEFAULT_LOG_FILE_PREFIX):
                    logger_name = self.logger_name
                else:
                    logger_name = '{}_{}'.format(DEFAULT_LOG_FILE_PREFIX, self.logger_name)
            else:
                module_name = dct['__module__'].split('.')[-1]
                logger_suffix = name if module_name == '__main__' else module_name
                logger_name = '{}_{}'.format(DEFAULT_LOG_FILE_PREFIX, logger_suffix)
            self.logger = setup_logger(logger_name)
