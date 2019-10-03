# Copyright 2016 Splunk Inc. All rights reserved.
# Environment configuration
# N/A
# Standard Python Libraries
import os
import sys
import re
import site
# Third-Party Libraries
# N/A
# Custom Libraries
import em_constants

libs = ['external_lib', 'common_libs']

pattern = re.compile(r"[\\/]etc[\\/]apps[\\/][^\\/]+[\\/]bin[\\/]?$")
new_paths = [path for path in sys.path if not pattern.search(
    path) or em_constants.APP_NAME in path]

for lib_name in libs:
    # Add lib folder
    new_paths.insert(0, os.path.sep.join([os.path.dirname(__file__), lib_name]))

sys.path = new_paths

for lib_name in libs:
    # NOTE: this is needed because package in external_lib directory
    # could be a namespace package
    site.addsitedir(os.path.sep.join([os.path.dirname(__file__), lib_name]))
