import { atom, selector } from 'recoil';
import {
  Workflow,
  WorkflowConfig,
  WorkflowInitiatePayload,
  WorkflowTemplate,
  WorkflowTemplatePayload,
} from 'typings/workflow';
import { parseWidgetSchemas } from 'shared/formSchema';

export type StepOneForm = {
  _templateType: 'existing' | 'create';
  _templateSelected?: string;
} & Partial<Pick<WorkflowInitiatePayload, 'name' | 'forkable' | 'project_id'>>;

export type StepOneTemplateForm = WorkflowTemplatePayload;

export const DEFAULT_BASIC_VALUES = {
  // Fields start with underscore are solely UI releated things,
  // will not pass to backend on submit
  _templateType: 'existing' as const,
  _templateSelected: undefined,

  name: '',
  project_id: undefined,
  forkable: true,
};
export const workflowBasicForm = atom<StepOneForm>({
  key: 'WorkflowBasicForm',
  default: DEFAULT_BASIC_VALUES,
});

export const DEFAULT_JOBS_CONFIG_VALUES = ({
  group_alias: '',
  job_definitions: [],
} as any) as WorkflowConfig;
export const workflowJobsConfigForm = atom<WorkflowConfig>({
  key: 'WorkflowJobsConfigForm',
  default: DEFAULT_JOBS_CONFIG_VALUES,
});

export const DEFAULT_TEMPLATE_VALUES = {
  name: '',
  config: '',
  comment: '',
};
export const workflowTemplateForm = atom<StepOneTemplateForm>({
  key: 'WorkflowTemplateForm',
  default: DEFAULT_TEMPLATE_VALUES,
});

export const workflowInEditing = atom<Workflow>({
  key: 'WorkflowInEditing',
  default: (null as unknown) as Workflow,
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
      currentWorkflowTpl: get(templateInUsing) && parseWidgetSchemas(get(templateInUsing)),
    };
  },
});
