#!/usr/bin/env python2
# CI Build spec generator
#
# Copyright (C) 2018, ARM Limited, All Rights Reserved
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# This file is part of Mbed TLS (https://tls.mbed.org)

"""
Generates Build and Test specification for CI builds. This includes:
- Generating build & test scripts for CI
- Specify platform requirements
"""

import os
import sys
import json
from optparse import OptionParser

CI_META_FILE="cijobs.json"
SH_ENV_FILE="cienv.sh"
BATCH_ENV_FILE="cienv.bat"


def get_cidata():
    cidatafile = os.path.join(os.path.dirname(os.path.realpath(__file__)), CI_META_FILE)
    with open(cidatafile) as f:
        cidata = json.load(f)
    return cidata

def check_scripts(campaign_name):
    try:
        campaign = get_cidata()[campaign_name]
    except KeyError:
        print("Error: Invalid campaign name")
        sys.exit(1)

    for test_name, details in campaign.items():
        for platform in details["platforms"]:
            ci_test_name = "%s-%s" %(test_name, platform)
            yield ci_test_name, details['build'], details.get('environment', {}), details.get('tests', []), platform


def gen_env_file(test_name, build_name, environment, tests, set_cmd, env_file):
    """
    Generate environment script env_file using specified environment set
    command.
    
    :param test_name:
    :param build_name:
    :param environment:
    :param tests:
    :param set_cmd:
    :param env_file:
    :return: 
    """
    with open(env_file, 'w') as f:
        for k, v in environment.items():
            f.write("%s %s=%s\n" % (set_cmd, k, v))
        f.write("%s %s=%s\n" % (set_cmd, 'TEST_NAME', test_name))
        f.write("%s %s=%s\n" % (set_cmd, 'BUILD', build_name))
        for test in tests:
            f.write("%s %s=%s\n" % (set_cmd, 'RUN_%s_TEST' % test.upper(), '1'))
        os.chmod(SH_ENV_FILE, 0o777)


def list_tests(campaign, filename):
    """
    List tests and config
    
    :param campaign:
    :param filename:
    :return: 
    """
    if filename:
        with open(filename, 'w') as f:
            for test_name, build_name, environment, tests, platform in check_scripts(campaign):
                f.write("%s|%s\n" %(test_name, platform))
    else:
        for test_name, build_name, environment, tests, platform in check_scripts(campaign):
            print("%s|%s" %(test_name, platform))


def list_campaigns():
    """
    List campaigns.
    
    :return: 
    """
    for campaign in get_cidata():
        print(campaign)


def gen(test_to_generate):
    """
    Generate script for specified test.
    
    :param campaign:
    :param test_to_generate: 
    :return: 
    """
    for campaign in get_cidata().keys():
        for test_name, build_name, environment, tests, platform in check_scripts(campaign):
            if test_name == test_to_generate:
                if 'windows' in platform.lower():
                    gen_env_file(test_name, build_name, environment, tests, "set", BATCH_ENV_FILE)
                else:
                    gen_env_file(test_name, build_name, environment, tests, "export", SH_ENV_FILE)
                return
    print("Error: Campaign or test not found!")
    sys.exit(1)


if __name__=='__main__':
    parser = OptionParser()
    parser.add_option('-C', '--list-compaigns', action="store_true", dest="list_campaigns", metavar="LIST_CAMPAIGNS")
    parser.add_option('-c', '--list-tests', dest="campaign_name", metavar="CAMPAIGN_NAME")
    parser.add_option('-o', '--tests-out-file', dest="tests_outfile", metavar="TESTS_OUTFILE")
    parser.add_option('-e', '--gen-env', dest="gen_env", metavar="GEN_ENV", help="Generate envorinment")
    opts, args = parser.parse_args()

    if opts.list_campaigns:
        list_campaigns()
    elif opts.campaign_name:
        list_tests(opts.campaign_name, opts.tests_outfile)
    elif opts.gen_env:
        gen(opts.gen_env)
    else:
        parser.print_help()
