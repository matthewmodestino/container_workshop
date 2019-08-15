import logging
import logging.handlers
import splunk
import os


MAX_FILE_SIZE = 10*1024  # 10 MB log size before rollover
DEFAULT_LOGGING_FORMAT = "%(asctime)s - pid:%(process)d %(levelname)-s %(module)s:%(lineno)d - %(message)s"


def getLogger(
        logging_file_name="splunk_app_infra.log",
        logging_stanza_name="python",
        log_format=DEFAULT_LOGGING_FORMAT):
    """
    source : http://dev.splunk.com/view/logging/SP-CAAAFCN
    """
    logger = logging.getLogger('splunk_app_infra')
    SPLUNK_HOME = os.environ.get('SPLUNK_HOME', '~')
    LOGGING_DEFAULT_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log.cfg')
    LOGGING_LOCAL_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log-local.cfg')
    LOGGING_STANZA_NAME = logging_stanza_name
    LOGGING_FILE_NAME = logging_file_name
    BASE_LOG_PATH = os.path.join(SPLUNK_HOME, 'var', 'log', 'splunk')
    COMPLETE_PATH = os.path.join(BASE_LOG_PATH, LOGGING_FILE_NAME)
    if not os.path.exists(BASE_LOG_PATH):
        os.makedirs(BASE_LOG_PATH)
    LOGGING_FORMAT = log_format
    file_handler = logging.FileHandler(COMPLETE_PATH)
    splunk_log_handler = logging.handlers.RotatingFileHandler(COMPLETE_PATH, mode='a',
                                                              maxBytes=MAX_FILE_SIZE,
                                                              backupCount=5)
    splunk_log_handler.setFormatter(logging.Formatter(LOGGING_FORMAT))
    logger.addHandler(file_handler)
    logger.addHandler(splunk_log_handler)
    splunk.setupSplunkLogger(logger, LOGGING_DEFAULT_CONFIG_FILE, LOGGING_LOCAL_CONFIG_FILE, LOGGING_STANZA_NAME)
    logger.setLevel(logging.WARNING)
    return logger
