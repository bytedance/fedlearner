from collections import namedtuple


class Constants:
    input_files_key = "input_files"
    input_format_key = "input_format"
    job_type_key = "job_type"
    output_partition_num_key = "output_partition_num"
    output_type_key = "output_type"
    output_path_key = "output_path"
    output_format_key = "output_format"
    data_block_threshold_key = "data_block_threshold"
    compression_type_key = "compression_type"
    validation_key = "validation"


class JobType:
    Streaming = "Streaming"
    PSI = "PSI"


class DataKeyword:
    event_time = "event_time"
    example_id = "example_id"
    raw_id = "raw_id"


class FileFormat:
    TF_RECORD = "TF_RECORD"
    CSV = "CSV"

    @classmethod
    def check_format(cls, in_type):
        type_array = [cls.TF_RECORD, cls.CSV]
        if in_type not in type_array:
            return False, "only support types {}".format(type_array)
        return True, ""


class OutputType:
    RawData = "raw_data"
    DataBlock = "data_block"


class RawDataSchema:
    InvalidEventTime = -9223372036854775808
    InvalidBytes = ''.encode()
    InvalidInt = -1
    ALLOWED_FIELD = namedtuple('ALLOW_FIELD', ['default_value', 'default_type',
                                               'types', 'required'])
    Schema = dict({
        'example_id': ALLOWED_FIELD(InvalidBytes, "string", ["string"], True),
        'event_time': ALLOWED_FIELD(InvalidEventTime, "long",
                                    ["integer", "long"], False),
        'index': ALLOWED_FIELD(InvalidInt, "long", ["integer", "long"], False),
        'event_time_deep': ALLOWED_FIELD(InvalidEventTime, "long",
                                         ["integer", "long"], False),
        'raw_id': ALLOWED_FIELD(InvalidBytes, "string", ["string"], False),
        'type': ALLOWED_FIELD(InvalidBytes, "string", ["string"], False),
        'id_type': ALLOWED_FIELD(InvalidBytes, "string", ["string"], False),
        'joined': ALLOWED_FIELD(InvalidInt, "integer",
                                ["integer", "long"], False),
        'click_id': ALLOWED_FIELD(InvalidBytes, "string", ["string"], False),
        'req_id': ALLOWED_FIELD(InvalidBytes, "string", ["string"], False),
        'label': ALLOWED_FIELD(InvalidInt, "integer",
                               ["integer", "long"], False),
        'cid': ALLOWED_FIELD(InvalidBytes, "string", ["string"], False)
    })
