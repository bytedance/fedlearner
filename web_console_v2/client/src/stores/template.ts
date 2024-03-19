import { Perspective } from './../views/WorkflowTemplates/TemplateConfig/JobComposeDrawer/DefaultMode/index';
import { JobColorsMark } from 'components/WorkflowJobsCanvas/types';
import { atom } from 'recoil';
import { giveWeakRandomKey } from 'shared/helpers';
import { JobDependency } from 'typings/job';
import { WorkflowTemplateType } from 'typings/workflow';

export type JobNodeRawDataSlim = {
  uuid: string;
  mark?: JobColorsMark;
  dependencies: JobDependency[];
};

export type WorkflowTemplateForm = {
  id: number;
  revision_id?: number;
  name: string;
  is_local?: boolean;
  group_alias: string;
  comment?: string;
  creator_username?: string;
  updated_at?: number;
  created_at?: number;
  /**
   * The values of config is actually inside ../store.ts (with Map<uuid, values> struct) not on recoil,
   * here we only keep datas minimum-required for rendering template flow chart:
   *  1. variables is an empty array which is just a placeholder
   *  2. each job_definition with a uuid and dependencies<{ source: uuid }>
   */
  config: {
    variables: never[];
    job_definitions: JobNodeRawDataSlim[];
  };
  kind: WorkflowTemplateType;
};

export const jobComposeDrawerState = atom({
  key: 'JobComposeDrawerState',
  default: {
    isGLobal: false,
    perspective: Perspective.Slots,
  },
});

export const defaultTemplateForm: WorkflowTemplateForm = {
  id: 0,
  revision_id: 0,
  name: '',
  is_local: false,
  group_alias: '',
  config: {
    variables: [],
    job_definitions: [
      // Give an initial empty job node
      {
        uuid: giveWeakRandomKey(),
        dependencies: [],
      },
    ],
  },
  creator_username: '',
  updated_at: 0,
  created_at: 0,
  comment: '',
  kind: WorkflowTemplateType.MY,
};

export const templateForm = atom<WorkflowTemplateForm>({
  key: 'WorkflowTemplateForm',
  default: {
    id: 0,
    revision_id: 0,
    name: '',
    is_local: false,
    group_alias: '',
    config: {
      variables: [],
      job_definitions: [
        // Give an initial empty job node
        {
          uuid: giveWeakRandomKey(),
          dependencies: [],
        },
      ],
    },
    creator_username: '',
    updated_at: 0,
    created_at: 0,
    comment: '',
    kind: WorkflowTemplateType.MY,
  },
});

export type baseInfoForm = {
  name: string;
  group_alias: string;
  comment?: string;
};

export const defaultBaseInfoForm: baseInfoForm = {
  name: '',
  group_alias: '',
  comment: '',
};

export const templateBaseInfoForm = atom<baseInfoForm>({
  key: 'templateBaseInfoForm',
  default: {
    name: '',
    group_alias: '',
    comment: '',
  },
});
