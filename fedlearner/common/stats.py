# Copyright 2020 The FedLearner Authors. All Rights Reserved.

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

import os
import sys
import threading
import abc
import random
import socket
import time
try:
    from time import perf_counter as time_now
except ImportError:
    from time import time as time_now
from collections import deque
from datetime import timedelta
from distutils.util import strtobool
from urllib.parse import urlparse, parse_qs
from fedlearner.common import fl_logging

_client_lock = threading.Lock()
_client = None
_enabled = False

def _get_or_create_client():
    global _client #pylint: disable=global-statement
    if _client:
        return _client

    with _client_lock:
        if not _client:
            _client = _create_client()
        return _client


def _create_client():
    """ Enable stats from env """
    global _enabled #pylint: disable=global-statement

    enabled_str = os.getenv("FL_STATS_ENABLED")
    url = os.getenv("FL_STATS_URL")
    try:
        _enabled = strtobool(enabled_str) if enabled_str else bool(url)
    except ValueError:
        fl_logging.warning("[Stats] env FL_STATS_ENABLED=%s "
                           "is invalid truth value. Disable stats ",
                           enabled_str)
        _enabled = False

    if not _enabled:
        fl_logging.info("[Stats] stats not enabled")
        return NoneClient()

    if not url:
        fl_logging.warning("[Stats] FL_STATS_URL not found, redirect to stderr")
        url = "stderr://"

    try:
        return Client(url)
    except Exception as e: #pylint: disable=broad-except
        fl_logging.error("[Stats] new client error: %s, redirect to stderr", e)
        return Client("stderr://")


class Tags:
    def __init__(self, tags=None):
        self._str = Tags.to_str(tags)

    def __str__(self):
        return self._str

    @staticmethod
    def to_str(tags):
        if not tags:
            return ""
        if isinstance(tags, Tags):
            return str(tags)
        if isinstance(tags, dict):
            data = ""
            for k, v in tags.items():
                if not isinstance(k, str):
                    continue
                k = k.strip()
                if k:
                    data += ",%s=%s"%(k, str(v))
            return data[1:]

        raise TypeError("tags type not 'Tags' or 'dict'")

    @staticmethod
    def concat(tag1, tag2):
        s1 = Tags.to_str(tag1)
        s2 = Tags.to_str(tag2)
        delim = "," if s1 and s2 else ""
        tags = Tags()
        tags._str = s1 + delim + s2 #pylint: disable=protected-access
        return tags


class Timer(object):
    """A context manager/decorator for statsd.timing()."""
    def __init__(self, client, stat, tags=None, rate=1):
        self._client = client
        self._stat = stat
        self._tags = tags
        self._rate = rate
        self._ms = None
        self._sent = False
        self._start_time = None

    def __call__(self, f):
        """Thread-safe timing function decorator."""
        def _wrapped(*args, **kwargs):
            start_time = time_now()
            try:
                return f(*args, **kwargs)
            finally:
                dur = 1000.0 * (time_now() - start_time)
                self._client.timing(self._stat, dur, self._tags, self._rate)
        return _wrapped

    def __enter__(self):
        return self.start()

    def __exit__(self, typ, value, tb):
        self.stop()

    def start(self):
        self._ms = None
        self._sent = False
        self._start_time = time_now()
        return self

    def stop(self, send=True):
        if self._start_time is None:
            raise RuntimeError('Timer has not started.')
        dt = time_now() - self._start_time
        self._ms = 1000.0 * dt  # Convert to milliseconds.
        if send:
            self.send()
        return self

    def send(self):
        if self._ms is None:
            raise RuntimeError('No data recorded.')
        if self._sent:
            raise RuntimeError('Already sent data.')
        self._sent = True
        self._client.timing(self._stat, self._ms, self._tags, self._rate)


class _ClientBase():
    def __init__(self, prefix=None):
        self._prefix = prefix

    @abc.abstractmethod
    def _send(self, data):
        ...

    def timer(self, stat, tags=None, rate=1):
        return Timer(self, stat, tags, rate)

    def timing(self, stat, delta, tags=None, rate=1):
        if isinstance(delta, timedelta):
            # Convert timedelta to number of milliseconds.
            delta = delta.total_seconds() * 1000.
        self._send_stat(stat, "%0.6f|ms"%delta, tags, rate)

    def incr(self, stat, count=1, tags=None, rate=1):
        """Increment a stat by `count`."""
        self._send_stat(stat, "%s|c"%count, tags, rate)

    def decr(self, stat, count=1, tags=None, rate=1):
        """Decrement a stat by `count`."""
        self.incr(stat, -count, tags, rate)

    def gauge(self, stat, value, tags=None, delta=False, rate=1):
        """Set a gauge value."""
        if value < 0 and not delta:
            if rate < 1:
                if random.random() > rate:
                    return
            with self.pipeline() as pipe:
                pipe._send_stat(stat, "0|g", tags, 1) #pylint: disable=protected-access
                pipe._send_stat(stat, "%s|g"%value, tags, 1) #pylint: disable=protected-access
        else:
            prefix = '+' if delta and value >= 0 else ''
            self._send_stat(stat, "%s%s|g"%(prefix, value), tags, rate)

    def sets(self, stat, value, tags=None, rate=1):
        """Set a set value."""
        self._send_stat(stat, "%s|s" % value, tags, rate)

    def pipeline(self):
        return Pipeline(self)

    def _send_stat(self, stat, value, tags, rate):
        self._after(self._prepare(stat, value, tags, rate))

    def _prepare(self, stat, value, tags, rate):
        if rate < 1:
            if random.random() > rate:
                return None
            value = "%s|@%s" % (value, rate)

        return self._format(stat, tags, value)

    def _after(self, data):
        if data:
            self._send(data)

    def _format(self, stat, tags, value):
        if not stat:
            return None
        if self._prefix:
            stat = self._prefix + "." + stat

        tagstr = Tags.to_str(tags)
        if tagstr:
            stat = stat + "," +  tagstr

        return stat + ":" + value


class Client(_ClientBase):
    def __init__(self, url: str):
        u = urlparse(url.lower())
        qs = parse_qs(u.query)
        prefix = qs.get("prefix", None)
        if u.scheme == "udp":
            self._writer = _UDPWriter(host=u.hostname,
                                      port=u.port)
        elif u.scheme == "file":
            filename = u.hostname + u.path
            self._writer = _FileWriter(filename)
        elif u.scheme == "stdout":
            self._writer = _IOWriter(sys.stdout)
        elif u.scheme == "stderr":
            self._writer = _IOWriter(sys.stderr)
        elif u.scheme == "":
            raise ValueError("url scheme not found")
        else:
            raise ValueError("unknow url scheme: %s"%(u.scheme))

        self._closed = False
        super(Client, self).__init__(prefix)


    def _send(self, data):
        if not self._closed:
            self._writer.write(data)

    def close(self):
        if not self._closed:
            self._writer.close()
            self._closed = True

    def with_tags(self, tags):
        return WithTagsClient(self, tags)


class Pipeline(_ClientBase):
    def __init__(self, client):
        self._client = client
        self._buf = deque()
        super(Pipeline, self).__init__(self._client._prefix)

    def _format(self, stat, tags, value):
        return self._client._format(stat, tags, value) #pylint: disable=protected-access

    def _after(self, data):
        if data:
            self._buf.append(data)

    def _send(self):
        self._client._after("\n".join(self._buf)) #pylint: disable=protected-access

    def __enter__(self):
        return self

    def __exit__(self, typ, value, tb):
        self.send()

    def send(self):
        if self._buf:
            self._send()


class WithTagsClient(_ClientBase):
    def __init__(self, client, tags):
        self._client = client
        self._tags = Tags(tags)
        self._closed = False
        super(WithTagsClient, self).__init__(self._client._prefix)

    def _send(self, data):
        if not self._closed:
            self._client._send(data) #pylint: disable=protected-access

    def _format(self, stat, tags, value):
        if self._tags:
            tags = Tags.concat(self._tags, tags)

        return super(WithTagsClient, self)._format(stat, tags, value)

    def close(self):
        self._closed = True

    def with_tags(self, tags):
        tags = Tags.concat(self._tags, tags)
        return WithTagsClient(self, tags)


class NoneClient():
    def timer(self, stat, tags=None):
        return self

    def timing(self, stat, delta, tags=None):
        pass

    def incr(self, stat, count=1, tags=None):
        pass

    def decr(self, stat, count=1, tags=None):
        pass

    def gauge(self, stat, value, delta=False, tags=None):
        pass

    def sets(self, stat, value, tags=None):
        pass

    def pipeline(self):
        return self

    def close(self):
        pass

    def with_tags(self, tags):
        return self

    def start(self):
        return self

    def stop(self):
        pass

    def send(self):
        pass

    def __call__(self, f):
        return f

    def __enter__(self):
        return self

    def __exit__(self, typ, value, tb):
        pass

class _WriteCloser():
    @abc.abstractmethod
    def write(self, data):
        ...

    @abc.abstractmethod
    def close(self):
        ...

class _UDPWriter(_WriteCloser):
    def __init__(self, host="localhost", port=8125, maxudpsize=512, ipv6=False):
        fam = socket.AF_INET6 if ipv6 else socket.AF_INET
        family, _, _, _, addr = socket.getaddrinfo(
            host, port, fam, socket.SOCK_DGRAM)[0]
        self._addr = addr
        self._sock = socket.socket(family, socket.SOCK_DGRAM)
        self._maxudpsize = maxudpsize if maxudpsize > 0 else 512

    def write(self, data):
        if not self._sock:
            return
        while data:
            if len(data) > self._maxudpsize:
                pos = data[:self._maxudpsize].rfind('\n')
                if pos < 0:
                    pos = data[self._maxudpsize:].find('\n')
                    if pos >= 0:
                        pos += self._maxudpsize
                if pos >= 0:
                    payload = data[:pos]
                    data = data[pos+1:]
                else:
                    payload = data
                    data = None
            else:
                payload = data
                data = None

            try:
                self._sock.sendto(payload.encode('ascii'), self._addr)
            except (socket.error, RuntimeError):
                pass

    def close(self):
        if self._sock:
            self._sock.close()
            self._sock = None


class _IOWriter(_WriteCloser):
    def __init__(self, io):
        self._io = io

    def write(self, data):
        self._io.write(data+"\n")

    def close(self):
        if hasattr(self._io, "flush"):
            self._io.flush()


class _FileWriter(_IOWriter):
    def __init__(self, filename):
        self._fp = open(filename, mode="a+")
        super(_FileWriter, self).__init__(self._fp)

    def close(self):
        if self._fp:
            super(_FileWriter, self).close()
            self._fp.close()
            self._fp = None


def is_enabled():
    return _enabled

def timer(stat, tags=None):
    return _get_or_create_client().timer(stat, tags)

def timing(stat, delta, tags=None):
    return _get_or_create_client().timing(stat, delta, tags)

def incr(stat, count=1, tags=None):
    return _get_or_create_client().incr(stat, count, tags)

def decr(stat, count=1, tags=None):
    return _get_or_create_client().decr(stat, count, tags)

def gauge(stat, value, delta=False, tags=None):
    return _get_or_create_client().gauge(stat, value, delta, tags)

def sets(stat, value, tags=None):
    """ function name use sets instand of set """
    return _get_or_create_client().sets(stat, value, tags) #pylint: disable=redefined-builtin

def pipeline():
    return _get_or_create_client().pipeline()

def with_tags(tags):
    return _get_or_create_client().with_tags(tags)


# temporary cpu/memory stats
_system_stats_lock = threading.Lock()
_system_stats_running = False
_system_stats_interval = 0.5
_cpu_enabled = False
_cpu_stats_client = None
_cpu_stats_interval = 0
_mem_enabled = False
_mem_stats_client = None
_mem_stats_interval = 0

def enable_cpu_stats(client=None, interval=10):
    if not os.path.exists("/sys/fs/cgroup/cpu,cpuacct"):
        return

    global _cpu_enabled, _cpu_stats_client, _cpu_stats_interval #pylint: disable=global-statement
    with _system_stats_lock:
        if _cpu_enabled:
            return
        _cpu_enabled = True
        _cpu_stats_client = client or _get_or_create_client()
        _cpu_stats_interval = interval
        if not _system_stats_running:
            threading.Thread(target=_system_stats_process, daemon=True).start()

def disable_cpu_stats():
    global _cpu_enabled, _cpu_stats_client, _cpu_stats_interval #pylint: disable=global-statement
    with _system_stats_lock:
        _cpu_enabled = False
        _cpu_stats_client = None
        _cpu_stats_interval = 0

def enable_mem_stats(client=None, interval=10):
    if not os.path.exists("/sys/fs/cgroup/memory"):
        return

    global _mem_enabled, _mem_stats_client, _mem_stats_interval #pylint: disable=global-statement
    with _system_stats_lock:
        if _mem_enabled:
            return
        _mem_enabled = True
        _mem_stats_client = client or _get_or_create_client()
        _mem_stats_interval = interval
        if not _system_stats_running:
            threading.Thread(target=_system_stats_process, daemon=True).start()

def disable_mem_stats():
    global _mem_enabled, _mem_stats_client, _mem_stats_interval #pylint: disable=global-statement
    with _system_stats_lock:
        _mem_enabled = False
        _mem_stats_client = None
        _mem_stats_interval = 0

def _system_stats_process():
    cpu_last_runing_at = 0
    mem_last_runing_at = 0
    while True:
        now = time_now()
        if _cpu_enabled and (now - cpu_last_runing_at > _cpu_stats_interval):
            try:
                _cpu_stats_process()
            except Exception: #pylint: disable=broad-except
                pass
            cpu_last_runing_at = now

        if _mem_enabled and (now - mem_last_runing_at > _mem_stats_interval):
            try:
                _mem_stats_process()
            except Exception: #pylint: disable=broad-except
                pass
            mem_last_runing_at = now

        time.sleep(_system_stats_interval)

_cpu_last_time = 0
_cpu_last_usage = 0
_cpu_last_user_usage = 0
_cpu_last_sys_usage = 0
_cpu_last_nr_periods = 0
_cpu_last_nr_throttled = 0

def _cpu_stats_process():
    #pylint: disable=global-statement
    global _cpu_last_time, \
        _cpu_last_usage, _cpu_last_user_usage, _cpu_last_sys_usage, \
        _cpu_last_nr_periods, _cpu_last_nr_throttled
    #pylint: enable=global-statement

    def stat_parse(line):
        pos = line.rfind(" ")
        return line[:pos], int(line[pos+1:])
    def div_or_zero(a, b):
        return a / b if b != 0 else 0

    with open("/sys/fs/cgroup/cpu,cpuacct/cpu.cfs_quota_us") as fp:
        cfs_quota_us = int(fp.read())
    if cfs_quota_us < 0:
        cfs_quota_us = os.cpu_count() * 100000

    with open("/sys/fs/cgroup/cpu,cpuacct/cpu.cfs_period_us") as fp:
        cfs_period_us = int(fp.read())
    cpu_limit = (cfs_quota_us / cfs_period_us) * 100

    with open("/sys/fs/cgroup/cpu,cpuacct/cpu.stat") as fp:
        _, nr_periods = stat_parse(fp.readline()[:-1])
        _, nr_throttled = stat_parse(fp.readline()[:-1])

    with open("/sys/fs/cgroup/cpu,cpuacct/cpuacct.stat") as fp:
        _, user_usage = stat_parse(fp.readline()[:-1])
        _, sys_usage = stat_parse(fp.readline()[:-1])
    usage = user_usage + sys_usage
    now = time_now()

    if _cpu_last_time > 0:
        time_diff = now - _cpu_last_time
        stats_usage = div_or_zero(usage - _cpu_last_usage,
                                  time_diff)
        stats_usage_user = div_or_zero(user_usage - _cpu_last_user_usage,
                                       time_diff)
        stats_usage_sys = div_or_zero(sys_usage - _cpu_last_sys_usage,
                                      time_diff)
        stats_throttled = div_or_zero(nr_throttled - _cpu_last_nr_throttled,
                                      nr_periods - _cpu_last_nr_periods)
        with _cpu_stats_client.pipeline() as pipe:
            pipe.gauge("cpu.limit", cpu_limit)
            pipe.gauge("cpu.usage", stats_usage)
            pipe.gauge("cpu.usage_user", stats_usage_user)
            pipe.gauge("cpu.usage_sys", stats_usage_sys)
            pipe.gauge("cpu.throttled", stats_throttled)

    _cpu_last_time = now
    _cpu_last_usage = usage
    _cpu_last_user_usage = user_usage
    _cpu_last_sys_usage = sys_usage
    _cpu_last_nr_periods = nr_periods
    _cpu_last_nr_throttled = nr_throttled

def _mem_stats_process():
    with open('/sys/fs/cgroup/memory/memory.limit_in_bytes') as fp:
        limit_in_bytes = int(fp.read())

    with open('/sys/fs/cgroup/memory/memory.usage_in_bytes') as fp:
        usage_in_bytes = int(fp.read())

    with _mem_stats_client.pipeline() as pipe:
        pipe.gauge("memory.limit_in_bytes", limit_in_bytes)
        pipe.gauge("memory.usage_in_bytes", usage_in_bytes)
