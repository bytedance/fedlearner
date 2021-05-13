import unittest

from fedlearner.data_join.raw_data.raw_data_config import *


class RawDataConfigTests(unittest.TestCase):
    def test_spark_task_config(self):
        task_name = "test"
        spark_file_config = SparkFileConfig("/a", "/b", "")
        spark_driver_config = SparkDriverConfig(2, "2g")
        spark_executor_config = SparkExecutorConfig(2, "2g", 10)
        res = SparkTaskConfig.task_json(task_name,
                                        spark_file_config,
                                        spark_driver_config,
                                        spark_executor_config)
        print(res)


if __name__ == '__main__':
    unittest.main()
