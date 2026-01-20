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

# pylint: disable=redefined-outer-name
import argparse
import glob
import json
import os

import sys
from pathlib import Path


def _format_json(content: str) -> str:
    # set ensure_ascii to false to support chinese characters
    return json.dumps(json.loads(content), ensure_ascii=False, indent=4, sort_keys=True)


def format_json_file(file_path: str, check_only: bool = False) -> bool:
    """Formats or checks json file format.

    Returns:
        True if the file should be formatted
    """
    original = Path(file_path).read_text(encoding='utf-8')
    formatted = _format_json(original)
    should_format = original != formatted
    if should_format and not check_only:
        Path(file_path).write_text(formatted, encoding='utf-8')
    return should_format


def format_json_files(file_wildcard: str, check_only: bool = False) -> bool:
    if Path(file_wildcard).is_dir():
        all_files = []
        for root, dirs, files in os.walk(file_wildcard):
            for file in files:
                all_files.append(os.path.join(root, file))
    else:
        all_files = glob.glob(file_wildcard, recursive=True)

    any_formatted = False
    for f in all_files:
        formatted = format_json_file(f, check_only)
        if formatted:
            if check_only:
                print(f'JSON format is invalid: {f}')
            else:
                print(f'{f} is formatted')
        any_formatted = any_formatted or formatted
    return any_formatted


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Json formatter')
    parser.add_argument('-c', '--check_only', action='store_true', help='Whether to check json format only')
    parser.add_argument('files', type=str, nargs='+', help='list of json file wildcard')
    args = parser.parse_args()

    formatted = False
    for file_wildcard in args.files:
        formatted = formatted or format_json_files(file_wildcard, args.check_only)
    if formatted and args.check_only:
        sys.exit(1)
