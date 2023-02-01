import { JobNodeRawData } from 'components/WorkflowJobsCanvas/types';
import { atom, selector } from 'recoil';
import { CreateJobFlag } from 'typings/job';
import {
  WorkflowExecutionDetails,
  WorkflowConfig,
  WorkflowForkPayload,
  WorkflowInitiatePayload,
  WorkflowTemplate,
  WorkflowTemplatePayload,
} from 'typings/workflow';

export type CreateWorkflowBasicForm = {
  _templateSelected?: string;
  _revisionSelected?: string;
  _keepUsingOriginalTemplate?: boolean;
} & Partial<Pick<WorkflowInitiatePayload, 'name' | 'forkable' | 'project_id' | 'cron_config'>>;

export type CreateTemplateForm = WorkflowTemplatePayload;

export const workflowBasicForm = atom<CreateWorkflowBasicForm>({
  key: 'WorkflowBasicForm',
  default: {
    // Fields start with underscore are solely UI releated things,
    // will not pass to backend on submit
    _templateSelected: undefined,
    _revisionSelected: undefined,
    _keepUsingOriginalTemplate: true,

    name: '',
    project_id: undefined,
    forkable: true,
    cron_config: '',
  },
});

export const workflowConfigForm = atom<WorkflowConfig<JobNodeRawData>>({
  key: 'WorkflowConfigForm',
  default: {
    /** initial value is undefined so we can tell the UI back to step one */
    group_alias: undefined,
    variables: [],
    job_definitions: [],
  } as any,
});

// NOTE: this atom only been used in Workflow Create/Accept,
// DO NOT IMPORT it in template upsert flow
export const workflowTemplateForm = atom<CreateTemplateForm>({
  key: 'WorkflowCreateTemplateForm',
  default: { name: '', config: '', comment: '' } as any,
});

export const workflowInEditing = atom<WorkflowExecutionDetails>({
  key: 'WorkflowInEditing',
  default: (null as unknown) as WorkflowExecutionDetails,
});

export const peerConfigInPairing = atom<WorkflowConfig>({
  key: 'PeerConfigInPairing',
  default: (null as unknown) as WorkflowConfig,
});

// Template being used when creating workflow
export const templateInUsing = atom<WorkflowTemplate>({
  key: 'TemplateInUsing',
  default: null as any,
});

export const workflowGetters = selector({
  key: 'WorkflowGetters',
  get: ({ get }) => {
    return {
      hasTplSelected: Boolean(get(workflowTemplateForm).config),
    };
  },
});

export const forkWorkflowForm = atom<WorkflowForkPayload>({
  key: 'ForkWorkflowBasicForm',
  default: {
    name: '',
    project_id: '',
    is_local: false,
    forkable: true,
    config: null as any,
    fork_proposal_config: null as any,
    comment: '',
    forked_from: '',
    create_job_flags: [] as CreateJobFlag[],
    peer_create_job_flags: [] as CreateJobFlag[],
    template_id: undefined,
  },
});
