const list = new Array(4).fill(undefined).map((_, index) => {
  return {
    id: index + 1,
    name: 'mock评估任务名称' + (index + 1),
    state: Math.floor(Math.random() * 3),
    dataset: 'test-dataset',
    dataset_id: 109,
    comment: '我是说明文案',
    modelList: ['Xgbootst-v8', 'Xgbootst-v7', 'Xgbootst-v6'],
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
