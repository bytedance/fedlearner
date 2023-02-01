import { separateLng } from 'i18n/helpers';

const trusted_center = {
  btn_create_trusted_computing: { zh: '创建可信计算', en: 'Create trusted computing' },
  btn_authorized: { zh: '授权', en: 'Authorized' },
  btn_unauthorized: { zh: '撤销', en: 'Unauthorized' },
  btn_submit_apply: { zh: '提交并申请', en: 'Submit and apply' },
  btn_confirm_authorization: { zh: '确认授权', en: 'Confirm authorization' },
  btn_submit_and_run: { zh: '提交并执行', en: 'Submit and run' },
  btn_cancel: { zh: '取消', en: 'Cancel' },
  btn_post_task: { zh: '发起任务', en: 'Post task' },
  btn_termination: { zh: '终止', en: 'termination' },
  btn_export: { zh: '导出', en: 'Export' },
  btn_pass: { zh: '通过', en: 'Pass' },
  btn_reject: { zh: '拒绝', en: 'Reject' },
  btn_go_back: { zh: '返回', en: 'Go back' },
  btn_inspect_logs: { zh: '查看日志', en: 'Inspect log' },

  label_trusted_center: { zh: '可信中心', en: 'Trusted Center' },
  label_coordinator_self: { zh: '本方', en: 'this party' },
  label_computing_name: { zh: '计算名称', en: 'Computing name' },
  label_description: { zh: '描述', en: 'Description' },
  label_algorithm_type: { zh: '算法类型', en: 'Algorithm Type' },
  label_algorithm_select: { zh: '选择算法', en: 'Algorithm select' },
  label_our_dataset: { zh: '我方数据集', en: 'Our dataset' },
  label_partner_one_dataset: { zh: '合作伙伴 1 数据集', en: 'Partner 1 dataset' },
  label_partner_two_dataset: { zh: '合作伙伴 2 数据集', en: 'Partner 2 dataset' },
  label_resource_template: { zh: '资源模板', en: 'Resource Template' },
  label_resource_config_params_detail: {
    zh: '资源配置参数详情',
    en: 'Resource config params detail',
  },
  label_trusted_job_comment: { zh: '任务备注', en: 'Trusted job comment' },

  placeholder_search_task: { zh: '输入任务名称', en: 'Enter task name' },
  placeholder_input: { zh: '请输入', en: 'Please Input' },
  placeholder_select: { zh: '请选择', en: 'Please select' },
  placeholder_select_algo_type: { zh: '请选择算法类型', en: 'Please select algorithm type' },
  placeholder_input_comment: { zh: '最多为200个字符', en: 'Maxsize 200 words' },
  placeholder_select_algo: { zh: '请选择算法', en: 'Please select algorithm' },
  placeholder_select_algo_version: { zh: '请选择算法版本', en: 'Please select algorithm version' },
  placeholder_select_dataset: {
    zh: '请选择一发布的原始/结果数据集',
    en: 'Please select released original/resulting dataset',
  },
  placeholder_trusted_job_set_comment: {
    zh: '支持1～100位可见字符，且只包含大小写字母、中文、数字、中划线、下划线',
    en:
      'Supports 1-100 visible characters, and only contains uppercase and lowercase letters, Chinese characters, numbers, underscores, and underscores',
  },

  title_trusted_job_create: { zh: '创建可信计算', en: 'Create trusted computing' },
  title_trusted_job_edit: { zh: '编辑可信计算', en: 'Edit trusted computing' },
  title_authorization_request: {
    zh: '{{peerName}}向您发起「{{name}}」可信计算申请',
    en: '{{peerName}} initiates a trusted computing authorization application for "{{name}}"',
  },
  title_base_info: { zh: '基本信息', en: 'Base info' },
  title_resource_config: { zh: '资源配置', en: 'Resource config' },
  title_computing_config: { zh: '计算配置', en: 'Computing config' },
  title_computing_task_list: { zh: '计算任务列表', en: 'Computing task list' },
  title_trusted_job_detail: { zh: '{{name}} 详情', en: '{{name}} Detail' },
  title_instance_info: { zh: '实例信息', en: 'Instance information' },
  title_todo_computing_tasks: { zh: '待处理计算任务', en: 'Pending computing job' },
  title_initiate_trusted_job: { zh: '发起任务 {{name}}', en: 'Initiate trusted job {{name}}' },
  title_edit_trusted_job: { zh: '编辑任务 {{name}}', en: 'Edit trusted job {{name}}' },
  title_dataset_export_application: {
    zh: '「{{name}}」 的导出申请',
    en: "「{{name}}」's export application ",
  },
  title_export_application: {
    zh: '数据集导出申请',
    en: 'Dataset export application',
  },
  title_passed: {
    zh: '已通过申请',
    en: 'Application passed',
  },
  title_rejected: {
    zh: '已拒绝申请',
    en: 'Application rejected',
  },
  title_status_tip: {
    zh: '{{second}}S 后自动返回',
    en: '{{second}} seconds later, automatically go back',
  },

  tip_agree_authorization: {
    zh: '授权后，发起方可以运行可信计算任务',
    en: 'After agreeing to the authorization, the applicant can run trusted computing job',
  },

  msg_required: { zh: '必填项', en: 'Required' },
  msg_trusted_computing_create: {
    zh: '合作伙伴均同意后，任务将自动运行，计算完成后的计算结果授权后才可以导出到本地',
    en:
      'After the partners agree, the task will run automatically, and the calculation results after the calculation is completed can be exported to the local machine after authorization.',
  },
  unauthorized_confirm_title: {
    zh: '确认撤销对「{{name}}」的授权？',
    en: 'Are you sure to unauthorized trusted computing "{{name}}" ?',
  },
  msg_todo_computing_tasks: { zh: '待处理计算任务 {{count}}' },
  msg_prefix_computing_tasks: { zh: '发起了', en: 'sent' },
  msg_suffix_computing_tasks: { zh: '的计算任务', en: "'s computing job" },
  msg_dataset_export_comment: {
    zh: '该数据集为可信中心安全计算生成的计算结果，导出时需各合作伙伴审批通过',
    en:
      "The dataset is the calculation result generated by the trusted center's secure calculation, and it needs the approval of each partner when exporting",
  },
  msg_create_success: { zh: '创建成功', en: 'Create success' },
  msg_auth_success: { zh: '授权成功', en: 'Authorize success' },
  msg_publish_success: { zh: '发布成功', en: 'Publish success' },
  msg_delete_success: { zh: '删除成功', en: 'Delete success' },
  msg_edit_success: { zh: '编辑成功', en: 'Edit success' },

  col_trusted_job_name: { zh: '名称', en: 'Name' },
  col_trusted_job_coordinator: { zh: '发起方', en: 'Coordinator' },
  col_trusted_job_status: { zh: '状态', en: 'Status' },
  col_job_status: { zh: '任务状态', en: 'Job status' },
  col_trusted_job_runtime: { zh: '运行时长', en: 'Runtime' },
  col_trusted_job_start_time: { zh: '开始时间', en: 'Start time' },
  col_trusted_job_end_time: { zh: '结束时间', en: 'End time' },
  col_trusted_job_create_at: { zh: '创建时间', en: 'Create time' },
  col_trusted_job_update_at: { zh: '更新时间', en: 'Update time' },
  col_trusted_job_creator: { zh: '创建人', en: 'Creator' },
  col_trusted_job_dataset: { zh: '数据集', en: 'Dataset' },
  col_trusted_job_operation: { zh: '操作', en: 'Operation' },
  col_trusted_job_comment: { zh: '备注', en: 'Comment' },
  col_instance_id: { zh: '实例 ID', en: 'Instance ID' },
  col_instance_status: { zh: '状态', en: 'Status' },
  col_instance_cpu: { zh: 'CPU', en: 'CPU' },
  col_instance_memory: { zh: 'MEM', en: 'MEM' },
  col_instance_start_at: { zh: '开始时间', en: 'Start time' },

  state_trusted_job_unknown: { zh: '未知', en: 'Unknown' },
  state_trusted_job_pending: { zh: '待执行', en: 'Pending' },
  state_trusted_job_running: { zh: '执行中', en: 'Running' },
  state_trusted_job_succeeded: { zh: '已成功', en: 'Succeeded' },
  state_trusted_job_failed: { zh: '已失败', en: 'Failed' },
  state_trusted_job_stopped: { zh: '已终止', en: 'Stopped' },

  state_auth_status_authorized: { zh: '已授权', en: 'Authorized' },
  state_auth_status_unauthorized: { zh: '未授权', en: 'Unathorized' },
};

export default separateLng(trusted_center);
