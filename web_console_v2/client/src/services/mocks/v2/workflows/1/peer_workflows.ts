import { cloneDeep } from 'lodash';
import { JobState } from 'typings/job';
import { newlyCreated, withExecutionDetail } from '../example';

const get = () => {
  const modified = cloneDeep(withExecutionDetail);

  modified.jobs[1].state = JobState.COMPLETE;
  modified.jobs[2].state = JobState.RUNNING;

  return {
    data: {
      data: { peer_1: modified || newlyCreated },
    },
    status: 200,
  };
};

export default get;
