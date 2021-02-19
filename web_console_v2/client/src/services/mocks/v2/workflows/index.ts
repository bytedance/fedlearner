import { AxiosRequestConfig } from 'axios';
import { Workflow } from 'typings/workflow';
import { newlyCreated, awaitParticipantConfig, completed } from './examples';

const list: Workflow[] = [awaitParticipantConfig, newlyCreated, completed];

export const get = {
  data: {
    data: list,
  },
  status: 200,
};

export const post = (config: AxiosRequestConfig) => {
  return {
    data: {
      data: config.data,
    },
    status: 200,
  };
};

export default get;
