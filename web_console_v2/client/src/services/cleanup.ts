import request from 'libs/request';
import { APIResponse } from 'typings/app';
import { Cleanup, CleanupQueryParams } from 'typings/cleanup';

export function fetchCleanupList(params?: CleanupQueryParams): APIResponse<Cleanup[]> {
  return request(`/v2/cleanups`, { params, snake_case: true });
}

export function fetchCleanupById(cleanup_id?: ID): APIResponse<Cleanup> {
  return request(`/v2/cleanups/${cleanup_id}`);
}

export function postCleanupState(cleanup_id?: ID): APIResponse<Cleanup> {
  return request.post(`/v2/cleanups/${cleanup_id}:cancel`);
}
