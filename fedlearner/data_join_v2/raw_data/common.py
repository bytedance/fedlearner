from collections import namedtuple


class Constants:
    input_files_key = "input_files"
    job_type_key = "job_type"
    job_id_key = "job_id"
    output_partition_num_key = "output_partition_num"
    output_type_key = "output_type"
    output_path_key = "output_path"
    data_block_threshold_key = "data_block_threshold"
    compression_type_key = "compression_type"


class JobType:
    Streaming = "Streaming"
    PSI = "PSI"


class DataKeyword:
    event_time = "event_time"
    example_id = "example_id"
    raw_id = "raw_id"
    click_id = "click_id"
    job_id = "_job_id"
    index = "_index"
    partition_key = "_part"
    data = "_data"


class OutputType:
    RawData = "raw_data"
    DataBlock = "data_block"


AllowedFieldType = namedtuple('AllowedFieldType',
                              ['default_value', 'type', 'required'])


class RawDataSchema(object):
    @staticmethod
    def invalid_bytes():
        return ''.encode()

    @staticmethod
    def invalid_int():
        return -1

    @staticmethod
    def invalid_event_time():
        return 0

    @staticmethod
    def wanted_fields():
        return {
            DataKeyword.event_time: RawDataSchema.invalid_event_time(),
            DataKeyword.example_id: RawDataSchema.invalid_bytes(),
            DataKeyword.raw_id: RawDataSchema.invalid_bytes(),
            DataKeyword.click_id: RawDataSchema.invalid_bytes(),
        }

    @staticmethod
    def schema():
        return [
            (DataKeyword.job_id,
             AllowedFieldType(RawDataSchema.invalid_int(), int, True)),
            (DataKeyword.index,
             AllowedFieldType(RawDataSchema.invalid_int(), int, True)),
            (DataKeyword.data,
             AllowedFieldType(RawDataSchema.invalid_bytes(), bytes, True)),
            (DataKeyword.event_time,
             AllowedFieldType(RawDataSchema.invalid_int(), int, False)),
            (DataKeyword.example_id,
             AllowedFieldType(RawDataSchema.invalid_bytes(), str, False)),
            (DataKeyword.raw_id,
             AllowedFieldType(RawDataSchema.invalid_bytes(), str, False)),
            (DataKeyword.click_id,
             AllowedFieldType(RawDataSchema.invalid_bytes(), str, False)),
            (DataKeyword.partition_key,
             AllowedFieldType(RawDataSchema.invalid_bytes(), str, False)),
        ]
