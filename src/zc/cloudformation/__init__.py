"""usage: %prog module_name
"""
import boto.cloudformation
import json
import optparse
import re
import sys

parser = optparse.OptionParser(__doc__)

is_module = re.compile(r'[a-zA-Z]\w*(\.[a-zA-Z]\w*)*$').match

class Resource:

    def __init__(self, type, DependsOn=None, DeletionPolicy=None, Metadata=None,
                 **properties):
        if 'Tags' in properties and isinstance(properties['Tags'], dict):
            properties['Tags'] = sorted(
                (dict(Key=k, Value=v)
                 for (k, v) in properties['Tags'].items()),
                key=lambda i: i['Key'])
        self.data = dict(Type=type, Properties=properties)
        if DependsOn:
            self.data.update(DependsOn=DependsOn)
        if DeletionPolicy:
            self.data.update(DeletionPolicy=DeletionPolicy)
        if Metadata:
            self.data.update(Metadata=Metadata)

class JSONEncoder(json.JSONEncoder):

    def default(self, o):
        if isinstance(o, Resource):
            return o.data
        return json.JSONEncoder.default(self, o)

class Resources:
    pass

class Stack:

    def __init__(self, region_name, name):

        self.region_name = region_name
        self.name = name

        self.resources = Resources()
        self.data = dict(Resources=self.resources.__dict__)

        if self.__doc__:
            self.data['Description'] = self.__doc__

        self.init()

    def init(self):
        pass

    # Decorator support:
    def __call__(self, func):
        func(self)
        return self

    def to_json(self):
        return json.dumps(self.data, cls=JSONEncoder)


def main(args=None):
    if args is None:
        args = sys.argv[1:]

    options, args = parser.parse_args(args)

    [module_name] = args

    if is_module(module_name):
        globs = __import__(module_name, {}, {}, ['*']).__dict__
    else:
        globs = {}
        execfile(module_name, globs)

    stack = globs['stack']
    cfconn = boto.cloudformation.connect_to_region(stack.region_name)

    update = [s for s in cfconn.describe_stacks() if s.stack_name == stack.name]
    if update:
        cfconn.update_stack(stack.name, stack.to_json())
    else:
        cfconn.create_stack(stack.name, stack.to_json())
