import { isEmpty, clone } from 'lodash';
import { useMemo } from 'react';
import { Job } from 'typings/job';
import { NodeDataRaw } from './helpers';

export type JobColorsMark = 'blue' | 'green' | 'yellow' | 'magenta' | 'cyan';

const COLORS_POOL: JobColorsMark[] = ['blue', 'green', 'yellow', 'magenta', 'cyan'];

export function useMarkFederatedJobs() {
  const colorsPool = useMemo(() => clone(COLORS_POOL), []);
  const markedJobs = useMemo<Record<string, JobColorsMark>>(() => ({}), []);

  function markThem(jobs?: Array<NodeDataRaw | Job>, ...otherJobsArr: Array<NodeDataRaw | Job>[]) {
    if (!jobs) return;

    /**
     * Remember the Major premise for marking progress:
     * No matter how many workflows in the pairing, number of the federated jobs of each is exactly same,
     * thus we can know how many colors we using after mark first group of jobs
     */
    if (isEmpty(markedJobs)) {
      jobs.forEach((job: NodeDataRaw) => {
        if (job.is_federated) {
          const color = colorsPool.shift() || 'blue';

          markedJobs[job.name] = color;
          job.mark = color;
        }
      });
    } else {
      jobs.forEach((job: NodeDataRaw) => {
        if (job.is_federated) {
          job.mark = markedJobs[job.name];
        }
      });
    }

    // Recursivly mark jobs as long as you give them
    if (otherJobsArr && otherJobsArr.length) {
      markThem(...otherJobsArr);
    }
  }

  return { markedJobs, markThem };
}
