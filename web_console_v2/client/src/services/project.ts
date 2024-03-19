import request from 'libs/request';
import { APIResponse } from 'typings/app';
import {
  CreateProjectPayload,
  Project,
  UpdateProjectPayload,
  FetchPendingProjectsPayload,
  CreatePendingProjectPayload,
} from 'typings/project';

export function fetchProjectList(): Promise<{ data: Project[] }> {
  return request('/v2/projects', {
    singleton: Symbol('fetchProjectList'),
  });
}
export function createProject(data: CreateProjectPayload): Promise<Project> {
  return request.post('/v2/projects', data);
}

export function getProjectDetailById(id: ID): Promise<{ data: Project }> {
  return request(`/v2/projects/${id}`);
}

export function updateProject(id: ID, data: UpdateProjectPayload): Promise<Project> {
  return request.patch(`/v2/projects/${id}`, data);
}

export function deleteProject(id: ID): Promise<APIResponse> {
  return request.delete(`/v2/projects/${id}`);
}

export function checkConnection(id: ID): Promise<{ data: { success: boolean } }> {
  return request(`/v2/projects/${id}/connection_checks`);
}

export function fetchPendingProjectList(
  params?: FetchPendingProjectsPayload,
): Promise<{ data: Project[] }> {
  return request('/v2/pending_projects', { params });
}

export function createPendingProject(data: CreatePendingProjectPayload): Promise<Project> {
  return request.post('/v2/pending_projects', data);
}

export function getPendingProjectDetailById(id: ID): Promise<{ data: Project }> {
  return request(`/v2/pending_projects/${id}`);
}
// todo: support edit pendingProject
export function updatePendingProject(id: ID, data: UpdateProjectPayload): Promise<Project> {
  return request.patch(`/v2/pending_projects/${id}`, data);
}

export function authorizePendingProject(id: ID, params: { state: string }) {
  return request.patch(`/v2/pending_project/${id}`, params);
}

export function deletePendingProject(id: ID): Promise<APIResponse> {
  return request.delete(`/v2/pending_project/${id}`);
}
