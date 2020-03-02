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
# pylint: disable=W0622

import click
from prettytable import PrettyTable
from fedlearner.scheduler.db.db_model import Job, \
            ModelMeta, ModelVersion, DataSourceMeta


@click.group()
def list():
    '''
      list job / model / data in FedLearner
    '''
    pass  #pylint: disable=W0107


@list.command('job', help='Get running job in fedlearner')
@click.option('-i', '--id', type=int)
def get_job_list(id):
    '''
       Get all fedLearner job list.
    '''
    if id:
        job_list = Job.select(Job, ModelMeta, ModelVersion, DataSourceMeta).\
                   join(ModelVersion).join(ModelMeta).\
                   join(DataSourceMeta,
                        on=(Job.data_source_id == DataSourceMeta.id)).\
                    where(Job.id == id)
        for item in job_list:
            click.echo('FedLearner Job [%d] Detail:' % id)
            click.echo('\tname: %s' % item.name)
            click.echo('\trole: %s' % item.role)
            click.echo('\tapplication_id: %s' % item.application_id)
            click.echo('\tmodel_uri: %s' %
                       item.model_version_id.model_meta_id.name)
            click.echo('\tmodel_commit: %s' % item.model_version_id.commit)
            click.echo('\tdata_source: %s' % item.data_source_id.name)
            click.echo('\tdata_path: %s' % item.data_source_id.path)
            click.echo('\tcluster_spec: %s' % item.cluster_spec)
            click.echo('\tstatus: %s' % item.status)
            click.echo('\tk8s_status: %s' % item.k8s_status)
            click.echo('\tgroup_list: %s' % item.group_list)
            click.echo('\tcreate_time: %s' %
                       item.create_time.strftime('%Y-%m-%d %H:%M:%S'))
            click.echo('\tupdate_time: %s' %
                       item.update_time.strftime('%Y-%m-%d %H:%M:%S'))
            if item.start_time:
                click.echo('\tstart_time: %s' %
                           item.start_time.strftime('%Y-%m-%d %H:%M:%S'))
            if item.end_time:
                click.echo('\tend_time: %s' %
                           item.end_time.strftime('%Y-%m-%d %H:%M:%S'))
    else:
        job_list = Job.select(Job, ModelMeta, ModelVersion, DataSourceMeta).\
                   join(ModelVersion).join(ModelMeta).\
                   join(DataSourceMeta,
                        on=(Job.data_source_id == DataSourceMeta.id))

        table = PrettyTable([
            'id', 'name', 'role', 'application_id', 'model_uri', 'data_source',
            'status', 'group_list', 'create_time'
        ])
        for item in job_list:
            table.add_row([
                item.id, item.name, item.role, item.application_id,
                item.model_version_id.model_meta_id.name,
                item.data_source_id.name, item.status, item.group_list,
                item.create_time.strftime('%Y-%m-%d %H:%M:%S')
            ])
        click.echo(table)


@list.command('model', help='Get model meta list in fedlearner')
def get_model_list():
    '''
        Get all fedLearner model list.
    '''
    model_list = ModelVersion.select(ModelMeta, ModelVersion).join(ModelMeta)
    table = PrettyTable([
        'id', 'name', 'description', 'image', 'code_url', 'commit',
        'create_time'
    ])
    for item in model_list:
        table.add_row([
            item.id, item.model_meta_id.name, item.description,
            item.model_meta_id.image, item.model_meta_id.code_url, item.commit,
            item.create_time.strftime('%Y-%m-%d %H:%M:%S')
        ])
    click.echo(table)


@list.command('data_source', help='Get data source list in fedlearner')
def get_data_list():
    '''
        Get all fedLearner data source list.
    '''
    data_list = DataSourceMeta.select()
    table = PrettyTable(['id', 'name', 'description', 'path', 'create_time'])
    for item in data_list:
        table.add_row([
            item.id, item.name, item.description, item.path,
            item.create_time.strftime('%Y-%m-%d %H:%M:%S')
        ])
    click.echo(table)
