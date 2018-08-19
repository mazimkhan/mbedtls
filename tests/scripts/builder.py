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
- Introspect builds, campaigns and CI jobs
- Execute builds
- Take build, campaign and jobs input from mbedtls/tests/scripts/build_info.py
"""

import os
import re
import sys
import types
import shlex
import shutil
import signal
import argparse
import subprocess
from build_info_parser import BuildInfo


#####################################################################
# Build execution
#####################################################################


class Build(object):
    """
    Configure, build and test Mbed TLS for specified configuration.
    """
    CONFIG_H = "include/mbedtls/config.h"
    CONFIG_H_BAK = CONFIG_H + ".bak"
    CLEANUP_SCRIPT = './tests/scripts/cleanup.sh'

    def __init__(self, config, set_config, unset_config,
                 build, script, environment, tests, requirements,
                 test_scripts):
        """
        Constructor expects mutually exclusive 'build' or 'script' to be passed by the creator. Rest of the parameters
        are optional. It assumes parameters to be in expected format, since data validation is done prior to this call.

        :param config: config defined by config.pl
        :param set_config: List of macros to set in config.h
        :param unset_config: List of macros to unset in config.h
        :param build: Build type make/cmake. Mutually exclusive with script.
        :param script: Script to run instead of a build.
        :param environment: Build environment
        :param tests: List of tests. Either a script path or link into test_scripts.
        :param requirements: List of labels representing requirements for the build
        :param test_scripts: dict of test scripts specified in build_info.py.
        """
        self.config = config
        self.set_config = set_config
        self.unset_config = unset_config
        self.build = build
        self.script = script
        self.environment = environment
        self.tests = tests
        self.requirements = requirements
        self.test_scripts = test_scripts

    @staticmethod
    def on_child_signalled(signum, frame):
        print("Signal %d received!" % signum)

    @staticmethod
    def on_child_startup():
        # Ignore signals in subprocess to avoid unintentional termination.
        for attr in [x for x in dir(signal) if x.startswith("SIG")]:
            try:
                signum = getattr(signal, attr)
                signal.signal(signum, Build.on_child_signalled)
            except Exception:
                pass

    def run_command(self, cmd_str, environment=None):
        """
        Run command with given environment.

        :param cmd_str: Command to run.
        :param environment: Environment dict k,v = env name, value
        """
        # Create copy of system environment and expand and add test environment
        env = os.environ.copy()
        if environment:
            env.update(environment)

        # Extract leading variables in command and put into env
        cmd = []
        for part in shlex.split(cmd_str):
            m = re.match("(.*?)=(.*)", part)
            if len(cmd) == 0 and m:
                env[m.group(1)] = m.group(2)
            else:
                cmd.append(part)
        env = {k: os.path.expandvars(v) for k,v in env.items()}
        print(cmd_str)

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
        cmake_build_type = self.environment.get("CMAKE_BUILD_TYPE", "")
        pwd = os.path.abspath(os.path.curdir)
        self.run_with_env("cmake -D UNSAFE_BUILD=%s -D CMAKE_BUILD_TYPE:String=%s %s" % (unsafe_build, cmake_build_type, pwd))
        self.do_make()

    def run(self):
        """
        Execute the build in following order:
        1. Do Mbed TLS config.
        2. Perform make or cmake build or execute a script.
        3. Perform tests.
        """
        # Call cleanup first, since there may be left over build artefact from
        # the previous build.
        self.cleanup()

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
            if isinstance(test, types.FunctionType):
                assert test() == True, "Test %s returned False" % getattr(a, '__name__', '')
            else:
                if test in self.test_scripts:
                    for cmd in self.test_scripts[test]:
                        self.run_with_env(cmd)
                else:
                    self.run_with_env(test)

    def cleanup(self):
        """
        Clean the workspace, remove generated build artefacts and restore
        config.
        """
        self.run_with_env(self.CLEANUP_SCRIPT)


#####################################################################
# CI data parsing
#####################################################################


#####################################################################
# Command line option parsers
#####################################################################


def build_opt_handler(args):
    """
    Handler for build sub command options.
    :param args:
    :return:
    """
    parser = BuildInfo()
    if args.list_builds:
        for build in parser.get_build_names():
            print(build)
    elif args.run_build:
        build_info = parser.get_build(args.run_build)
        build = Build(**build_info)
        build.run()


def campaign_opt_handler(args):
    """
    Handler for campaign sub command options.
    :param args:
    :return:
    """
    parser = BuildInfo()

    if args.list_campaigns:
        print("\n".join(parser.get_campaigns()))
    elif args.list_builds:
        campaign_name = args.list_builds
        print("\n".join(parser.get_builds_in_campaign(campaign_name)))
    elif args.run_builds:
        campaign_name = args.run_builds
        builds = parser.get_builds_in_campaign(campaign_name)
        for build_name in builds:
            print("*********************************************")
            print("Running build: %s" % build_name)
            print("*********************************************")
            build_info = parser.get_build(build_name)
            build = Build(**build_info)
            build.run()


def job_opt_handler(args):
    """
    Handler for job sub command options.
    :param args:
    :return:
    """
    parser = BuildInfo()

    if args.list_jobs:
        print("\n".join(parser.get_jobs()))
    elif args.list_builds:
        job_name = args.list_builds
        for platform, build in parser.get_builds_in_job(job_name):
            print("%s|%s" % (platform, build))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="List and execute builds.")
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
        '-t', '--list-builds',
        dest='list_builds',
        metavar="CAMPAIGN_NAME",
        help='List builds in a campaign')
    campaign_parser.add_argument(
        '-r', '--run-builds',
        dest='run_builds',
        metavar="CAMPAIGN_NAME",
        help='Run builds in a campaign')
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
        '-t', '--list-builds',
        dest='list_builds',
        metavar="JOB_NAME",
        help='List builds in a job')
    job_parser.set_defaults(func=job_opt_handler)

    # Parser for build options
    build_parser = subparsers.add_parser(
        'build',
        help='Build options')
    build_parser.add_argument(
        '-l', '--list',
        action='store_true',
        dest='list_builds',
        help='List builds')
    build_parser.add_argument(
        '-r', '--run-build',
        dest='run_build',
        metavar="TEST_NAME",
        help='Run a build')
    build_parser.set_defaults(func=build_opt_handler)
    args = parser.parse_args()
    args.func(args)

