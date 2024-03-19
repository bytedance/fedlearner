import request from 'libs/request';
import { APIResponse } from 'typings/app';
import { JobInfo, JobGroupFetchPayload, JobItem, Dashboard } from 'typings/operation';
import { DatasetForceState } from '../typings/dataset';

export function fetchOperationList(payload: Partial<JobGroupFetchPayload>): APIResponse<JobItem[]> {
  return request.post('/v2/e2e_jobs:initiate', payload);
}

export function fetchOperationDetail(params?: { job_name: string }): Promise<{ data: JobInfo }> {
  return request(`/v2/e2e_jobs/${params?.job_name}`);
}

export function fetchDashboardList(): Promise<{ data: Dashboard[] }> {
  return request('/v2/dashboards');
}

export function datasetFix(params: {
  datasetId: ID;
  force?: DatasetForceState;
}): Promise<{ data: any }> {
  const { datasetId, force } = params;
  return request.post(`v2/datasets/${datasetId}:state_fix`, {
    force,
  });
}
