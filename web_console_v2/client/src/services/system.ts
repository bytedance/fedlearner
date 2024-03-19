import request from 'libs/request';

export function fetchPodNameList(): Promise<{ data: string[] }> {
  return request('/v2/system_pods/name');
}

export function fetchSystemLogs(tailLines: number, podName: string): Promise<{ data: string[] }> {
  return request(`/v2/system_pods/${podName}/logs`, { params: { tailLines }, snake_case: true });
}

export function fetchSystemVersion(): Promise<{
  data: { version?: string; revision: string; pub_date: string };
}> {
  return request('/v2/versions');
}
