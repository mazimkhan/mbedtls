import os
import sys
import json
import argparse


JSON_ROOT_KEY_TESTS = "tests"
JSON_ROOT_KEY_CAMPAIGNS = "campaigns"
JSON_ROOT_KEY_JOBS = "jobs"


class Test(object):
    """
    """

    def __init__(self, config=None, set_config=[], unset_config=[],
                 build=None, script=None, environment={}, tests=[], test_scripts={}):
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

    def run_command(self, cmd):
        """
        """
        print("Running: %s" % cmd)
        os.system(cmd)

    def run_with_env(self, cmd):
        """
        """
        env_str = " ".join(["%s=%s" % (k,v) for k,v in self.environment.items()])
        cmd = " ".join((env_str, cmd))
        self.run_command(cmd)

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
        make_cmd = "{MAKE}".format(**self.environment)
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


class CIDataParser(object):
    CI_META_FILE="cijobs.json"

    def __init__(self):
        ci_data_file = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                self.CI_META_FILE)
        with open(ci_data_file, 'r') as f:
            self.ci_data = json.load(f)
        self.validate()

    def validate(self):
        """
        """
        # Validate root data type
        assert type(self.ci_data) == dict, "CI Test data root should be a map!"

        # Validate root keys
        for root_key in ("tests", "campaigns", "jobs"):
            assert root_key in self.ci_data, \
                "Mandatory root key '%s' not present!" % root_key

        # Validate tests
        assert type(self.ci_data["tests"]) == dict, "'tests' data is not a map!"
        for test_name, test_data in self.ci_data["tests"].items():
            assert type(test_data) == dict, "Test '%s' data is not a map!" % test_name
            assert "build" in test_data or "script" in test_data, \
                "Test '%s' should specify either 'build' or 'script'" % test_name
            if "config" in test_data:
                assert type(test_data["config"]) == dict, \
                    "Test '%s' config data shoud be a map!" % test_data
                for key in test_data["config"].keys():
                    assert key in ("config", "set", "unset"), \
                        "Test '%s' 'config' element '%s' is unknown" % (test_name, key)
                if "set" in test_data["config"]:
                    assert type(test_data["config"]["set"]) == list, \
                        "Test '%s' 'config' element 'set' is not a list" % test_name
                if "unset" in test_data["config"]:
                    assert type(test_data["config"]["unset"]) == list, \
                        "Test '%s' 'config' element 'unset' is not a list" % test_name
            if "environment" in test_data:
                assert type(test_data["environment"]) == dict, \
                    "Test '%s' 'environment' is not a map" % test_name
            if "tests" in test_data:
                assert type(test_data["tests"]) == list, \
                    "Test '%s' 'tests' is not a list" % test_name

        # Validate Campaigns
        assert type(self.ci_data["campaigns"]) == dict, "'campaigns' data is not a map!"
        for campaign_name, campaign in self.ci_data["campaigns"].items():
            assert type(campaign) == list, \
                "Campaign '%s' type is not a list!" % campaign_name
            for test_name in campaign:
                assert test_name in self.ci_data["tests"], \
                    "Test '%s' reference in campaign '%s' not found in \"tests\"" % \
                    (test_name, campaign_name)

        # Validate Jobs
        assert type(self.ci_data["jobs"]) == dict, "'jobs' data is not a map!"
        for job_name, job in self.ci_data["jobs"].items():
            assert type(job) == list, "Job '%s' type is not a list!" % job_name
            for combo in job:
                # Check mandatory keys in job
                for mandatory_key in ("campaigns", "platforms"):
                    assert mandatory_key in combo, \
                        "Mandatory key '%s' not present in job!" % \
                        (mandatory_key, job_name)
                # Check campaigns
                assert type(combo["campaigns"]) == list, \
                    "Element \"campaigns\" in job '%s' is not a list!" % job_name
                # Check campaigns exist
                for campaign_name in combo["campaigns"]:
                    assert campaign_name in self.ci_data["campaigns"], \
                        "Campaign '%s' referenced by job '%s' not found!" % \
                        (campaign_name, job_name)
                # Check platforms
                assert type(combo["platforms"]) == list, \
                    "Element \"platforms\" in job '%s' is not a list!" % job_name

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
    campaign_parser = subparsers.add_parser('campaigns', help='Campaign options')
    campaign_parser.add_argument('-l', '--list', action='store_true',
                                 dest='list_campaigns', help='List campaigns')
    campaign_parser.add_argument('-t', '--list-tests', dest='list_tests',
                                 metavar="CAMPAIGN_NAME",
                                 help='List tests in a campaign')
    campaign_parser.set_defaults(func=campaign_opt_handler)

    # Parser for job options
    job_parser = subparsers.add_parser('jobs', help='Job options')
    job_parser.add_argument('-l', '--list', action='store_true',
                            dest='list_jobs', help='List jobs')
    job_parser.add_argument('-t', '--list-tests', dest='list_tests',
                            metavar="JOB_NAME", help='List tests in a job')
    job_parser.set_defaults(func=job_opt_handler)

    # Parser for test options
    test_parser = subparsers.add_parser('test', help='Test options')
    test_parser.add_argument('-l', '--list', action='store_true',
                             dest='list_tests', help='List tests')
    test_parser.add_argument('-r', '--run-test', dest='run_test',
                             metavar="TEST_NAME", help='Run a test')
    test_parser.set_defaults(func=test_opt_handler)


    args = parser.parse_args()
    args.func(args)

