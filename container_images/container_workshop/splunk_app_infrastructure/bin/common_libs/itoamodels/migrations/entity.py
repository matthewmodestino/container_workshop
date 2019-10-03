"""
Copyright (C) 2018 Splunk Inc. All Rights Reserved.
"""

from collections import OrderedDict


migrations = OrderedDict()

"""
Add migration functions as needed. For example:

def v1_0_1(data);
    data['new_field'] = data['old_field']
    del data['old_field']
    return data

# Any model versions <= 1.0.1 will run the above function
migrations['1.0.1'] = v1_0_1

# Functions will execute in the order they were added,
# e.g. v2_0_0 will run after v1_0_1 for model versions <= 1.0.1
migrations['2.0.0'] = v2_0_0
"""
