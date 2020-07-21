module.exports = {
  name: 'raw_data_TEST',
  input: 'hdfs://open.aliyun.com/foo/bar',
  output: 'hdfs://open.aliyun.com/foo/bar',
  context: '{}',
  remark: 'raw_data_TEST comment',
  federation_id: 1,
  output_partition_num: 8,
  data_portal_type: 'Streaming',
};
