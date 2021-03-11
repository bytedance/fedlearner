import { JobColorsMark } from 'components/WorkflowJobsCanvas/types';
import { atom } from 'recoil';
import { giveWeakRandomKey } from 'shared/helpers';
import { JobDependency } from 'typings/job';
import { Variable } from 'typings/variable';

export type JobNodeRawDataSlim = {
  uuid: string;
  mark?: JobColorsMark;
  dependencies: JobDependency[];
};

export type WorkflowTemplateForm = {
  name: string;
  is_left: boolean;
  group_alias: string;
  comment: string;
  config: {
    variables: Variable[];
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
