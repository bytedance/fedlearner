import request from 'libs/request'

export function fetchExampleWorkflowTemplate() {
  return request('/v2/workflows/example')
}

export function fetchWorkflowList() {
  return request('/v2/workflows')
}
