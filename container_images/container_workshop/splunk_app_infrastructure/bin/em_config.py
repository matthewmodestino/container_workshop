# Copyright 2016 Splunk Inc. All rights reserved.
# Environment configuration
# N/A
# Standard Python Libraries

sai_config = {
  'featureFlag': {
    'isMultiCloudEnabled': 0
  }
}


def isMultiCloudEnabled():
    """
    check whether Multi Cloud is enabled for SAI
    :return: boolean
    """
    return sai_config['featureFlag']['isMultiCloudEnabled']
