const project_list = new Array(5).fill(undefined).map((_, index) => {
  return {
    id: index + 1,
    name: `Project-${index + 1}`,
    token: '51aa8b39a5444f24ae7e403ac7f6029c',
    config: {
      token: '51aa8b39a5444f24ae7e403ac7f6029c',
      participants: [
        {
          name: `合作方-${index + 1}`,
          domain_name: 'fl-test.com',
          url: '127.0.0.1:32443',
        },
      ],
      variables: [
        {
          name: 'testkey',
          value: 'testval',
        },
      ],
    },
    comment: 'comment here',
    created_at: 1608582145,
    updated_at: 1608582145,
    deleted_at: null,
    num_workflow: ~~(Math.random() * 10),
  };
});

const get = {
  data: {
    data: project_list,
  },
  status: 200,
};

export const post = (config: any) => {
  return { data: { data: config.data }, status: 200 };
};

export default get;
