import request from 'libs/request';

import { APIResponse, PageQueryParams } from 'typings/app';

import { ModelServing, ModelServingInstance, ModelServingQueryParams } from 'typings/modelServing';

export function fetchModelServingList(
  params?: ModelServingQueryParams,
): APIResponse<ModelServing[]> {
  return request('/v2/serving_services', { params, removeFalsy: true, snake_case: true });
}
export function fetchModelServingDetail(
  modelServingId: ID,
  params?: ModelServingQueryParams,
): APIResponse<ModelServing> {
  return request(`/v2/serving_services/${modelServingId}`, { params });
}

export function fetchModelServingInstanceList(
  modelServingId: ID,
  params: PageQueryParams,
): APIResponse<ModelServingInstance[]> {
  return request(`/v2/serving_services/${modelServingId}/instances`, {
    params,
    removeFalsy: true,
    snake_case: true,
  });
}

export function fetchModelServingInstanceLog(
  modelServingId: ID,
  instanceName: string,
  params?: { tail_lines: number },
): APIResponse<string[]> {
  return request(`/v2/serving_services/${modelServingId}/instances/${instanceName}/log`, {
    params,
    removeFalsy: true,
    snake_case: true,
  });
}
export function createModelServing(modelId: ID, payload: any): APIResponse<ModelServing> {
  return request.post(`/v2/models/${modelId}/serving_services`, payload);
}
export function updateModelServing(modelServingId: ID, payload: any): APIResponse<ModelServing> {
  return request.patch(`/v2/serving_services/${modelServingId}`, payload);
}
export function deleteModelServing(modelServingId: ID) {
  return request.delete(`/v2/serving_services/${modelServingId}`);
}

/**
 *
 * new service functions
 * old and new service functions will coexist for a period of time
 *
 */

export function fetchModelServingList_new(
  projectId: ID,
  params?: ModelServingQueryParams,
): APIResponse<ModelServing[]> {
  return request(`/v2/projects/${projectId}/serving_services`, {
    params,
    removeFalsy: true,
    snake_case: true,
  });
}

export function fetchModelServingDetail_new(
  projectId: ID,
  modelServingId: ID,
  params?: ModelServingQueryParams,
): APIResponse<ModelServing> {
  return request(`/v2/projects/${projectId}/serving_services/${modelServingId}`, { params });
}

export function createModelServing_new(projectId: ID, payload: any): APIResponse<ModelServing> {
  return request.post(`/v2/projects/${projectId}/serving_services`, payload);
}

export function updateModelServing_new(
  projectId: ID,
  modelServingId: ID,
  payload: any,
): APIResponse<ModelServing> {
  return request.patch(`/v2/projects/${projectId}/serving_services/${modelServingId}`, payload);
}
export function deleteModelServing_new(projectId: ID, modelServingId: ID) {
  return request.delete(`/v2/projects/${projectId}/serving_services/${modelServingId}`);
}

export function fetchModelServingInstanceLog_new(
  projectId: ID,
  modelServingId: ID,
  instanceName: string,
  params?: { tail_lines: number },
): APIResponse<string[]> {
  return request(
    `/v2/projects/${projectId}/serving_services/${modelServingId}/instances/${instanceName}/log`,
    {
      params,
      removeFalsy: true,
      snake_case: true,
    },
  );
}
export function fetchUserTypeInfo(projectId: ID): APIResponse {
  return request(`/v2/projects/${projectId}/serving_services/remote_platforms`);
}
