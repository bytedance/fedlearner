import { I18nMessageModule, separateLng } from 'i18n/helpers'

const workflow: I18nMessageModule = {
  name: { zh: '工作流名称' },
  our_config: { zh: '我方配置' },
  ptcpt_permission: { zh: '合作伙伴编辑权限' },
  current_config: { zh: '当前配置' },
  create_workflow: { zh: '创建工作流', en: 'Create workflow' },

  action_re_run: { zh: '重新运行' },
  action_run: { zh: '立即运行' },
  action_stop_running: { zh: '停止运行' },
  action_duplicate: { zh: '复制' },
  action_detail: { zh: '详情' },

  btn_close: { zh: '关闭' },
  btn_conf_done: { zh: '配置完成' },
  btn_conf_next_step: { zh: '配置下一步（{{current}}/{{total}}）' },
  btn_see_ptcpt_config: { zh: '查看对方配置' },
  btn_send_2_ptcpt: { zh: '发送给合作伙伴' },

  col_status: { zh: '任务状态' },
  col_project: { zh: ' 隶属项目' },
  col_creator: { zh: ' 创建者' },
  col_date: { zh: ' 创建时间' },
  col_actions: { zh: '操作' },
  status_success: { zh: '成功' },
  status_failed: { zh: '失败' },
  status_running: { zh: '运行中' },
  status_pending: { zh: '待发送' },
  status_configuring: { zh: '合作伙伴配置中' },
  sent_failed: { zh: '发送失败' },
  sent_failed_desc: {
    zh: '与合作伙伴连接失败，失败原因，请检查连接状态成功后在工作流列表中重新发送',
  },
  override_warn: { zh: '重新运行将覆盖历史结果' },
  override_warn_desc: { zh: '是否确认重新运行当前工作流任务将覆盖历史运行结果？' },

  label_name: { zh: '工作流名称' },
  label_project: { zh: '关联项目' },
  label_peer_forkable: { zh: '合作伙伴复制权限' },
  label_template: { zh: '工作流模板' },
  label_allow: { zh: '允许' },
  label_not_allow: { zh: '不允许' },
  label_exist_template: { zh: '选择已有' },
  label_new_template: { zh: '新建模板' },
  label_new_template_name: { zh: '新建模板名称' },
  label_upload_template: { zh: '上传模板文件' },
  label_template_comment: { zh: '工作流模板说明' },

  placeholder_name_searchbox: { zh: '根据工作流名称搜索' },
  placeholder_name: { zh: '请输入工作流名称' },
  placeholder_template: { zh: '请选择模板' },
  placeholder_project: { zh: '请关联一个项目' },
  placeholder_comment: { zh: '请输入工作流模板说明' },
  placeholder_template_name: { zh: '请输入新建模板名称' },

  msg_sent_success: { zh: '工作流发送成功' },
  msg_template_required: { zh: '请选择一个模板！' },
  msg_get_template_failed: { zh: '获取模板列表失败' },
  msg_only_1_tpl: { zh: '只允许上传一个模板文件！' },
  msg_config_unfinished: { zh: '未完成配置，请先完成配置后再次点击发送' },
  msg_sure_2_cancel_create: { zh: '确认取消创建工作流？' },
  msg_sure_2_exist_create: { zh: '确定要离开吗，当前表单内容将全部丢失！' },
  msg_effect_of_cancel_create: { zh: '取消后，已配置内容将不再保留' },

  var_auth_write: { zh: '可编辑' },
  var_auth_read: { zh: '可见' },
  var_auth_private: { zh: '不可见' },

  step_basic: { zh: '基础配置' },
  step_config: { zh: '工作流配置' },

  job_node_pending: { zh: ' 待配置' },
  job_node_configuring: { zh: '配置中' },
  job_node_completed: { zh: '配置完成' },
  job_node_unfinished: { zh: '未完成配置' },
}

export default separateLng(workflow)
