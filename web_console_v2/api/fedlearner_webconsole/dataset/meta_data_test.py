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

import unittest
import json
from envs import Envs
from fedlearner_webconsole.dataset.meta_data import ImageMetaData


class ImageMetaDataTest(unittest.TestCase):

    def setUp(self):
        super().setUp()
        self.maxDiff = None
        with open(f'{Envs.BASE_DIR}/testing/test_data/image_meta.json', mode='r', encoding='utf-8') as f:
            self.image_data = json.load(f)
        with open(f'{Envs.BASE_DIR}/testing/test_data/expected_image_preview.json', mode='r', encoding='utf-8') as f:
            self.expected_image_preview = json.load(f)
        self.thumbnail_dir_path = '/fake_dir/'

    def test_image_preview(self):
        image_meta = ImageMetaData(self.thumbnail_dir_path, self.image_data)
        image_preview = image_meta.get_preview()
        self.assertDictEqual(self.expected_image_preview, image_preview)

    def test_empty_meta(self):
        image_meta = ImageMetaData(self.thumbnail_dir_path, None)
        image_preview = image_meta.get_preview()
        expected_response = {'dtypes': [], 'sample': [], 'num_example': 0, 'metrics': {}, 'images': []}
        self.assertDictEqual(expected_response, image_preview)


if __name__ == '__main__':
    unittest.main()
