

class Constants:
    input_files_key = "input_files"
    schema_path_key = "schema_path"
    job_type_key = "job_type"
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


class OutputType:
    RawData = "raw_data"
    DataBlock = "data_block"


