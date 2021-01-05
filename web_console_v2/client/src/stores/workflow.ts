import { atom, selector } from 'recoil'
import { fetchWorkflowTemplateList } from 'services/workflow'
import { WorkflowForm, WorkflowTemplate, WorkflowTemplateForm } from 'typings/workflow'
import template from 'services/mocks/v2/workflow_templates/example'

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

    name: '',
    project_token: '',
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

// Template being used when creating workflow
export const currentWorkflowTemplate = atom<WorkflowTemplate>({
  key: 'CurrentWorkflowTemplate',
  default: template.data as WorkflowTemplate,
})

export const workflowGetters = selector({
  key: 'WorkflowGetters',
  get: ({ get }) => {
    return {
      whetherCreateNewTpl: get(workflowCreating)._templateType === 'create',
      hasTplSelected: Boolean(get(workflowTemplateCreating).template),

      // TODO: distinguish current creation is user side or participant side
      // isParticipantConfiguring: false
    }
  },
})

export const workflowConfigValue = atom({
  key: 'WorkflowConfigValue',
  default: {
    group_alias: '',
    jobs: [] as Array<{}>,
  },
})
