"""
@generated by mypy-protobuf.  Do not edit manually!
isort:skip_file
"""
import builtins
import fedlearner_webconsole.proto.dataset_pb2
import fedlearner_webconsole.proto.mmgr_pb2
import google.protobuf.descriptor
import google.protobuf.message
import typing
import typing_extensions

DESCRIPTOR: google.protobuf.descriptor.FileDescriptor = ...

class InformTrustedJobGroupRequest(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor = ...
    UUID_FIELD_NUMBER: builtins.int
    AUTH_STATUS_FIELD_NUMBER: builtins.int
    uuid: typing.Text = ...
    auth_status: typing.Text = ...

    def __init__(self,
        *,
        uuid : typing.Text = ...,
        auth_status : typing.Text = ...,
        ) -> None: ...
    def ClearField(self, field_name: typing_extensions.Literal[u"auth_status",b"auth_status",u"uuid",b"uuid"]) -> None: ...
global___InformTrustedJobGroupRequest = InformTrustedJobGroupRequest

class UpdateTrustedJobGroupRequest(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor = ...
    UUID_FIELD_NUMBER: builtins.int
    ALGORITHM_UUID_FIELD_NUMBER: builtins.int
    uuid: typing.Text = ...
    algorithm_uuid: typing.Text = ...

    def __init__(self,
        *,
        uuid : typing.Text = ...,
        algorithm_uuid : typing.Text = ...,
        ) -> None: ...
    def ClearField(self, field_name: typing_extensions.Literal[u"algorithm_uuid",b"algorithm_uuid",u"uuid",b"uuid"]) -> None: ...
global___UpdateTrustedJobGroupRequest = UpdateTrustedJobGroupRequest

class DeleteTrustedJobGroupRequest(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor = ...
    UUID_FIELD_NUMBER: builtins.int
    uuid: typing.Text = ...

    def __init__(self,
        *,
        uuid : typing.Text = ...,
        ) -> None: ...
    def ClearField(self, field_name: typing_extensions.Literal[u"uuid",b"uuid"]) -> None: ...
global___DeleteTrustedJobGroupRequest = DeleteTrustedJobGroupRequest

class GetTrustedJobGroupRequest(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor = ...
    UUID_FIELD_NUMBER: builtins.int
    uuid: typing.Text = ...

    def __init__(self,
        *,
        uuid : typing.Text = ...,
        ) -> None: ...
    def ClearField(self, field_name: typing_extensions.Literal[u"uuid",b"uuid"]) -> None: ...
global___GetTrustedJobGroupRequest = GetTrustedJobGroupRequest

class GetTrustedJobGroupResponse(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor = ...
    AUTH_STATUS_FIELD_NUMBER: builtins.int
    auth_status: typing.Text = ...

    def __init__(self,
        *,
        auth_status : typing.Text = ...,
        ) -> None: ...
    def ClearField(self, field_name: typing_extensions.Literal[u"auth_status",b"auth_status"]) -> None: ...
global___GetTrustedJobGroupResponse = GetTrustedJobGroupResponse

class InformTrustedJobRequest(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor = ...
    UUID_FIELD_NUMBER: builtins.int
    AUTH_STATUS_FIELD_NUMBER: builtins.int
    uuid: typing.Text = ...
    auth_status: typing.Text = ...

    def __init__(self,
        *,
        uuid : typing.Text = ...,
        auth_status : typing.Text = ...,
        ) -> None: ...
    def ClearField(self, field_name: typing_extensions.Literal[u"auth_status",b"auth_status",u"uuid",b"uuid"]) -> None: ...
global___InformTrustedJobRequest = InformTrustedJobRequest

class GetTrustedJobRequest(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor = ...
    UUID_FIELD_NUMBER: builtins.int
    uuid: typing.Text = ...

    def __init__(self,
        *,
        uuid : typing.Text = ...,
        ) -> None: ...
    def ClearField(self, field_name: typing_extensions.Literal[u"uuid",b"uuid"]) -> None: ...
global___GetTrustedJobRequest = GetTrustedJobRequest

class GetTrustedJobResponse(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor = ...
    AUTH_STATUS_FIELD_NUMBER: builtins.int
    auth_status: typing.Text = ...

    def __init__(self,
        *,
        auth_status : typing.Text = ...,
        ) -> None: ...
    def ClearField(self, field_name: typing_extensions.Literal[u"auth_status",b"auth_status"]) -> None: ...
global___GetTrustedJobResponse = GetTrustedJobResponse

class CreateTrustedExportJobRequest(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor = ...
    UUID_FIELD_NUMBER: builtins.int
    NAME_FIELD_NUMBER: builtins.int
    EXPORT_COUNT_FIELD_NUMBER: builtins.int
    PARENT_UUID_FIELD_NUMBER: builtins.int
    TICKET_UUID_FIELD_NUMBER: builtins.int
    uuid: typing.Text = ...
    name: typing.Text = ...
    export_count: builtins.int = ...
    parent_uuid: typing.Text = ...
    ticket_uuid: typing.Text = ...

    def __init__(self,
        *,
        uuid : typing.Text = ...,
        name : typing.Text = ...,
        export_count : builtins.int = ...,
        parent_uuid : typing.Text = ...,
        ticket_uuid : typing.Text = ...,
        ) -> None: ...
    def ClearField(self, field_name: typing_extensions.Literal[u"export_count",b"export_count",u"name",b"name",u"parent_uuid",b"parent_uuid",u"ticket_uuid",b"ticket_uuid",u"uuid",b"uuid"]) -> None: ...
global___CreateTrustedExportJobRequest = CreateTrustedExportJobRequest

class CreateModelJobRequest(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor = ...
    NAME_FIELD_NUMBER: builtins.int
    UUID_FIELD_NUMBER: builtins.int
    GROUP_UUID_FIELD_NUMBER: builtins.int
    MODEL_JOB_TYPE_FIELD_NUMBER: builtins.int
    ALGORITHM_TYPE_FIELD_NUMBER: builtins.int
    GLOBAL_CONFIG_FIELD_NUMBER: builtins.int
    VERSION_FIELD_NUMBER: builtins.int
    name: typing.Text = ...
    uuid: typing.Text = ...
    group_uuid: typing.Text = ...
    model_job_type: typing.Text = ...
    algorithm_type: typing.Text = ...
    version: builtins.int = ...

    @property
    def global_config(self) -> fedlearner_webconsole.proto.mmgr_pb2.ModelJobGlobalConfig: ...

    def __init__(self,
        *,
        name : typing.Text = ...,
        uuid : typing.Text = ...,
        group_uuid : typing.Text = ...,
        model_job_type : typing.Text = ...,
        algorithm_type : typing.Text = ...,
        global_config : typing.Optional[fedlearner_webconsole.proto.mmgr_pb2.ModelJobGlobalConfig] = ...,
        version : builtins.int = ...,
        ) -> None: ...
    def HasField(self, field_name: typing_extensions.Literal[u"global_config",b"global_config"]) -> builtins.bool: ...
    def ClearField(self, field_name: typing_extensions.Literal[u"algorithm_type",b"algorithm_type",u"global_config",b"global_config",u"group_uuid",b"group_uuid",u"model_job_type",b"model_job_type",u"name",b"name",u"uuid",b"uuid",u"version",b"version"]) -> None: ...
global___CreateModelJobRequest = CreateModelJobRequest

class CreateDatasetJobStageRequest(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor = ...
    DATASET_JOB_UUID_FIELD_NUMBER: builtins.int
    DATASET_JOB_STAGE_UUID_FIELD_NUMBER: builtins.int
    NAME_FIELD_NUMBER: builtins.int
    EVENT_TIME_FIELD_NUMBER: builtins.int
    dataset_job_uuid: typing.Text = ...
    dataset_job_stage_uuid: typing.Text = ...
    name: typing.Text = ...
    event_time: builtins.int = ...

    def __init__(self,
        *,
        dataset_job_uuid : typing.Text = ...,
        dataset_job_stage_uuid : typing.Text = ...,
        name : typing.Text = ...,
        event_time : builtins.int = ...,
        ) -> None: ...
    def ClearField(self, field_name: typing_extensions.Literal[u"dataset_job_stage_uuid",b"dataset_job_stage_uuid",u"dataset_job_uuid",b"dataset_job_uuid",u"event_time",b"event_time",u"name",b"name"]) -> None: ...
global___CreateDatasetJobStageRequest = CreateDatasetJobStageRequest

class GetDatasetJobStageRequest(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor = ...
    DATASET_JOB_STAGE_UUID_FIELD_NUMBER: builtins.int
    dataset_job_stage_uuid: typing.Text = ...

    def __init__(self,
        *,
        dataset_job_stage_uuid : typing.Text = ...,
        ) -> None: ...
    def ClearField(self, field_name: typing_extensions.Literal[u"dataset_job_stage_uuid",b"dataset_job_stage_uuid"]) -> None: ...
global___GetDatasetJobStageRequest = GetDatasetJobStageRequest

class GetDatasetJobStageResponse(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor = ...
    DATASET_JOB_STAGE_FIELD_NUMBER: builtins.int

    @property
    def dataset_job_stage(self) -> fedlearner_webconsole.proto.dataset_pb2.DatasetJobStage: ...

    def __init__(self,
        *,
        dataset_job_stage : typing.Optional[fedlearner_webconsole.proto.dataset_pb2.DatasetJobStage] = ...,
        ) -> None: ...
    def HasField(self, field_name: typing_extensions.Literal[u"dataset_job_stage",b"dataset_job_stage"]) -> builtins.bool: ...
    def ClearField(self, field_name: typing_extensions.Literal[u"dataset_job_stage",b"dataset_job_stage"]) -> None: ...
global___GetDatasetJobStageResponse = GetDatasetJobStageResponse

class CreateModelJobGroupRequest(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor = ...
    NAME_FIELD_NUMBER: builtins.int
    UUID_FIELD_NUMBER: builtins.int
    ALGORITHM_TYPE_FIELD_NUMBER: builtins.int
    DATASET_UUID_FIELD_NUMBER: builtins.int
    ALGORITHM_PROJECT_LIST_FIELD_NUMBER: builtins.int
    name: typing.Text = ...
    uuid: typing.Text = ...
    algorithm_type: typing.Text = ...
    dataset_uuid: typing.Text = ...

    @property
    def algorithm_project_list(self) -> fedlearner_webconsole.proto.mmgr_pb2.AlgorithmProjectList: ...

    def __init__(self,
        *,
        name : typing.Text = ...,
        uuid : typing.Text = ...,
        algorithm_type : typing.Text = ...,
        dataset_uuid : typing.Text = ...,
        algorithm_project_list : typing.Optional[fedlearner_webconsole.proto.mmgr_pb2.AlgorithmProjectList] = ...,
        ) -> None: ...
    def HasField(self, field_name: typing_extensions.Literal[u"algorithm_project_list",b"algorithm_project_list"]) -> builtins.bool: ...
    def ClearField(self, field_name: typing_extensions.Literal[u"algorithm_project_list",b"algorithm_project_list",u"algorithm_type",b"algorithm_type",u"dataset_uuid",b"dataset_uuid",u"name",b"name",u"uuid",b"uuid"]) -> None: ...
global___CreateModelJobGroupRequest = CreateModelJobGroupRequest

class GetModelJobRequest(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor = ...
    UUID_FIELD_NUMBER: builtins.int
    uuid: typing.Text = ...

    def __init__(self,
        *,
        uuid : typing.Text = ...,
        ) -> None: ...
    def ClearField(self, field_name: typing_extensions.Literal[u"uuid",b"uuid"]) -> None: ...
global___GetModelJobRequest = GetModelJobRequest

class GetModelJobGroupRequest(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor = ...
    UUID_FIELD_NUMBER: builtins.int
    uuid: typing.Text = ...

    def __init__(self,
        *,
        uuid : typing.Text = ...,
        ) -> None: ...
    def ClearField(self, field_name: typing_extensions.Literal[u"uuid",b"uuid"]) -> None: ...
global___GetModelJobGroupRequest = GetModelJobGroupRequest

class InformModelJobGroupRequest(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor = ...
    UUID_FIELD_NUMBER: builtins.int
    AUTH_STATUS_FIELD_NUMBER: builtins.int
    uuid: typing.Text = ...
    auth_status: typing.Text = ...

    def __init__(self,
        *,
        uuid : typing.Text = ...,
        auth_status : typing.Text = ...,
        ) -> None: ...
    def ClearField(self, field_name: typing_extensions.Literal[u"auth_status",b"auth_status",u"uuid",b"uuid"]) -> None: ...
global___InformModelJobGroupRequest = InformModelJobGroupRequest

class UpdateDatasetJobSchedulerStateRequest(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor = ...
    UUID_FIELD_NUMBER: builtins.int
    SCHEDULER_STATE_FIELD_NUMBER: builtins.int
    uuid: typing.Text = ...
    scheduler_state: typing.Text = ...

    def __init__(self,
        *,
        uuid : typing.Text = ...,
        scheduler_state : typing.Text = ...,
        ) -> None: ...
    def ClearField(self, field_name: typing_extensions.Literal[u"scheduler_state",b"scheduler_state",u"uuid",b"uuid"]) -> None: ...
global___UpdateDatasetJobSchedulerStateRequest = UpdateDatasetJobSchedulerStateRequest
