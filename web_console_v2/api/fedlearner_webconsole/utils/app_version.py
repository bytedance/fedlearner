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

import re
from typing import Optional

from fedlearner_webconsole.proto import common_pb2

_VERSION_RE = re.compile(r'^(\d+).(\d+).(\d+)')


class Version(object):

    def __init__(self, version: Optional[str] = None):
        self._version = version
        self._major = None
        self._minor = None
        self._patch = None
        if version is not None:
            self._parse_version(version)

    def _parse_version(self, version: str):
        matches = _VERSION_RE.match(version)
        if matches:
            self._major = int(matches.group(1))
            self._minor = int(matches.group(2))
            self._patch = int(matches.group(3))

    @property
    def version(self):
        return self._version

    @property
    def major(self):
        return self._major

    @property
    def minor(self):
        return self._minor

    @property
    def patch(self):
        return self._patch

    def is_standard(self):
        return self.major is not None and self.minor is not None and self.patch is not None

    def __eq__(self, other):
        assert isinstance(other, Version)
        if self.is_standard():
            return self.major == other.major and self.minor == other.minor and self.patch == other.patch
        return self.version == other.version

    def __ne__(self, other):
        assert isinstance(other, Version)
        return not self.__eq__(other)

    def __gt__(self, other):
        assert isinstance(other, Version)
        if not self.is_standard() or not other.is_standard():
            # Not compatible
            return False
        if self.major > other.major:
            return True
        if self.major < other.major:
            return False
        if self.minor > other.minor:
            return True
        if self.minor < other.minor:
            return False
        return self.patch > other.patch

    def __lt__(self, other):
        assert isinstance(other, Version)
        if not self.is_standard() or not other.is_standard():
            # Not compatible
            return False
        return not self.__ge__(other)

    def __ge__(self, other):
        assert isinstance(other, Version)
        return self.__gt__(other) or self.__eq__(other)

    def __le__(self, other):
        assert isinstance(other, Version)
        return self.__lt__(other) or self.__eq__(other)


class ApplicationVersion(object):
    """Version of the application.

    Attributes:
        revision: Commit id of the head
        branch_name: Branch name of the image
        pub_date: Date when image is built in ISO format
        version: Semantic version
    """

    def __init__(self, revision: str, branch_name: str, pub_date: str, version: Optional[str] = None):
        self.revision = revision
        self.branch_name = branch_name
        self.pub_date = pub_date
        self.version = Version(version)

    def to_proto(self) -> common_pb2.ApplicationVersion:
        return common_pb2.ApplicationVersion(pub_date=self.pub_date,
                                             revision=self.revision,
                                             branch_name=self.branch_name,
                                             version=self.version.version)
