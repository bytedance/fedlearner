import { AxiosPromise } from 'axios';
import request from 'libs/request';
import {
  Workflow,
  WorkflowInitiatePayload,
  WorkflowTemplate,
  WorkflowAcceptPayload,
} from 'typings/workflow';

export function fetchWorkflowTemplateList(params?: {
  isLeft?: boolean;
  groupAlias?: string;
}): AxiosPromise<{ data: WorkflowTemplate[] }> {
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

export function fetchWorkflowList(params?: { project?: string; keyword?: string }) {
  return request('/v2/workflows', {
    params,
    removeFalsy: true,
  });
}

export function getPeerWorkflowsConfig(
  id: string | number,
): AxiosPromise<{ data: Record<string, Workflow> }> {
  return request(`/v2/workflows/${id}/peer_workflows`);
}

export function getWorkflowDetailById(id: string | number): AxiosPromise<{ data: Workflow }> {
  return request(`/v2/workflows/${id}`);
}

export function initiateAWorkflow(payload: WorkflowInitiatePayload) {
  return request.post('/v2/workflows', payload);
}

export function acceptNFillTheWorkflowConfig(id: number | string, payload: WorkflowAcceptPayload) {
  return request.put(`/v2/workflows/${id}`, payload);
}

export function peerConfirmToStart(id: number) {
  return request.put(`/v2/workflows/update/${id}`);
}

export function deteleWorkflowById(id: number) {
  return request.delete(`/v2/workflows/${id}`);
}

export function forkWorkflok(payload: any) {
  return request.post(`/v2/workflows/fork`, payload);
}

export function peerConfirmFork(id: number) {
  return request.post(`/v2/workflows/fork/${id}`);
}
