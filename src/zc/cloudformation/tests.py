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

    def __init__(self, stack_name, src):
        self.stack_name = stack_name
        self.set_data(src)

    def set_data(self, src):
        data = json.loads(src)
        pprint.pprint(data, width=1)
        for n, r in sorted(data.get('Resources', {}).items()):
            self.__class__.rid += 1
            r['id'] = str(self.__class__.rid)
        self.data = data

class Connection:

    def __init__(self):
        self.stacks = {}

    def describe_stacks(self):
        return self.stacks.values()

    def create_stack(self, stack_name, src):
        if stack_name in self.stacks:
            raise KeyError(stack_name)
        print 'create', stack_name
        self.stacks[stack_name] = Stack(stack_name, src)

    def update_stack(self, stack_name, src):
        self.stacks[stack_name].set_data(src)

    def describe_stack_resource(self, stack_name, resource_name):
        resource = self.stacks[stack_name].data['Resources'][resource_name]
        return dict(
            DescribeStackResourceResponse=dict(
                DescribeStackResourceResult=dict(
                    StackResourceDetail=dict(
                        PhysicalResourceId=resource['id']))))

def writefile(file_name, data):
    with open(file_name, 'w') as f:
        f.write(data)

def setUp(test):
    setupstack.setUpDirectory(test)
    connect_to_region = setupstack.context_manager(
        test, mock.patch('boto.cloudformation.connect_to_region'))

    connection = Connection()

    @side_effect(connect_to_region)
    def _(region_name):
        print 'connecting to', region_name
        return connection

    test.globs['writefile'] = writefile


def test_suite():
    return unittest.TestSuite((
        manuel.testing.TestSuite(
            manuel.doctest.Manuel() + manuel.capture.Manuel(),
            'README.test',
            setUp=setUp, tearDown=setupstack.tearDown,
            ),
        ))

