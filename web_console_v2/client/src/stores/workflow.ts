import { atom, selector } from 'recoil';
import {
  Workflow,
  WorkflowConfig,
  WorkflowInitiatePayload,
  WorkflowTemplate,
  WorkflowTemplatePayload,
} from 'typings/workflow';

export type StepOneForm = {
  _templateType: 'existing' | 'create';
  _templateSelected?: string;
} & Partial<Pick<WorkflowInitiatePayload, 'name' | 'forkable' | 'project_id'>>;

export type StepOneTemplateForm = WorkflowTemplatePayload;

export const workflowBasicForm = atom<StepOneForm>({
  key: 'WorkflowBasicForm',
  default: {
    // Fields start with underscore are solely UI releated things,
    // will not pass to backend on submit
    _templateType: 'existing' as const,
    _templateSelected: undefined,

    name: '',
    project_id: undefined,
    forkable: true,
  },
});

export const workflowConfigForm = atom<WorkflowConfig>({
  key: 'WorkflowConfigForm',
  default: {
    group_alias: '',
    variables: [],
    job_definitions: [],
  } as any,
});

export const workflowTemplateForm = atom<StepOneTemplateForm>({
  key: 'WorkflowTemplateForm',
  default: { name: '', config: '', comment: '' } as any,
});

export const workflowInEditing = atom<Workflow>({
  key: 'WorkflowInEditing',
  default: (null as unknown) as Workflow,
});

export const peerConfigInPairing = atom<WorkflowConfig>({
  key: 'PeerConfigInPairing',
  default: (null as unknown) as WorkflowConfig,
});

// Template being used when creating workflow
export const templateInUsing = atom<WorkflowTemplate>({
  key: 'templateInUsing',
  default: null as any,
});

export const workflowGetters = selector({
  key: 'WorkflowGetters',
  get: ({ get }) => {
    return {
      whetherCreateNewTpl: get(workflowBasicForm)._templateType === 'create',
      hasTplSelected: Boolean(get(workflowTemplateForm).config),
    };
  },
});
