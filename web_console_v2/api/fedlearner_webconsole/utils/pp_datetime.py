# Copyright 2023 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# coding: utf-8
from typing import Optional, Union
from datetime import datetime, timezone
from dateutil.parser import isoparse


def to_timestamp(dt: Union[datetime, str]) -> int:
    """Converts DB datetime to timestamp in second."""
    # If there is no timezone, we should treat it as UTC datetime,
    # otherwise it will be calculated as local time when converting
    # to timestamp.
    # Context: all datetime in db is UTC datetime,
    # see details in config.py#turn_db_timezone_to_utc
    if isinstance(dt, str):
        dt = isoparse(dt)
    if dt.tzinfo is None:
        return int(dt.replace(tzinfo=timezone.utc).timestamp())
    return int(dt.timestamp())


def from_timestamp(timestamp: int) -> datetime:
    """Converts timestamp to datetime with utc timezone."""
    return datetime.fromtimestamp(timestamp, timezone.utc)


def now(tz: Optional[timezone] = timezone.utc) -> datetime:
    """A wrapper of datetime.now.

    This is for easy testing, as datetime.now is referred by a lot
    of components, mock that will break tests easily. Using this wrapper
    so that developers can mock this function to get a fake datetime."""
    return datetime.now(tz)
