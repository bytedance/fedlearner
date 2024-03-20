import { KibanaQueryParams, KiabanaMetrics } from './../typings/kibana';
import request from 'libs/request';
import {
  WorkflowForkPayload,
  WorkflowInitiatePayload,
  WorkflowTemplate,
  WorkflowAcceptPayload,
  Workflow,
  WorkflowState,
  WorkflowExecutionDetails,
  WorkflowTemplatePayload,
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

export function fetchTemplateById(id: ID): Promise<{ data: WorkflowTemplate }> {
  return request(`/v2/workflow_templates/${id}`);
}

export function getTemplateDownloadHref(id: ID): string {
  return `/v2/workflow_templates/${id}?download=true`;
}

export function createWorkflowTemplate(payload: WorkflowTemplatePayload) {
  return request.post('/v2/workflow_templates', payload);
}

export function updateWorkflowTemplate(id: ID, payload: WorkflowTemplatePayload) {
  return request.put(`/v2/workflow_templates/${id}`, payload);
}

export function deleteTemplate(id: ID) {
  return request.delete(`/v2/workflow_templates/${id}`);
}

export function fetchWorkflowList(params?: {
  project?: ID;
  keyword?: string;
}): Promise<{ data: Workflow[] }> {
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

export function patchWorkflow(id: ID, payload: Partial<Workflow>) {
  return request.patch(`/v2/workflows/${id}`, payload);
}

export function runTheWorkflow(id: ID) {
  return request.patch(`/v2/workflows/${id}`, {
    target_state: WorkflowState.RUNNING,
  });
}

export function stopTheWorkflow(id: ID) {
  return request.patch(`/v2/workflows/${id}`, {
    target_state: WorkflowState.STOPPED,
  });
}

export function invalidTheWorkflow(id: ID) {
  return request.patch(`/v2/workflows/${id}`, {
    state: WorkflowState.INVALID,
  });
}

export function forkTheWorkflow(payload: WorkflowForkPayload) {
  return request.post(`/v2/workflows`, payload);
}

export function fetchJobLogs(
  jobId: ID,
  params?: { startTime?: DateTime; maxLines: number },
): Promise<{ data: string[] }> {
  return request(`/v2/jobs/${jobId}/log`, { params, snake_case: true });
}

/**
 * Q: What's the diff between Logs and Events?
 * A: Events is the summary version of Logs, i.e. Logs includes Events
 */
export function fetchJobEvents(
  jobId: ID,
  params?: { startTime?: DateTime; maxLines: number },
): Promise<{ data: string[] }> {
  return request(`/v2/jobs/${jobId}/events`, { params, snake_case: true });
}

export function fetchPeerJobEvents(
  workflowUuid: string,
  k8sJobName: string,
  params?: { startTime?: DateTime; maxLines: number },
): Promise<{ data: string[] }> {
  return request(
    `/v2/workflows/${workflowUuid}/peer_workflows/${
      0 /** peerId, fix to 0 so far */
    }/jobs/${k8sJobName}/events`,
    {
      params,
      snake_case: true,
    },
  );
}

export function fetchPodLogs(
  podName: string,
  jobId: ID,
  params?: { startTime?: DateTime; maxLines: number },
): Promise<{ data: string[] }> {
  return request(`/v2/jobs/${jobId}/pods/${podName}/log`, { params, snake_case: true });
}

export function toggleWofklowForkable(id: ID, forkable: boolean) {
  return request.patch(`/v2/workflows/${id}`, {
    forkable,
  });
}

export function toggleMetricsPublic(id: ID, metric_is_public: boolean) {
  return request.patch(`/v2/workflows/${id}`, {
    metric_is_public,
  });
}

export function fetchJobMpld3Metrics(id: ID): Promise<{ data: any[] }> {
  return request(`/v2/jobs/${id}/metrics`);
}

export function fetchPeerJobMpld3Metrics(
  workflowUuid: string,
  jobName: string,
): Promise<{ data: any[] }> {
  return request(
    `/v2/workflows/${workflowUuid}/peer_workflows/${
      0 /** peerId, fix to 0 so far */
    }/jobs/${jobName}/metrics`,
  );
}

export function fetchJobEmbedKibanaSrc(
  id: ID,
  params: KibanaQueryParams,
): Promise<{ data: any[] }> {
  return request(`/v2/jobs/${id}/kibana_metrics`, { params });
}

export function fetchPeerKibanaMetrics(
  workflowUuid: string,
  k8sJobName: string,
  params: KibanaQueryParams,
): Promise<{ data: KiabanaMetrics }> {
  return request(
    `/v2/workflows/${workflowUuid}/peer_workflows/${
      0 /** peerId, fix to 0 so far */
    }/jobs/${k8sJobName}/kibana_metrics`,
    {
      params,
    },
  );
}
