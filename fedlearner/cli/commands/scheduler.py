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
# pylint: disable=W0621

import logging
import daemon
import click
from daemon.pidfile import TimeoutPIDLockFile

from fedlearner import settings
from fedlearner.scheduler.db import db_model
from fedlearner.scheduler.scheduler import Scheduler
from fedlearner.cli.utils import init_logging


@click.group()
def scheduler():
    '''
       do action for scheduler in FedLearner.
    '''
    pass  #pylint: disable=W0107


@scheduler.command('init', help='initialize scheduler environment & database')
@click.option('-c', '--config', required=False, type=click.File('r'))
def scheduler_initialize(config):
    '''
        FedLearner scheduler initialize environment parameter and database init.
    '''
    db_model.init_database_tables()


@scheduler.command('start', help='start fedlearner scheduler service')
@click.option('-p', '--port', type=int, default=50001)
@click.option('-d', '--daemon_mode', type=bool, default=False)
def scheduler_start(port, daemon_mode):
    '''
        FedLearner scheduler service start.
    '''
    click.echo(click.style(settings.HEADER, fg='bright_blue'))
    scheduler = Scheduler()
    if daemon_mode:
        handle = init_logging(settings.LOG_PATH)
        stdout = open(settings.STDOUT_PATH, 'w+')
        stderr = open(settings.STDERR_PATH, 'w+')

        ctx = daemon.DaemonContext(
            pidfile=TimeoutPIDLockFile(settings.PID_FILE, -1),
            files_preserve=[handle],
            stdout=stdout,
            stderr=stderr,
        )
        with ctx:
            scheduler.run(listen_port=port)

        stdout.close()
        stderr.close()
    else:
        logging.getLogger().setLevel(logging.DEBUG)
        scheduler.run(listen_port=port)
