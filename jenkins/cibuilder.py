# CI Build spec generator
#
# Copyright (C) 2006-2017, ARM Limited, All Rights Reserved
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


SH_ENV_FILE='cienv.sh'
BATCH_ENV_FILE='cienv.bat'

mbedtls_scripts = {
    'mingw-make': {
        'script': """
cmake . -G MinGW Makefiles
            mingw32-make clean
            mingw32-make
        mingw32-make test
        programs\\test\\selftest.exe
"""
    },
    'msvc12-32': {
        'script': """ cmake . -G Visual Studio 12
MSBuild ALL_BUILD.vcxproj
"""
    },
    'msvc12-64': {
        'script': """ cmake . -G Visual Studio 12 Win64
MSBuild ALL_BUILD.vcxproj
"""
    }
}


ci_test_campaigns = {
   "commit_tests": {
       'make-gcc': {
           'script': 'make',
           'environment': {'MAKE': 'make', 'CC': 'gcc'},
           'platforms': ['debian-9-i386', 'debian-9-x64'],

       },
       'gmake-gcc': {
           'script': 'make',
           'environment': {'MAKE': 'gmake', 'CC': 'gcc'},
           'platforms': ['debian-9-i386', 'debian-9-x64'],
       },
       'cmake': {
           'script': 'cmake',
           'environment': {'MAKE': 'gmake', 'CC': 'gcc'},
           'platforms': ['debian-9-i386', 'debian-9-x64'],
       },
       'cmake-full':  {
           'script': 'cmake-full',
           'environment': {'MAKE': 'gmake', 'CC': 'gcc'},
           'platforms': ['debian-9-i386', 'debian-9-x64'],
       },
       'cmake-asan': {
           'script': 'cmake-asan',
           'environment': {'MAKE': 'gmake', 'CC': 'clang'},
           'platforms': ['debian-9-i386', 'debian-9-x64'],
       },
       'mingw-make': {
           'script': 'mingw-make',
           'platforms': ['windows'],
       },
       'msvc12-32': {
           'script': 'msvc12-32',
           'platforms': ['windows'],
       },
       'msvc12-64': {
           'script': 'msvc12-64',
           'platforms': ['windows'],
       }
   },
   "release_tests": {
        'all.sh': {
            'script': './tests/scripts/all.sh',
            'platforms': ['ubuntu-16.04-x64']
        }
    }
}


def check_scripts(campaign_name):
    try:
        campaign = ci_test_campaigns[campaign_name]
    except KeyError:
        print("Error: Invalid campaign name")
        sys.exit(1)

    for test_name, details in campaign.iteritems():
        for platform in details['platforms']:
            ci_test_name = "%s-%s" %(test_name, platform)
            yield ci_test_name, details['script'], details.get('environment', None), platform


def gen_sh_env_file(environment):
    """
    Generate environment script for ciscript.sh.
    
    :param environment: 
    :return: 
    """
    with open(SH_ENV_FILE, 'w') as f:
        if environment:
            for k, v in environment.iteritems():
                f.write("%s=%s\n" % (k, v))
        os.chmod(SH_ENV_FILE, 0o777)


def gen_bat_env_file(environment):
    """
    Generate environment script for ciscript.bat.
    
    :param environment: 
    :return: 
    """
    with open('cienv.bat', 'w') as f:
        if environment:
            for k, v in environment.iteritems():
                f.write("set %s=%s\n" % (k, v))


def list(campaign):
    """
    List tests and config
    
    :param campaign:
    :return: 
    """
    for ci_test_name, test_name, environment, platform in check_scripts(campaign):
        print "%s|%s" %(ci_test_name, platform)


def gen(test_to_generate):
    """
    Generate script for specified test.
    
    :param campaign:
    :param test_to_generate: 
    :return: 
    """
    for campaign in ci_test_campaigns.keys():
        for ci_test_name, test_name, environment, platform in check_scripts(campaign):
            if ci_test_name == test_to_generate:
                if 'windows' in platform.lower():
                    gen_bat_env_file(environment)
                else:
                    gen_sh_env_file(environment)
                return
    print ("Error: Campaign or test not found!")
    sys.exit(1)


if __name__=='__main__':
    usage = '''%s: Usage: python %s [ list <campaign> | gen <test> ]

Commands:
    list <campaign>         Lists tests and platforms in specified campaign.
                            Campaigns are [ commit_tests | release_test ]
    gen <campaign> <test>   Generates a script for specified test.
''' % (sys.argv[0], sys.argv[0])
    if len(sys.argv) < 3:
        print(usage)
        sys.exit(1)

    if sys.argv[1] == 'list':
        list(sys.argv[2])
    elif sys.argv[1] == 'gen':
        gen(sys.argv[2])
    else:
        print(usage)
        sys.exit(1)

