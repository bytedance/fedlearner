import request from 'libs/request';
import {
  DataBatchImportPayload,
  Dataset,
  DatasetCreatePayload,
  DatasetEditPayload,
  FileToImport,
  IntersectionDataset,
  PreviewData,
  FeatureMetric,
  ExportInfo,
  DataSource,
  DataSourceCreatePayload,
  DataSourceEditPayload,
  DataSourceCheckConnectionPayload,
  ParticipantDataset,
  DataJobBackEndType,
  DataJobVariable,
  DatasetJobCreatePayload,
  ProcessedDatasetCreatePayload,
  DatasetJob,
  DatasetJobListItem,
  DatasetJobStop,
  DatasetLedger,
  ExportDataset,
  DatasetStateFront,
  DataBatchV2,
  DatasetJobStage,
  FileTreeNode,
} from 'typings/dataset';
import { PageMeta, APIResponse } from '../typings/app';

export function fetchDatasetList(params?: {
  order_by?: string;
  filter?: string;
  state_frontend?: DatasetStateFront[];
  page_size?: number;
  page?: number;
  dataset_job_kind?: DataJobBackEndType;
  cron_interval?: Array<'DAYS' | 'HOURS'>;
}): Promise<{ data: Dataset[]; page_meta?: PageMeta }> {
  return request('/v2/datasets', { params, removeFalsy: true, snake_case: true });
}

export function fetchParticipantDatasetList(
  id: ID,
  params?: any,
): Promise<{ data: ParticipantDataset[]; page_meta?: PageMeta }> {
  return request(`/v2/project/${id}/participant_datasets`, {
    params,
    removeFalsy: true,
    snake_case: true,
  });
}

export function authorizeDataset(id: ID) {
  return request.post(`/v2/datasets/${id}:authorize`);
}

export function cancelAuthorizeDataset(id: ID) {
  return request.delete(`/v2/datasets/${id}:authorize`);
}

export function fetchDatasetFlushAuthStatus(id?: ID) {
  return request.post(`/v2/datasets/${id}:flush_auth_status`);
}

export function fetchDatasetDetail(id?: ID): Promise<{ data: Dataset }> {
  return request(`/v2/datasets/${id}`);
}

export function createDataset(payload: DatasetCreatePayload) {
  return request.post('/v2/datasets', payload);
}

export function editDataset(id: ID, payload: DatasetEditPayload) {
  return request.patch(`/v2/datasets/${id}`, payload);
}

export function startToImportDataBatch(id: ID, payload: DataBatchImportPayload) {
  return request.post(`/v2/datasets/${id}/batches`, payload);
}

export function fetchDataBatchs(
  id: ID,
  params = {},
): Promise<{ data: DataBatchV2[]; page_meta?: PageMeta }> {
  return request(`/v2/datasets/${id}/batches`, {
    params,
    removeFalsy: true,
    snake_case: true,
  });
}

export function fetchDataBatchById(dataset_id: ID, id: ID): Promise<{ data: DataBatchV2 }> {
  return request(`/v2/datasets/${dataset_id}/batches/${id}`);
}

export function rerunDatasetBatchById(dataset_id: ID, data_batch_id: ID, payload: any) {
  return request.post(`/v2/datasets/${dataset_id}/batches/${data_batch_id}:rerun`, payload);
}

export function fetchFileList(params?: { directory?: string }): Promise<{ data: FileToImport[] }> {
  return request('/v2/files', { params, removeFalsy: true, snake_case: true });
}

export function deleteDataset(
  id: ID,
): Promise<{
  code?: number;
  message?: string;
}> {
  return request.delete(`/v2/datasets/${id}`).catch((error) => {
    // If HTTP response status code is 409, meaning delete fail
    if (error.code === 409) {
      return Promise.resolve(error.extra);
    }
    return Promise.reject(error);
  });
}

export function stopDatasetStreaming(project_id: ID, dataset_job_id: ID) {
  return request.post(`/v2/projects/${project_id}/dataset_jobs/${dataset_job_id}:stop_scheduler`);
}

// TODO: this api will be removed after ModelCenter module updated and do not use it anyway!
export function fetchIntersectionDatasetList(params?: {
  kind?: number;
  projectId?: ID;
  datasetId?: ID;
}): Promise<{ data: IntersectionDataset[] }> {
  return request('/v2/intersection_datasets', { params, removeFalsy: true, snake_case: true });
}

export function fetchDatasetPreviewData(id: ID): Promise<{ data: PreviewData }> {
  return request(`/v2/datasets/${id}/preview`);
}

export function fetchDataBatchPreviewData(id: ID, batch_id: ID): Promise<{ data: PreviewData }> {
  return request(`/v2/datasets/${id}/preview`, {
    params: {
      batch_id,
    },
  });
}

export function analyzeDataBatch(id: ID, batch_id: ID, payload: any): Promise<any> {
  return request.post(`/v2/datasets/${id}/batches/${batch_id}:analyze`, payload);
}

export async function fetchFeatureInfo(
  id: ID,
  batch_id: ID,
  featKey: string,
): Promise<{
  data: FeatureMetric;
}> {
  return request(`/v2/datasets/${id}/batches/${batch_id}/feature_metrics`, {
    params: {
      name: featKey,
    },
  });
}

export function fetchDatasetExportInfo(id: ID, params = {}): Promise<{ data: ExportInfo[] }> {
  return request(`/v2/datasets/${id}/exports`, params);
}

export function exportDataset(id: ID, payload: any): Promise<{ data: ExportDataset }> {
  return request.post(`/v2/datasets/${id}:export`, payload);
}

export function postPublishDataset(id: ID, payload: { value?: number }) {
  return request.post(`/v2/datasets/${id}:publish`, payload);
}

export function unpublishDataset(id: ID) {
  return request.delete(`/v2/datasets/${id}:publish`);
}

export function fetchDataSourceList(params?: {
  projectId?: ID;
  keyword?: string;
}): Promise<{ data: DataSource[] }> {
  return request('/v2/data_sources', { params, removeFalsy: true, snake_case: true });
}
export function createDataSource(payload: DataSourceCreatePayload): Promise<{ data: DataSource }> {
  return request.post('/v2/data_sources', payload);
}
export function updateDataSource(payload: DataSourceEditPayload): Promise<{ data: DataSource }> {
  return request.put('/v2/data_sources', payload);
}

export function fetchDataSourceDetail(params: { id: ID }): Promise<{ data: DataSource }> {
  const { id } = params;
  return request(`/v2/data_sources/${id}`);
}

export function checkDataSourceConnection(
  payload: DataSourceCheckConnectionPayload,
): Promise<{
  data: {
    message: string;
    file_names: string[];
    extra_nums: number;
  };
}> {
  return request.post('/v2/data_sources:check_connection', payload);
}
export function deleteDataSource(dataSourceId: ID) {
  return request.delete(`/v2/data_sources/${dataSourceId}`);
}

export function fetchDataSourceFileTreeList(id: ID): APIResponse<FileTreeNode> {
  return request.get(`/v2/data_sources/${id}/tree`);
}

export function fetchDataJobVariableDetail(
  dataJobType: DataJobBackEndType,
  params?: any,
): Promise<{
  data: {
    is_federated: boolean;
    variables: DataJobVariable[];
  };
}> {
  return request(`/v2/dataset_job_definitions/${dataJobType}`, {
    params,
    removeFalsy: true,
    snake_case: true,
  });
}

export function fetchDatasetJobList(
  project_id: ID,
  params?: {
    input_dataset_id?: ID;
    dataset_job_kind?: string;
    filter?: string;
    order_by?: string;
    page?: number;
    page_size?: number;
  },
): Promise<{ data: DatasetJobListItem[]; page_meta?: PageMeta }> {
  return request(`/v2/projects/${project_id}/dataset_jobs`, {
    params: {
      ...(params ?? {}),
    },
    removeFalsy: true,
    snake_case: true,
  });
}

export function fetchChildrenDatasetList(
  dataset_id: ID,
): Promise<{ data: DatasetJobListItem[]; page_meta?: PageMeta }> {
  return request(`/v2/datasets/${dataset_id}/children_datasets`);
}

export function createProcessedDataset(
  project_id: ID,
  payload: ProcessedDatasetCreatePayload,
): Promise<{ data: any }> {
  return request.post(`/v2/projects/${project_id}/dataset_jobs`, payload);
}

export function createDatasetJobs(
  project_id: ID,
  payload: DatasetJobCreatePayload,
): Promise<{ data: any }> {
  return request.post(`/v2/projects/${project_id}/dataset_jobs`, payload);
}

export function fetchDatasetJobDetail(
  project_id: ID,
  id: ID,
  params?: any,
): Promise<{ data: DatasetJob }> {
  return request(`/v2/projects/${project_id}/dataset_jobs/${id}`, {
    params,
    removeFalsy: true,
    snake_case: true,
  });
}

export function fetchDatasetJobStageList(
  project_id: ID,
  job_id: ID,
  params = {},
): Promise<{ data: DatasetJobStage[]; page_meta?: PageMeta }> {
  return request(`/v2/projects/${project_id}/dataset_jobs/${job_id}/dataset_job_stages`, {
    params,
    removeFalsy: true,
    snake_case: true,
  });
}

export function fetchDatasetJobStageById(
  projectId: ID,
  datasetJobId: ID,
  datasetJobStageId: ID,
): Promise<{ data: DatasetJobStage }> {
  return request(
    `/v2/projects/${projectId}/dataset_jobs/${datasetJobId}/dataset_job_stages/${datasetJobStageId}`,
  );
}

export function stopDatasetJob(project_id: ID, job_id: ID): Promise<DatasetJobStop> {
  return request.post(`/v2/projects/${project_id}/dataset_jobs/${job_id}:stop`);
}

export function deleteDatasetJob(
  project_id: ID,
  job_id: ID,
): Promise<{
  code?: number;
  message?: {
    [job_id: string]: string[];
  };
}> {
  return request.delete(`/v2/projects/${project_id}/dataset_jobs/${job_id}`).catch((error) => {
    // If HTTP response status code is 409, meaning delete fail
    if (error.code === 409) {
      return Promise.resolve(error.extra);
    }
    return Promise.reject(error);
  });
}

export function fetchDatasetLedger(dataset_id: ID): Promise<{ data: DatasetLedger }> {
  return request(`v2/datasets/${dataset_id}/ledger`);
}
