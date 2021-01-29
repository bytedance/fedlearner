import request from 'libs/request';
import { CreateProjectPayload, Project, UpdateProjectPayload } from 'typings/project';

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

export function checkConnection(id: ID): Promise<{ data: { success: boolean } }> {
  return request.post(`/v2/projects/${id}/connection_checks`);
}
