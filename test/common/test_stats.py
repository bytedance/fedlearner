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
# limitations under the License

import os
import unittest
import time

from fedlearner.common import stats

class TestTags(unittest.TestCase):
    def test_tags(self):
        tags = stats.Tags({
            "tag1": "val1",
            "tag2": "val2",
            "tag3": "val3"})
        assert str(tags) == "tag1=val1,tag2=val2,tag3=val3"

def _test_timer(client, tags):
    client.timing("test_timing_stat", 100, tags=tags)
    client.timing("test_timing_stat", 101, tags=tags)
    client.timing("test_timing_stat", 102, tags=tags)

    timer = client.timer("test_timer_stat", tags=tags)

    timer.start()
    time.sleep(0.1)
    timer.stop()

    timer.start()
    time.sleep(0.2)
    timer.stop()

    @client.timer("test_timer_decorator_stat", tags=tags)
    def process():
        time.sleep(0.1)

    process()
    process()
    process()

def _test_incr_decr(client, tags):
    client.incr("test_incr_stat", tags=tags)
    client.incr("test_incr_stat", 2, tags=tags)
    client.incr("test_incr_stat", 3, tags=tags)
    client.decr("test_incr_stat", tags=tags)
    client.decr("test_incr_stat", 3, tags=tags)

def _test_gauge(client, tags):
    client.gauge("test_gauge_stat", 100, tags=tags)
    client.gauge("test_gauge_stat", 101, tags=tags)
    client.gauge("test_gauge_stat", 102, tags=tags)

def _test_set(client, tags):
    client.sets("test_set_stat", 1, tags=tags)
    client.sets("test_set_stat", 2, tags=tags)
    client.sets("test_set_stat", 3, tags=tags)
    client.sets("test_set_stat", 1, tags=tags)

def _test_pipline(client, tags):
    def pipe_case(pipe, stat_prefix, tags):
        pipe.timing(stat_prefix+"timing_stat", 1, tags=tags)
        timer = pipe.timer(stat_prefix+"timer_stat", tags=tags)
        timer.start()
        time.sleep(0.1)
        timer.stop()
        @pipe.timer(stat_prefix+"timer_decorator_stat", tags=tags)
        def process():
            time.sleep(0.1)
        process()

        pipe.incr(stat_prefix+"incr_stat", 2, tags=tags)
        pipe.decr(stat_prefix+"decr_stat", 3, tags=tags)
        pipe.gauge(stat_prefix+"gauge_stat", 4, tags=tags)
        pipe.sets(stat_prefix+"incr_stat", 5, tags=tags)

    pipe = client.pipeline()
    pipe_case(pipe, "test_pipe_", tags)
    pipe.send()

    with client.pipeline() as pipe:
        pipe_case(pipe, "test_with_pipe_", tags)
        with pipe.pipeline() as pipe2:
            pipe_case(pipe2, "test_with_pipe2_", tags)
            with pipe2.pipeline() as pipe3:
                pipe_case(pipe3, "test_with_pipe3_", tags)
        pipe_case(pipe, "test_with_pipe_end_", tags)


class TestUDPClient(unittest.TestCase):
    def setUp(self):
        self._url = "udp://localhost:8125"
        self._client = stats.Client(self._url)
        self._tags = stats.Tags({"client": "udp"})

    def test_timer(self):
        _test_timer(self._client, self._tags)

    def test_incr_decr(self):
        _test_incr_decr(self._client, self._tags)

    def test_gauge(self):
        _test_gauge(self._client, self._tags)

    def test_set(self):
        _test_set(self._client, self._tags)

    def test_pipeline(self):
        _test_pipline(self._client, self._tags)

    def tearDown(self):
        self._client.close()


class TestFileClient(unittest.TestCase):
    def setUp(self):
        self._filename = "./stats.output"
        self._url = "file://" + self._filename
        self._client = stats.Client(self._url)
        self._tags = stats.Tags({"client": "file"})

    def test_timer(self):
        _test_timer(self._client, self._tags)

    def test_incr_decr(self):
        _test_incr_decr(self._client, self._tags)

    def test_gauge(self):
        _test_gauge(self._client, self._tags)

    def test_set(self):
        _test_set(self._client, self._tags)

    def test_pipeline(self):
        _test_pipline(self._client, self._tags)

    def tearDown(self):
        self._client.close()
        if os.path.exists(self._filename):
            os.remove(self._filename)


class TestStdoutClient(unittest.TestCase):
    def setUp(self):
        self._url = "stdout://"
        self._client = stats.Client(self._url)
        self._tags = stats.Tags({"client": "stdout"})

    def test_timer(self):
        _test_timer(self._client, self._tags)

    def test_incr_decr(self):
        _test_incr_decr(self._client, self._tags)

    def test_gauge(self):
        _test_gauge(self._client, self._tags)

    def test_set(self):
        _test_set(self._client, self._tags)

    def test_pipeline(self):
        _test_pipline(self._client, self._tags)

    def tearDown(self):
        self._client.close()


class TestStderrClient(unittest.TestCase):
    def setUp(self):
        self._url = "stderr://"
        self._client = stats.Client(self._url)
        self._tags = stats.Tags({"client": "stderr"})

    def test_timer(self):
        _test_timer(self._client, self._tags)

    def test_incr_decr(self):
        _test_incr_decr(self._client, self._tags)

    def test_gauge(self):
        _test_gauge(self._client, self._tags)

    def test_set(self):
        _test_set(self._client, self._tags)

    def test_pipeline(self):
        _test_pipline(self._client, self._tags)

    def tearDown(self):
        self._client.close()


class TestNoneClient(unittest.TestCase):
    def setUp(self):
        self._client = stats.NoneClient()
        self._tags = stats.Tags({"client": "stderr"})

    def test_timer(self):
        _test_timer(self._client, self._tags)

    def test_incr_decr(self):
        _test_incr_decr(self._client, self._tags)

    def test_gauge(self):
        _test_gauge(self._client, self._tags)

    def test_set(self):
        _test_set(self._client, self._tags)

    def test_pipeline(self):
        _test_pipline(self._client, self._tags)

    def tearDown(self):
        self._client.close()


class TestGlobalClient(unittest.TestCase):
    def setUp(self):
        os.environ["STATS_ENABLED"] = "1"
        os.environ["STATS_URL"] = "stderr://"
        self._tags = stats.Tags({"client": "env_stderr"})

    def test_timer(self):
        _test_timer(stats, self._tags)

    def test_incr_decr(self):
        _test_incr_decr(stats, self._tags)

    def test_gauge(self):
        _test_gauge(stats, self._tags)

    def test_set(self):
        _test_set(stats, self._tags)

    def test_pipeline(self):
        _test_pipline(stats, self._tags)

    def tearDown(self):
        pass

class TestWithTagsClient(unittest.TestCase):
    def setUp(self):
        self._url = "stdout://"
        self._client = stats.Client(self._url).with_tags(
            {"tag1": "value1"}
        )
        self._client = self._client.with_tags(
            {"tag2": "value2"}
        )
        self._tags = stats.Tags({"client": "with_tags_stdout"})

    def test_timer(self):
        _test_timer(self._client, self._tags)

    def test_incr_decr(self):
        _test_incr_decr(self._client, self._tags)

    def test_gauge(self):
        _test_gauge(self._client, self._tags)

    def test_set(self):
        _test_set(self._client, self._tags)

    def test_pipeline(self):
        _test_pipline(self._client, self._tags)

    def tearDown(self):
        self._client.close()

class TestCPUStats(unittest.TestCase):
    def setUp(self):
        self._url = "stdout://"
        self._client = stats.Client(self._url).with_tags(
            {"client": "cpu_stats"}
        )

    def test_enable_cpu_stats(self):
        stats.enable_cpu_stats(self._client, 0.5)
        time.sleep(2)

    def tearDown(self):
        self._client.close()

class TestMemStats(unittest.TestCase):
    def setUp(self):
        self._url = "stdout://"
        self._client = stats.Client(self._url).with_tags(
            {"client": "mem_stats"}
        )

    def test_enable_cpu_stats(self):
        stats.enable_mem_stats(self._client, 0.5)
        time.sleep(2)

    def tearDown(self):
        self._client.close()


if __name__ == '__main__':
    unittest.main()