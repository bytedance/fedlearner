import { NodeDataRaw } from 'components/WorkflowJobsFlowChart/types';
import { atom, selector } from 'recoil';
import {
  Workflow,
  WorkflowConfig,
  WorkflowForkPayload,
  WorkflowInitiatePayload,
  WorkflowTemplate,
  WorkflowTemplatePayload,
} from 'typings/workflow';

export type CreateWorkflowBasicForm = {
  _templateType: 'existing' | 'create';
  _templateSelected?: string;
} & Partial<Pick<WorkflowInitiatePayload, 'name' | 'forkable' | 'project_id'>>;

export type CreateTemplateForm = WorkflowTemplatePayload;

export const workflowBasicForm = atom<CreateWorkflowBasicForm>({
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

export const workflowConfigForm = atom<WorkflowConfig<NodeDataRaw>>({
  key: 'WorkflowConfigForm',
  default: {
    group_alias: '',
    variables: [],
    job_definitions: [],
  } as any,
});

export const workflowTemplateForm = atom<CreateTemplateForm>({
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

export const forkWorkflowForm = atom<WorkflowForkPayload>({
  key: 'ForkWorkflowBasicForm',
  default: {
    name: '',
    project_id: '',
    forkable: true,
    config: null as any,
    fork_proposal_config: null as any,
    comment: '',
    forked_from: '',
    reuse_job_names: [],
    peer_reuse_job_names: [],
  },
});
