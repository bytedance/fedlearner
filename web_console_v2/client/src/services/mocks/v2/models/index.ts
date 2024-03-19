import { Model } from 'typings/modelCenter';

const modelList: Model[] = [
  {
    id: 7,
    name: 'ucce42a49cbff4c4e930-nn-train-20210927-124432-3bd1a',
    uuid: 'u3a0507d64bc442a2b66',
    model_type: 'NN_MODEL',
    model_path:
      'hdfs:///trimmed',
    favorite: false,
    comment: 'created_by ucce42a49cbff4c4e930-nn-train at 2021-09-27 12:44:32.419496+00:00',
    group_id: null,
    project_id: 14,
    job_id: 42877,
    model_job_id: null,
    version: null,
    created_at: 1632746672,
    updated_at: 1632746672,
    deleted_at: null,
    workflow_id: 153952,
    workflow_name: 'test-workflow',
    job_name: 'test-job',
    model_job_name: 'test-model-job',
    federated_type: '',
  },
  {
    id: 8,
    name: 'ucce42a49cbff4c4e930-nn-train-20210927-124437-3748d',
    uuid: 'u195c5a39d1e44804a1a',
    model_type: 'NN_MODEL',
    model_path:
      'hdfs:///trimmed',
    favorite: false,
    comment: 'created_by ucce42a49cbff4c4e930-nn-train at 2021-09-27 12:44:37.030088+00:00',
    group_id: null,
    project_id: 14,
    job_id: 42877,
    model_job_id: null,
    version: null,
    created_at: 1632746677,
    updated_at: 1632746677,
    deleted_at: null,
    workflow_id: 153952,
    workflow_name: 'test-workflow',
    job_name: 'test-job',
    model_job_name: 'test-model-job',
    federated_type: '',
  },
  {
    id: 86,
    name: 'ud8b9cb500fc3435cb66-nn-train-20211009-070848-7c28f',
    uuid: 'u70ca285687eb4d2fbb0',
    model_type: 'NN_MODEL',
    model_path:
      'hdfs:///trimmed',
    favorite: false,
    comment: 'created_by ud8b9cb500fc3435cb66-nn-train at 2021-10-09 07:08:48.729397+00:00',
    group_id: 1,
    project_id: 14,
    job_id: null,
    model_job_id: 1,
    version: null,
    created_at: 1633763328,
    updated_at: 1633763328,
    deleted_at: null,
    workflow_id: 153952,
    workflow_name: 'test-workflow',
    job_name: 'test-job',
    model_job_name: 'test-model-job',
    federated_type: '',
  },
  {
    id: 87,
    name: 'ud8b9cb500fc3435cb66-nn-train-20211009-070856-6ca71',
    uuid: 'u4b6e82b75e644c90907',
    model_type: 'NN_MODEL',
    model_path:
      'hdfs:///trimmed',
    favorite: false,
    comment: 'created_by ud8b9cb500fc3435cb66-nn-train at 2021-10-09 07:08:56.799515+00:00',
    group_id: 2,
    project_id: 14,
    job_id: null,
    model_job_id: 2,
    version: null,
    created_at: 1633763336,
    updated_at: 1633763336,
    deleted_at: null,
    workflow_id: 153952,
    workflow_name: 'test-workflow',
    job_name: 'test-job',
    model_job_name: 'test-model-job',
    federated_type: '',
  },
];

const get = {
  data: {
    data: modelList,
  },
  status: 200,
};

export const post = (config: any) => {
  return { data: { data: config.data }, status: 200 };
};

export default get;
