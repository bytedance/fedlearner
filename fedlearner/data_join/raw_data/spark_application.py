import collections
import logging
import os
import sys
import time

from fedlearner.data_join.raw_data.webconsole_client import \
    FakeWebConsoleClient, WebConsoleClient, SparkAPPStatus


SparkFileConfig = collections.namedtuple('SparkFileConfig',
                                         ['image', 'entry_file',
                                          'config_file', 'dep_file'])

SparkDriverConfig = collections.namedtuple('SparkDriverConfig',
                                           ["cores", "memory"])

SparkExecutorConfig = collections.namedtuple('SparkExecutorConfig',
                                             ["cores", "memory", "instances"])


class SparkApplication(object):
    def __init__(self, name, file_config, driver_config, executor_config,
                 web_console_url, web_console_username, web_console_password,
                 progress_fn=None,
                 use_fake_client=False):
        self._name = name
        self._file_config = file_config
        self._driver_config = driver_config
        self._executor_config = executor_config
        self._progress_fn = progress_fn
        if use_fake_client:
            self._update_local_file_config()
            self._client = FakeWebConsoleClient()
        else:
            self._client = WebConsoleClient(web_console_url,
                                            web_console_username,
                                            web_console_password)

    def launch(self):
        try:
            self._client.delete_sparkapplication(self._name)
        except RuntimeError as error:
            logging.info("Spark application %s not exist",
                         self._name)

        try:
            self._client.create_sparkapplication(
                self._name, self._file_config, self._driver_config,
                self._executor_config)
        except RuntimeError as error:
            logging.fatal("Spark application error %s", error)
            sys.exit(-1)

    def join(self):
        try:
            while True:
                logging.info(self._progress_fn())
                status, msg = self._client.get_sparkapplication(self._name)
                if status == SparkAPPStatus.COMPLETED:
                    logging.info("Spark job %s completed", self._name)
                    break
                if status == SparkAPPStatus.FAILED:
                    logging.error("Spark job %s failed, with response %s",
                                  self._name, msg)
                    sys.exit(-1)
                else:
                    logging.info("Sleep 10s to wait spark job done...")
                    time.sleep(10)
            self._client.delete_sparkapplication(self._name)
        except RuntimeError as error:
            logging.fatal("Spark application error %s", error)
            sys.exit(-1)

    def _update_local_file_config(self):
        local_jars = os.environ.get("SPARK_JARS", "")
        self._file_config = SparkFileConfig(
            self._file_config.image, self._file_config.entry_file,
            ["--config={}".format(self._file_config.config_file),
             "--packages={}".format(local_jars)], self._file_config.dep_file)
