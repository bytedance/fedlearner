import { separateLng } from 'i18n/helpers';

const audit = {
  title_event_record: { zh: '事件记录', en: 'Event record' },
  title_event_detail: { zh: '事件详情', en: 'Event detail' },
  title_base_info: { zh: '基础信息', en: 'Base info' },
  title_request_info: { zh: '请求信息', en: 'Request info' },

  tip_event_record: {
    zh: '以下列表最长展示过去9个月的事件记录',
    en: 'The following list shows up to the past 9 months of event records',
  },

  col_event_time: { zh: '事件时间', en: 'Event time' },
  col_user_name: { zh: '用户名', en: 'User name' },
  col_event_name: { zh: '事件名称', en: 'Event name' },
  col_resource_type: { zh: '资源类型', en: 'Resource type' },
  col_resource_name: { zh: '资源名称', en: 'Resource name' },

  placeholder_search: { zh: '搜索关键词', en: 'Search keyword' },

  radio_label_all: { zh: '全部', en: 'All' },
  radio_label_one_week: { zh: '近7天', en: 'Nearly 7 days' },
  radio_label_one_month: { zh: '近1月', en: 'Nearly 1 month' },
  radio_label_three_months: { zh: '近3月', en: 'Nearly 3 months' },

  btn_delete: { zh: '删除6个月前的记录', en: 'Delete records from 6 months ago' },

  label_event_id: { zh: '事件ID', en: 'Event ID' },
  label_event_time: { zh: '事件时间', en: 'Event time' },
  label_event_name: { zh: '事件名称', en: 'Event name' },
  label_user_name: { zh: '用户名', en: 'User name' },
  label_operation_name: { zh: '操作名称', en: 'Operation name' },

  label_request_id: { zh: '请求ID', en: 'Request ID' },
  label_access_key_id: { zh: 'AccessKey ID', en: 'AccessKey ID' },
  label_event_result: { zh: '事件结果', en: 'Event result' },
  label_error_code: { zh: '错误码', en: 'Error code' },
  label_resource_type: { zh: '资源类型', en: 'Resource type' },
  label_resource_name: { zh: '资源名称', en: 'Resource name' },
  label_original_ip_address: { zh: '源IP地址', en: 'Source ip address' },
  label_extra_info: { zh: '额外信息', en: 'Extra info' },

  msg_title_confirm_delete: { zh: '确定要删除吗？', en: 'You sure you want to delete it?' },
  msg_content_confirm_delete: {
    zh: '基于安全审核的原因，平台仅支持清理6个月前的事件记录',
    en:
      'Due to security audit reasons, the platform only supports cleaning up the event records 6 months ago',
  },
  msg_delete_success: { zh: '删除成功', en: 'Delete success' },
};

export default separateLng(audit);
