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
                          input_format,
                          output_path,
                          output_type,
                          output_format,
                          compression_type,
                          data_block_threshold=0):
        config_dict = {
            Constants.input_files_key: ",".join(input_files),
            Constants.input_format_key: input_format,
            Constants.output_type_key: output_type,
            Constants.output_path_key: output_path,
            Constants.output_format_key: output_format,
            Constants.compression_type_key: compression_type,
            Constants.data_block_threshold_key: data_block_threshold,
        }
        with gfile.Open(self._config_path, 'w') as f:
            f.write(json.dumps(config_dict))

    def raw_data_config(self,
                        input_files,
                        input_format,
                        job_type,
                        output_type,
                        output_format,
                        output_partition_num,
                        output_path,
                        validation,
                        oss_access_key_id,
                        oss_access_key_secret,
                        oss_endpoint):
        config_dict = {
            Constants.job_type_key: job_type,
            Constants.input_files_key: ",".join(input_files),
            Constants.input_format_key: input_format,
            Constants.output_type_key: output_type,
            Constants.output_partition_num_key: output_partition_num,
            Constants.output_format_key: output_format,
            Constants.output_path_key: output_path,
            Constants.validation_key: validation
        }
        with gfile.Open(self._config_path, 'w') as f:
            f.write(json.dumps(config_dict))
