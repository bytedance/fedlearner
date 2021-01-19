import { Workflow } from 'typings/workflow';
import { newlyCreated, awaitParticipantConfig } from './example';

const list: Workflow[] = [awaitParticipantConfig, newlyCreated];

export const get = {
  data: {
    data: list,
  },
  status: 200,
};

export default get;
