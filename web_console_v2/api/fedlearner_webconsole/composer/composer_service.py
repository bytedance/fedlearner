# Copyright 2023 The FedLearner Authors. All Rights Reserved.
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

# pylint: disable=global-statement
# coding: utf-8

import logging
from typing import List, Optional, Tuple
from sqlalchemy.sql.schema import Column
from sqlalchemy.sql import func
from sqlalchemy.orm import Session
from croniter import croniter
from fedlearner_webconsole.composer.models import ItemStatus, RunnerStatus
from fedlearner_webconsole.composer.interface import ItemType
from fedlearner_webconsole.composer.models import SchedulerItem, SchedulerRunner
from fedlearner_webconsole.proto import composer_pb2
from fedlearner_webconsole.proto.composer_pb2 import RunnerInput
from fedlearner_webconsole.utils.metrics import emit_store
from fedlearner_webconsole.exceptions import InvalidArgumentException
from fedlearner_webconsole.utils.filtering import SupportedField, FieldType, FilterBuilder
from fedlearner_webconsole.proto.filtering_pb2 import FilterOp, FilterExpression, SimpleExpression
from fedlearner_webconsole.utils.paginate import Pagination, paginate


def _contains_case_insensitive(exp: SimpleExpression):
    c: Column = getattr(SchedulerItem, exp.field)
    return c.ilike(f'%{exp.string_value}%')


def _is_cron(exp: SimpleExpression):
    c: Column = SchedulerItem.cron_config
    if exp.bool_value:
        exp.string_value = '*'
        return c.ilike(f'%{exp.string_value}%')
    return c


def _equal_item_status(exp: SimpleExpression):
    c: Column = SchedulerItem.status
    return c == ItemStatus[exp.string_value].value


def _equal_runner_status(exp: SimpleExpression):
    c: Column = SchedulerRunner.status
    return c == RunnerStatus[exp.string_value].value


class ComposerService(object):
    # attributes that you can patch
    MUTABLE_ITEM_KEY = ['cron_config', 'retry_cnt']

    def __init__(self, session: Session):
        self._session = session

    def get_item_status(self, name: str) -> Optional[ItemStatus]:
        """Get item status

        Args:
            name (str): item name

        Returns:
            ItemStatus: item status
        """
        existed = self._session.query(SchedulerItem).filter(SchedulerItem.name == name).first()
        if not existed:
            return None
        return ItemStatus(existed.status)

    def patch_item_attr(self, name: str, key: str, value: str):
        """ patch item args

        Args:
            name (str): name of this item
            key (str): key you want to update
            value (str): value you want to set

        Raises:
            ValueError: if some check violates
            Exception: if session failed
        """
        if key not in self.__class__.MUTABLE_ITEM_KEY:
            raise ValueError(f'fail to change attribute {key}')

        # TODO(linfan.fine): add validations
        item: SchedulerItem = self._session.query(SchedulerItem).filter(SchedulerItem.name == name).first()
        if not item:
            raise ValueError(f'cannot find item {name}')
        setattr(item, key, value)
        self._session.add(item)
        try:
            self._session.flush()
        except Exception as e:  # pylint: disable=broad-except
            logging.error(f'[composer] failed to patch item attr, ' f'name: {name}, exception: {e}')
            raise e

    def collect_v2(self, name: str, items: List[Tuple[ItemType, RunnerInput]], cron_config: Optional[str] = None):
        """Collect scheduler item.

        Args:
             name (str): item name, should be unique
             items (List[Tuple[IItem, RunnerInput]): specify the execution pipeline (in order)
             cron_config (Optional[str]): a cron expression for running item periodically

        Raises:
            ValueError: if `cron_config` is invalid
            Exception: if db session failed
        """
        if len(name) == 0:
            return
        if cron_config and not croniter.is_valid(cron_config):
            raise ValueError('invalid cron_config')
        # check name if exists
        existed = self._session.query(SchedulerItem.id).filter_by(name=name).first()
        if existed:
            logging.warning('SchedulerItem %s already existed', name)
            return
        scheduler_item = SchedulerItem(name=name, cron_config=cron_config, created_at=func.now())
        queue = []
        for item_type, rinput in items:
            runner_input = RunnerInput(runner_type=item_type.value)
            runner_input.MergeFrom(rinput)
            queue.append(runner_input)
        pipeline = composer_pb2.Pipeline(version=2, name=name, queue=queue)
        scheduler_item.set_pipeline(pipeline)
        self._session.add(scheduler_item)
        try:
            self._session.flush()
        except Exception as e:  # pylint: disable=broad-except
            logging.error(f'[composer] failed to create scheduler_item, name: {name}, exception: {e}')
            raise e

    def start(self, name: str):
        """Enable an OFF scheduler item"""
        existed = self._session.query(SchedulerItem).filter_by(name=name).first()
        existed.status = ItemStatus.ON.value

    def finish(self, name: str):
        """Finish item

        Args:
            name (str): item name

        Raises:
            Exception: if db session failed
        """
        existed = self._session.query(SchedulerItem).filter_by(name=name, status=ItemStatus.ON.value).first()
        if not existed:
            return
        existed.status = ItemStatus.OFF.value
        self._session.query(SchedulerRunner).filter(
            SchedulerRunner.item_id == existed.id,
            SchedulerRunner.status.in_([RunnerStatus.INIT.value, RunnerStatus.RUNNING.value])).delete()
        try:
            self._session.flush()
        except Exception as e:  # pylint: disable=broad-except
            logging.error(f'[composer] failed to finish scheduler_item, ' f'name: {name}, exception: {e}')
            raise e

    def get_recent_runners(self, name: str, count: int = 10) -> List[SchedulerRunner]:
        """Get recent runners order by created_at in desc

        Args:
            name (str): item name
            count (int): the number of runners

        Returns:
            List[SchedulerRunner]: list of SchedulerRunner
        """
        runners = self._session.query(SchedulerRunner).join(
            SchedulerItem, SchedulerItem.id == SchedulerRunner.item_id).filter(SchedulerItem.name == name).order_by(
                SchedulerRunner.created_at.desc()).limit(count).all()
        if not runners:
            return []
        return runners


class CronJobService:

    def __init__(self, session: Session):
        self._session = session

    def start_cronjob(self, item_name: str, items: List[Tuple[ItemType, RunnerInput]], cron_config: str):
        """Starts a cronjob if cron_config is valid.

        Args:
            item_name (str): name of scheduler item
            items: list of scheduler items with inputs
            cron_config (str): cron expression;

        Raises:
            Raise if some check violates
            InvalidArgumentException: if some check violates
        """
        if not croniter.is_valid(cron_config):
            raise InvalidArgumentException(f'cron config {cron_config} is not valid')
        service = ComposerService(self._session)
        status = service.get_item_status(name=item_name)
        # create a cronjob
        if status is None:
            service.collect_v2(name=item_name, items=items, cron_config=cron_config)
            return
        if status == ItemStatus.OFF:
            logging.info(f'[start_cronjob] start composer item {item_name}')
            service.start(name=item_name)
        # patch a cronjob
        try:
            service.patch_item_attr(name=item_name, key='cron_config', value=cron_config)
        except ValueError as err:
            emit_store('path_item_attr_error', 1)
            raise InvalidArgumentException(details=repr(err)) from err

    def stop_cronjob(self, item_name: str):
        service = ComposerService(self._session)
        logging.info(f'[start_or_stop_cronjob] finish composer item {item_name}')
        service.finish(name=item_name)


class SchedulerItemService():
    """ 'is_cron' param means whether should only display cron-jobs. """
    FILTER_FIELDS = {
        'is_cron': SupportedField(type=FieldType.BOOL, ops={FilterOp.EQUAL: _is_cron}),
        'status': SupportedField(type=FieldType.STRING, ops={FilterOp.EQUAL: _equal_item_status}),
        'name': SupportedField(type=FieldType.STRING, ops={FilterOp.CONTAIN: _contains_case_insensitive}),
        'id': SupportedField(type=FieldType.NUMBER, ops={FilterOp.EQUAL: None})
    }

    def __init__(self, session: Session):
        self._session = session
        self._filter_builder = FilterBuilder(model_class=SchedulerItem, supported_fields=self.FILTER_FIELDS)

    def get_scheduler_items(self,
                            page: Optional[int] = None,
                            page_size: Optional[int] = None,
                            filter_exp: Optional[FilterExpression] = None) -> Pagination:
        query = self._session.query(SchedulerItem)
        if filter_exp:
            query = self._filter_builder.build_query(query, filter_exp)
        query = query.order_by(SchedulerItem.id.desc())
        return paginate(query, page, page_size)


class SchedulerRunnerService():
    FILTER_FIELDS = {
        'status': SupportedField(type=FieldType.STRING, ops={FilterOp.EQUAL: _equal_runner_status}),
    }

    def __init__(self, session: Session):
        self._session = session
        self._filter_builder = FilterBuilder(model_class=SchedulerRunner, supported_fields=self.FILTER_FIELDS)

    def get_scheduler_runners(self,
                              item_id: Optional[int] = None,
                              page: Optional[int] = None,
                              page_size: Optional[int] = None,
                              filter_exp: Optional[FilterExpression] = None) -> Pagination:
        # runner_status used as index to optimize sql query
        # id.desc better than created_at.desc for index can be used
        query = self._session.query(SchedulerRunner).order_by(
            SchedulerRunner.id.desc()).filter(SchedulerRunner.status > -1)
        if filter_exp:
            query = self._filter_builder.build_query(query, filter_exp)
        if item_id is not None:
            query = query.filter_by(item_id=item_id)

        return paginate(query, page, page_size)
