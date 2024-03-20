import { cloneDeep } from 'lodash';
import { JobState } from 'typings/job';
import { newlyCreated, withExecutionDetail } from '../examples';

const get = () => {
  const modified = cloneDeep(withExecutionDetail);

  modified.jobs[1].state = JobState.COMPLETED;
  modified.jobs[2].state = JobState.STARTED;

  return {
    data: {
      data: { peer_1: modified || newlyCreated },
    },
    status: 200,
  };
};

export default get;
