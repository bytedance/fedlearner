import { unfinishImporting, importFailed } from './examples';

const get = {
  data: {
    data: [unfinishImporting, importFailed],
  },
  status: 200,
};

export const post = {
  data: {
    data: unfinishImporting,
  },
  status: 200,
};

export default get;
