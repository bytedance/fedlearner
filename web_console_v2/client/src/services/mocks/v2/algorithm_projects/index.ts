import { normalAlgorithmProject } from 'services/mocks/v2/algorithm_projects/examples';

const get = {
  data: {
    data: [normalAlgorithmProject],
  },
  status: 200,
};

export const post = (config: any) => {
  return { data: { data: config.data }, status: 200 };
};

export default get;
