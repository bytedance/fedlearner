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

import json
import datetime
import click
from fedlearner.scheduler.db.db_model import Job, \
            ModelMeta, ModelVersion, DataSourceMeta, \
            JOBSTATUS


@click.group()
def create():
    '''
      create job / model / data for FedLearner.
    '''
    pass  # pylint: disable=W0107


@create.command('job', help='Create a job run for fedlearner')
@click.option('-c', '--config', required=True, type=click.File('r'))
def create_job_run(config):
    '''
    FedLearner create a job run.
    '''
    create_job = json.loads(config.read())
    try:
        model_meta = ModelMeta.get(ModelMeta.name == create_job['model_uri'])
    except Exception:  #pylint: disable=W0703
        click.echo('Model [%s] was not authorized, job cant be created.' %
                   create_job['name'])
        return

    try:
        model_version = ModelVersion.get(
            (ModelVersion.commit == create_job['model_commit'])
            and (ModelVersion.model_meta_id == model_meta.id))
    except Exception:  #pylint: disable=W0703
        click.echo(
            'ModelVersion [%s] was not authorized, job cant be created.' %
            create_job['model_commit'])
        return

    try:
        data_source = DataSourceMeta.get(
            DataSourceMeta.name == create_job['data_source'])
    except Exception:  #pylint: disable=W0703
        click.echo('DataSource [%s] was not authorized, job cant be created.' %
                   create_job['data_source'])
        return

    job = Job.create(name=create_job['name'],
                     description=create_job.get('description', ''),
                     role='Leader',
                     namespace=create_job.get('namespace', 'leader'),
                     model_version_id=model_version.id,
                     distributed_version=create_job['distributed_version'],
                     data_source_id=data_source.id,
                     cluster_spec=json.dumps(create_job.get(
                         'cluster_spec', {})),
                     status=JOBSTATUS.SUBMMITTED,
                     group_list=json.dumps(create_job.get('group_list', [])),
                     create_time=datetime.datetime.now())
    click.echo("job [%s] model: %s data_source %s create success." %
               (job.name, model_meta.name, data_source.name))


@create.command('model', help='Create a model meta for fedlearner')
@click.option('-c', '--config', required=True, type=click.File('r'))
def create_model_meta(config):
    '''
      FedLearner create / authorize model meta.
    '''
    create_model = json.loads(config.read())
    model_meta = ModelMeta.select().where(
        ModelMeta.name == create_model['name'])
    if not model_meta:
        model_meta = ModelMeta.create(name=create_model['name'],
                                      image=create_model['image'],
                                      code_url=create_model['code_url'],
                                      create_time=datetime.datetime.now())
    else:
        model_meta = model_meta[0]

    model_version = ModelVersion.select().where(
        (ModelVersion.commit == create_model['commit'])
        and (ModelVersion.model_meta_id == model_meta.id))
    if model_version:
        model_version = model_version[0]
        click.echo("model_version [%s] commit: %s already exist." %
                   (model_meta.name, model_version.commit))
    else:
        model_version = ModelVersion.create(model_meta_id=model_meta.id,
                                            commit=create_model['commit'],
                                            description=create_model.get(
                                                'description', ''))
        click.echo("model_version [%s] commit: %s create success." %
                   (model_meta.name, model_version.commit))


@create.command('data_source', help='Create data source for fedlearner')
@click.option('-c', '--config', required=True, type=click.File('r'))
def create_data_source(config):
    '''
    FedLearner create / authorize datasource meta.
    '''
    create_data = json.loads(config.read())
    data_source = DataSourceMeta.select().where(
        DataSourceMeta.name == create_data['name'])
    if data_source:
        click.echo("data source [%s] path: %s already exist." %
                   (data_source[0].name, data_source[0].path))
    else:
        DataSourceMeta.create(name=create_data['name'],
                              description=create_data.get('description', ''),
                              path=create_data['path'])
