import { atom, selector } from 'recoil'
import { fetchWorkflowTemplateList } from 'services/workflow'
import { WorkflowConfig, WorkflowForm, WorkflowTemplateForm } from 'typings/workflow'

export type StepOneForm = {
  _templateType: 'existed' | 'create'
  _templateSelected?: string
} & Pick<WorkflowForm, 'name' | 'peer_forkable' | 'project_token'>

export type StepOneTemplateForm = {
  _files: File[]
} & WorkflowTemplateForm

export const workflowCreating = atom<StepOneForm>({
  key: 'WorkflowCreating',
  default: {
    // Fields start with underscore are solely UI releated things,
    // will not pass to backend on submit
    _templateType: 'existed',
    _templateSelected: undefined,

    // FIXME: remove mock name and project_token
    name: 'foo',
    project_token: 'bar',
    peer_forkable: true,
  },
})

export const workflowTemplateCreating = atom<StepOneTemplateForm>({
  key: 'WorkflowTemplateCreating',
  default: {
    _files: [],

    name: '',
    template: '',
    comment: '',
  },
})

export const forceReloadTplList = atom({
  key: 'ForceReloadTplList',
  default: 0,
})
export const workflowTemplateListQuery = selector({
  key: 'WorkflowTemplateListQuery',
  get: async ({ get }) => {
    get(forceReloadTplList)
    try {
      const res = await fetchWorkflowTemplateList()
      return res.data.list
    } catch (error) {
      throw error
    }
  },
})

export const currentWorkflowConfig = atom<WorkflowConfig>({
  key: 'CurrentWorkflowConfig',
  default: {
    group_alias: '',
    jobs: [],
    variables: [],
  },
})

export const workflowGetters = selector({
  key: 'WorkflowGetters',
  get: ({ get }) => {
    return {
      whetherCreateNewTpl: get(workflowCreating)._templateType === 'create',
      hasTplSelected: Boolean(get(workflowTemplateCreating).template),
    }
  },
})
