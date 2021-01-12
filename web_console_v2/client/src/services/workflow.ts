import { AxiosPromise } from 'axios'
import request from 'libs/request'
import { Workflow, WorkflowTemplate } from 'typings/workflow'

export function fetchWorkflowTemplateList(params?: {
  is_left?: boolean
  group_alias?: string
}): AxiosPromise<{ data: WorkflowTemplate[] }> {
  return request('/v2/workflow_templates', {
    params,
    removeFalsy: true,
  })
}

export function getWorkflowTemplateById(id: number) {
  return request(`/v2/workflow_templates/${id}`)
}

export function createWorkflowTemplate(payload: any) {
  return request.post('/v2/workflow_templates', payload)
}

export function fetchWorkflowList(params?: { project?: string; keyword?: string }) {
  return request('/v2/workflows', {
    params,
    removeFalsy: true,
  })
}

export function getPeerWorkflowConfig() {
  return request('/v2/workflows/id/peer_workflows')
}

export function getWorkflowDetailById(id: string): AxiosPromise<Workflow> {
  return request(`/v2/workflows/${id}`)
}

export function createWorkflow(payload: any) {
  return request.post('/v2/workflows', payload)
}

export function acceptNFillTheWorkflowConfig(id: number) {
  return request.put(`/v2/workflows/${id}`)
}

export function peerConfirmToStart(id: number) {
  return request.put(`/v2/workflows/update/${id}`)
}

export function deteleWorkflowById(id: number) {
  return request.delete(`/v2/workflows/${id}`)
}

export function forkWorkflok(payload: any) {
  return request.post(`/v2/workflows/fork`, payload)
}

export function peerConfirmFork(id: number) {
  return request.post(`/v2/workflows/fork/${id}`)
}
