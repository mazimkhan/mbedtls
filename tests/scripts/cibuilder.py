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

    def __init__(self, test_data):
        """
        """
        self.test_data = test_data
        self.environment = test_data.get('environment', {})

    def run_command(self, cmd):
        """
        """
        env_str = " ".join(["%s=%s" % (k,v) for k,v in self.environment.items()])
        cmd = " ".join((env_str, cmd))
        print("Running: %s" % cmd)
        os.system(cmd)

    def execute_tests(test):
        env_str = " ".join(["%s=%s" % (k,v) for k,v in self.environment.items()])
        print(" ".join((env_str, test)))

    def do_mbedtls_config(config):
        """
        """
        if "config" in config:
            self.run_command("./test/config.pl %s" % config["config"])
        for flag in config.get('set', []):
            self.run_command("./test/config.pl set %s" % flag)
        for flag in config.get('unset', []):
            self.run_command("./test/config.pl unset %s" % flag)

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
        self.run_command("%s clean" % make_cmd)
        self.run_command("%s %s" % (make_cmd, make_target))

    def do_cmake(self):
        """
        """
        make_cmd = self.environment.get("MAKE", "make")
        unsafe_build = self.environment.get("UNSAFE_BUILD", "OFF")
        cmake_build_type = self.environment.get("CMAKE_BUILD_TYPE", "Check")
        pwd = os.path.abspath(os.path.curdir)
        self.run_command("cmake -D UNSAFE_BUILD=%s -D CMAKE_BUILD_TYPE:String=%s %s" % (unsafe_build, cmake_build_type, pwd))
        self.do_make()

    def run(self):
        """
        """
        test_data = self.test_data

        # config
        if "config" in test_data:
            do_mbedtls_config(test_data["config"])

        # build
        if "build" in test_data:
            if test_data["build"] == "make":
                self.do_make()
            elif test_data["build"] == "cmake":
                self.do_cmake()
        elif "script" in test_data:
            self.run_command(test_data["script"])

        # test
        if "tests" in test_data:
            for test in test_data["tests"]:
                self.execute_tests(test)


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

        # Validate Jobs
        assert type(self.ci_data["jobs"]) == dict, "Jobs data is not a map!"
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

        # Validate Campaigns
        assert type(self.ci_data["campaigns"]) == dict, "Campaigns data is not a map!"
        for campaign_name, campaign in self.ci_data["campaigns"].items():
            assert type(campaign) == list, \
                "Campaign '%s' type is not a list!" % campaign_name
            for test_name in campaign:
                assert test_name in self.ci_data["tests"], \
                    "Test '%s' reference in campaign '%s' not found in \"tests\"" % \
                    (test_name, campaign_name)

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
        assert test_name in self.ci_data["tests"], "Test '%s' no found!" % test_name
        test_data = self.ci_data["tests"][test_name]
        return Test(test_data)


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

