import { separateLng } from 'i18n/helpers';

const operation_maintenance = {
  btn_submit: { zh: '提交', en: 'Submit' },
  btn_reset: { zh: '重置', en: 'Reset' },

  col_job_name: { zh: 'K8s Job名称', en: 'job_name' },
  col_job_type: { zh: '测试类型', en: 'job_type' },
  col_operation: { zh: '测试状态', en: 'Operation' },

  job_detail: { zh: '工作详情', en: 'job_detail' },

  state_check_success: { zh: '校验成功', en: 'Success' },
  state_check_fail: { zh: '校验不通过', en: 'Fail' },
  state_check_repeat: { zh: '工作已存在，请更改name_prefix字段', en: 'Repeat' },
};

export default separateLng(operation_maintenance);
