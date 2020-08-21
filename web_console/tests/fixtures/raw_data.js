module.exports = {
  name: 'raw-data-test',
  input: 'hdfs://open.aliyun.com/foo/bar',
  output: 'hdfs://open.aliyun.com/foo/bar',
  context: '{}',
  remark: 'raw-data-test comment',
  federation_id: 1,
  output_partition_num: 8,
  data_portal_type: 'Streaming',
};
