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


ROOT_KEY_BUILDS = "builds"
ROOT_KEY_CAMPAIGNS = "campaigns"
ROOT_KEY_JOBS = "jobs"


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
        schema = self._schema("list")
        for element in data:
            schema.validate(element, tag)


class AttributeSchema(Schema):
    """
    Validate a dictionary with specific keys (attribute names) and value (attribute value) types. Example:

    class BuildSchema(AttributeSchema):
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
        known_attributes = [schema.get_name() for schema in self._attributes]
        for key in data.keys():
            if key not in known_attributes:
                    raise ValueError("%s Unknown attribute '%s' found in '%s'"
                    % (tag, key, self.get_name()))


class StrSchema(Schema):
    """String object schema"""
    _type = str


class StringDictSchema(DictSchema):
    """Dictionary of strings schema."""
    _schema = StrSchema


class StrListSchema(ListSchema):
    """String list schema."""
    _schema = StrSchema


class ConfigSchema(AttributeSchema):
    """
    Schema for config item in a build.
    """
    _attributes = [
        StrSchema("config", False),
        StrListSchema("set", False),
        StrListSchema("unset", False),
    ]

class BuildSchema(AttributeSchema):
    """
    Test schema with member attributes.
    """
    _attributes = [
        StringDictSchema("environment", False),
        ConfigSchema("config", False),
        StrSchema("build", False),
        StrSchema("script", False),
        Schema("tests", False, list),
        StrListSchema("requires", False),
    ]

    def validate(self, data, tag=""):
        """
        Check either 'build' or 'script' is present in addition to base AttributeSchema Validation.

        :param data:
        :param tag:
        :return:
        """
        super(BuildSchema, self).validate(data, tag)
        tag = self.update_tag(tag)
        if "build" not in data and "script" not in data:
            raise ValueError("%s Neither 'build' nor 'script' present in build '%s'" % (tag, self.get_name()))
        if "build" in data and "script" in data:
            raise ValueError("%s Both 'build' and 'script' specified in build '%s'" % (tag, self.get_name()))


class BuildSequence(DictSchema):
    """Tests dict {name: value} schema"""
    _schema = BuildSchema


class CampaignSequence(DictSchema):
    """Test Campaign dict schema"""
    _schema = StrListSchema


class PlatformListSchema(ListSchema):
    """Platform list"""
    _schema = StrSchema


class CampaignListSchema(ListSchema):
    """Campaign list"""
    _schema = StrSchema


class ComboSchema(AttributeSchema):
    """
    Platforms x Campaigns combinations.
    """
    _attributes = [
        PlatformListSchema("platforms"),
        CampaignListSchema(ROOT_KEY_CAMPAIGNS)
    ]


class ComboList(ListSchema):
    """
    List of Platforms x Campaigns
    """
    _schema = ComboSchema


class JobSequence(DictSchema):
    """
    Job schema containing list of Platforms x Campaigns combinations. 
    """
    _schema = ComboList


class TestScriptSchema(ListSchema):
    """Test script a list of commands."""
    _schema = StrSchema


class TestScriptSequence(DictSchema):
    """ List of test scripts"""
    _schema = TestScriptSchema


class RootSchema(AttributeSchema):
    """
    Root schema with attributes: builds, test-scripts, campaigns and jobs.
    """
    _attributes = [
        BuildSequence(ROOT_KEY_BUILDS),
        CampaignSequence(ROOT_KEY_CAMPAIGNS),
        JobSequence(ROOT_KEY_JOBS),
        TestScriptSequence("test-scripts", False)
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
        self.validate()

    def validate(self):
        """
        Validate CI data file.
        """
        vr = RootSchema("root")
        vr.validate(self.ci_data)

    def get_campaigns(self):
        """Get campaign names"""
        return sorted(self.ci_data[ROOT_KEY_CAMPAIGNS].keys())

    def get_builds_in_campaign(self, campaign_name):
        """
        Get builds in campaign.
        """
        return sorted(self.ci_data[ROOT_KEY_CAMPAIGNS][campaign_name])

    def get_jobs(self):
        """
        Get job names.
        """
        return sorted(self.ci_data[ROOT_KEY_JOBS].keys())

    def get_builds_in_job(self, job_name):
        """
        Get builds in job.
        """
        job_data = self.ci_data[ROOT_KEY_JOBS][job_name]
        for combo in job_data:
            platforms = combo["platforms"]
            campaigns = combo[ROOT_KEY_CAMPAIGNS]
            for platform in sorted(platforms):
                for campaign in campaigns:
                    builds = self.get_builds_in_campaign(campaign)
                    for build in builds:
                        yield platform, build

    def get_build_names(self):
        """
        Get build names.
        """
        return sorted(self.ci_data[ROOT_KEY_BUILDS].keys())

    def get_build(self, build_name):
        """Gives Test object for specified build name."""
        assert build_name in self.ci_data[ROOT_KEY_BUILDS], \
            "Test '%s' no found!" % build_name
        build_data = self.ci_data[ROOT_KEY_BUILDS][build_name]
        build_info = dict()
        build_info["config"] = build_data.get("config", {}).get("config", None)
        build_info["set_config"] = build_data.get("config", {}).get("set", [])
        build_info["unset_config"] = build_data.get("config", {}).get("unset", [])
        build_info["build"] = build_data.get("build", None)
        build_info["script"] = build_data.get("script", None)
        build_info["environment"] = build_data.get("environment", {})
        build_info["tests"] = build_data.get('tests', [])
        build_info["requirements"] = build_data.get('requires', [])
        build_info["test_scripts"]=self.ci_data.get("test-scripts", {})
        return build_info


if __name__=="__main__":
    build_info = BuildInfo()
    print("Build info valid!")
