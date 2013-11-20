##############################################################################
#
# Copyright (c) Zope Corporation and Contributors.
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
name = 'zc.cloudformation'
version = '0.4.0'
description = """
"""

import os
from setuptools import setup, find_packages
install_requires = ['setuptools', 'boto', 'zc.zk [static]']
extras_require = dict(test=['zope.testing', 'manuel', 'mock', 'zc.zk [test]'])

entry_points = """
[console_scripts]
cloudformation = zc.cloudformation:main
delete-stacks = zc.cloudformation:delete_stacks
"""

setup(
    name = name,
    version = version,
    author = 'Jim Fulton',
    author_email = 'jim@zope.com',
    description = description.split('\n', 1)[0],
    long_description = description.split('\n', 1)[1].lstrip(),
    license = 'ZPL 2.1',

    packages = find_packages('src'),
    namespace_packages = name.split('.')[:1],
    package_dir = {'': 'src'},
    install_requires = install_requires,
    zip_safe = False,
    entry_points=entry_points,
    extras_require = extras_require,
    tests_require = extras_require['test'],
    test_suite = name+'.tests.test_suite',
    )
