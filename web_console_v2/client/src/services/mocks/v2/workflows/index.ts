import { AxiosRequestConfig } from 'axios';
import { Workflow } from 'typings/workflow';
import { newlyCreated, pendingAcceptAndConfig, completed } from './examples';

const list: Workflow[] = [pendingAcceptAndConfig, newlyCreated, completed];

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
