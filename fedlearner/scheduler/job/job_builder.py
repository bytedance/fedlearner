# Copyright 2020 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# coding: utf-8
# pylint: disable=C0303
from fedlearner import settings

class CustomResourceDefinition(object):
    """
        Base class to describe customed resource defintinition on kubernetes.
        Inherit this class in Fedleaner to define Master/ Worker / PS 
        deployment and execute mode.

        Attributes:
            name(string): resource name in ['PS', 'Worker', 'Master'].
            image(string): docker image path for this resource.
            command(list): execute command list in docker.
            pair(bool): if need to pair the follower's resource or not
            replicas(int): replica number of this resource.
            args(list): execute command's arguments in docker.
            env(dict): programe's environment parameter.
            resources(dict): define cpu/memory/gpu's limit and request.
            restart_policy(Enum): docker restart policy.
            image_pull_policy(Enum): docker image pull policy to define 
                                     image update method.
            volume_mounts(list): mount directory.
            template_name(string): template name default 'tensorflow'
    """
    def __init__(self,
                 name,
                 image,
                 command,
                 pair=False,
                 replicas=0,
                 args=None,
                 env=None,
                 resources=None,
                 ports=None,
                 restart_policy='Never',
                 image_pull_policy='IfNotPresent',
                 template_name='tensorflow'):
        '''
            initialize CustomResourceDefinition function.
        '''
        self._name = name
        self._image = image
        self._command = command
        self._pair = pair
        self._replicas = replicas
        self._args = args
        self._env = env
        self._resources = {}
        self._ports = ports
        self._restart_policy = restart_policy
        self._image_pull_policy = image_pull_policy
        self._volume_mounts = []
        self._template_name = template_name

    @property
    def name(self):
        return self._name

    @property
    def image(self):
        return self._image

    @image.setter
    def image(self, image):
        self._image = image

    @property
    def command(self):
        return self._command

    @command.setter
    def command(self, command):
        if not isinstance(command, list):
            raise ValueError('command must be list!')
        self._command = command

    @property
    def replicas(self):
        return self._replicas

    @replicas.setter
    def replicas(self, replica):
        if not isinstance(replica, int):
            raise ValueError('replica must be an integer!')
        self._replica = replica

    @property
    def volume_mounts(self):
        return self._volume_mounts

    @volume_mounts.setter
    def volume_mounts(self, volume_mounts):
        self._volume_mounts = volume_mounts

    def add_volume(self, name, path):
        self._volume_mounts.append({'name': name, 'path': path})
        return self

    @property
    def env(self):
        return self._env

    @env.setter
    def env(self, env):
        if not isinstance(env, list):
            raise ValueError('environ must be a list')

    def set_env(self, name, value, value_from=False):
        if not self._env:
            self._env = []

        if value_from:
            self._env.append({
                'name': name,
                'valueFrom': {
                    'fieldRef': {
                        'fieldPath': str(value)
                    }
                }
            })
        else:
            self._env.append({'name': name, 'value': str(value)})

    @property
    def ports(self):
        return self._ports

    @ports.setter
    def ports(self, ports):
        if not isinstance(ports, list):
            raise ValueError('ports must be a list')
        for port in ports:
            if not port.get('containerPort', None):
                raise ValueError('port must contain containerPort')
            if not port.get('name', None):
                raise ValueError('port must contain name')
        self._ports = ports

    def set_port(self, port_name, port):
        if not self._ports:
            self._ports = []

        if not isinstance(port, int):
            raise TypeError('port must be integer')
        self._ports.append({'containerPort': port, 'name': port_name})

    @property
    def resources(self):
        return self._resources

    @resources.setter
    def resources(self, resources):
        if not isinstance(resources, dict):
            raise ValueError('resources must be a dict')
        self._resources = resources

    @property
    def args(self):
        return self._args

    @args.setter
    def args(self, args):
        if not isinstance(args, list):
            raise ValueError('args must be a list')
        self._args = args

    @property
    def restart_policy(self):
        return self._restart_policy

    @restart_policy.setter
    def restart_policy(self, restart_policy):
        if not isinstance(restart_policy, str):
            raise ValueError('restart_policy must be a list')
        self._restart_policy = restart_policy

    @property
    def image_pull_policy(self):
        return self._image_pull_policy

    @image_pull_policy.setter
    def image_pull_policy(self, image_pull_policy):
        if not isinstance(image_pull_policy, str):
            raise ValueError('image_pull_policy must be a list')
        self._image_pull_policy = image_pull_policy

    @property
    def pair(self):
        return self._pair

    @pair.setter
    def pair(self, pair):
        self._pair = pair

    @property
    def template_name(self):
        return self._template_name

    @template_name.setter
    def template_name(self, template_name):
        self._template_name = template_name


class JobConfigBuidler(object):
    """
        Base class to build job config/yaml to create FedLearner crd for 
        deploying on kubernetes.
        
        Attributes:
            name(string): name equals to application id.
            namespace(string): namespace in ['leader', 'follower'].
            role(string): job role in ['leader', 'follower'].
            application_id(string): 'leader' role create a new fedlearner 
                job with an application id, format with [{job_name}_{timestamp}]
    """
    def __init__(self, name, namespace, role, application_id):
        '''
            initialize JobConfigBuidler function.
        '''
        self._job_config = self.init_job_yaml(name, namespace, role,
                                              application_id)

    def init_job_yaml(self, name, namespace, role, application_id):
        return {
            'apiVersion':
            '%s/%s' % (settings.FL_CRD_GROUP, settings.FL_CRD_VERSION),
            'kind':
            settings.FL_KIND,
            'metadata': {
                'name': name,
                'namespace': namespace
            },
            'spec': {
                'role': role
            }
        }

    def validate(self):
        pass

    def build(self):
        return self._job_config

    def add_crd(self, resource_config):
        if not isinstance(resource_config, CustomResourceDefinition):
            raise ValueError(
                'resource_config must be ResourceConfig Base Class')

        resource_config_dict = {}
        resource_config_dict['replicas'] = resource_config.replicas
        resource_config_dict['pair'] = resource_config.pair
        resource_config_dict['template'] = {}
        spec = {}
        spec['restartPolicy'] = resource_config.restart_policy
        spec['containers'] = []
        container = {}
        container['name'] = resource_config.template_name
        container['env'] = resource_config.env
        container['image'] = resource_config.image
        container['imagePullPolicy'] = resource_config.image_pull_policy
        container['command'] = resource_config.command
        container['args'] = resource_config.args
        container['ports'] = resource_config.ports
        container['resources'] = resource_config.resources
        spec['containers'].append(container)
        resource_config_dict['template']['spec'] = spec
        if 'spec' not in self._job_config:
            self._job_config['spec'] = {}
        if 'flReplicaSpecs' not in self._job_config['spec']:
            self._job_config['spec']['flReplicaSpecs'] = {}
        self._job_config['spec']['flReplicaSpecs'][
            resource_config.name] = resource_config_dict
