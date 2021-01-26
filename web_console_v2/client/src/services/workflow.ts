import request from 'libs/request';
import {
  WorkflowInitiatePayload,
  WorkflowTemplate,
  WorkflowAcceptPayload,
  WorkflowState,
  WorkflowExecutionDetails,
} from 'typings/workflow';

export function fetchWorkflowTemplateList(params?: {
  isLeft?: boolean;
  groupAlias?: string;
}): Promise<{ data: WorkflowTemplate[] }> {
  return request('/v2/workflow_templates', {
    params,
    removeFalsy: true,
    snake_case: true,
  });
}

export function getWorkflowTemplateById(id: number) {
  return request(`/v2/workflow_templates/${id}`);
}

export function initiateAWorkflowTemplate(payload: any) {
  return request.post('/v2/workflow_templates', payload);
}

export function fetchWorkflowList(params?: { project?: string | number; keyword?: string }) {
  return request('/v2/workflows', {
    params,
    removeFalsy: true,
    snake_case: true,
  });
}

export function getPeerWorkflowsConfig(
  id: string | number,
): Promise<{ data: Record<string, WorkflowExecutionDetails> }> {
  return request(`/v2/workflows/${id}/peer_workflows`);
}

export function getWorkflowDetailById(
  id: string | number,
): Promise<{ data: WorkflowExecutionDetails }> {
  return request(`/v2/workflows/${id}`);
}

export function initiateAWorkflow(payload: WorkflowInitiatePayload) {
  return request.post('/v2/workflows', payload);
}

export function acceptNFillTheWorkflowConfig(id: ID, payload: WorkflowAcceptPayload) {
  return request.put(`/v2/workflows/${id}`, payload);
}

export function runTheWorkflow(id: number) {
  return request.patch(`/v2/workflows/${id}`, {
    target_state: WorkflowState.RUNNING,
  });
}

export function stopTheWorkflow(id: number) {
  return request.patch(`/v2/workflows/${id}`, {
    target_state: WorkflowState.STOPPED,
  });
}

export function forkWorkflow(id: number) {
  return request.post(`/v2/workflows/fork/${id}`);
}

export function fetchPodLogs(jobId: ID, podName: string) {
  return request(`/v2/jobs/${jobId}/pods/${podName}/logs`);
}
