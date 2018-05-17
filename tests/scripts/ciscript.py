import os
import sys
import json
import argparse

CI_META_FILE="cijobs.json"

JSON_ROOT_KEY_TESTS = "tests"
JSON_ROOT_KEY_CAMPAIGNS = "campaigns"
JSON_ROOT_KEY_JOBS = "jobs"


def get_ci_data():
    """
    """
    ci_data_file = os.path.join(os.path.dirname(os.path.realpath(__file__)),
            CI_META_FILE)
    with open(ci_data_file, 'r') as f:
        return json.load(f)


def get_tests_in_campaign(campaign_name):
    """
    """
    ci_data = get_ci_data()
    return sorted(ci_data[JSON_ROOT_KEY_CAMPAIGNS][campaign_name])


def job_opt_handler(args):
    ci_data = get_ci_data()
    assert JSON_ROOT_KEY_JOBS in ci_data, \
        "Mandatory field '%s' not present in %s" % \
        (JSON_ROOT_KEY_JOBS, CI_META_FILE)

    if args.list_jobs:
        print("\n".join(sorted(ci_data[JSON_ROOT_KEY_JOBS])))
    elif args.list_tests:
        job_name = args.list_tests
        for plaform, test in get_tests_in_job(job_name):
            print("%s|%s" % (plaform, test))


def campaign_opt_handler(args):
    ci_data = get_ci_data()
    assert JSON_ROOT_KEY_CAMPAIGNS in ci_data, \
        "Mandatory field '%s' not present in %s" % \
        (JSON_ROOT_KEY_CAMPAIGNS, CI_META_FILE)

    if args.list_campaigns:
        print("\n".join(sorted(ci_data[JSON_ROOT_KEY_CAMPAIGNS])))
    elif args.list_tests:
        campaign_name = args.list_tests
        print("\n".join(get_tests_in_campaign(campaign_name)))


def get_tests_in_job(job_name):
    """
    """
    ci_data = get_ci_data()
    job_data = ci_data[JSON_ROOT_KEY_JOBS][job_name]
    for combo in job_data:
        platforms = combo["platforms"]
        campaigns = combo[JSON_ROOT_KEY_CAMPAIGNS]
        for platform in sorted(platforms):
            for campaign in campaigns:
                tests = get_tests_in_campaign(campaign)
                for test in tests:
                    yield platform, test


def get_test_names():
    """
    """
    ci_data = get_ci_data()
    return ci_data["tests"].keys()


def run_command(cmd, environment={}):
    """
    """
    env_str = " ".join(["%s=%s" % (k,v) for k,v in environment.items()])
    os.system(" ".join((env_str, cmd)))


def execute_tests(test, environment):
    env_str = " ".join(["%s=%s" % (k,v) for k,v in environment.items()])
    print(" ".join((env_str, test)))


def do_mbedtls_config(config):
    """
    """
    if "config" in config:
        run_command("./test/config.pl %s" % config["config"])
    for flag in config.get('set', []):
        run_command("./test/config.pl set %s" % flag)
    for flag in config.get('unset', []):
        run_command("./test/config.pl unset %s" % flag)


def check_environment(vars, environment):
    """
    """
    msg = "Mandatory environment variable '{var}' not specified!"
    errors = [msg.format(var=x) for x in vars if x not in environment]
    if len(errors):
        print("\n".join(errors))
        sys.exit(1)

def do_make(environment):
    """
    """
    check_environment(['MAKE', 'CC'], environment)
    make_cmd = "{MAKE}".format(**environment)
    make_target = environment.get("MAKE_TARGET", "")
    run_command("%s clean" % make_cmd, environment)
    run_command("%s %s" % (make_cmd, make_target), environment)


def do_cmake(environment):
    """
    """
    make_cmd = environment.get("MAKE", "make")
    unsafe_build = environment.get("UNSAFE_BUILD", "OFF")
    cmake_build_type = environment.get("CMAKE_BUILD_TYPE", "Check")
    pwd = os.path.abspath(os.path.curdir)
    run_command("cmake -D UNSAFE_BUILD=%s -D CMAKE_BUILD_TYPE:String=%s %s" % (unsafe_build, cmake_build_type, pwd))
    do_make(environment)


def run_test(test_name):
    """
    """
    ci_data = get_ci_data()
    assert test_name in ci_data["tests"], "Test '%s' no found!" % test_name
    test_data = ci_data["tests"][test_name]

    # config
    if "config" in test_data:
        do_mbedtls_config(test_data["config"])

    # build
    if "build" in test_data:
        if test_data["build"] == "make":
            do_make(test_data["environment"])
        elif test_data["build"] == "cmake":
            do_cmake(test_data["environment"])
    elif "script" in test_data:
        run_script(test_data["script"], test_data["environment"])

    # test
    if "tests" in test_data:
        for test in test_data["tests"]:
            pass
            execute_tests(test, test_data["environment"])


def test_opt_handler(args):
    """
    """
    if args.list_tests:
        for test in get_test_names():
            print(test)
    elif args.run_test:
        run_test(args.run_test)


if __name__=='__main__':
    parser = argparse.ArgumentParser(description="List and execute tests.")
    subparsers = parser.add_subparsers(help='<-- Sub commands')

    # Parser for campaign options
    campaign_parser = subparsers.add_parser('campaigns', help='Campaign options')
    campaign_parser.add_argument('-l', '--list', action='store_true',
            dest='list_campaigns', help='List campaigns')
    campaign_parser.add_argument('-t', '--list-tests', dest='list_tests',
            metavar="CAMPAIGN_NAME", help='List tests in a campaign')
    campaign_parser.set_defaults(func=campaign_opt_handler)

    # Parser for job options
    job_parser = subparsers.add_parser('jobs', help='Job options')
    job_parser.add_argument('-l', '--list', action='store_true',
            dest='list_jobs', help='List jobs')
    job_parser.add_argument('-t', '--list-tests', dest='list_tests',
            metavar="JOB_NAME", help='List tests in a job')
    job_parser.set_defaults(func=job_opt_handler)

    # Parser for test options
    test_parser = subparsers.add_parser('test', help='Job options')
    test_parser.add_argument('-l', '--list', action='store_true',
            dest='list_tests', help='List tests')
    test_parser.add_argument('-r', '--run-test', dest='run_test',
            metavar="TEST_NAME", help='Run a test')
    test_parser.set_defaults(func=test_opt_handler)


    args = parser.parse_args()
    args.func(args)
