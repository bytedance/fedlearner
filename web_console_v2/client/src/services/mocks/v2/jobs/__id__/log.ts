let offset = 0;

const get = (config: any) => {
  offset += 1;
  return {
    data: {
      data: Array(config.params.max_lines)
        .fill(null)
        .map((_, index) => index + offset),
    },
    status: 200,
  };
};

export default get;
