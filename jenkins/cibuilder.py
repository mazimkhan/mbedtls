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


class CIEnv(object):
    """
    Specify execution environment for a Test.
    """
    pass


class CIBuilder(object):
    """
    CI Build & test steps builder.
    """

    def __init__(self, env, platform):
        """
        Instantiate builder with execution environment and platform spec.
        :param env: 
        :param platform: 
        """
        pass

    def gen(self):
        """
        Generate build script and specification.
        :return: 
        """
        platform = None
        name = None
        script = None
        return platform, name, script




mbedtls_scripts = {
    'make': {
        'script': """
${MAKE} clean
${MAKE}
${MAKE} check
./programs/test/selftest
""",
        'environment': ['CC', 'MAKE']
    },
    'cmake': {
        'script': """cmake -D CMAKE_BUILD_TYPE:String=Check .
${MAKE} clean
${MAKE}
${MAKE} test
./programs/test/selftest
""",
        'environment': ['CC', 'MAKE']
    },
    'cmake-full': {
        'script': """
${MAKE} clean
${MAKE}
${MAKE} test
./programs/test/selftest
openssl version
gnutls-serv -v
export PATH=/usr/local/openssl-1.0.2g/bin:/usr/local/gnutls-3.4.10/bin:$PATH
export SEED=1
./tests/compat.sh
find . -name c-srv-1.log|xargs cat 
./tests/ssl-opt.sh
./tests/scripts/test-ref-configs.pl
""",
        'environment': ['CC', 'MAKE']
    },
    'cmake-asan': {
        'script': """
set +e
grep \"fno-sanitize-recover=undefined,integer\" CMakeLists.txt
if [ $? -ne 0 ]; 
then 
    sed -i s/\"fno-sanitize-recover\"/\"fno-sanitize-recover=undefined,integer\"/ CMakeLists.txt; 
fi
set -e
cmake -D CMAKE_BUILD_TYPE:String=ASan .
make
make test
./programs/test/selftest
export PATH=/usr/local/openssl-1.0.2g/bin:/usr/local/gnutls-3.4.10/bin:$PATH
export SEED=1
./tests/compat.sh
./tests/ssl-opt.sh
./tests/scripts/test-ref-configs.pl
""",
        'environment': ['CC', 'MAKE']
    },
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
            print details
            yield ci_test_name, details['script'], details.get('environment', None), platform


def list(campaign):
    """
    List tests and config
    
    :param campaign:
    :return: 
    """
    for ci_test_name, test_name, environment, platform in check_scripts(campaign):
        print "%s|%s" %(ci_test_name, platform)


def gen_batch_script(script):
    """
    
    :param script: 
    :return: 
    """
    return script


def gen_sh_script(script):
    """
    
    :param script: 
    :return: 
    """
    script = "!#/bin/sh\n\nset -e\nset -x\nset -v\n\n" + script
    return script


def check_if_windows(platform):
    """
    
    :param platform: 
    :return: 
    """
    return 'windows' in platform.lower()


def gen_script(test_name, environment, platform):
    print test_name
    print environment
    print platform

    script = mbedtls_scripts[test_name]['script']
    if environment:
        for k, v in environment.iteritems():
            script = "%s=%s\n" % (k, v) + script
    if check_if_windows(platform):
        script = gen_batch_script(script)
    else:
        script = gen_sh_script(script)
    with open('script.sh', 'w') as f:
        f.write(script)


def gen(test_to_generate):
    """
    Generate script for specified test.
    
    :param campaign:
    :param test_to_generate: 
    :return: 
    """
    for campaign in ci_test_campaigns.keys():
        for ci_test_name, test_name, environment, platform in check_scripts(campaign):
            print "%s == %s" % (ci_test_name, test_to_generate)
            if ci_test_name == test_to_generate:
                gen_script(test_name, environment, platform)
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
