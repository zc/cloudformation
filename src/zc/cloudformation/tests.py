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

    def __init__(self, stack_name, src):
        self.stack_name = stack_name
        self.src = src

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
        pprint.pprint(json.loads(src))

    def update_stack(self, stack_name, src):
        self.stacks[stack_name].src = src
        pprint.pprint(json.loads(src))

def setUp(test):
    setupstack.setUpDirectory(test)
    connect_to_region = setupstack.context_manager(
        test, mock.patch('boto.cloudformation.connect_to_region'))
    @side_effect(connect_to_region)
    def _(region_name):
        print 'connecting to', region_name
        return Connection()


def test_suite():
    return unittest.TestSuite((
        manuel.testing.TestSuite(
            manuel.doctest.Manuel() + manuel.capture.Manuel(),
            'README.test',
            setUp=setUp, tearDown=setupstack.tearDown,
            ),
        ))
