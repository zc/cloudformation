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
import boto.exception
import json
import manuel.capture
import manuel.doctest
import manuel.testing
import mock
import pprint
import unittest

def side_effect(m):
    return lambda f: setattr(m, 'side_effect', f)

class Region:

    def __init__(self, name):
        self.name = name

class Stack:
    rid = 0
    stack_status = None

    def __init__(self, stack_name, connection):
        self.stack_name = stack_name
        self.connection = connection
        self.data = self.raw = {}

    def _setid(self, resource, base):
        if base:
            resource['id'] = base['id']
        else:
            self.__class__.rid += 1
            resource['id'] = str(self.__class__.rid)

    def update(self):
        if 'fail' in self.data.get('Resources', ()):
            self.stack_status = 'ROLLBACK_COMPLETE'
        else:
            self.stack_status = self.stack_status.replace(
                'IN_PROGRESS', 'COMPLETE')

    def set_data(self, src, noisy=True):
        raw = json.loads(src)
        if raw and raw == self.raw:
            raise boto.exception.BotoServerError(
                '400', 'Bad Request',
                '{"Error":{"Code":"ValidationError",'
                '"Message":"No updates are to be performed.",'
                '"Type":"Sender"},'
                '"RequestId":"ab2b78fa-2761-11e2-9605-ff38a7d8daf7"}'
                )
        self.raw = raw
        data = json.loads(src)
        if noisy:
            pprint.pprint(data, width=1)
        self._setid(data, self.data)
        for n, r in sorted(data.get('Resources', {}).items()):
            self._setid(r, self.data.get(n))
        self.data = data
        if self.stack_status is None:
            self.stack_status = 'CREATE_IN_PROGRESS'
        else:
            self.stack_status = 'UPDATE_IN_PROGRESS'

    def describe_resource(self, resource_name):
        resource = self.data['Resources'][resource_name]
        return dict(
            DescribeStackResourceResponse=dict(
                DescribeStackResourceResult=dict(
                    StackResourceDetail=dict(
                        PhysicalResourceId=resource['id']))))

class CloudFormationConnection:

    def __init__(self, region):
        self.stacks = {}
        self.region = region
        self.create_stack('inall', '{}', False)

    def describe_stacks(self, name=None):
        if name:
            return [stack for stack in self.stacks.values()
                    if stack.stack_name == name]
        return self.stacks.values()

    def create_stack(self, stack_name, src, noisy=True):
        if stack_name in self.stacks:
            raise KeyError(stack_name)
        if noisy:
            print 'create', stack_name
        self.stacks[stack_name] = Stack(stack_name, self)
        self.stacks[stack_name].set_data(src, noisy)

    def update_stack(self, stack_name, src):
        self.stacks[stack_name].set_data(src)

    def describe_stack_resource(self, stack_name, resource_name):
        return self.stacks[stack_name].describe_resource(resource_name)

    def delete_stack(self, stack_name):
        stack = self.stacks.pop(stack_name)
        stack.stack_status = "DELETE_IN_PROGRESS"

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

    regions = ()
    connections = {}
    for name in 'us-f12g', 'us-manassas':
        regions += (Region(name), )
        connections[name] = CloudFormationConnection(regions[-1])

    test.globs['connections'] = connections

    @side_effect(
        setupstack.context_manager(
            test, mock.patch('boto.cloudformation.connect_to_region')))
    def _(region_name):
        print 'connecting to', region_name
        return connections[region_name]

    setupstack.context_manager(
        test, mock.patch('boto.cloudformation.regions',
                         side_effect=lambda : regions)
        )

    @side_effect(
        setupstack.context_manager(
            test, mock.patch('boto.ec2.connect_to_region')))
    def _(region_name):
        if region_name != 'us-f12g':
            raise AssertionError
        return EC2Connection()

    test.globs['writefile'] = writefile

    setupstack.context_manager(test, mock.patch('logging.basicConfig'))
    setupstack.context_manager(test, mock.patch('time.sleep'))


def test_suite():
    return unittest.TestSuite((
        manuel.testing.TestSuite(
            manuel.doctest.Manuel() + manuel.capture.Manuel(),
            'README.test', 'storage.test',
            setUp=setUp, tearDown=setupstack.tearDown,
            ),
        ))

