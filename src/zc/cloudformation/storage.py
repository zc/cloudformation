import zc.cloudformation

class volume:

    def __init__(self, stack, name, zone, size, count=1, replicas=('',)):
        self.stack = stack
        self.name = name
        self.zone = zone
        self.size = size
        self.count = count
        self.replicas = replicas

        for replica in replicas:
            for n in range(count):
                rname = self.rname(replica, n)
                setattr(stack.resources, rname,
                        zc.cloudformation.Resource(
                            "AWS::EC2::Volume",
                            Size=size,
                            AvailabilityZone=zone,
                            DeletionPolicy="Retain",
                            Tags=dict(Name="%s %s" % (stack.name, rname)),
                            ))

    def rname(self, replica, index):
        name = self.name
        replica = str(replica)
        if replica:
            name += 'R'+replica
        if self.count > 1:
            name += 'N%s' % (index + 1)
        return name

    def __call__(self, *args, **kw):
        return Attachment(self, *args, **kw)


class Attachment:

    def __init__(self, volume, mount_point, device, replica=None):
        self.volume = volume
        self.mount_point = mount_point
        self.device = device
        self.replica = replica

class InconsistentAttachements(Exception):
    """Multiple attachments for a server have inconsistent stacks or replicas
    """

user_data_base = '''#!/bin/sh -vex
mkdir -p /etc/zim
'''

def servers(attachment, image, name='storage', zone=None, subnet=None,
            type='m1.small', domain=None, role=None, security_groups=None,
            instance_profile=None, tags=None):

    if isinstance(attachment, Attachment):
        attachment = attachment,

    stack = attachment[0].volume.stack
    replicas = attachment[0].volume.replicas
    for a in attachment[1:]:
        if a.replica is not None:
            raise TypeError("Can't use attachment replicats with servers")
        if (a.volume.stack is not stack or
            a.volume.replicas != replicas):
            raise InconsistentAttachements

    for replica in replicas:
        if tags:
            tags = tags.copy()
        else:
            tags = {}
        rname = name + str(replica)
        if domain:
            hostname = rname + '.' + domain
        else:
            hostname = None
            tags.update(Name=rname)

        setattr(stack.resources, rname,
                server(attachment, image, zone, subnet,
                       type, role, security_groups,
                       instance_profile, tags,
                       replica=replica, hostname=hostname))

def server(attachment, image, zone=None, subnet=None,
           type='m1.small', role=None, security_groups=None,
           instance_profile=None, tags=None, replica='', hostname=None):

    tags = tags or {}

    user_data = user_data_base
    if hostname:
        user_data += 'hostname %s\n' % hostname
        tags = tags.copy()
        tags.update(Name=hostname)

    if role:
        user_data += 'cat %r > /etc/zim/role' % role

    if isinstance(attachment, Attachment):
        attachment = attachment,

    vzone = attachment[0].volume.zone
    for a in attachment[1:]:
        if a.volume.zone != vzone:
            raise InconsistentAttachements

    volumes = []
    for a in attachment:
        areplica = replica if a.replica is None else a.replica
        if isinstance(a.device, basestring):
            devices = ["%s%s" % (a.device, n+1) for n in range(a.volume.count)]
        else:
            devices = a.device
        for n in range(a.volume.count):
            volumes.append(
                dict(Device=devices[n],
                     VolumeId=zc.cloudformation.ref(
                         a.volume.rname(areplica, n))
                    ))
        user_data += "cat %s %s >> /etc/zim/volumes\n" % (
            a.mount_point, ' '.join(devices))

    properties = dict(
        ImageId=image,
        InstanceType=type,
        Tags=tags,
        Volumes=volumes,
        UserData=user_data.encode('base64'),
        )
    if zone:
        if zone != vzone:
            raise ValueError("Volume and server in different zones")
        properties.update(AvailabilityZone=zone)
        if subnet:
            raise TypeError("Can't specify both zone and subnet")
    elif subnet:
        # XXX check subnet zome
        properties.update(SubnetId=subnet)
    else:
        properties.update(AvailabilityZone=vzone)

    if security_groups:
        if subnet:
            properties.update(SecurityGroups=security_groups)
        else:
            properties.update(SecurityGroupIds=security_groups)

    if instance_profile:
        properties.update(IamInstanceProfile=instance_profile)

    return zc.cloudformation.Resource("AWS::EC2::Instance", **properties)

