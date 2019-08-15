from em_exceptions import ThresholdInvalidArgsException

# Splunk packages
from splunk.appserver.mrsparkle.lib import i18n

_ = i18n.ugettext


class EMThreshold(object):
    """
    EMThreshold represents one em_thresholds entry
    """

    def __init__(self,
                 info_min=None,
                 info_max=None,
                 warning_min=None,
                 warning_max=None,
                 critical_min=None,
                 critical_max=None):

        self.info_min = info_min
        self.info_max = info_max
        self.warning_min = warning_min
        self.warning_max = warning_max
        self.critical_min = critical_min
        self.critical_max = critical_max

        self._validate_thresholds(['info', 'warning', 'critical'])

    def _validate_thresholds(self, threshold_types):
        """
        Validates the min max values
        """
        for threshold_type in threshold_types:
            values = []
            values.append(getattr(self, '%s_min' % threshold_type, None))
            values.append(getattr(self, '%s_max' % threshold_type, None))
            if not (all(v is not None for v in values) or all(v is None for v in values)):
                raise ThresholdInvalidArgsException(_('Invalid values for thresholds provided'))

            if values[0] is not None and values[0] > values[1]:
                raise ThresholdInvalidArgsException(_('Threshold min can not be greater than max'))
