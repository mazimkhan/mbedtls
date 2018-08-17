#!/usr/bin/env python
# Parser for the build info specified in build_info.py
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
This module defines schema and parser for the build info (Like the one
specified in build_info.py).
"""

import importlib


JSON_ROOT_KEY_TESTS = "tests"
JSON_ROOT_KEY_CAMPAIGNS = "campaigns"
JSON_ROOT_KEY_JOBS = "jobs"


class Schema(object):
    """
    Base schema class, it provides methods for validation of a JSON data
    element. It implements validation by type.
    Example:

        class StrSchema(Schema):
            _type = str

    Above schema validates an object of type string.
    """
    _type = None

    def __init__(self, name=None, is_mandatory=True, type=None):
        """
        Instantiate the object with element name, type and presence
        requirement.

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
        Updates the tag with this element name. Tag string is
        useful while printing format validation error as it
        indicates path of an element in the JSON document.

        :param tag:
        :return:
        """
        return "->".join((tag, self.get_name())) if tag else self.name

    def validate(self, data, tag=""):
        """
        Validate schema. In this base class validation is done for
        specified object type. This method can be overriden by
        derived classes implementing complex object schemas.

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
    Schema for validating dict objects. A validator class can be created
    by simply inheriting this class and specifying dictionary element types.
    Example:

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


class BuildInfo(object):
    """
    Parser for build_info.py. Since the build_info.py contains build
    data in the form of python objects, no special parsing is required.
    This class is more about providing utility methods to fetch the
    required information easily than traversing the data directly.
    """
    CI_META_MODULE = "build_info"

    def __init__(self):
        """
        Instantiate by importing job config.
        """
        m = importlib.import_module(self.CI_META_MODULE)
        self.ci_data = m.data

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

