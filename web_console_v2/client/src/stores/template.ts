import { JobColorsMark } from 'components/WorkflowJobsCanvas/types';
import { atom } from 'recoil';
import { giveWeakRandomKey } from 'shared/helpers';
import { JobDependency } from 'typings/job';

export type JobNodeRawDataSlim = {
  uuid: string;
  mark?: JobColorsMark;
  dependencies: JobDependency[];
};

export type WorkflowTemplateForm = {
  id?: ID;
  name: string;
  is_left: boolean;
  group_alias: string;
  comment?: string;
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
};

export const templateForm = atom<WorkflowTemplateForm>({
  key: 'WorkflowTemplateForm',
  default: {
    name: '',
    is_left: true,
    group_alias: '',
    config: {
      variables: [],
      job_definitions: [
        {
          uuid: giveWeakRandomKey(),
          dependencies: [],
        },
      ],
    },
    comment: '',
  },
});
