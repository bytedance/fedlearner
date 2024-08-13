import request, { BASE_URL } from 'libs/request';
import { APIResponse } from 'typings/app';
import {
  FileTreeNode,
  FileContent,
  FileQueryParams,
  UploadFileQueryParams,
  UpdateFileQueryParams,
  RenameFileQueryParams,
  DeleteFileQueryParams,
  AlgorithmProject,
  Algorithm,
} from 'typings/algorithm';

export function fetchAlgorithmProjectFileTreeList(id: ID): APIResponse<FileTreeNode[]> {
  return request.get(`/v2/algorithm_projects/${id}/tree`).then((resp) => {
    // 204 No Content
    if (!resp) {
      return {
        data: [],
      };
    }
    return resp;
  });
}
export function fetchAlgorithmProjectFileContentDetail(
  id: ID,
  params: FileQueryParams,
): APIResponse<FileContent> {
  return request.get(`/v2/algorithm_projects/${id}/files`, {
    params,
  });
}

export function uploadAlgorithmProjectFileContent(
  id: ID,
  payload: UploadFileQueryParams,
): APIResponse<Omit<FileContent, 'content'>> {
  const formData = new FormData();

  Object.keys(payload).forEach((key) => {
    const value = (payload as any)[key];
    formData.append(key, value);
  });

  return request.post(`/v2/algorithm_projects/${id}/files`, formData);
}
export function createOrUpdateAlgorithmProjectFileContent(
  id: ID,
  payload: UpdateFileQueryParams,
): APIResponse<FileContent> {
  const formData = new FormData();

  Object.keys(payload).forEach((key) => {
    const value = (payload as any)[key];
    formData.append(key, value);
  });

  return request.put(`/v2/algorithm_projects/${id}/files`, formData);
}
export function renameAlgorithmProjectFileContent(
  id: ID,
  payload: RenameFileQueryParams,
): Promise<null> {
  return request.patch(`/v2/algorithm_projects/${id}/files`, payload);
}
export function deleteAlgorithmProjectFileContent(
  id: ID,
  params: DeleteFileQueryParams,
): Promise<null> {
  return request.delete(`/v2/algorithm_projects/${id}/files`, {
    params,
  });
}

export function fetchAlgorithmFileTreeList(id?: ID): APIResponse<FileTreeNode[]> {
  return request.get(`/v2/algorithms/${id}/tree`).then((resp) => {
    // 204 No Content
    if (!resp) {
      return {
        data: [],
      };
    }
    return resp;
  });
}

export function fetchAlgorithmFileContentDetail(
  id: ID,
  params: FileQueryParams,
): APIResponse<FileContent> {
  return request.get(`/v2/algorithms/${id}/files`, {
    params,
  });
}

export function fetchPendingAlgorithmFileTreeList(
  projId?: ID,
  id?: ID,
): APIResponse<FileTreeNode[]> {
  return request.get(`/v2/projects/${projId}/pending_algorithms/${id}/tree`).then((resp) => {
    // 204 No Content
    if (!resp) {
      return {
        data: [],
      };
    }
    return resp;
  });
}

export function fetchPendingAlgorithmFileContentDetail(
  projId?: ID,
  id?: ID,
  params?: FileQueryParams,
): APIResponse<FileContent> {
  return request.get(`/v2/projects/${projId}/pending_algorithms/${id}/files`, {
    params,
  });
}

export function fetchProjectList(
  projectId?: ID,
  params?: Record<string, any> | string,
): APIResponse<AlgorithmProject[]> {
  if (!projectId && projectId !== 0) {
    return Promise.reject(new Error('请选择工作区'));
  }
  return request.get(`/v2/projects/${projectId}/algorithm_projects`, {
    params,
    removeFalsy: true,
    snake_case: true,
  });
}

// 拉取对侧发送过来的算法列表
export function fetchProjectPendingList(projectId?: ID): APIResponse<Algorithm[]> {
  if (!projectId && projectId !== 0) {
    return Promise.reject(new Error('请选择工作区'));
  }
  return request.get(`/v2/projects/${projectId}/pending_algorithms`);
}

export function createProject(
  platformProjId: ID,
  payload: FormData,
): APIResponse<AlgorithmProject> {
  return request.post(`/v2/projects/${platformProjId}/algorithm_projects`, payload);
}

export function patchProject(
  projectId: ID,
  payload: Partial<AlgorithmProject>,
): APIResponse<AlgorithmProject> {
  return request.patch(`/v2/algorithm_projects/${projectId}`, payload);
}

export function fetchProjectDetail(id: ID): APIResponse<AlgorithmProject> {
  return request.get(`/v2/algorithm_projects/${id}`);
}

export function getAlgorithmDetail(id: ID): APIResponse<Algorithm> {
  return request.get(`/v2/algorithms/${id}`);
}

export function postPublishAlgorithm(id: ID, comment?: string): APIResponse<AlgorithmProject> {
  return request.post(`/v2/algorithm_projects/${id}:publish`, { comment });
}

export function postSendAlgorithm(id: ID, comment?: string): APIResponse<AlgorithmProject> {
  return request.post(`/v2/algorithms/${id}:send`, {
    comment,
  });
}

export function postAcceptAlgorithm(
  projectId: ID,
  algorithmProjId: ID,
  payload: {
    name: string;
    comment?: string;
  },
) {
  return request.post(
    `/v2/projects/${projectId}/pending_algorithms/${algorithmProjId}:accept`,
    payload,
  );
}

export function fetchAlgorithmList(
  project_id?: ID,
  params?: { algo_project_id: ID },
): APIResponse<Algorithm[]> {
  return request.get(`/v2/projects/${project_id}/algorithms`, { params });
}

export function deleteAlgorithm(id: ID) {
  return request.delete(`/v2/algorithms/${id}`);
}

export function deleteAlgorithmProject(id: ID) {
  return request.delete(`/v2/algorithm_projects/${id}`);
}

export function getFullAlgorithmProjectDownloadHref(algorithmProjectId: ID): string {
  return `${window.location.origin}${BASE_URL}/v2/algorithm_projects/${algorithmProjectId}?download=true`;
}
export function getFullAlgorithmDownloadHref(algorithmId: ID): string {
  return `${window.location.origin}${BASE_URL}/v2/algorithms/${algorithmId}?download=true`;
}

export function updatePresetAlgorithm(payload?: any): APIResponse<AlgorithmProject[]> {
  return request.post(`/v2/preset_algorithms:update`, payload);
}

export function releaseAlgorithmProject(
  projectId?: ID,
  algorithmId?: ID,
  params?: { comment: string },
): Promise<null> {
  return request.post(`/v2/projects/${projectId}/algorithms/${algorithmId}:release`, { params });
}

export function publishAlgorithm(
  projectId?: ID,
  algorithmId?: ID,
  params?: { comment: string },
): Promise<null> {
  return request.post(`/v2/projects/${projectId}/algorithms/${algorithmId}:publish`, { params });
}

export function unpublishAlgorithm(projectId?: ID, algorithmId?: ID): Promise<null> {
  return request.post(`/v2/projects/${projectId}/algorithms/${algorithmId}:unpublish`);
}

export function fetchPeerAlgorithmProjectList(
  projectId?: ID,
  participantId?: ID,
  params?: Record<string, any> | string,
): APIResponse<AlgorithmProject[]> {
  return request.get(`/v2/projects/${projectId}/participants/${participantId}/algorithm_projects`, {
    params,
    removeFalsy: true,
    snake_case: true,
  });
}

export function fetchPeerAlgorithmProjectById(
  projectId?: ID,
  participantId?: ID,
  algorithm_project_uuid?: ID,
): APIResponse<AlgorithmProject> {
  return request.get(
    `/v2/projects/${projectId}/participants/${participantId}/algorithm_projects/${algorithm_project_uuid}`,
  );
}

export function fetchPeerAlgorithmList(
  projectId?: ID,
  participantId?: ID,
  params?: { algorithm_project_uuid: ID },
): APIResponse<Algorithm[]> {
  return request.get(`/v2/projects/${projectId}/participants/${participantId}/algorithms`, {
    params,
  });
}

export function fetchPeerAlgorithmDetail(
  projectId?: ID,
  participantId?: ID,
  uuid?: ID,
): APIResponse<Algorithm> {
  return request.get(`/v2/projects/${projectId}/participants/${participantId}/algorithms/${uuid}`);
}

export function fetchPeerAlgorithmFileTreeList(
  projectId?: ID,
  participantId?: ID,
  uuid?: ID,
): APIResponse<FileTreeNode[]> {
  return request
    .get(`/v2/projects/${projectId}/participants/${participantId}/algorithms/${uuid}/tree`)
    .then((resp) => {
      // 204 No Content
      if (!resp) {
        return {
          data: [],
        };
      }
      return resp;
    });
}

export function fetchPeerAlgorithmProjectFileContentDetail(
  projectId?: ID,
  participantId?: ID,
  uuid?: ID,
  params?: FileQueryParams,
): APIResponse<FileContent> {
  return request.get(
    `/v2/projects/${projectId}/participants/${participantId}/algorithms/${uuid}/files`,
    { params },
  );
}

export function fetchAlgorithmByUuid(projectId: ID, algorithmUuid: ID): APIResponse<Algorithm> {
  return request.get(`/v2/projects/${projectId}/algorithms/${algorithmUuid}`);
}
