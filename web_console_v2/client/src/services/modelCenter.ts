import request, { BASE_URL } from 'libs/request';
import { APIResponse } from 'typings/app';
import {
  ModelJob,
  ModelSet,
  ModelSetCreatePayload,
  ModelSetUpdatePayload,
  Algorithm,
  AlgorithmChangeLog,
  FakeAlgorithm,
  Model,
  ModelJobQueryParams,
  ModelJobType,
  ModelJobGroup,
  ModelJobGroupCreatePayload,
  ModelJobGroupUpdatePayload,
  ModelJobMetrics,
  ModelJobPatchFormData,
  PeerModelJobGroupUpdatePayload,
  ModelJobQueryParams_new,
  ModelJobDefinitionQueryParams,
  ModelJobDefinitionResult,
  ModelJobTrainCreateForm,
  ModelJobGroupCreateForm,
} from 'typings/modelCenter';
import { formatExtra } from 'shared/modelCenter';

export function fetchModelSetList(params?: { keyword?: string }): Promise<{ data: ModelSet[] }> {
  return request('/v2/model_groups', { params, removeFalsy: true, snake_case: true });
}
export function createModelSet(payload: ModelSetCreatePayload): Promise<{ data: ModelSet }> {
  return request.post('/v2/model_groups', payload);
}
export function updateModelSet(
  id: ID,
  payload: ModelSetUpdatePayload,
): Promise<{ data: ModelSet }> {
  return request.patch(`/v2/model_groups/${id}`, payload);
}
export function deleteModelSet(id: ID) {
  return request.delete(`/v2/model_groups/${id}`);
}

export function fetchModelList(
  project_id: ID,
  params?: {
    group_id?: ID;
    algorithm_type?: 'NN_HORIZONTAL' | 'TREE_VERTICAL' | 'NN_VERTICAL';
    keyword?: string;
  },
): Promise<{ data: Model[] }> {
  return request(`/v2/projects/${project_id}/models`, {
    params,
    removeFalsy: true,
    snake_case: true,
  });
}

export function fetchModelDetail_new(project_id: ID, model_id: ID): Promise<{ data: Model }> {
  return request(`/v2/projects/${project_id}/models/${model_id}`);
}

export function updateModel(project_id: ID, id: ID, payload: Partial<Model>) {
  return request.patch(`/v2/projects/${project_id}/models/${id}`, payload);
}
export function deleteModel(project_id: ID, id: ID) {
  return request.delete(`/v2/projects/${project_id}/models/${id}`);
}

export function fetchModelJobList(params?: {
  project_id?: ID;
  group_id?: ID;
  types?: ModelJobType[];
}): Promise<{ data: ModelJob[] }> {
  return request('/v2/model_jobs', { params, removeFalsy: true, snake_case: true });
}
export function fetchModelJobDetail(id: ID, params?: any): Promise<{ data: ModelJob }> {
  return request(`/v2/model_jobs/${id}`, { params });
}
export function updateModelJob(projectId: ID, id: ID, payload: Partial<ModelJob>) {
  return request.patch(`/v2/projects/${projectId}/model_jobs/${id}`, payload);
}
export function deleteModelJob(id: ID) {
  return request.delete(`/v2/model_jobs/${id}`);
}
export function stopModelJob(projectId: ID, modelJobId: ID) {
  return request.post(`/v2/projects/${projectId}/model_jobs/${modelJobId}:stop`);
}

export function fetchFavouriteModelList(params?: {}): Promise<{ data: ModelJob[] }> {
  return request('/v2/models/favourite', { params, removeFalsy: true, snake_case: true });
}

export function fetchEvaluationList(params?: ModelJobQueryParams): Promise<{ data: ModelJob[] }> {
  const types: ModelJobType[] = ['TREE_EVALUATION', 'NN_EVALUATION', 'EVALUATION'];

  return request('/v2/model_jobs', {
    params: {
      ...params,
      types,
    },
    removeFalsy: true,
    snake_case: true,
  }).then((resp) => {
    resp.data = resp.data.map((item: ModelJob) => {
      item.workflow = formatExtra(item.workflow);
      return formatExtra(item);
    });
    return resp;
  });
}

export function fetchCompareModelReportList(params?: {}): Promise<{ data: ModelSet[] }> {
  return request('/v2/model_groups', { params, removeFalsy: true, snake_case: true }).then(
    (resp) => {
      resp.data = resp.data.map((item: ModelSet) => {
        return formatExtra(item);
      });
      return resp;
    },
  );
}
export function fetchCompareModelReportDetail(id: ID) {
  return request(`/v2/model_groups/${id}`);
}

export function fetchOfflinePredictionList(
  params?: ModelJobQueryParams,
): Promise<{ data: ModelJob[] }> {
  const types: ModelJobType[] = ['TREE_PREDICTION', 'NN_PREDICTION', 'PREDICTION'];

  return request('/v2/model_jobs', {
    params: {
      ...params,
      types,
    },
    removeFalsy: true,
    snake_case: true,
  }).then((resp) => {
    resp.data = resp.data.map((item: ModelJob) => {
      item.workflow = formatExtra(item.workflow);
      return formatExtra(item);
    });
    return resp;
  });
}

export function fetchMyAlgorithm(params?: { keyword?: string }): Promise<{ data: Algorithm[] }> {
  return request('/v2/algorithm', { params, removeFalsy: true, snake_case: true });
}
export function fetchFakeAlgorithmList(params?: {
  keyword?: string;
}): Promise<{ data: FakeAlgorithm[] }> {
  return request('/v2/fake_algorithms', { params, removeFalsy: true, snake_case: true });
}
export function fetchBuiltInAlgorithm(params?: {
  keyword?: string;
}): Promise<{ data: Algorithm[] }> {
  return request('/v2/algorithm/built-in', { params, removeFalsy: true, snake_case: true });
}
export function fetchMyAlgorithmDetail(id: ID, params?: any): Promise<{ data: Algorithm }> {
  return request(`/v2/algorithm/${id}`, { params });
}

export function fetchAlgorithmChangeLog(
  id: ID,
  params?: any,
): Promise<{ data: AlgorithmChangeLog[] }> {
  return request(`/v2/algorithm/change_log/${id}`, { params });
}

export function getModelJobDownloadHref(projectId: ID, modelJobId: ID): string {
  return `/v2/projects/${projectId}/model_jobs/${modelJobId}/results`;
}
export function getFullModelJobDownloadHref(projectId: ID, modelJobId: ID): string {
  return `${window.location.origin}${BASE_URL}/v2/projects/${projectId}/model_jobs/${modelJobId}/results`;
}

export function fetchModelJobGroupList(
  projectId: ID,
  params?: {
    keyword?: string;
    page?: number;
    pageSize?: number;
    filter?: string;
    configured?: boolean;
  },
): APIResponse<ModelJobGroup[]> {
  return request(`/v2/projects/${projectId}/model_job_groups`, {
    params,
    removeFalsy: true,
    snake_case: true,
  });
}
export function fetchModelJobGroupDetail(
  projectId: ID,
  modelJobGroupId: ID,
): Promise<{ data: ModelJobGroup }> {
  return request(`/v2/projects/${projectId}/model_job_groups/${modelJobGroupId}`);
}
export function fetchPeerModelJobGroupDetail(
  projectId: ID,
  modelJobGroupId: ID,
  participantId: ID,
): Promise<{ data: ModelJobGroup }> {
  return request(
    `/v2/projects/${projectId}/model_job_groups/${modelJobGroupId}/peers/${participantId}`,
  );
}

export function createModelJobGroup(
  projectId: ID,
  payload: ModelJobGroupCreatePayload,
): Promise<{ data: ModelJobGroup }> {
  return request.post(`/v2/projects/${projectId}/model_job_groups`, payload);
}

export function updateModelJobGroup(
  projectId: ID,
  modelJobGroupId: ID,
  payload: ModelJobGroupUpdatePayload,
): Promise<{ data: ModelJobGroup }> {
  return request.put(`/v2/projects/${projectId}/model_job_groups/${modelJobGroupId}`, payload);
}

export function deleteModelJobGroup(
  projectId: ID,
  modelJobGroupId: ID,
  payload?: any,
): Promise<{ data: ModelJobGroup }> {
  return request.delete(`/v2/projects/${projectId}/model_job_groups/${modelJobGroupId}`, payload);
}

export function updatePeerModelJobGroup(
  projectId: ID,
  modelJobGroupId: ID,
  participantId: ID,
  payload: PeerModelJobGroupUpdatePayload,
): Promise<{ data: ModelJobGroup }> {
  return request.patch(
    `/v2/projects/${projectId}/model_job_groups/${modelJobGroupId}/peers/${participantId}`,
    payload,
  );
}

export function launchModelJobGroup(
  projectId: ID,
  modelJobGroupId: ID,
  payload: any = {}, // For auto set request header 'Content-Type': 'application/json'
): Promise<{ data: ModelJobGroup }> {
  return request.post(
    `/v2/projects/${projectId}/model_job_groups/${modelJobGroupId}:launch`,
    payload,
  );
}

export function authorizeModelJobGroup(
  projectId: ID,
  modelJobGroupId: ID,
  authorized: boolean,
): Promise<any> {
  return request.put(`/v2/projects/${projectId}/model_job_groups/${modelJobGroupId}`, {
    authorized,
  });
}

export function fetchModelJobDefinition(
  params: ModelJobDefinitionQueryParams,
): Promise<{ data: ModelJobDefinitionResult }> {
  return request(`/v2/model_job_definitions`, { params });
}

/**
 *
 * new service functions
 *
 */

export function fetchModelJobList_new(
  project_id: ID,
  params: ModelJobQueryParams_new,
): APIResponse<ModelJob[]> {
  return request(`/v2/projects/${project_id}/model_jobs`, { params });
}

export function fetchModelJob_new(project_id: ID, job_id: ID): Promise<{ data: ModelJob }> {
  return request(`/v2/projects/${project_id}/model_jobs/${job_id}`);
}

export function fetchModelJobDetail_new(
  project_id: ID,
  model_job_id: ID,
  params?: any,
): Promise<{ data: ModelJob }> {
  return request(`/v2/projects/${project_id}/model_jobs/${model_job_id}`, { params });
}
export function fetchModelJobMetrics_new(
  project_id: ID,
  model_job_id: ID,
  params?: any,
): Promise<{ data: ModelJobMetrics }> {
  return request(`/v2/projects/${project_id}/model_jobs/${model_job_id}/metrics`, { params });
}
export function fetchPeerModelJobDetail_new(
  project_id: ID,
  model_job_id: ID,
  participant_id: ID,
): Promise<{ data: ModelJob }> {
  return request(`/v2/projects/${project_id}/model_jobs/${model_job_id}/peers/${participant_id}`);
}
export function fetchPeerModelJobMetrics_new(
  project_id: ID,
  model_job_id: ID,
  participant_id: ID,
): Promise<{ data: ModelJobMetrics }> {
  return request(
    `/v2/projects/${project_id}/model_jobs/${model_job_id}/peers/${participant_id}/metrics`,
  );
}

export function createModelJob_new(
  project_id: ID,
  data: ModelJobPatchFormData,
): Promise<{ data: ModelJob }> {
  return request.post(`/v2/projects/${project_id}/model_jobs`, data);
}

export function updateModelJob_new(project_id: ID, job_id: ID, data: ModelJobPatchFormData) {
  return request.put(`/v2/projects/${project_id}/model_jobs/${job_id}`, data);
}

export function stopJob_new(project_id: ID, job_id: ID): Promise<any> {
  return request.post(`/v2/projects/${project_id}/model_jobs/${job_id}:stop`);
}

export function deleteJob_new(project_id: ID, job_id: ID): Promise<any> {
  return request.delete(`/v2/projects/${project_id}/model_jobs/${job_id}`);
}

export function fetchModelJobMetries_new(project_id: ID, job_id: ID) {
  return request(`/v2/projects/${project_id}/model_jobs/${job_id}/metrics`);
}

export function fetchModelJobResult_new(project_id: ID, job_id: ID) {
  return request(`/v2/projects/${project_id}/model_jobs/${job_id}/result`);
}

// 中心化

export function createModeJobGroupV2(project_id: ID, data: ModelJobGroupCreateForm) {
  return request.post(`/v2/projects/${project_id}/model_job_groups_v2`, data);
}
export function createModelJob(
  project_id: ID,
  data: ModelJobTrainCreateForm,
): Promise<{ data: ModelJob }> {
  return request.post(`/v2/projects/${project_id}/model_jobs`, data);
}

export function stopAutoUpdateModelJob(project_id: ID, model_group_id: ID) {
  return request.post(
    `/v2/projects/${project_id}/model_job_groups/${model_group_id}:stop_auto_update`,
    {}, // For auto set request header 'Content-Type': 'application/json'
  );
}

export function fetchAutoUpdateModelJobDetail(project_id: ID, model_group_id: ID) {
  return request(
    `/v2/projects/${project_id}/model_job_groups/${model_group_id}/next_auto_update_model_job`,
  );
}
