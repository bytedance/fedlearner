import request from 'libs/request';
import {
  DataBatchImportPayload,
  Dataset,
  DatasetCreatePayload,
  FileToImport,
} from 'typings/dataset';

export function fetchDatasetList(params?: {
  keyword?: string;
  project?: number;
}): Promise<{ data: Dataset[] }> {
  return request('/v2/datasets', { params, removeFalsy: true, snake_case: true });
}

export function createDataset(payload: DatasetCreatePayload) {
  return request.post('/v2/datasets', payload);
}

export function startToImportDataBatch(id: ID, payload: DataBatchImportPayload) {
  return request.post(`/v2/datasets/${id}/batches`, payload);
}

export function fetchFileList(params?: { directory?: string }): Promise<{ data: FileToImport[] }> {
  return request('/v2/files', { params, removeFalsy: true, snake_case: true });
}

export function deleteDataset(id: ID) {
  return request.delete(`/v2/datasets/${id}`);
}
