import { unfinishedImporting, importFailed, successfullyImport } from './examples';

const get = {
  data: {
    data: [unfinishedImporting, importFailed, successfullyImport],
  },
  status: 200,
};

export const post = {
  data: {
    data: unfinishedImporting,
  },
  status: 200,
};

export default get;
