import { unfinishedImporting, importFailed } from '../examples';

const get = {
  data: {
    data: [unfinishedImporting, importFailed],
  },
  status: 200,
};

export const DELETE = {
  data: {
    data: unfinishedImporting,
  },
  status: 200,
};

export default get;
