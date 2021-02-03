import { AxiosRequestConfig } from 'axios';

const get = (config: AxiosRequestConfig) => ({
  data: {
    data: {
      id: config._id,
      name: 'Foo project',
      token: '51aa8b39a5444f24ae7e403ac7f6029c',
      config: {
        token: '51aa8b39a5444f24ae7e403ac7f6029c',
        participants: [
          {
            name: 'name',
            domain_name: 'fl-test.com',
            url: '127.0.0.1:32443',
          },
        ],
        variables: [
          {
            name: 'test',
            value: 'test',
          },
        ],
      },
      comment: '3',
      created_at: 1608582145.0,
      updated_at: 1608582145.0,
      deleted_at: null,
    },
  },
  status: 200,
});

export const patch = { data: {}, status: 200 };

export default get;
