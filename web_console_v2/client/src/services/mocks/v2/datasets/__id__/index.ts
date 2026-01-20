import { AxiosRequestConfig } from 'axios';

import { unfinishedImporting } from '../examples';

const get = () => ({
  data: {
    data: unfinishedImporting,
  },
  status: 200,
});

export const DELETE = (config: AxiosRequestConfig) => {
  const datasetId = config._id as string;

  return Math.random() > 0.5
    ? {
        // Delete success
        data: '',
        status: 204,
      }
    : {
        // Delete fail
        data: {
          code: 409,
          message: {
            [datasetId]: [`The dataset ${datasetId} is being processed`],
          },
        },
        status: 409,
      };
};

export default get;
