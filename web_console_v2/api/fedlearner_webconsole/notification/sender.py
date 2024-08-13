# Copyright 2023 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import abc
import logging

from fedlearner_webconsole.proto.notification_pb2 import Notification


class Sender(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def send(self, notification: Notification):
        """Sends notification by third-party services."""


senders = {}


def register_sender(name: str, sender: Sender):
    senders[name] = sender


def send(notification: Notification):
    """Sends a notification.

    Invoking senders directly while there is no performance concerns as of now.
    In the future, it should be sent to a queue, and we can use consumer-producers pattern
    to send those notifications asynchronously."""
    if not senders:
        logging.info('[Notification] no sender for %s', notification.subject)
        return
    for name, sender in senders.items():
        try:
            sender.send(notification)
            logging.info('[Notification] %s sent by %s', notification.subject, name)
        except Exception:  # pylint: disable=broad-except
            logging.exception('[Notification] sender %s failed to send %s', name, notification.subject)
