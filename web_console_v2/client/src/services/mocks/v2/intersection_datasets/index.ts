import { readyToRun, invalid, running, completed, stopped, failed } from './examples';

const get = {
  data: {
    data: [running, completed, stopped, failed, readyToRun, invalid],
  },
  status: 200,
};

export default get;
