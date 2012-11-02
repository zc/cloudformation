##############################################################################
#
# Copyright (c) 2010 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
from zope.testing import setupstack
import json
import manuel.capture
import manuel.doctest
import manuel.testing
import mock
import pprint
import unittest

def side_effect(m):
    return lambda f: setattr(m, 'side_effect', f)

class Stack:
    rid = 0

    def __init__(self, stack_name):
        self.stack_name = stack_name

    def _setid(self, resource):
        self.__class__.rid += 1
        resource['id'] = str(self.__class__.rid)

    def set_data(self, src):
        data = json.loads(src)
        pprint.pprint(data, width=1)
        self._setid(data)
        for n, r in sorted(data.get('Resources', {}).items()):
            self.__class__.rid += 1
            r['id'] = str(self.__class__.rid)
        self.data = data

class CloudFormationConnection:

    def __init__(self):
        self.stacks = {}

    def describe_stacks(self):
        return self.stacks.values()

    def create_stack(self, stack_name, src):
        if stack_name in self.stacks:
            raise KeyError(stack_name)
        print 'create', stack_name
        self.stacks[stack_name] = Stack(stack_name)
        return self.stacks[stack_name].set_data(src)

    def update_stack(self, stack_name, src):
        return self.stacks[stack_name].set_data(src)

    def describe_stack_resource(self, stack_name, resource_name):
        resource = self.stacks[stack_name].data['Resources'][resource_name]
        return dict(
            DescribeStackResourceResponse=dict(
                DescribeStackResourceResult=dict(
                    StackResourceDetail=dict(
                        PhysicalResourceId=resource['id']))))

class O:
    def __init__(self, **kw):
        self.__dict__.update(**kw)

class EC2Connection:

    def get_all_images(self, filters=None):
        if filters and filters.get('tag:Name') == 'default':
            return [O(id='ami-42')]

def writefile(file_name, data):
    with open(file_name, 'w') as f:
        f.write(data)

def setUp(test):
    setupstack.setUpDirectory(test)
    connect_to_region = setupstack.context_manager(
        test, mock.patch('boto.cloudformation.connect_to_region'))

    connection = CloudFormationConnection()

    @side_effect(
        setupstack.context_manager(
            test, mock.patch('boto.cloudformation.connect_to_region')))
    def _(region_name):
        print 'connecting to', region_name
        return connection

    @side_effect(
        setupstack.context_manager(
            test, mock.patch('boto.ec2.connect_to_region')))
    def _(region_name):
        if region_name != 'us-f12g':
            raise AssertionError
        return EC2Connection()

    test.globs['writefile'] = writefile


def test_suite():
    return unittest.TestSuite((
        manuel.testing.TestSuite(
            manuel.doctest.Manuel() + manuel.capture.Manuel(),
            'README.test', 'storage.test',
            setUp=setUp, tearDown=setupstack.tearDown,
            ),
        ))

