#!/usr/bin/env python
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
This script provides following features:
- Introspect tests, campaigns and CI jobs
- Execute tests
- Take test, campaign and jobs input from mbedtls/tests/scripts/cijobs.json
"""

import os
import re
import sys
import json
import shlex
import shutil
import signal
import argparse
import subprocess


JSON_ROOT_KEY_TESTS = "tests"
JSON_ROOT_KEY_CAMPAIGNS = "campaigns"
JSON_ROOT_KEY_JOBS = "jobs"


#####################################################################
# Test execution
#####################################################################


class Test(object):
    """
    Configure, build and test Mbed TLS for specified configuration.
    """
    CONFIG_H = "include/mbedtls/config.h"
    CONFIG_H_BAK = CONFIG_H + ".bak"

    def __init__(self, config, set_config, unset_config,
                 build, script, environment, tests,
                 test_scripts):
        """
        Constructor expects mutually exclusive 'build' or 'script' to be passed by the creator. Rest of the parameters
        are optional. It assumes parameters to be in expected format, since data validation is done prior to this call.

        :param config: config defined by config.pl
        :param set_config: List of macros to set in config.h
        :param unset_config: List of macros to unset in config.h
        :param build: Build type make/cmake. Mutually exclusive with script.
        :param script: Script to run instead of a build.
        :param environment: Test environment
        :param tests: List of tests. Either a script path or link into test_scripts.
        :param test_scripts: dict of test scripts specified in cijobs.json.
        """
        self.config = config
        self.set_config = set_config
        self.unset_config = unset_config
        self.build = build
        self.script = script
        self.environment = environment
        self.tests = tests
        self.test_scripts = test_scripts

    def expand_vars(self, cmd):
        """
        Expand variables in the command string.

        :param cmd: Command to expands the environment variables.
        :return: Returns expanded command.
        """
        # Expand test environment variables
        for name, value in self.environment.items():
            cmd = re.sub("(\${name})|(\$\{{{name}}})".format(name=name), value, cmd)
        # Expand system environment variables
        return os.path.expandvars(cmd)

    @staticmethod
    def on_child_signalled(signum, frame):
        print("Signal %d received!" % signum)

    @staticmethod
    def on_child_startup():
        # Ignore signals in subprocess to avoid unintentional termination.
        for attr in [x for x in dir(signal) if x.startswith("SIG")]:
            try:
                signum = getattr(signal, attr)
                signal.signal(signum, Test.on_child_signalled)
            except Exception:
                print("Unable to handle signal: %s", attr)

    def run_command(self, cmd_str, environment=None):
        """
        Run command with given environment.

        :param cmd_str: Command to run.
        :param environment: Environment dict k,v = env name, value
        """
        self.expand_vars(cmd_str)
        print(cmd_str)

        # Create copy of system environment and expand and add test environment
        env = os.environ.copy()
        if environment:
            env.update({k:self.expand_vars(v) for k,v in environment.items()})

        # Extract leading variables in command and put into env
        cmd = []
        for part in shlex.split(cmd_str):
            m = re.match("(.*?)=(.*)", part)
            if len(cmd) == 0 and m:
                env[m.group(1)] = self.expand_vars(m.group(2))
            else:
                cmd.append(part)
        p = subprocess.Popen(cmd, env=env, stderr=subprocess.STDOUT,
                             preexec_fn=self.on_child_startup)
        p.wait()
        if p.returncode and p.returncode != 0:
            raise Exception("The command \"%s\" exited with %d." % \
                           (cmd_str, p.returncode))

    def run_with_env(self, cmd):
        """
        Run command with test variables.

        :param cmd: Command to run.
        """
        self.run_command(cmd, environment=self.environment)

    def do_mbedtls_config(self):
        """
        Perform Mbed TLS config by running config.pl script. Creates backup of existing config.h before changing it.
        """
        if self.config or self.set_config or self.unset_config:
            bakup_file = self.CONFIG_H_BAK
            if os.path.exists(self.CONFIG_H_BAK):
                enumerator = 0
                while os.path.exists("%s.%d" % (self.CONFIG_H_BAK, enumerator)):
                    enumerator += 1
                bakup_file = "%s.%d" % (self.CONFIG_H_BAK, enumerator)
            shutil.copy(self.CONFIG_H, bakup_file)

        if self.config:
            self.run_command("./scripts/config.pl %s" % self.config)
        for flag in self.set_config:
            self.run_command("./scripts/config.pl set %s" % flag)
        for flag in self.unset_config:
            self.run_command("./scripts/config.pl unset %s" % flag)

    def check_environment(self, vars):
        """
        Check if variables are defined in the test environment and exit with
        error if not.

        :param vars: Environment variables to check.
        """
        msg = "Mandatory environment variable '{var}' not specified!"
        errors = [msg.format(var=x) for x in vars if x not in self.environment]
        if len(errors):
            print("\n".join(errors))
            sys.exit(1)

    def do_make(self):
        """
        Execute make build with the test environment.
        """
        self.check_environment(['MAKE', 'CC'])
        make_cmd = self.environment.get("MAKE", "make")
        make_target = self.environment.get("MAKE_TARGET", "")
        self.run_with_env("%s clean" % make_cmd)
        self.run_with_env("%s %s" % (make_cmd, make_target))

    def do_cmake(self):
        """
        Execute cmake build with the test environment.
        """
        make_cmd = self.environment.get("MAKE", "make")
        unsafe_build = self.environment.get("UNSAFE_BUILD", "OFF")
        cmake_build_type = self.environment.get("CMAKE_BUILD_TYPE", "Check")
        pwd = os.path.abspath(os.path.curdir)
        self.run_with_env("cmake -D UNSAFE_BUILD=%s -D CMAKE_BUILD_TYPE:String=%s %s" % (unsafe_build, cmake_build_type, pwd))
        self.do_make()

    def run(self):
        """
        Execute the test in following order:
        1. Do Mbed TLS config.
        2. Perform make or cmake build or execute a script.
        3. Perform tests.
        """
        # config
        self.do_mbedtls_config()

        # build
        if self.build:
            if self.build == "make":
                self.do_make()
            elif self.build == "cmake":
                self.do_cmake()
        elif self.script:
            self.run_with_env(self.script)

        # test
        for test in self.tests:
            if test in self.test_scripts:
                for cmd in self.test_scripts[test]:
                    self.run_with_env(cmd)
            else:
                self.run_with_env(test)


#####################################################################
# CI data schema and validation
#####################################################################


class Schema(object):
    """
    Base schema class, it provides methods for validation of a JSON data element. It implements validation by type.
    Example:

        class StrSchema(Schema):
            _type = str

    Above schema validates an object of type string. 
    """
    _type = None

    def __init__(self, name=None, is_mandatory=True, type=None):
        """
        Instantiate the object with element name, type and presence requirement.

        :param name: Data element name
        :param is_mandatory: True if element is mandatory
        :param type: Element type
        """
        self.name = name
        self.is_mandatory = is_mandatory
        if type:
            self._type = type

    def get_name(self):
        """
        Gives field name.

        :return: name string
        """
        return self.name

    def update_tag(self, tag):
        """
        Updates the tag with this element name. Tag string is useful while printing format validation error as it
        indicates path of an element in the JSON document.

        :param tag:
        :return:
        """
        return "->".join((tag, self.get_name())) if tag else self.name

    def validate(self, data, tag=""):
        """
        Validate schema. In this base class validation is done for specified object type. This method can be overriden
        by derived classes implementing complex object schemas.

        :param data:
        :param tag:
        :return:
        """
        tag = self.update_tag(tag)
        if self._type == str:
            if type(data) not in (str, unicode):
                raise ValueError("%s Key '%s' value should be of type str or unicode" % (tag, self.get_name()))
        elif type(data) != self._type:
            raise ValueError("%s Key '%s' value should be of type %s" % (tag, self.get_name(), self._type))


class DictSchema(Schema):
    """
    Schema for validating dict objects. A validator class can be created by simply inheriting this class and specifying
    dictionary element types. Example:

        class StringDictSchema(DictSchema):
            _schema = StrSchema

    Above is an example for validating a dictionary of strings.
    """
    _schema = None

    def validate(self, data, tag=""):
        """
        Validates a dictionary object by validating each element with it's own schema.
        :param data: 
        :param tag: 
        :return: 
        """
        tag = self.update_tag(tag)
        if type(data) != dict:
            raise ValueError("%s Data type of '%s' should be dict." % (tag, self.get_name()))
        for name, value in data.items():
            if type(name) not in (str, unicode):
                print("%s not str" % name)
                raise ValueError("%s Keys in dictionary '%s' should be strings." % (tag, self.get_name()))
            schema = self._schema(name)
            schema.validate(value, tag)


class ListSchema(Schema):
    """
    Similar to DictSchema, but validates a list.
    """
    _schema = None

    def validate(self, data, tag=""):
        """
        Validates a list object by validating each element with it's own schema.
        :param data: 
        :param tag: 
        :return: 
        """
        tag = self.update_tag(tag)
        if type(data) != list:
            raise ValueError("%s Data type of '%s' should be list." % (tag, self.get_name()))
        for element in data:
            self._schema.validate(element, tag)


class AttributeSchema(Schema):
    """
    Validate a dictionary with specific keys (attribute names) and value (attribute value) types. Example:

    class TestSchema(AttributeSchema):
        _attributes = [
            StringDictSchema("environment", False),
            StrSchema("build", False),
            StrSchema("script", False),
            Schema("tests", False, list)
        ]

    """
    _attributes = []

    def validate(self, data, tag=""):
        tag = self.update_tag(tag)
        if type(data) != dict:
            raise ValueError("%s Data type of '%s' should be dict." % (tag, self.get_name()))
        for schema in self._attributes:
            if schema.get_name() not in data:
                if schema.is_mandatory:
                    raise ValueError("%s '%s' not found in '%s'" % (tag, schema.get_name(), self.get_name()))
            else:
                schema.validate(data[schema.get_name()], tag)


class StrSchema(Schema):
    """String object schema"""
    _type = str


class StringDictSchema(DictSchema):
    """Dictionary of sctrings schema."""
    _schema = StrSchema


class TestSchema(AttributeSchema):
    """
    Test schema with member attributes.
    """
    _attributes = [
        StringDictSchema("environment", False),
        StrSchema("build", False),
        StrSchema("script", False),
        Schema("tests", False, list)
    ]

    def validate(self, data, tag=""):
        """
        Check either 'build' or 'script' is present in addition to base AttributeSchema Validation.

        :param data: 
        :param tag: 
        :return: 
        """
        super(TestSchema, self).validate(data, tag)
        tag = self.update_tag(tag)
        if "build" not in data and "script" not in data:
            raise ValueError("%s Neither 'build' nor 'script' present in test '%s'" % (tag, self.get_name()))
        if "build" in data and "script" in data:
            raise ValueError("%s Both 'build' and 'script' specified in test '%s'" % (tag, self.get_name()))


class TestSequence(DictSchema):
    """Tests dict {name: value} schema"""
    _schema = TestSchema


class TestListSchema(ListSchema):
    """Test list schema. Used for test commands list validation."""
    _schema = StrSchema("test")


class CampaignSequence(DictSchema):
    """Test Campaign dict schema"""
    _schema = TestListSchema


class PlatformListSchema(ListSchema):
    """Platform list"""
    _schema = StrSchema("platform")


class CampaignListSchema(ListSchema):
    """Campaign list"""
    _schema = StrSchema("campaigns")


class ComboSchema(AttributeSchema):
    """
    Platforms x Campaigns combinations.
    """
    _attributes = [
        PlatformListSchema("platforms"),
        CampaignListSchema("campaigns")
    ]


class ComboList(ListSchema):
    """
    List of Platforms x Campaigns
    """
    _schema = ComboSchema("Platform & Campaign")


class JobSequence(DictSchema):
    """
    Job schema containing list of Platforms x Campaigns combinations. 
    """
    _schema = ComboList


class TestScriptSchema(ListSchema):
    """Test script a list of commands."""
    _schema = StrSchema("test-script")


class TestScriptSequence(DictSchema):
    """ List of test scripts"""
    _schema = TestScriptSchema


class RootSchema(AttributeSchema):
    """
    Root schema with attributes: tests, test-script, campaigns and jobs.
    """
    _attributes = [
        TestSequence("tests"),
        CampaignSequence("campaigns"),
        JobSequence("jobs"),
        TestScriptSequence("test-script", False)
    ]


#####################################################################
# CI data parsing
#####################################################################


class CIDataParser(object):
    """
    Parser for cijobs.json. Provides data as requested by command line.
    """
    CI_META_FILE="cijobs.json"

    def __init__(self):
        """
        Instantiate by reading CI data file and loading json data. 
        """
        ci_data_file = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                self.CI_META_FILE)
        with open(ci_data_file, 'r') as f:
            self.ci_data = json.load(f)

    def validate(self):
        """
        Validate CI data file.
        """
        vr = RootSchema("root")
        vr.validate(self.ci_data)

    def get_campaigns(self):
        """Get campaign names"""
        return sorted(self.ci_data[JSON_ROOT_KEY_CAMPAIGNS].keys())

    def get_tests_in_campaign(self, campaign_name):
        """
        Get tests in campaign.
        """
        return sorted(self.ci_data[JSON_ROOT_KEY_CAMPAIGNS][campaign_name])

    def get_jobs(self):
        """
        Get job names.
        """
        return sorted(self.ci_data[JSON_ROOT_KEY_JOBS].keys())

    def get_tests_in_job(self, job_name):
        """
        Get tests in job.
        """
        job_data = self.ci_data[JSON_ROOT_KEY_JOBS][job_name]
        for combo in job_data:
            platforms = combo["platforms"]
            campaigns = combo[JSON_ROOT_KEY_CAMPAIGNS]
            for platform in sorted(platforms):
                for campaign in campaigns:
                    tests = self.get_tests_in_campaign(campaign)
                    for test in tests:
                        yield platform, test

    def get_test_names(self):
        """
        Get test names.
        """
        return sorted(self.ci_data["tests"].keys())

    def get_test(self, test_name):
        """Gives Test object for specified test name."""
        assert test_name in self.ci_data["tests"], \
            "Test '%s' no found!" % test_name
        test_data = self.ci_data["tests"][test_name]
        return Test(config = test_data.get("config", {}).get("config", None),
                    set_config = test_data.get("config", {}).get("set", []),
                    unset_config = test_data.get("config", {}).get("unset", []),
                    build = test_data.get("build", None),
                    script = test_data.get("script", None),
                    environment = test_data.get("environment", {}),
                    tests = test_data.get('tests', []),
                    test_scripts=self.ci_data.get("test-scripts", {}))


#####################################################################
# Command line option parsers
#####################################################################


def test_opt_handler(args):
    """
    Handler for test sub command options.
    :param args: 
    :return: 
    """
    parser = CIDataParser()
    if args.list_tests:
        for test in parser.get_test_names():
            print(test)
    elif args.run_test:
        test = parser.get_test(args.run_test)
        test.run()


def campaign_opt_handler(args):
    """
    Handler for campaign sub command options.
    :param args: 
    :return: 
    """
    parser = CIDataParser()

    if args.list_campaigns:
        print("\n".join(parser.get_campaigns()))
    elif args.list_tests:
        campaign_name = args.list_tests
        print("\n".join(parser.get_tests_in_campaign(campaign_name)))


def job_opt_handler(args):
    """
    Handler for job sub command options.
    :param args: 
    :return: 
    """
    parser = CIDataParser()

    if args.list_jobs:
        print("\n".join(parser.get_jobs()))
    elif args.list_tests:
        job_name = args.list_tests
        for platform, test in parser.get_tests_in_job(job_name):
            print("%s|%s" % (platform, test))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="List and execute tests.")
    subparsers = parser.add_subparsers(help='For help run: %(prog)s <sub-command> -h')

    # Parser for campaign options
    campaign_parser = subparsers.add_parser(
        'campaigns',
        help='Campaign options')
    campaign_parser.add_argument(
        '-l', '--list',
        action='store_true',
        dest='list_campaigns',
        help='List campaigns')
    campaign_parser.add_argument(
        '-t', '--list-tests',
        dest='list_tests',
        metavar="CAMPAIGN_NAME",
        help='List tests in a campaign')
    campaign_parser.set_defaults(func=campaign_opt_handler)

    # Parser for job options
    job_parser = subparsers.add_parser(
        'jobs',
        help='Job options')
    job_parser.add_argument(
        '-l', '--list',
        action='store_true',
        dest='list_jobs',
        help='List jobs')
    job_parser.add_argument(
        '-t', '--list-tests',
        dest='list_tests',
        metavar="JOB_NAME",
        help='List tests in a job')
    job_parser.set_defaults(func=job_opt_handler)

    # Parser for test options
    test_parser = subparsers.add_parser(
        'test',
        help='Test options')
    test_parser.add_argument(
        '-l', '--list',
        action='store_true',
        dest='list_tests',
        help='List tests')
    test_parser.add_argument(
        '-r', '--run-test',
        dest='run_test',
        metavar="TEST_NAME",
        help='Run a test')
    test_parser.set_defaults(func=test_opt_handler)
    args = parser.parse_args()
    args.func(args)

