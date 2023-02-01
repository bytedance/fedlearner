import { DataSource } from 'typings/dataset';

const list: DataSource[] = [
  {
    id: 1,
    uuid: 'uxbuxa',
    type: 'hdfs',
    name: 'mock数据源1',
    created_at: 1608582145,
    url: 'hdfs://hadoop-master:9000/user/hadoop/test.csv',
    project_id: 1,
    dataset_format: 'TABULAR',
    dataset_type: 'STREAMING',
    store_format: 'TFRECORDS',
  },
  {
    id: 2,
    uuid: 'uxbusxa',
    type: 'hdfs',
    name: 'mock数据源2',
    created_at: 1609582145,
    url:
      'hdfs://home/byte_aml_tob/fedlearner_v2/dataset/20220218_141000_e2e-test-dataset-20220218-060927',
    project_id: 1,
    dataset_format: 'TABULAR',
    dataset_type: 'STREAMING',
    store_format: 'TFRECORDS',
  },
  {
    id: 3,
    uuid: 'uxbusxa',
    type: 'http',
    name: 'mock数据源3',
    created_at: 1610582145,
    url: 'http://www.baidu.com',
    project_id: 1,
    dataset_format: 'TABULAR',
    dataset_type: 'STREAMING',
    store_format: 'TFRECORDS',
  },
];

const get = {
  data: {
    data: list,
  },
  status: 200,
};

export const post = {
  data: {
    data: undefined,
  },
  status: 201,
};

export default get;
