import { separateLng } from 'i18n/helpers';

const intersection_dataset = {
  status: { zh: '状态' },
  no_result: { zh: '暂无数据集' },

  col_name: { zh: '名称' },
  col_status: { zh: '求交状态' },
  col_job_name: { zh: '求交任务' },
  col_peer_name: { zh: '求交参与方' },
  col_sample_num: { zh: '数据集样本量' },
  col_sample_filesize: { zh: '数据集大小' },
  col_files_size: { zh: '文件大小' },
  col_num_example: { zh: '数据集样本量' },
};

export default separateLng(intersection_dataset);
