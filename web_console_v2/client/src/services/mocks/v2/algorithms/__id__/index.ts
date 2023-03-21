import { AxiosRequestConfig } from 'axios';

const get = (config: AxiosRequestConfig) => {
  return {
    data: {
      data: {
        id: config._id,
        uuid: 'udea6a8a478404f85b17',
        name: 'hang-e2e-test-122323',
        project_id: 31,
        version: 3,
        type: 'NN_VERTICAL',
        source: 'USER',
        algorithm_project_id: 73,
        username: 'admin',
        participant_id: null,
        path:
          'hdfs:///trimmed',
        parameter: {
          variables: [
            {
              name: 'lr',
              value: '0.1',
              required: true,
              display_name: '',
              comment: '',
              value_type: 'STRING',
            },
          ],
        },
        favorite: false,
        comment: 'aaa',
        created_at: 1641463720,
        updated_at: 1649310452,
        deleted_at: null,
        participant_name: null,
      },
    },
    status: config._id === 110 ? 500 : 200,
  };
};

export default get;
