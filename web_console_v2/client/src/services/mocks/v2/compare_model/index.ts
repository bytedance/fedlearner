const list = new Array(4).fill(undefined).map((_, index) => {
  return {
    id: index + 1,
    name: 'mock对比报告名称' + (index + 1),
    comment: '我是说明文案',
    compare_number: 5,
    extra: JSON.stringify({
      comment: '我是说明',
      creator: '测试员',
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
