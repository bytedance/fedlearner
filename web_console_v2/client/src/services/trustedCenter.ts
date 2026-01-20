import request from 'libs/request';
import { APIResponse } from 'typings/app';
import {
  AuthStatus,
  NotificationItem,
  TrustedJob,
  TrustedJobGroup,
  TrustedJobGroupItem,
  TrustedJobGroupPayload,
  TrustedJobListItem,
  TrustedJobParamType,
} from 'typings/trustedCenter';

export function fetchTrustedJobGroupList(
  projectId: ID,
  params?: {
    filter?: string;
    page?: number;
    pageSize?: number;
  },
): APIResponse<TrustedJobGroupItem[]> {
  return request(`/v2/projects/${projectId}/trusted_job_groups`, { params });
}

export function fetchTrustedJobGroupById(
  projectId: ID,
  id: ID,
): Promise<{ data: TrustedJobGroup }> {
  return request(`/v2/projects/${projectId}/trusted_job_groups/${id}`);
}

export function createTrustedJobGroup(projectId: ID, payload: TrustedJobGroupPayload) {
  return request.post(`/v2/projects/${projectId}/trusted_job_groups`, payload);
}

export function updateTrustedJobGroup(projectId: ID, id: ID, payload: TrustedJobGroupPayload) {
  return request.put(`/v2/projects/${projectId}/trusted_job_groups/${id}`, payload);
}

export function deleteTrustedJobGroup(projectId: ID, id: ID) {
  return request.delete(`/v2/projects/${projectId}/trusted_job_groups/${id}`);
}

export function launchTrustedJobGroup(projectId: ID, id: ID, payload: { comment: string }) {
  return request.post(`/v2/projects/${projectId}/trusted_job_groups/${id}:launch`, payload);
}

export function fetchTrustedJobList(
  projectId: ID,
  params: {
    trusted_job_group_id: ID;
    type?: TrustedJobParamType;
  },
): APIResponse<TrustedJobListItem[]> {
  return request(`/v2/projects/${projectId}/trusted_jobs`, { params });
}

export function fetchTrustedJob(projectId: ID, id: ID): Promise<{ data: TrustedJob }> {
  return request(`/v2/projects/${projectId}/trusted_jobs/${id}`);
}

export function updateTrustedJob(
  projectId: ID,
  id: ID,
  payload: { comment: string; auth_status?: AuthStatus },
) {
  return request.put(`/v2/projects/${projectId}/trusted_jobs/${id}`, payload);
}

export function exportTrustedJobResult(projectId: ID, id: ID) {
  return request.post(`/v2/projects/${projectId}/trusted_jobs/${id}:export`);
}

export function stopTrustedJob(projectId: ID, id: ID) {
  return request.post(`/v2/projects/${projectId}/trusted_jobs/${id}:stop`);
}

export function fetchTrustedNotifications(projectId: ID): APIResponse<NotificationItem[]> {
  return request(`/v2/projects/${projectId}/trusted_notifications`);
}
