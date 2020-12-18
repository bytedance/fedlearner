import request from 'libs/request'

export function fetchExampleWorkflowTemplate() {
  return request('/v2/workflows/example')
}

export function fetchWorkflowTemplateList() {
  return request('/v2/workflow_templates')
}

export function getWorkflowTemplateById(id: number) {
  return request(`/v2/workflow_templates/${id}`)
}

export function createWorkflowTemplate(payload: any) {
  return request.post('/v2/workflow_templates', payload)
}

export function fetchWorkflowList() {
  return request('/v2/workflows')
}

export function getWorkflowById(id: number) {
  return request(`/v2/workflows/${id}`)
}

export function createWorkflow(payload: any) {
  return request.post('/v2/workflows', payload)
}

export function sendWorkflowToParticipant(id: number) {
  return request.patch(`/v2/workflows/create/${id}`)
}

export function participantFillTheConfig(id: number) {
  return request.put(`/v2/workflows/update/${id}`)
}

export function participantConfirmToStart(id: number) {
  return request.put(`/v2/workflows/update/${id}`)
}

export function deteleWorkflowById(id: number) {
  return request.delete(`/v2/workflows/${id}`)
}

export function forkWorkflok(payload: any) {
  return request.post(`/v2/workflows/fork`, payload)
}

export function participantConfirmFork(id: number) {
  return request.post(`/v2/workflows/fork/${id}`)
}
