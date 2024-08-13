import { normalAlgorithmProject } from 'services/mocks/v2/algorithm_projects/examples';

const get = () => {
  return {
    data: { data: normalAlgorithmProject },
    status: 200,
  };
};

export default get;
