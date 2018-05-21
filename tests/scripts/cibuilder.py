#!/usr/bin/env python
import os
import re
import sys
import json
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
    """

    def __init__(self, config=None, set_config=[], unset_config=[],
                 build=None, script=None, environment={}, tests=[],
                 test_scripts={}):
        """
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
        """
        # Expand test environment variables
        for name, value in self.environment.items():
            cmd = re.sub("(\${name})|(\$\{{{name}}})".format(name=name), value, cmd)
        # Expand system environment variables
        return os.path.expandvars(cmd)

    def run_command(self, cmd, environment={}):
        """
        """
        self.expand_vars(cmd)
        print(cmd)
        # Create copy of system environment and expand and add test environment
        env = os.environ.copy()
        env.update({k:self.expand_vars(v) for k,v in environment.items()})
        subprocess.call(cmd.split(), env=env)

    def run_with_env(self, cmd):
        """
        """
        self.run_command(cmd, environment=self.environment)

    def do_mbedtls_config(self):
        """
        """
        if self.config or self.set_config or self.unset_config:
            pass # backup original config

        if self.config:
            self.run_command("./scripts/config.pl %s" % self.config)
        for flag in self.set_config:
            self.run_command("./scripts/config.pl set %s" % flag)
        for flag in self.unset_config:
            self.run_command("./scripts/config.pl unset %s" % flag)

    def check_environment(self, vars):
        """
        """
        msg = "Mandatory environment variable '{var}' not specified!"
        errors = [msg.format(var=x) for x in vars if x not in self.environment]
        if len(errors):
            print("\n".join(errors))
            sys.exit(1)

    def do_make(self):
        """
        """
        self.check_environment(['MAKE', 'CC'])
        make_cmd = self.environment.get("MAKE", "make")
        make_target = self.environment.get("MAKE_TARGET", "")
        self.run_with_env("%s clean" % make_cmd)
        self.run_with_env("%s %s" % (make_cmd, make_target))

    def do_cmake(self):
        """
        """
        make_cmd = self.environment.get("MAKE", "make")
        unsafe_build = self.environment.get("UNSAFE_BUILD", "OFF")
        cmake_build_type = self.environment.get("CMAKE_BUILD_TYPE", "Check")
        pwd = os.path.abspath(os.path.curdir)
        self.run_with_env("cmake -D UNSAFE_BUILD=%s -D CMAKE_BUILD_TYPE:String=%s %s" % (unsafe_build, cmake_build_type, pwd))
        self.do_make()

    def run(self):
        """
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
    _type = None

    def __init__(self, name=None, is_mandatory=True, type=None):
        self.name = name
        self.is_mandatory = is_mandatory
        if type:
            self._type = type

    def get_name(self): return self.name

    def update_tag(self, tag):
        return "->".join((tag, self.get_name())) if tag else self.name

    def validate(self, data, tag=""):
        tag = self.update_tag(tag)
        if self._type == str:
            if type(data) not in (str, unicode):
                raise ValueError("%s Key '%s' value should be of type str or unicode" % (tag, self.get_name()))
        elif type(data) != self._type:
            raise ValueError("%s Key '%s' value should be of type %s" % (tag, self.get_name(), self._type))

class DictSchema(Schema):
    _schema = None

    def validate(self, data, tag=""):
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
    _schema = None

    def validate(self, data, tag=""):
        tag = self.update_tag(tag)
        if type(data) != list:
            raise ValueError("%s Data type of '%s' should be list." % (tag, self.get_name()))
        for element in data:
            self._schema.validate(element, tag)


class AttributeSchema(Schema):
    _attributes = {}

    def validate(self, data, tag=""):
        tag = self.update_tag(tag)
        if type(data) != dict:
            raise ValueError("%s Data type of '%s' should be dict." % (tag, self.get_name()))
        for name, schema in self._attributes.items():
            if name not in data:
                if schema.is_mandatory:
                    raise ValueError("%s '%s' not found in '%s'" % (tag, name, self.get_name()))
            else:
                schema.validate(data[name], tag)


class StrSchema(Schema):
    _type = str


class StringDictSchema(DictSchema):
    _schema = StrSchema


class TestSchema(AttributeSchema):
    _attributes = {
        "environment": StringDictSchema("environment", False),
        "build": StrSchema("build", False),
        "script": StrSchema("script", False),
        "tests": Schema("tests", False, list)
    }

    def validate(self, data, tag=""):
        super(TestSchema, self).validate(data, tag)
        tag = self.update_tag(tag)
        if "build" not in data and "script" not in data:
            raise ValueError("%s Neither 'build' nor 'script' present in test '%s'" % (tag, self.get_name()))
        if "build" in data and "script" in data:
            raise ValueError("%s Both 'build' and 'script' specified in test '%s'" % (tag, self.get_name()))


class TestSequence(DictSchema):
    _schema = TestSchema


class TestListSchema(ListSchema):
    _schema = StrSchema("test")


class CampaignSequence(DictSchema):
    _schema = TestListSchema


class PlatformListSchema(ListSchema):
    _schema = StrSchema("platform")


class CampaignListSchema(ListSchema):
    _schema = StrSchema("campaigns")


class ComboSchema(AttributeSchema):
    _attributes = {
        "platforms": PlatformListSchema("platforms"),
        "campaigns": CampaignListSchema("campaigns")
    }


class ComboList(ListSchema):
    _schema = ComboSchema("Platform & Campaign")


class JobSequence(DictSchema):
    _schema = ComboList


class TestScriptSchema(ListSchema):
    _schema = StrSchema("test-script")


class TestScriptSequence(DictSchema):
    _schema = TestScriptSchema


class RootSchema(AttributeSchema):
    _attributes = {
        "tests": TestSequence("tests"),
        "campaigns": CampaignSequence("campaigns"),
        "jobs": JobSequence("jobs"),
        "test-scripts": TestScriptSequence("test-script", False)
    }


#####################################################################
# CI data parsing
#####################################################################


class CIDataParser(object):
    CI_META_FILE="cijobs.json"

    def __init__(self):
        ci_data_file = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                self.CI_META_FILE)
        with open(ci_data_file, 'r') as f:
            self.ci_data = json.load(f)

    def validate(self):
        """
        """
        vr = RootSchema("root")
        vr.validate(self.ci_data)

    def get_campaigns(self):
        return sorted(self.ci_data[JSON_ROOT_KEY_CAMPAIGNS].keys())

    def get_tests_in_campaign(self, campaign_name):
        """
        """
        return sorted(self.ci_data[JSON_ROOT_KEY_CAMPAIGNS][campaign_name])

    def get_jobs(self):
        """
        """
        return sorted(self.ci_data[JSON_ROOT_KEY_JOBS].keys())

    def get_tests_in_job(self, job_name):
        """
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
        """
        return sorted(self.ci_data["tests"].keys())

    def get_test(self, test_name):
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
    """
    parser = CIDataParser()
    if args.list_tests:
        for test in parser.get_test_names():
            print(test)
    elif args.run_test:
        test = parser.get_test(args.run_test)
        test.run()


def campaign_opt_handler(args):
    parser = CIDataParser()

    if args.list_campaigns:
        print("\n".join(parser.get_campaigns()))
    elif args.list_tests:
        campaign_name = args.list_tests
        print("\n".join(parser.get_tests_in_campaign(campaign_name)))


def job_opt_handler(args):
    parser = CIDataParser()

    if args.list_jobs:
        print("\n".join(parser.get_jobs()))
    elif args.list_tests:
        job_name = args.list_tests
        for plaform, test in parser.get_tests_in_job(job_name):
            print("%s|%s" % (plaform, test))


if __name__=='__main__':
    parser = argparse.ArgumentParser(description="List and execute tests.")
    subparsers = parser.add_subparsers(help='For help run: %(prog)s <sub-command> -h')

    # Parser for campaign options
    campaign_parser = subparsers.add_parser('campaigns',
        help='Campaign options')
    campaign_parser.add_argument('-l', '--list',
        action='store_true',
        dest='list_campaigns',
        help='List campaigns')
    campaign_parser.add_argument('-t', '--list-tests',
        dest='list_tests',
        metavar="CAMPAIGN_NAME",
        help='List tests in a campaign')
    campaign_parser.set_defaults(func=campaign_opt_handler)

    # Parser for job options
    job_parser = subparsers.add_parser('jobs',
        help='Job options')
    job_parser.add_argument('-l', '--list',
        action='store_true',
        dest='list_jobs',
        help='List jobs')
    job_parser.add_argument('-t', '--list-tests',
        dest='list_tests',
        metavar="JOB_NAME",
        help='List tests in a job')
    job_parser.set_defaults(func=job_opt_handler)

    # Parser for test options
    test_parser = subparsers.add_parser('test',
        help='Test options')
    test_parser.add_argument('-l', '--list',
        action='store_true',
        dest='list_tests',
        help='List tests')
    test_parser.add_argument('-r', '--run-test',
        dest='run_test',
        metavar="TEST_NAME",
        help='Run a test')
    test_parser.set_defaults(func=test_opt_handler)


    args = parser.parse_args()
    args.func(args)

