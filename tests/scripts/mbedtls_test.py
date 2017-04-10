"""
mbed SDK
Copyright (c) 2011-2013 ARM Limited

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import re
import os
import time
from mbed_host_tests import BaseHostTest, event_callback


class TestDataParser(object):
    """
    parser for mbedtls test data files.
    """

    def __init__(self):
        """
        Constructor
        """
        self.tests = []

    def parse(self, data_file):
        """

        """
        with open(data_file, 'r') as f:
            self.__parse(f)

    @staticmethod
    def __readline(fd):
        """
        Reads a full line.
        """
        ret = ''
        line = fd.readline(1024)
        while line:
            ret += line
            if line[-1] != '\n':
                break
            line = fd.readline(1024)
        return ret

    @staticmethod
    def __escaped_split(str, ch):
        """
        """
        if len(ch) > 1:
            raise ValueError('Expected split character. Found string!')
        out = []
        part = ''
        escape = False
        for i in range(len(str)):
            if not escape and str[i] == ch:
                out.append(part)
                part = ''
            else:
                part += str[i]
                escape = not escape and str[i] == '\\'
        if len(part):
            out.append(part)
        return out

    def __parse(self, file):
        """
        """
        line = file.readline().strip()
        while line:
            line = line.strip()
            if len(line) == 0:
                line = file.readline()
                continue
            # Read test name
            name = line

            # Check dependencies
            deps = []
            line = file.readline().strip()
            m = re.search('depends_on\:(.*)', line)
            if m:
                deps = m.group(1).split(':')
                line = file.readline().strip()

            # Read test vectors
            line = line.replace('\\n', '\n#')
            parts = self.__escaped_split(line, ':')
            function = parts[0]
            x = parts[1:]
            l = len(x)
            assert l % 2 == 0, "Number of test arguments should be even: %s" % line
            args = [(x[i * 2], x[(i * 2) + 1]) for i in range(len(x)/2)]
            self.tests.append((name, function, deps, args))
            line = file.readline()

    def get_test_data(self):
        """
        """
        return self.tests


class MbedTlsTest(BaseHostTest):
    """
    Host test for mbed-tls target tests.
    """

    def __init__(self):
        """
        """
        super(MbedTlsTest, self).__init__()
        self.tests = []
        self.test_index = -1
        self.dep_index = 0

    def setup(self):
        """
        """
        binary_path = self.get_config_item('image_path')
        script_dir = os.path.split(os.path.abspath(__file__))[0]
        data_file = ".".join((os.path.splitext(os.path.basename(binary_path))[0], 'data'))
        data_file = os.path.join(script_dir, 'suites', data_file)
        if os.path.exists(data_file):
            self.log("Running tests from %s" % data_file)
            parser = TestDataParser()
            parser.parse(data_file)
            self.tests = parser.get_test_data()
            self.print_test_info()
        else:
            self.log("Data file not found: %s" % data_file)
            self.notify_complete(False)

    def print_test_info(self):
        """
        """
        self.log('{{__testcase_count;%d}}' % len(self.tests))
        for name, _, _, _ in self.tests:
            self.log('{{__testcase_name;%s}}' % name)

    def run_next_test(self):
        """
        Send next test function to the target.

        """
        self.test_index += 1
        self.dep_index = 0
        self.test_started = False
        if self.test_index < len(self.tests):
            name, function, deps, args = self.tests[self.test_index]
            if len(deps):
                dep = deps[self.dep_index]
                self.send_kv('CD', dep)
                self.dep_index += 1
            else:
                self.send_kv("T", function)
        else:
            self.notify_complete(True)

    def get_test_name(self):
        """
        Gives test name
        """
        if self.test_index < len(self.tests):
            name = self.tests[self.test_index][0]
            return name
        return None

    def get_test_func(self):
        """
        Gives test function name
        """
        if self.test_index < len(self.tests):
            name = self.tests[self.test_index][1]
            return name
        return None

    def get_result(self, value):
        try:
            return int(value)
        except ValueError:
            self.log("ValueError for received value in 'check_dep' k,v. Should be integer.")
        return 0

    @event_callback('GO')
    def on_go(self, key, value, timestamp):
        self.run_next_test()

    @event_callback('CD')
    def on_dep_check(self, key, value, timestamp):
        name, function, deps, args = self.tests[self.test_index]
        if value == "1":
            if self.dep_index < len(deps):
                dep = deps[self.dep_index]
                self.send_kv('CD', dep)
                self.dep_index += 1
            else:
                self.send_kv("T", function)

    @event_callback('SC')
    def on_send_count(self, key, value, timestamp):
        name, function, deps, args = self.tests[self.test_index]
        self.send_kv("N", len(args))

    @event_callback('SP')
    def on_send_param(self, key, value, timestamp):
        i = int(value)
        name, function, deps, args = self.tests[self.test_index]
        typ, arg = args[i]
        if typ == 'int':
            self.send_kv("I", arg)
        elif typ == 'exp':
            self.send_kv("E", arg)
        elif typ == 'char*':
            self.send_kv("S", str(len(arg.strip('"'))))
        else:
            raise ValueError("Invalid type '%s'" % typ)

    @event_callback('D')
    def on_send_data(self, key, value, timestamp):
        i = int(value)
        name, function, deps, args = self.tests[self.test_index]
        typ, arg = args[i]
        self.send_kv('D', arg.strip('"'))

    @event_callback("ST")
    def on_start_test(self, key, value, timestamp):
        """
        """
        name, function, deps, args = self.tests[self.test_index]
        self.log('{{__testcase_start;%s}}' % name)

    @event_callback("R")
    def on_result(self, key, value, timestamp):
        """
        Handle result.

        """
        int_val = self.get_result(value)
        name, function, deps, args = self.tests[self.test_index]
        self.log('{{__testcase_finish;%s;%d;%d}}' % (name, int_val, not int_val))

