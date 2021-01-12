import { atom, selector } from 'recoil'
import { fetchWorkflowTemplateList } from 'services/workflow'
import {
  WorkflowConfig,
  WorkflowInitiatePayload,
  WorkflowTemplate,
  WorkflowTemplatePayload,
} from 'typings/workflow'
import tpls from 'services/mocks/v2/workflow_templates'
import { parseWidgetSchemas } from 'shared/formSchema'

export type StepOneForm = {
  _templateType: 'existing' | 'create'
  _templateSelected?: string
} & Partial<Pick<WorkflowInitiatePayload, 'name' | 'forkable' | 'project_id'>>

export type StepOneTemplateForm = {
  _files: File[]
} & WorkflowTemplatePayload

export const workflowBasicForm = atom<StepOneForm>({
  key: 'WorkflowBasicForm',
  default: {
    // Fields start with underscore are solely UI releated things,
    // will not pass to backend on submit
    _templateType: 'existing',
    _templateSelected: undefined,

    name: '',
    project_id: undefined,
    forkable: true,
  },
})

export const workflowJobsConfigForm = atom<WorkflowConfig>({
  key: 'WorkflowJobsConfigForm',
  default: {
    group_alias: '',
    job_definitions: [],
  } as any,
})

export const workflowTemplateForm = atom<StepOneTemplateForm>({
  key: 'WorkflowTemplateForm',
  default: {
    _files: [],

    name: '',
    config: '',
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
      return res.data.data
    } catch (error) {
      throw error
    }
  },
})

// Template being used when creating workflow
export const currentWorkflowTemplate = atom<WorkflowTemplate>({
  key: 'CurrentWorkflowTemplate',
  default: tpls.data.data[0] as any,
})

export const workflowGetters = selector({
  key: 'WorkflowGetters',
  get: ({ get }) => {
    return {
      whetherCreateNewTpl: get(workflowBasicForm)._templateType === 'create',
      hasTplSelected: Boolean(get(workflowTemplateForm).config),
      currentWorkflowTpl: parseWidgetSchemas(get(currentWorkflowTemplate)),

      // TODO: distinguish current creation is user side or participant side
      // isParticipantConfiguring: false
    }
  },
})
