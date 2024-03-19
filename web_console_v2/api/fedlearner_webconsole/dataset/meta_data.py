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

import os
import logging
import dateutil.parser
from typing import List, Optional, Dict, Any


class MetaData(object):
    _DTYPES = 'dtypes'
    _SAMPLE = 'sample'
    _FEATURES = 'features'
    _HIST = 'hist'
    _COUNT = 'count'

    def __init__(self, metadata: Optional[dict] = None):
        self.metadata = metadata or {}

    @property
    def dtypes(self) -> List[Any]:
        return self.metadata.get(self._DTYPES, [])

    @property
    def sample(self) -> List[Any]:
        return self.metadata.get(self._SAMPLE, [])

    @property
    def metrics(self) -> Dict[str, Dict[Any, Any]]:
        return self.metadata.get(self._FEATURES, {})

    @property
    def hist(self) -> Dict[str, Dict[Any, Any]]:
        return self.metadata.get(self._HIST, {})

    @property
    def num_feature(self) -> int:
        return len(self.dtypes)

    @property
    def num_example(self) -> int:
        return self.metadata.get(self._COUNT, 0)

    def get_metrics_by_name(self, name: str) -> Dict[Any, Any]:
        return self.metrics.get(name, {})

    def get_hist_by_name(self, name: str) -> Dict[Any, Any]:
        return self.hist.get(name, {})

    def get_preview(self) -> dict:
        """ get the preview data
        Returns:
            preview dict format:
        {
            'dtypes': [
                {'key': 'f01', 'value': 'bigint'}
            ],
            'sample': [
                [1],
                [0],
            ],
            'count': 1000
            'metrics': {
                'f01': {
                'count': '2',
                'mean': '0.0015716767309123998',
                'stddev': '0.03961485047808605',
                'min': '0',
                'max': '1',
                'missing_count': '0'
                }
            },
            'hist': {
                'x': [0.0, 0.1, 0.2, 0.30000000000000004, 0.4, 0.5,
                        0.6000000000000001, 0.7000000000000001, 0.8, 0.9, 1],
                'y': [12070, 0, 0, 0, 0, 0, 0, 0, 0, 19]
            }
        }
        """
        preview = {}
        preview['dtypes'] = self.dtypes
        preview['sample'] = self.sample
        preview['num_example'] = self.num_example
        preview['metrics'] = self.metrics
        return preview


class ImageMetaData(MetaData):
    _LABEL_COUNT = 'label_count'
    _THUMBNAIL_EXTENSION = '.png'

    def __init__(self, thumbnail_dir_path: str, metadata: Optional[dict] = None):
        super().__init__(metadata=metadata)
        self.thumbnail_dir_path = thumbnail_dir_path

    @property
    def label_count(self) -> List[Any]:
        return self.metadata.get(self._LABEL_COUNT, [])

    def _get_column_idx(self, col_name: str):
        col_idx = -1
        for index, col_map in enumerate(self.dtypes):
            if col_map['key'] == col_name:
                col_idx = index
                break
        if col_idx < 0:
            logging.warning(f'can\'t found the {col_name} column in dtypes:{self.dtypes}')
        return col_idx

    def _get_thumbnail_file_name(self, file_name: str) -> str:
        thumbnail_file_name = file_name.split('.')[0] + self._THUMBNAIL_EXTENSION
        return thumbnail_file_name

    def get_preview(self) -> dict:
        """ get the preview data
        Returns:
            preview dict format:
        {
            "dtypes": [
                { "key": "file_name", "value": "string" },
                { "key": "width", "value": "int" },
                { "key": "height", "value": "int" },
                { "key": "nChannels", "value": "int" },
                { "key": "mode", "value": "int" },
                { "key": "name", "value": "string" },
                { "key": "created_at", "value": "string" },
                { "key": "caption", "value": "string" },
                { "key": "label", "value": "string" }
            ],
            "label_count": [
                {
                    "label": "B",
                    "count": 1
                },
            ],
            "count": 50,
            "sample": [
                [
                    "000000050576.jpg",
                    640,
                    480,
                    3,
                    16,
                    "000000050576.jpg",
                    "2021-08-30T16:52:15.501516",
                    "A tow truck loading a bank security truck by a building.",
                    "B"
                ],
                ...
            ],
            "features": {
                "file_name": {
                    "count": "50",
                    "mean": null,
                    "stddev": null,
                    "min": "000000005756.jpg",
                    "max": "000000562222.jpg",
                    "missing_count": "0"
                },
                ...
            },
            "hist": {
                "width": {
                    "x": [ 333.0, 363.7, 394.4, 425.1, 455.8, 486.5, 517.2, 547.9, 578.6, 609.3, 640.0 ],
                    "y": [ 1, 1, 4, 3, 4, 0, 0, 0, 36 ]
                },
                ...
            }
        }
        """
        preview = super().get_preview()
        display_name_idx = self._get_column_idx('name')
        file_name_idx = self._get_column_idx('file_name')
        height_idx = self._get_column_idx('height')
        width_idx = self._get_column_idx('width')
        created_at_idx = self._get_column_idx('created_at')
        label_idx = self._get_column_idx('label')
        images = []
        for sample in self.sample:
            sample[created_at_idx] = dateutil.parser.isoparse(sample[created_at_idx]).strftime('%Y-%m-%d')
            image = {
                'name': sample[display_name_idx],
                'file_name': sample[file_name_idx],
                'width': sample[width_idx],
                'height': sample[height_idx],
                'created_at': sample[created_at_idx],
                # TODO(wangzeju): hard code for the classification task, need to support more image follow up tasks.
                'annotation': {
                    'label': sample[label_idx]
                },
                'path': os.path.join(self.thumbnail_dir_path, self._get_thumbnail_file_name(sample[file_name_idx]))
            }
            images.append(image)
        preview['images'] = images
        return preview
