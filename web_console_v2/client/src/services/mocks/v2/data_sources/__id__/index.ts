import { AxiosRequestConfig } from 'axios';

const get = () => ({
  data: {
    data: {
      id: 1,
      type: 'hdfs',
      name: 'mock数据源1',
      created_at: 1608582145,
      url: 'hdfs://hadoop-master:9000/user/hadoop/test.csv',
    },
  },
  status: 200,
});

export const DELETE = (config: AxiosRequestConfig) => {
  return {
    data: '',
    status: 204,
  };
};

export default get;
