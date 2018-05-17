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
- Generating list of tests for a CI job
- Provide target platform information for each test
- Generate execution environment for a given test to be executed by ciscript.sh/bat
"""

import os
import sys
import json
from optparse import OptionParser

CI_META_FILE="cijobs.json"
SH_ENV_FILE="cienv.sh"
BATCH_ENV_FILE="cienv.bat"

# JSON format keys
JSON_ROOT_KEY_TESTS = "tests"
JSON_ROOT_KEY_CAMPAIGNS = "campaigns"
JSON_ROOT_KEY_JOBS = "jobs"
JSON_CAMPAIGN_KEY_PLATFORMS = "platforms"
JSON_CAMPAIGN_KEY_TESTS = "tests"
JSON_TEST_KEY_BUILD = "build"
JSON_TEST_KEY_SCRIPT = "script"
JSON_TEST_KEY_ENV = "environment"
JSON_TEST_KEY_CONFIG = "config"
JSON_TEST_KEY_TESTS = "tests"
JSON_CONFIG_KEY_CONFIG = "config"
JSON_CONFIG_KEY_SET = "set"
JSON_CONFIG_KEY_UNSET = "unset"


class CIBuilderException(Exception):
    pass


class Config(object):
    """
    """

    def __init__(self):
        """
        """
        self.config = None
        self.set = []
        self.unset = []

    @staticmethod
    def parse(test_name, data):
        """
        """
        config = Config()
        assert type(data) == dict, \
            "'%s' in test '%s' should be a dict" % \
            (JSON_TEST_KEY_CONFIG, test_name)
        if JSON_CONFIG_KEY_CONFIG in data:
            config.config = data[JSON_CONFIG_KEY_CONFIG]
        if JSON_CONFIG_KEY_SET in data:
            flags = data[JSON_CONFIG_KEY_SET]
            assert type(flags) == list, \
                "'%s' data in config for test %s should be a list" % \
                (JSON_CONFIG_KEY_SET, test_name)
            for flag in flags:
                assert type(flag) in [str, unicode], \
                    "Flags in '%s' list in config for test '%s' should string type." %\
                    (JSON_CONFIG_KEY_SET, test_name)
                config.set.append(flag)
        if JSON_CONFIG_KEY_UNSET in data:
            flags = data[JSON_CONFIG_KEY_UNSET]
            assert type(flags) == list, \
                "'%s' data in config for test %s should be a list" % \
                (JSON_CONFIG_KEY_UNSET, test_name)
            for flag in flags:
                assert type(flag) in [str, unicode], \
                    "Flags in '%s' list in config for test '%s' should string type." %\
                    (JSON_CONFIG_KEY_UNSET, test_name)
                config.unset.append(flag)
        return config


class TestBase(object):
    """
    Parser and container for test data.
    """

    def __init__(self, name, platforms, config=None, build=None, script=None,
                 environment=None, tests=None):
        """
        """
        self.name = name
        self.config = config
        self.build = build
        self.script = script
        self.environment = environment if environment else []
        self.tests = tests if tests else []
        self.platforms = platforms

    def get_platform_by_name(self, test_n_platform_name):
        """
        """
        for platform in self.platforms:
            if test_n_platform_name == "%s-%s" % (self.name, platform):
                return platform
        return None

    def get_test_names(self):
        """
        """
        return ["%s-%s" % (self.name, platform) for platform in self.platforms]

    def gen_environment(self, platform):
        """
        Generate environment script for specified test. The test is a descriptive
        test name output by '-l job_name' option to this script.

        :param platform: Platform name
        """
        assert platform in self.platforms, \
            "Platform '%s' not found in test '%s'" % (platform, self.name)
        set_cmd, env_file = ('set', BATCH_ENV_FILE) if 'windows'\
            in platform.lower() else ('export', SH_ENV_FILE)
        self.gen_env_file(set_cmd, env_file)

    def gen_env_file(self, set_cmd, env_file):
        """
        Generates environment script env_file from test details.

        :param set_cmd: Example: 'set' for Windows, 'export' for POSIX
        :param env_file: Output environment file.
        """
        with open(env_file, 'w') as f:
            for k, v in self.environment.items():
                f.write("%s %s=%s\n" % (set_cmd, k, v))
            f.write("%s %s=%s\n" % (set_cmd, 'TEST_NAME', self.name))
            assert self.build or self.script, \
                "Neither BUILD nor SCRIPT specified for test %s" % self.name
            if self.config:
                f.write("%s %s=%s\n" % (set_cmd, 'CONFIG', self.config))
            if self.build:
                f.write("%s %s=%s\n" % (set_cmd, 'BUILD', self.build))
            if self.script:
                f.write("%s %s=%s\n" % (set_cmd, 'SCRIPT', self.script))
            for test in self.tests:
                f.write("%s %s=%s\n" % (set_cmd, 'RUN_%s_TEST' % test.upper(), '1'))
            mbedtls_root = os.path.realpath(__file__)
            # mbedtls root is 3 levels up
            for i in range(3):
                mbedtls_root = os.path.dirname(mbedtls_root)
            f.write("%s MBEDTLS_ROOT=%s\n" % (set_cmd, mbedtls_root))
            os.chmod(env_file, 0o777)

    @staticmethod
    def validate_test(name, ci_data):
        """
        Validate a test field. It asserts required test format.

        :param name: Test name
        :param test: Test details
        """
        assert name in ci_data[JSON_ROOT_KEY_TESTS], \
            "Test %s not defined in 'tests'" % name
        test = ci_data[JSON_ROOT_KEY_TESTS][name]
        assert (JSON_TEST_KEY_BUILD in test) or (JSON_TEST_KEY_SCRIPT in test),\
            "Neither '%s' nor '%s' field present in test '%s'" % \
            (JSON_TEST_KEY_BUILD, JSON_TEST_KEY_SCRIPT, name)
        if JSON_TEST_KEY_ENV in test:
            assert type(test[JSON_TEST_KEY_ENV]) == dict,\
                "Test '%s' field '%s' should be a dictionary." % \
                (name, JSON_TEST_KEY_ENV)
        if JSON_TEST_KEY_TESTS in test:
            assert type(test[JSON_TEST_KEY_TESTS]) == list,\
                "Test '%s' field '%s' should be a list." % \
                (name, JSON_TEST_KEY_TESTS)

    @staticmethod
    def parse(name, platforms, ci_data):
        """
        """
        test_data = ci_data[JSON_ROOT_KEY_TESTS][name]
        TestBase.validate_test(name, ci_data)
        params = {k: test_data.get(k, None) for k in [JSON_TEST_KEY_CONFIG,
            JSON_TEST_KEY_BUILD, JSON_TEST_KEY_SCRIPT, JSON_TEST_KEY_TESTS,
            JSON_TEST_KEY_ENV]}
        if params[JSON_TEST_KEY_CONFIG]:
            params[JSON_TEST_KEY_CONFIG] = \
                Config.parse(name, params[JSON_TEST_KEY_CONFIG])
        return TestBase(name, platforms, **params)


class Campaign(object):
    """
    Parser and container for Campaigns data.
    """
    def __init__(self):
        """
        """
        self.tests = dict()

    def add_test(self, name, test):
        """
        """
        assert name not in self.tests, \
            "Test with name %s already exists!" % name
        self.tests[name] = test

    def get_tests(self):
        """
        """
        for _, test in self.tests.items(): yield test

    @staticmethod
    def parse(name, ci_data):
        """
        """
        assert name in ci_data["campaigns"], \
            "Campaign '%s' not found in 'campaigns'" % name
        data = ci_data["campaigns"][name]
        assert type(data) == list, "Campaign '%s' type not a list!" % name
        campaign = Campaign()
        for platform_tests in data:
            platforms = platform_tests["platforms"]
            for test_name in platform_tests["tests"]:
                test = TestBase.parse(test_name, platforms, ci_data)
                campaign.add_test(test_name, test)
        return campaign


class Job(object):
    """
    Parser and container for jobs data.
    """

    def __init__(self):
        """
        """
        self.campaigns = dict()

    def add_campaign(self, name, campaign):
        """
        """
        self.campaigns[name] = campaign

    def get_tests(self):
        """
        """
        for _, campaign in self.campaigns.items():
            for test in campaign.get_tests():
                yield test

    @staticmethod
    def parse(job_data, ci_data):
        """
        """
        job = Job()
        for name in job_data["campaigns"]:
            campaign = Campaign.parse(name, ci_data)
            job.add_campaign(name, campaign)
        return job


class JobsParser(object):
    """
    Parser for cijobs.json
    """
    CI_JOBS_KEY_TESTS = "tests"
    CI_JOBS_KEY_CAMPAIGNS = "campaigns"
    CI_JOBS_KEY_JOBS = "jobs"

    def __init__(self):
        """
        """
        self.jobs = dict()

    def list_jobs(self):
        """
        """
        for job_name in self.jobs.keys():
            print(job_name)

    def list_tests(self, job_name=None):
        """
        """
        for job_name in filter(lambda x: job_name is None or x == job_name, self.jobs):
            job = self.jobs[job_name]
            for test in job.get_tests():
                for test_name in test.get_test_names():
                    print(test_name)

    def find_test(self, test_n_platform_name):
        """
        """
        for job_name, job in self.jobs.items():
            for test in job.get_tests():
                for test_name in test.get_test_names():
                    if test_n_platform_name == test_name:
                        return test
        return None

    def gen_environment_for_test(self, test_n_platform_name):
        """
        """
        test = self.find_test(test_n_platform_name)
        if test is None:
            raise CIBuilderException("Test '%s' not found!" % test_n_platform_name)
        platform = test.get_platform_by_name(test_n_platform_name)
        test.gen_environment(platform)

    @staticmethod
    def validate_root(data):
        """
        Validate root element format. It asserts required data format.

        :param data:  Data read from cijobs.json
        """
        for mandatory_keys in [JobsParser.CI_JOBS_KEY_TESTS,
                               JobsParser.CI_JOBS_KEY_CAMPAIGNS,
                               JobsParser.CI_JOBS_KEY_JOBS]:
            assert mandatory_keys in data, \
                "Mandatory key '%s' not found in cijobs.json" % mandatory_keys

    def parse(self, ci_data_file):
        """
        """
        with open(ci_data_file) as f:
            ci_data = json.load(f)
            JobsParser.validate_root(ci_data)
            for name, job_data in ci_data["jobs"].items():
                assert type(job_data) is dict, \
                    "Job '%s' data should be dict type!" % name
                job = Job.parse(job_data, ci_data)
                self.jobs[name] = job


if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option('-J', '--list-jobs', action="store_true",
                      dest="list_jobs", help="List jobs.")
    parser.add_option('-l', '--list-tests', dest="job_name",
                      help="List tests for job.")
    parser.add_option('-o', '--tests-out-file', dest="tests_outfile",
                      help="Output test list in this file.")
    parser.add_option('-e', '--gen-env', dest="test_n_platform_name",
                      metavar="TEST_NAME",
                      help="Generate environment file.")
    opts, args = parser.parse_args()

    ci_data_file = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                CI_META_FILE)
    jobs_parser = JobsParser()
    jobs_parser.parse(ci_data_file)
    if opts.list_jobs:
        jobs_parser.list_jobs()
    elif opts.job_name:
        jobs_parser.list_tests(opts.job_name)
    elif opts.test_n_platform_name:
        jobs_parser.gen_environment_for_test(opts.test_n_platform_name)
    else:
        parser.print_help()


