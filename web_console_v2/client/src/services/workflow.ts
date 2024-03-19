import { KibanaQueryParams, KiabanaMetrics } from './../typings/kibana';
import request from 'libs/request';
import { APIResponse } from 'typings/app';
import {
  WorkflowForkPayload,
  WorkflowInitiatePayload,
  WorkflowTemplate,
  WorkflowAcceptPayload,
  Workflow,
  WorkflowExecutionDetails,
  WorkflowTemplatePayload,
  WorkflowStateFilterParamType,
  TemplateRevision,
  RevisionDetail,
  RevisionPayload,
} from 'typings/workflow';
import { JobExecutionDetalis } from '../typings/job';
import { JobNodeRawData } from 'components/WorkflowJobsCanvas/types';
import { Job } from 'typings/job';

const specialProjectId = 0;

export function fetchWorkflowTemplateList(params?: {
  page?: number;
  pageSize?: number;
  filter?: string;
}): APIResponse<WorkflowTemplate[]> {
  return request('/v2/workflow_templates', {
    params,
    removeFalsy: true,
    snake_case: true,
  });
}

export function fetchDataJoinTemplates(): Promise<{ data: WorkflowTemplate[] }> {
  return request('/v2/workflow_templates?from=preset_datajoin');
}

export function fetchTemplateById(id: ID): Promise<{ data: WorkflowTemplate }> {
  return request(`/v2/workflow_templates/${id}`);
}

export function fetchRevisionList(id: ID): APIResponse<TemplateRevision[]> {
  return request(`/v2/workflow_templates/${id}/workflow_template_revisions`);
}

export function patchRevisionComment(id: ID, payload: RevisionPayload) {
  return request.patch(`/v2/workflow_template_revisions/${id}`, payload);
}

export function fetchWorkflowListByRevisionId(
  project: ID,
  params?: {
    template_revision_id?: number;
  },
): APIResponse<Workflow[]> {
  return request(`/v2/projects/${project}/workflows`, {
    params,
  });
}

export function fetchRevisionDetail(revision_id: ID): Promise<{ data: RevisionDetail }> {
  return request(`/v2/workflow_template_revisions/${revision_id}`);
}

export function deleteRevision(revision_id: ID) {
  return request.delete(`/v2/workflow_template_revisions/${revision_id}`);
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

export function createTemplateRevision(id: ID) {
  return request.post(`/v2/workflow_templates/${id}:create_revision`);
}

export function deleteTemplate(id: ID) {
  return request.delete(`/v2/workflow_templates/${id}`);
}

export function fetchWorkflowList(params?: {
  project?: ID;
  keyword?: string;
  states?: WorkflowStateFilterParamType[];
  state?: 'prepare';
  name?: string;
  uuid?: ID;
  page?: number;
  pageSize?: number;
  filter?: string;
}): APIResponse<Workflow[]> {
  return request(`/v2/projects/${params?.project ?? specialProjectId}/workflows`, {
    params,
    removeFalsy: true,
    snake_case: true,
  });
}

export const PEER_WORKFLOW_DETAIL_QUERY_KEY = 'getPeerWorkflow';
export function getPeerWorkflowsConfig(
  id: ID,
  projectId?: ID,
): Promise<{ data: Record<string, WorkflowExecutionDetails> }> {
  return request(`/v2/projects/${projectId ?? specialProjectId}/workflows/${id}/peer_workflows`);
}
export async function getPeerWorkflow(id: ID, projectId?: ID) {
  const res = await getPeerWorkflowsConfig(id, projectId);
  const anyPeerWorkflow = Object.values(res.data).find((item) => !!item.uuid)!;

  return anyPeerWorkflow;
}

export function getWorkflowDetailById(
  id: ID,
  projectId?: ID,
): Promise<{ data: WorkflowExecutionDetails }> {
  return request(`/v2/projects/${projectId ?? specialProjectId}/workflows/${id}`);
}
export function getWorkflowDownloadHref(id: ID, projectId?: ID): string {
  return `/v2/projects/${projectId ?? specialProjectId}/workflows/${id}?download=true`;
}

export function initiateAWorkflow(
  payload: WorkflowInitiatePayload<Job | JobNodeRawData>,
  projectId: ID,
): any {
  return request.post(`/v2/projects/${projectId}/workflows`, payload);
}

export function acceptNFillTheWorkflowConfig(
  id: ID,
  payload: WorkflowAcceptPayload<any>,
  projectId: ID,
) {
  return request.put(`/v2/projects/${projectId}/workflows/${id}`, payload);
}

export function patchWorkflow(id: ID, payload: Partial<Workflow>, projectId: ID) {
  return request.patch(`/v2/projects/${projectId}/workflows/${id}`, payload);
}

export function runTheWorkflow(id: ID, projectId: ID) {
  return request.post(`/v2/projects/${projectId}/workflows/${id}:start`);
}

export function stopTheWorkflow(id: ID, projectId: ID) {
  return request.post(`/v2/projects/${projectId}/workflows/${id}:stop`);
}

export function invalidTheWorkflow(id: ID, projectId: ID) {
  return request.post(`/v2/projects/${projectId}/workflows/${id}:invalidate`);
}

export function forkTheWorkflow(payload: WorkflowForkPayload, projectId: ID) {
  return request.post(`/v2/projects/${projectId}/workflows`, payload);
}

export function favourTheWorkFlow(projectId: ID, workflowId: ID, favour: boolean) {
  return request.patch(`/v2/projects/${projectId}/workflows/${workflowId}`, {
    favour: favour ? 1 : 0,
  });
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
  participantId: ID,
  params?: { startTime?: DateTime; maxLines: number },
): Promise<{ data: string[] }> {
  return request(
    `/v2/workflows/${workflowUuid}/peer_workflows/${participantId}/jobs/${k8sJobName}/events`,
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

export function fetchJobById(id: ID | undefined): Promise<{ data: JobExecutionDetalis }> {
  return request(`/v2/jobs/${id}`);
}

export function toggleWofklowForkable(id: ID, forkable: boolean, projectId: ID) {
  return request.patch(`/v2/projects/${projectId}/workflows/${id}`, {
    forkable,
  });
}

export function toggleMetricsPublic(id: ID, metric_is_public: boolean, projectId: ID) {
  return request.patch(`/v2/projects/${projectId}/workflows/${id}`, {
    metric_is_public,
  });
}

export function fetchJobMpld3Metrics(id: ID): Promise<{ data: any[] }> {
  return request(`/v2/jobs/${id}/metrics`);
}

export function fetchPeerJobMpld3Metrics(
  workflowUuid: string,
  jobName: string,
  participantId: ID,
): Promise<{ data: any[] }> {
  return request(
    `/v2/workflows/${workflowUuid}/peer_workflows/${participantId}/jobs/${jobName}/metrics`,
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
  participantId: ID,
  params: KibanaQueryParams,
): Promise<{ data: KiabanaMetrics }> {
  return request(
    `/v2/workflows/${workflowUuid}/peer_workflows/${participantId}/jobs/${k8sJobName}/kibana_metrics`,
    {
      params,
    },
  );
}

export function patchPeerWorkflow(id: ID, payload: Omit<Workflow, 'config'>, projectId: ID) {
  return request.patch(`/v2/projects/${projectId}/workflows/${id}/peer_workflows`, payload);
}

export function getTemplateRevisionDownloadHref(revision_id?: ID): string {
  return `/v2/workflow_template_revisions/${revision_id}?download=true`;
}

export function sendTemplateRevision(revision_id: ID, participant_id: ID) {
  return request.post(
    `/v2/workflow_template_revisions/${revision_id}:send?participant_id=${participant_id}`,
  );
}
