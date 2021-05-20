import json
import os
from tensorflow.compat.v1 import gfile
from fedlearner.data_join.raw_data.common import Constants


class RawDataJobConfig(object):
    def __init__(self, config_path, job_id):
        name_format = "raw_data_{}.config"
        self._config_path = os.path.join(config_path,
                                         name_format.format(job_id))

    @property
    def config_path(self):
        return self._config_path

    def data_block_config(self,
                          input_files,
                          output_path,
                          output_type,
                          compression_type,
                          data_block_threshold=0):
        config_dict = {
            Constants.input_files_key: ",".join(input_files),
            Constants.output_type_key: output_type,
            Constants.output_path_key: output_path,
            Constants.compression_type_key: compression_type,
            Constants.data_block_threshold_key: data_block_threshold,
        }
        with gfile.Open(self._config_path, 'w') as f:
            f.write(json.dumps(config_dict))

    def raw_data_config(self,
                        input_files,
                        schema_file_path,
                        job_type,
                        output_type,
                        output_partition_num,
                        output_path):
        config_dict = {
            Constants.job_type_key: job_type,
            Constants.input_files_key: ",".join(input_files),
            Constants.schema_path_key: schema_file_path,
            Constants.output_type_key: output_type,
            Constants.output_partition_num_key: output_partition_num,
            Constants.output_path_key: output_path,
        }
        with gfile.Open(self._config_path, 'w') as f:
            f.write(json.dumps(config_dict))
