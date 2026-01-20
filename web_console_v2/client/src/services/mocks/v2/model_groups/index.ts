const list = new Array(3).fill(undefined).map((_, index) => {
  return {
    id: index + 1,

    name: 'mock模型集' + (index + 1),
    comment: '我是说明',
    extra: JSON.stringify({
      name: 'mock模型集' + (index + 1),
      comment: '我是说明',
      creator: '测试员',
      project_id: 14,
    }),

    created_at: 1608582145,
    updated_at: 1608582145,
    deleted_at: 1608582145,
  };
});

const get = {
  data: {
    data: list,
  },
  status: 200,
};

export const post = (config: any) => {
  return { data: { data: config.data }, status: 200 };
};

export default get;
