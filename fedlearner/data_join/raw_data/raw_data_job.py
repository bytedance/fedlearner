import logging
import os
import sys
import time
from datetime import datetime, timedelta

from google.protobuf import text_format
from tensorflow.compat.v1 import gfile

from fedlearner.common.common import Timer
from fedlearner.common.db_client import DBClient
from fedlearner.common import common_pb2 as common_pb
from fedlearner.common import data_join_service_pb2 as dj_pb


from fedlearner.data_join.common import commit_data_source, partition_repr,\
    partition_manifest_kvstore_key, data_source_kvstore_base_dir, \
    encode_data_block_meta_fname, DataBlockSuffix, \
    data_source_data_block_dir
from fedlearner.data_join.raw_data.input_data_manager import InputDataManager
from fedlearner.data_join.raw_data.raw_data_meta import RawDataMeta, \
    raw_data_meta_path
from fedlearner.data_join.raw_data.raw_data_config import RawDataJobConfig
from fedlearner.data_join.raw_data.common import OutputType, JobType
from fedlearner.data_join.raw_data.spark_application import SparkFileConfig, \
    SparkApplication
from fedlearner.data_join.raw_data_publisher import RawDataPublisher


class RawDataJob:
    def __init__(self, job_name, root_path,
                 job_type=None,
                 output_type=OutputType.RawData,
                 output_partition_num=0,
                 raw_data_publish_dir="",
                 data_source_name="",
                 data_block_threshold=0,
                 compression_type=None,
                 check_success_tag=True,
                 wildcard=None,
                 single_subfolder=False,
                 files_per_job_limit=0,
                 upload_dir="",
                 long_running=False,
                 spark_k8s_config_path='',
                 spark_k8s_namespace='',
                 spark_dependent_package='',
                 spark_driver_config=None,
                 spark_executor_config=None,
                 use_fake_k8s=False):
        self._job_name = job_name
        self._root_path = root_path
        self._job_type = job_type
        self._output_partition_num = output_partition_num
        self._raw_data_publish_dir = raw_data_publish_dir
        self._data_block_threshold = data_block_threshold
        self._compression_type = compression_type
        self._data_source_name = data_source_name
        self._output_type = output_type
        self._upload_dir = upload_dir
        self._long_running = long_running
        self._spark_k8s_config_path = spark_k8s_config_path
        self._spark_k8s_namespace = spark_k8s_namespace
        self._spark_dependent_package = spark_dependent_package
        self._spark_driver_config = spark_driver_config
        self._spark_executor_config = spark_executor_config
        self._spark_entry_script_name = 'raw_data.py'

        if self._output_type == OutputType.DataBlock:
            # if output data block, run folder one by one
            single_subfolder = True

        meta_file_path = raw_data_meta_path(root_path)
        if not gfile.Exists(os.path.dirname(meta_file_path)):
            gfile.MakeDirs(os.path.dirname(meta_file_path))
        self._meta = RawDataMeta(meta_file_path)

        self._input_data_manager = InputDataManager(
            wildcard,
            check_success_tag,
            single_subfolder,
            files_per_job_limit)

        self._next_job_id = self._meta.job_id + 1
        self._template_dirname = "template"

        self._kvstore = DBClient("dfs")
        self._use_fake_k8s = use_fake_k8s

    def run(self, input_path):
        job_id = self._next_job_id
        while True:
            prev_job_id = job_id
            for rest_fpaths in self._input_data_manager.iterator(
                    input_path, self._meta.processed_fpath):
                with Timer("RawData Job {}".format(job_id)):
                    self._run(job_id, rest_fpaths)
                job_id += 1
            if not self._long_running:
                break
            if job_id == prev_job_id:
                logging.info("No new file to process, Wait 60s...")
                time.sleep(60)

    def _run(self, job_id, input_files):
        logging.info("Processing %s in job %d", input_files, job_id)
        # 0. launch new spark job
        if self._output_type == OutputType.DataBlock:
            self._run_data_block_job(job_id, input_files)
        else:
            self._run_raw_data_job(job_id, input_files)

        # 1. write meta
        self._meta.add_meta(job_id, input_files)
        self._meta.persist()

    def _run_raw_data_job(self, job_id, input_files):
        output_path = os.path.join(self._root_path, str(job_id))
        if gfile.Exists(output_path):
            gfile.DeleteRecursively(output_path)

        # 1. write config
        schema_file_path = os.path.join(self._root_path, "data.schema.json")
        job_config = RawDataJobConfig(self._upload_dir, job_id)
        job_config.raw_data_config(
            input_files, schema_file_path, self._job_type,
            OutputType.RawData,
            output_partition_num=self._output_partition_num,
            output_path=output_path,
            compression_type=self._compression_type)

        task_name = self._encode_spark_task_name(job_id)
        self._launch_spark_job(task_name, job_config.config_path)

        # 2. check spark job successful
        success_tag = os.path.join(output_path, "_SUCCESS")
        if not gfile.Exists(success_tag):
            logging.fatal("There is no _SUCCESS file in output path %s",
                          output_path)
            sys.exit(-1)

        # 3. publish
        self._publish_raw_data(job_id, output_path)

    def _run_data_block_job(self, job_id, input_files):
        data_source = self._create_data_source(job_id, self._root_path)
        output_base_path = data_source_data_block_dir(data_source)
        temp_output_path = os.path.join(output_base_path, str(job_id))
        if gfile.Exists(temp_output_path):
            gfile.DeleteRecursively(temp_output_path)
        # 1. write config
        job_config = RawDataJobConfig(self._upload_dir, job_id)
        job_config.data_block_config(
            input_files, temp_output_path,
            OutputType.DataBlock, self._compression_type,
            data_block_threshold=self._data_block_threshold)
        task_name = self._encode_spark_task_name(job_id)
        self._launch_spark_job(task_name, job_config.config_path)

        # 2. check spark job successful
        success_tag = os.path.join(temp_output_path, "_SUCCESS")
        if not gfile.Exists(success_tag):
            logging.fatal("There is no _SUCCESS file in output path %s",
                          temp_output_path)
            sys.exit(-1)

        # 3. publish data block
        self._publish_data_block(job_id, data_source, temp_output_path,
                                 output_base_path, input_files[0])

    @staticmethod
    def _is_flag_file(filename: str):
        return filename.startswith(('_', '.'))

    def _launch_spark_job(self, task_name, config_path):
        file_config = self._encode_spark_file_config(config_path)
        spark_app = SparkApplication(
            task_name, file_config,
            self._spark_driver_config,
            self._spark_executor_config,
            k8s_config_path=self._spark_k8s_config_path,
            use_fake_k8s=self._use_fake_k8s)
        spark_app.launch(self._spark_k8s_namespace)
        spark_app.join(self._spark_k8s_namespace)

    def _encode_data_block_filename(self,
                                    partition_id, block_id,
                                    start_time, end_time):
        return "{}.{}.{:08}.{}-{}{}".format(
            self._data_source_name,
            partition_repr(partition_id),
            block_id,
            start_time, end_time,
            DataBlockSuffix)

    def _encode_spark_task_name(self, job_id):
        return "raw-data-{}-{}".format(self._job_name, job_id)

    def _encode_spark_file_config(self, config_path):
        return SparkFileConfig(
            os.path.join(self._upload_dir, self._spark_entry_script_name),
            config_path,
            self._spark_dependent_package)

    @staticmethod
    def _decode_partition_id(filename):
        if not filename.startswith('part-'):
            raise RuntimeError("filename of raw_data should startswith " \
                               "{}".format('part-'))
        return int(filename.split('-')[-1].split(".")[0])

    def _publish_raw_data(self, job_id, output_dir):
        publisher = \
            RawDataPublisher(self._kvstore,
                             self._raw_data_publish_dir)
        publish_fpaths = []
        if gfile.Exists(output_dir) and gfile.IsDirectory(output_dir):
            fnames = [f for f in gfile.ListDirectory(output_dir)
                      if not self._is_flag_file(f)]
            for fname in sorted(fnames):
                partition_id = self._decode_partition_id(fname)
                file_path = os.path.join(output_dir, fname)
                publish_fpaths.append(file_path)
                publisher.publish_raw_data(partition_id, [file_path])
                if self._job_type == JobType.PSI:
                    publisher.finish_raw_data(partition_id)
        logging.info("Data Portal Master publish %d file of streaming job %d",
                     len(publish_fpaths), job_id)
        for seq, fpath in enumerate(publish_fpaths):
            logging.info("%d. %s", seq, fpath)

    def _publish_data_block(self, job_id, data_source, temp_output_path,
                            output_base_path, input_file):
        folder_name = os.path.basename(os.path.dirname(input_file))
        try:
            date_time = datetime.strptime(folder_name, '%Y%m%d')
            start_time_str = date_time.strftime("%Y%m%d%H%M%S")
            end_time_str = (date_time + timedelta(hours=23, minutes=59,
                                                  seconds=59)) \
                .strftime("%Y%m%d%H%M%S")
        except ValueError as e:
            logging.error("Input data's folder format is %s, want %s",
                          folder_name, "%Y%m%d")
            start_time_str = '0'
            end_time_str = '0'
        # 3. rename output files
        block_id = 0
        for filename in gfile.ListDirectory(temp_output_path):
            if self._is_flag_file(filename):
                continue
            new_filename = self._encode_data_block_filename(
                job_id, block_id, start_time_str, end_time_str)
            meta_filename = encode_data_block_meta_fname(
                self._data_source_name, job_id, block_id)
            in_file = os.path.join(temp_output_path, filename)
            out_file = os.path.join(temp_output_path, new_filename)
            gfile.Rename(in_file, out_file)
            meta_file = os.path.join(temp_output_path, meta_filename)
            with gfile.Open(meta_file, "w") as meta:
                meta.write("")
            block_id += 1
        # 4. move to destination path
        output_path = os.path.join(output_base_path, partition_repr(job_id))
        if gfile.Exists(output_path):
            gfile.DeleteRecursively(output_path)
        logging.info("Rename %s to %s", temp_output_path, output_path)
        gfile.Rename(temp_output_path, output_path)

        # 5. mock data_source
        self._update_data_source(job_id, data_source)

    def _update_manifest(self, manifest):
        partition_id = manifest.partition_id
        manifest_kvstore_key = partition_manifest_kvstore_key(
            self._data_source_name,
            partition_id
        )
        self._kvstore.set_data(manifest_kvstore_key,
                               text_format.MessageToString(manifest))

    def _mock_raw_data_manifest(self, partition_id):
        manifest = dj_pb.RawDataManifest()
        manifest.sync_example_id_rep.rank_id = -1
        manifest.join_example_rep.rank_id = -1
        manifest.partition_id = partition_id
        manifest.sync_example_id_rep.state = \
            dj_pb.SyncExampleIdState.Synced
        manifest.join_example_rep.state = \
            dj_pb.JoinExampleState.Joined
        self._update_manifest(manifest)

    def _create_data_source(self, job_id, output_base_dir):
        partition_num = job_id + 1
        data_source = common_pb.DataSource()
        data_source.data_source_meta.name = self._data_source_name
        data_source.data_source_meta.partition_num = partition_num
        data_source.output_base_dir = output_base_dir
        data_source.state = common_pb.DataSourceState.Init
        data_source.role = common_pb.FLRole.Leader
        return data_source

    def _update_data_source(self, job_id, data_source):
        master_kvstore_key = data_source_kvstore_base_dir(
            data_source.data_source_meta.name
        )
        raw_data = self._kvstore.get_data(master_kvstore_key)
        if raw_data is None:
            logging.info("data source %s exist, override it",
                         self._data_source_name)
        self._mock_raw_data_manifest(job_id)
        commit_data_source(self._kvstore, data_source)
        logging.info("apply new data source %s", self._data_source_name)
        return data_source
