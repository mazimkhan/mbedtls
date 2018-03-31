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


class JobsParser(object):
    """
    Parser for cijobs.json
    """
    CI_JOBS_KEY_TESTS = "tests"
    CI_JOBS_KEY_CAMPAIGNS = "campaigns"
    CI_JOBS_KEY_JOBS = "jobs"

    def __init__(self):
        """
        Initialize parser state.
        """
        self.tests = {}
        self.campaigns = {}
        self.jobs = {}

    def validate_root(self, data):
        """
        Validate root element format 
        
        :param data:  Data read from cijobs.json
        :return: 
        """
        for mandatory_keys in [self.CI_JOBS_KEY_TESTS,
                               self.CI_JOBS_KEY_CAMPAIGNS,
                               self.CI_JOBS_KEY_JOBS]:
            assert mandatory_keys in data, \
                "Mandatory key '%s' not found in cijobs.json" % mandatory_keys

    @staticmethod
    def validate_test(name, test):
        """
        Validate a test field.
        
        :param name: Test name
        :param test: Test details
        :return: 
        """
        assert ('build' in test) or ('script' in test),\
            "Neither 'build' nor 'script' field present in test '%s'" % name
        if 'environment' in test:
            assert type(test['environment']) == dict,\
                "Test '%s' field 'environment' should be a dictionary." % name
        if 'tests' in test:
            assert type(test['tests']) == list,\
                "Test '%s' field 'tests' should be a list." % name
        assert "platforms" in test,\
            "Mandatory field 'platforms' not in test '%s'" % name
        assert type(test["platforms"]) == list, \
            "Test '%s' field 'platforms' should be a list." % name

    @staticmethod
    def validate_job(name, job):
        """
        Validate job field.
        
        :param name: 
        :param job: 
        :return: 
        """
        assert name is not None and len(name) > 0, \
            "Invalid job name '%s'" % name
        assert type(job) == dict, \
            "Job '%s' value should be a dictionary." % name
        assert JobsParser.CI_JOBS_KEY_CAMPAIGNS in job,\
            "Mandatory field '%s' missing in job '%s'" % \
            (JobsParser.CI_JOBS_KEY_CAMPAIGNS, name)
        assert type(job[JobsParser.CI_JOBS_KEY_CAMPAIGNS]) == list,\
            "Field '%s' should be a list in job '%s'" %\
            (JobsParser.CI_JOBS_KEY_CAMPAIGNS, name)
        assert len(job[JobsParser.CI_JOBS_KEY_CAMPAIGNS]) != 0, \
            "No campaigns specified in job '%s'" % name

    def parse(self, data):
        """
        Parse data from cijobs.json
        
        :param data: Data read from cijobs.json 
        :return: 
        """
        self.validate_root(data)
        self.tests = data[self.CI_JOBS_KEY_TESTS]
        for name, test in self.tests.items():
            assert name is not None and len(name) > 0,\
                "Invalid test name '%s'" % name
            self.validate_test(name, test)
        self.campaigns = data[self.CI_JOBS_KEY_CAMPAIGNS]
        for name, campaign in self.campaigns.items():
            assert name is not None and len(name) > 0, \
                "Invalid campaign name '%s'" % name
            assert type(campaign) == list, \
                "Campaign '%s' should be a list of test names." % name
        self.jobs = data[self.CI_JOBS_KEY_JOBS]
        ret = {}
        for name, job in self.jobs.items():
            self.validate_job(name, job)
            # Construct a flat Job to test dict
            job_campaigns = job[self.CI_JOBS_KEY_CAMPAIGNS]
            for campaign_name in job_campaigns:
                assert campaign_name in self.campaigns,\
                    "Unknown campaign %s" % campaign_name
                campaign = self.campaigns[campaign_name]
                for test_name in campaign:
                    assert test_name in self.tests,\
                        "Unknown test %s" % test_name
                    test = self.tests[test_name]
                    if name in ret:
                        ret[name][test_name] = test
                    else:
                        ret[name] = {test_name: test}
        return ret


def get_ci_data():
    """
    Read CI campaign data from cijobs.json and return.

    :return:
    """
    ci_data_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), CI_META_FILE)
    with open(ci_data_file) as f:
        ci_data = json.load(f)
        parser = JobsParser()
        jobs = parser.parse(ci_data)
    return jobs


def get_tests_for_campaign(campaign_name):
    """
    Yields tests with details for passed campaign. Following data is returned
    as part of each test:
      CI test name - A descriptive name used by the CI to run test in parallel.
      build name - Build type. Example: make.
      environment - Dictionary containing environment variables for the test.
      tests - List of tests to run.
      platform - Platform on which the test has to run.

    :param campaign_name: Campaign name
    :return: yield tests with details
    """
    get_ci_data()
    try:
        campaign = get_ci_data()[campaign_name]
    except KeyError, e:
        print str(e)
        print("Error: Invalid campaign name '%s'" % campaign_name)
        sys.exit(1)

    for test_name, details in campaign.items():
        for platform in details["platforms"]:
            ci_test_name = "%s-%s" %(test_name, platform)
            yield ci_test_name, details.get('build', None),\
                details.get('script', None),\
                details.get('environment', {}),\
                details.get('tests', []), platform


def gen_env_file(test_name, build_name, script, environment, tests, set_cmd,
                 env_file):
    """
    Generates environment script env_file with test info passed as environment
     variables.

    :param test_name: A descriptive test name describing test, environment and
                      platform. Example: cmake-asan-debian-x64
    :param build_name: Build name. Example: make, cmake etc.
    :param script: Script to run. Example: tests/scripts/all.sh
    :param environment: Build & Test environment. Example: {'CC':'gcc'}
    :param tests: Tests to run. Example: [BASIC, FULL]
    :param set_cmd: Example: 'set' for Windows, 'export' for POSIX
    :param env_file: Output environment file.
    :return: 
    """
    with open(env_file, 'w') as f:
        for k, v in environment.items():
            f.write("%s %s=%s\n" % (set_cmd, k, v))
        f.write("%s %s=%s\n" % (set_cmd, 'TEST_NAME', test_name))
        assert build_name or script, "Neither BUILD nor SCRIPT specified for test %s" % test_name
        if build_name:
            f.write("%s %s=%s\n" % (set_cmd, 'BUILD', build_name))
        if script:
            f.write("%s %s=%s\n" % (set_cmd, 'SCRIPT', script))
        for test in tests:
            f.write("%s %s=%s\n" % (set_cmd, 'RUN_%s_TEST' % test.upper(), '1'))
        os.chmod(env_file, 0o777)


def list_tests(campaign, filename):
    """
    List tests with their descriptive name and platform. This function is used
    in CI discover tests and target platform.
    
    :param campaign: Campaign name from cijobs.json
    :param filename: Output file name.
    :return: 
    """
    if filename:
        with open(filename, 'w') as f:
            for test_name, build_name, script, environment, tests, platform\
                    in get_tests_for_campaign(campaign):
                f.write("%s|%s\n" %(test_name, platform))
    else:
        for test_name, build_name, script, environment, tests, platform\
                in get_tests_for_campaign(campaign):
            print("%s|%s" %(test_name, platform))


def list_campaigns():
    """
    List campaigns. Generally used for debugging.
    
    :return: 
    """
    for campaign in get_ci_data():
        print(campaign)


def gen_environment_for_campaign(test_to_generate):
    """
    Generate environment script for specified test. The test is a descriptive
    test name output by '-c campaign_name' option to this script.

    :param test_to_generate: Descriptive test name. Ex: cmake-asan-debian-x64
    :return: 
    """
    for campaign in get_ci_data().keys():
        for test_name, build_name, script, environment, tests, platform\
                in get_tests_for_campaign(campaign):
            if test_name == test_to_generate:
                set_cmd, env_file = ('set', BATCH_ENV_FILE) if 'windows'\
                    in platform.lower() else ('export', SH_ENV_FILE)
                gen_env_file(test_name, build_name, script, environment,
                             tests, set_cmd, env_file)
                return
    print("Error: Campaign or test not found!")
    sys.exit(1)


if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option('-C', '--list-compaigns', action="store_true",
                      dest="list_campaigns", metavar="LIST_CAMPAIGNS",
                      help="List campaigns.")
    parser.add_option('-c', '--list-tests', dest="campaign_name",
                      metavar="CAMPAIGN_NAME", help="List tests for campaign.")
    parser.add_option('-o', '--tests-out-file', dest="tests_outfile",
                      metavar="TESTS_OUTFILE",
                      help="Output test list in this file.")
    parser.add_option('-e', '--gen-env', dest="gen_env", metavar="GEN_ENV",
                      help="Generate environment file.")
    opts, args = parser.parse_args()

    if opts.list_campaigns:
        list_campaigns()
    elif opts.campaign_name:
        list_tests(opts.campaign_name, opts.tests_outfile)
    elif opts.gen_env:
        gen_environment_for_campaign(opts.gen_env)
    else:
        parser.print_help()
