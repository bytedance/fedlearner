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
# pylint: disable=C0303
# pylint: disable=W0102

from .job_builder import CustomResourceDefinition

DEFAULT_RESOURCE = {
    'requests': {
        'memory': "4Gi",
        'cpu': "4000m"
    },
    'limits': {
        'memory': "4Gi",
        'cpu': "4000m"
    }
}


class PSResourceConfig(CustomResourceDefinition):
    '''
        Inherit CustomeResourceDefinition base class to describe
        parameter server resource definition on kubernetes.

        Attributes:
            application_id(string) : a fedlearner job was created with
                an application id.
            name(string): resource name in ['PS', 'Worker', 'Master'].
            image(string): docker image path for this resource.
            command(list): execute command list in docker.
            pair(bool): if need to pair the follower's resource or not
            replicas(int): replica number of this resource.
            args(list): execute command's arguments in docker.
            env(dict): programe's environment parameter.
            resources(dict): define cpu/memory/gpu's limit and request.
            restart_policy(Enum): docker restart policy.
            image_pull_policy(Enum): docker image pull policy 
                to define image update method.
            volume_mounts(list): mount directory.
            template_name(string): template name default 'tensorflow',
    '''
    def __init__(self,
                 application_id,
                 image,
                 replicas,
                 pair=False,
                 command=['/app/deploy/scripts/trainer/run_trainer_ps.sh'],
                 args=[''],
                 env=None,
                 resources=None,
                 ports=None,
                 restart_policy='Never',
                 image_pull_policy='IfNotPresent',
                 template_name='tensorflow'):

        super(PSResourceConfig,
              self).__init__('PS', image, command, pair, replicas, args, env,
                             resources, ports, restart_policy,
                             image_pull_policy, template_name)
        self.init_config(application_id)

    def init_config(self, application_id):

        if not self.resources:
            self.resources = DEFAULT_RESOURCE

        self.set_env(name='POD_NAME', value='metadata.name', value_from=True)
        self.set_env(name='POD_IP', value='status.podIP', value_from=True)
        self.set_port(port_name='flapp-port', port=50051)


class MasterResourceConfig(CustomResourceDefinition):
    '''
        Inherit CustomeResourceDefinition base class to describe
        master resource definition on kubernetes.

        Attributes:
            application_id(string) : a fedlearner job was created with
                an application id.
            data_path(string): master distribute data from data_path 
                to federate trainer. 
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
            template_name(string): template name default 'tensorflow',
    '''
    def __init__(self,
                 application_id,
                 data_path,
                 image,
                 role,
                 replicas,
                 pair=False,
                 command=['/app/deploy/scripts/trainer/run_trainer_master.sh'],
                 args=[''],
                 env=None,
                 resources=None,
                 ports=None,
                 restart_policy='Never',
                 image_pull_policy='IfNotPresent',
                 template_name='tensorflow'):
        super(MasterResourceConfig,
              self).__init__('Master', image, command, pair, replicas, args,
                             env, resources, ports, restart_policy,
                             image_pull_policy, template_name)
        self.init_config(application_id, role, data_path)

    def init_config(self, application_id, role, hdfs_path):
        self._resources = DEFAULT_RESOURCE

        self.set_env(name='APPLICATION_ID', value=application_id)
        self.set_env(name='ROLE', value=role)
        self.set_env(name='DATA_PATH', value=hdfs_path)
        self.set_env(name='POD_IP', value='status.podIP', value_from=True)
        self.set_port(port_name='flapp-port', port=50051)


class WorkerResourceConfig(CustomResourceDefinition):
    '''
        Inherit CustomeResourceDefinition base class to describe
        master resource definition on kubernetes.

        Attributes:
            application_id(string) : a fedlearner job was created with
                an application id.
            checkpoint_path(string): worker dump checkpoint path. 
            export_path(string): export model dump to this path for 
                serving distribution.
            release_pkg(string): release model code package name.
            release_tag(string): release model code package tag version.
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
            template_name(string): template name default 'tensorflow',
    '''
    def __init__(self,
                 application_id,
                 checkpoint_path,
                 export_path,
                 release_pkg,
                 release_tag,
                 image,
                 role,
                 replicas,
                 pair=False,
                 command=['/app/deploy/scripts/wait4pair_wrapper.sh'],
                 args=['/app/deploy/scripts/trainer/run_trainer_worker.sh'],
                 env=None,
                 resources=None,
                 ports=None,
                 restart_policy='Never',
                 image_pull_policy='IfNotPresent',
                 template_name='tensorflow'):
        super(WorkerResourceConfig,
              self).__init__('Worker', image, command, pair, replicas, args,
                             env, resources, ports, restart_policy,
                             image_pull_policy, template_name)
        self.init_config(application_id, role, checkpoint_path, export_path,
                         release_pkg, release_tag)

    def init_config(self, application_id, role, checkpoint_path, export_path,
                    release_pkg, release_tag):
        self._resources = DEFAULT_RESOURCE

        self.set_env(name='APPLICATION_ID', value=application_id)
        self.set_env(name='ROLE', value=role)
        self.set_env(name='CHECKPOINT_DIR', value=checkpoint_path)
        self.set_env(name='EXPORT_PATH', value=export_path)
        self.set_env(name='POD_IP', value='status.podIP', value_from=True)
        self.set_env(name='RELEASE_PKG', value=release_pkg)
        self.set_env(name='RELEASE_TAG', value=release_tag)
        self.set_port(port_name='flapp-port', port=50051)
        self.set_port(port_name='tf-port', port=50052)
