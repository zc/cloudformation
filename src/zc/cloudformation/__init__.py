"""usage: %prog module_name
"""
import boto.cloudformation
import boto.exception
import boto.ec2
import json
import logging
import optparse
import re
import sys
import time

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
        self.connection = boto.cloudformation.connect_to_region(region_name)

        self.resources = Resources()
        self.data = dict(Resources=self.resources.__dict__)

        if self.__doc__:
            self.data['Description'] = self.__doc__

        self.init()

    def init(self):
        pass

    # Decorator support:
    def __call__(self, func):
        if func.__doc__:
            self.data['Description'] = func.__doc__
        func(self)
        return self

    def to_json(self):
        j = json.dumps(
            self.data, cls=JSONEncoder, sort_keys=True, indent=2
            )
        return j

    def stack_ref(self, stack_name, resource_name):
        return self.connection.describe_stack_resource(
            stack_name, resource_name
            )[u'DescribeStackResourceResponse'
              ][u'DescribeStackResourceResult'
                ][u'StackResourceDetail'
                  ][u'PhysicalResourceId']

    def image_by_name(self, name):
        [image] = boto.ec2.connect_to_region(self.region_name).get_all_images(
            filters={'tag:Name': name})
        return image.id

    def user_data(self, *args):
        return {"Fn::Base64": {"Fn::Join": ["", args]}}

    def resource(self, name, *args, **kw):
        setattr(self.resources, name, Resource(*args, **kw))

def ref(name):
    return dict(Ref=name)

def attr(rname, rattr):
    return {"Fn::GetAtt": [rname, rattr]}

def main(args=None):
    if args is None:
        args = sys.argv[1:]

    options, args = parser.parse_args(args)

    [module_name] = args

    logging.basicConfig()

    if is_module(module_name):
        globs = __import__(module_name, {}, {}, ['*']).__dict__
    else:
        globs = {}
        execfile(module_name, globs)

    stack = globs['stack']

    upload(stack)

def upload(stack=None, create_only=False):
    if stack is None:
        return lambda s: upload(s, create_only)

    try:
        update = [s for s in stack.connection.describe_stacks(stack.name)
                  if s.stack_name == stack.name]
    except boto.exception.BotoServerError:
        update = []

    if update:
        if create_only:
            raise SystemError("Updates not allowed.")

        try:
            stack.connection.update_stack(stack.name, stack.to_json())
        except boto.exception.BotoServerError, v:
            if "No updates are to be performed." in v.error_message:
                return
            else:
                print v.message
                raise
    else:
        try:
            stack.connection.create_stack(stack.name, stack.to_json())
        except boto.exception.BotoServerError, v:
            print v.message
            raise

    [boto_stack] = stack.connection.describe_stacks(stack.name)
    while not (boto_stack.stack_status.endswith('_COMPLETE') or
               boto_stack.stack_status.endswith('_FAILED')):
        print boto_stack.stack_status
        time.sleep(9)
        boto_stack.update()

    expected = 'UPDATE_COMPLETE' if update else 'CREATE_COMPLETE'
    if boto_stack.stack_status != expected:
        raise ValueError("Fail", boto_stack.stack_status)

    print boto_stack.stack_status

def find_stack(name, region_name=None):
    found = []

    if region_name:
        region_names = region_name,
    else:
        region_names = sorted(region.name
                              for region in boto.cloudformation.regions())

    for region_name in region_names:
        conn = boto.cloudformation.connect_to_region(region_name)
        found.extend([s for s in conn.describe_stacks()
                      if s.stack_name == name])

    if found:
        if len(found) > 1:
            raise LookupError("In more than one region", name)
        return found[0]

def stack_region(name, region_name=None):
    stack = find_stack(name, region_name)
    if stack:
        return stack.connection.region.name
    raise LookupError(name)

def delete_stacks(args=None):
    if args is None:
        args = sys.argv[1:]

    parser = optparse.OptionParser(__doc__)
    parser.add_option('--region', '-r', help='Region to look for stacks in')

    options, stacks = parser.parse_args(args)

    logging.basicConfig()

    for stack_name in stacks:
        stack = find_stack(stack_name, options.region)
        stack.connection.delete_stack(stack_name)
        stack.update()

        while not (stack.stack_status.endswith('_COMPLETE') or
                   stack.stack_status.endswith('_FAILED')):
            print stack.stack_status
            time.sleep(9)
            stack.update()

        if stack.stack_status != 'DELETE_COMPLETE':
            raise ValueError("Fail", stack.stack_status)

        print stack.stack_status
